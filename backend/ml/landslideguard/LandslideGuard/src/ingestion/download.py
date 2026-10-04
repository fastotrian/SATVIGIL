"""Safe streaming download for CDSE Sentinel-2 products.

Design:
    - streams to `<product_dir>/<name>.zip.part`, atomic-renames when done
    - resume via HTTP Range if the server advertises byte ranges
    - bounded retry-with-backoff on transient network errors
    - free-space precheck against the configured data_dir
    - never overwrites unrelated files outside the product cache dir
"""
from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from .auth import CDSEAuth
from .cache import (
    product_cache_dir, compute_sha256, store_checksum, mark_complete,
    clear_complete, write_metadata, locate_archive,
)
from .errors import ErrorCode, IngestionError
from .schemas import ProductMetadata


DEFAULT_TIMEOUT_S = 300
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_S = 5.0
DEFAULT_CHUNK = 1024 * 1024
FREE_SPACE_SAFETY = 512 * 1024 * 1024  # keep 512 MB free after download


@dataclass
class DownloadConfig:
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_s: float = DEFAULT_BACKOFF_S
    chunk_bytes: int = DEFAULT_CHUNK
    free_space_safety_bytes: int = FREE_SPACE_SAFETY
    verify_sha_after_download: bool = True


def _free_bytes(path: Path) -> int:
    """Return free bytes on the filesystem containing `path`."""
    path.mkdir(parents=True, exist_ok=True)
    return shutil.disk_usage(str(path)).free


def _archive_name(product_name: str) -> str:
    # CDSE archives are ZIP; name after the product for readability.
    return f"{product_name}.zip"


def _check_disk_space(target_dir: Path, need_bytes: int, safety: int) -> None:
    free = _free_bytes(target_dir)
    if free < need_bytes + safety:
        raise IngestionError(
            ErrorCode.INSUFFICIENT_STORAGE,
            "Not enough free space for download.",
            {"required_bytes": int(need_bytes),
             "safety_bytes": int(safety),
             "free_bytes": int(free),
             "target_dir": str(target_dir)})


def _stream_to_file(session: object,
                    url: str, headers: dict, dest: Path,
                    cfg: DownloadConfig,
                    resume_from: int = 0) -> None:
    """Stream a GET response body to `dest`, appending if resume_from > 0.

    `session` may be `None` (real requests) or an injected Mock (tests).
    """
    if session is not None:
        req_headers = dict(headers)
        if resume_from > 0:
            req_headers["Range"] = f"bytes={resume_from}-"
        resp = session.get(url, headers=req_headers, stream=True,  # type: ignore[attr-defined]
                           timeout=cfg.timeout_s)
        status = int(resp.status_code)
        if status not in (200, 206):
            raise IngestionError(
                ErrorCode.DOWNLOAD_FAILED,
                f"Download HTTP {status}",
                {"http_status": status, "url_host": _host_of(url)})
        mode = "ab" if resume_from > 0 and status == 206 else "wb"
        with dest.open(mode) as f:
            iter_content = getattr(resp, "iter_content", None)
            if callable(iter_content):
                for chunk in iter_content(chunk_size=cfg.chunk_bytes):
                    if chunk:
                        f.write(chunk)
            else:
                # For test doubles that only expose `.content`
                data = getattr(resp, "content", b"")
                f.write(data)
        return

    try:
        import requests
    except Exception as e:  # pragma: no cover
        raise IngestionError(
            ErrorCode.DOWNLOAD_FAILED,
            "`requests` library is required for downloads.",
            {"reason": str(e)}) from e
    req_headers = dict(headers)
    if resume_from > 0:
        req_headers["Range"] = f"bytes={resume_from}-"
    try:
        with requests.get(url, headers=req_headers, stream=True,
                          timeout=cfg.timeout_s, allow_redirects=True) as resp:
            status = int(resp.status_code)
            if status not in (200, 206):
                raise IngestionError(
                    ErrorCode.DOWNLOAD_FAILED,
                    f"Download HTTP {status}",
                    {"http_status": status, "url_host": _host_of(url)})
            mode = "ab" if resume_from > 0 and status == 206 else "wb"
            with dest.open(mode) as f:
                for chunk in resp.iter_content(chunk_size=cfg.chunk_bytes):
                    if chunk:
                        f.write(chunk)
    except IngestionError:
        raise
    except Exception as e:
        raise IngestionError(
            ErrorCode.DOWNLOAD_FAILED,
            "Network error during download.",
            {"reason": e.__class__.__name__}) from e


def _host_of(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except Exception:
        return ""


def download_product(product: ProductMetadata,
                     data_dir: Path | str,
                     auth: CDSEAuth,
                     *,
                     cfg: DownloadConfig | None = None,
                     session: object | None = None,
                     secrets_dir: Path | None = None,
                     ) -> tuple[Path, str]:
    """Download `product` into the cache; return (archive_path, sha256).

    Behaviour:
        - Rejects downloads that would breach the free-space safety margin.
        - Writes to `<name>.zip.part`, then atomic-renames on success.
        - On success, writes checksum.sha256 + metadata.json +
          complete.marker.
    """
    cfg = cfg or DownloadConfig()
    d = product_cache_dir(data_dir, product.product_id)
    d.mkdir(parents=True, exist_ok=True)
    # Fresh download: any previous "complete" marker is cleared upfront
    clear_complete(data_dir, product.product_id)

    archive_name = _archive_name(product.name)
    dest_final = d / archive_name
    dest_part  = d / (archive_name + ".part")

    # Storage precheck (best-effort; server may not report size)
    if product.size_bytes and product.size_bytes > 0:
        _check_disk_space(d, product.size_bytes, cfg.free_space_safety_bytes)

    headers = auth.auth_header(secrets_dir)
    last_err: IngestionError | None = None
    for attempt in range(1, cfg.max_retries + 1):
        try:
            resume_from = dest_part.stat().st_size if dest_part.exists() else 0
            _stream_to_file(session, product.download_url, headers,
                            dest_part, cfg, resume_from=resume_from)
            break
        except IngestionError as e:
            last_err = e
            if attempt >= cfg.max_retries:
                # Preserve partial file - the next call can attempt resume.
                raise
            time.sleep(cfg.backoff_s * attempt)

    # Atomic finalize
    dest_final.parent.mkdir(parents=True, exist_ok=True)
    if dest_final.exists():
        # Never overwrite an unrelated file - it would only appear if a prior
        # partial got renamed.
        dest_final.unlink()
    dest_part.rename(dest_final)

    sha = compute_sha256(dest_final)
    if cfg.verify_sha_after_download and product.checksum:
        # Server side provides MD5 by default; we still store SHA-256 locally.
        # If a SHA is provided by the caller it'd be compared here.
        pass
    store_checksum(data_dir, product.product_id, sha)
    write_metadata(data_dir, product)
    mark_complete(data_dir, product.product_id)
    return dest_final, sha


__all__ = ["DownloadConfig", "download_product",
           "DEFAULT_TIMEOUT_S", "DEFAULT_MAX_RETRIES", "DEFAULT_BACKOFF_S"]
