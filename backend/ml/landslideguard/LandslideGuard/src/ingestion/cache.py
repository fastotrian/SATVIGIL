"""Sentinel-2 product cache.

Layout under the configured `data_dir`:

    <data_dir>/
        <product_id>/
            metadata.json          # ProductMetadata snapshot
            checksum.sha256        # local SHA-256 of the archive
            complete.marker        # touched only after full validation
            <product_name>.zip     # the actual archive
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .schemas import ProductMetadata


COMPLETE_MARKER = "complete.marker"
METADATA_FILE   = "metadata.json"
CHECKSUM_FILE   = "checksum.sha256"


def product_cache_dir(root: Path | str, product_id: str) -> Path:
    return Path(root) / str(product_id)


def is_complete(root: Path | str, product_id: str) -> bool:
    """True iff a valid, fully-downloaded archive exists on disk."""
    d = product_cache_dir(root, product_id)
    if not d.is_dir():
        return False
    marker = d / COMPLETE_MARKER
    meta_p = d / METADATA_FILE
    if not (marker.is_file() and meta_p.is_file()):
        return False
    # Locate the archive
    archives = list(d.glob("*.zip")) + list(d.glob("*.SAFE"))
    if not archives:
        return False
    return True


def write_metadata(root: Path | str, product: ProductMetadata) -> Path:
    d = product_cache_dir(root, product.product_id)
    d.mkdir(parents=True, exist_ok=True)
    p = d / METADATA_FILE
    p.write_text(json.dumps(product.to_dict(), indent=2), encoding="utf-8")
    return p


def read_metadata(root: Path | str, product_id: str) -> dict | None:
    p = product_cache_dir(root, product_id) / METADATA_FILE
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def store_checksum(root: Path | str, product_id: str, sha: str) -> Path:
    d = product_cache_dir(root, product_id)
    d.mkdir(parents=True, exist_ok=True)
    p = d / CHECKSUM_FILE
    p.write_text(sha, encoding="utf-8")
    return p


def read_checksum(root: Path | str, product_id: str) -> str | None:
    p = product_cache_dir(root, product_id) / CHECKSUM_FILE
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8").strip()


def mark_complete(root: Path | str, product_id: str) -> Path:
    d = product_cache_dir(root, product_id)
    d.mkdir(parents=True, exist_ok=True)
    m = d / COMPLETE_MARKER
    m.write_text("ok", encoding="utf-8")
    return m


def clear_complete(root: Path | str, product_id: str) -> None:
    m = product_cache_dir(root, product_id) / COMPLETE_MARKER
    if m.is_file():
        m.unlink()


def locate_archive(root: Path | str, product_id: str) -> Path | None:
    d = product_cache_dir(root, product_id)
    if not d.is_dir():
        return None
    for ext in ("*.zip", "*.SAFE"):
        matches = list(d.glob(ext))
        if matches:
            return matches[0]
    return None


def validate_cached(root: Path | str, product_id: str) -> tuple[bool, str]:
    """Return (ok, reason).

    Non-destructive: on failure the CALLER decides whether to clear.
    """
    d = product_cache_dir(root, product_id)
    if not d.is_dir():
        return False, "product cache dir missing"
    if not (d / METADATA_FILE).is_file():
        return False, "metadata.json missing"
    if not (d / COMPLETE_MARKER).is_file():
        return False, "complete.marker missing"
    archive = locate_archive(root, product_id)
    if archive is None:
        return False, "archive file missing"
    stored_sha = read_checksum(root, product_id)
    if not stored_sha:
        return False, "checksum.sha256 missing"
    actual_sha = compute_sha256(archive)
    if actual_sha != stored_sha:
        return False, f"sha256 mismatch: expected {stored_sha[:12]}... "\
                      f"got {actual_sha[:12]}..."
    return True, "ok"


__all__ = [
    "product_cache_dir", "is_complete", "validate_cached",
    "write_metadata", "read_metadata",
    "store_checksum", "read_checksum", "mark_complete", "clear_complete",
    "locate_archive", "compute_sha256",
    "COMPLETE_MARKER", "METADATA_FILE", "CHECKSUM_FILE",
]
