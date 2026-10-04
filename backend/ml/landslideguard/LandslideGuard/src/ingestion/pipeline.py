"""End-to-end CDSE Sentinel-2 L2A ingestion.

Flow:
    IngestionRequest
        -> validate AOI / date / cloud
        -> auth (CDSE)
        -> catalog search
        -> post-filter
        -> deterministic rank
        -> select_best
        -> cache lookup (hit / corrupted / miss)
        -> download (retry-with-backoff)
        -> product-level validation
        -> IngestionResult
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from .aoi import (
    parse_aoi_wkt, validate_date_range, validate_cloud_threshold,
)
from .auth import CDSEAuth
from .cache import (
    is_complete, validate_cached, locate_archive,
    read_checksum, clear_complete,
)
from .catalog import CatalogClient, apply_filters
from .download import DownloadConfig, download_product
from .errors import ErrorCode, IngestionError
from .ranking import RANKING_POLICY, rank_products
from .schemas import (
    IngestionRequest, IngestionResult, IngestionStatus,
    CacheStatus, ProductMetadata,
)


DEFAULT_DATA_DIR = "data/external/sentinel2_l2a"

logger = logging.getLogger("landslideguard.ingestion")
if not logger.handlers:
    logger.setLevel(logging.INFO)


def _log_stage(stage: str, **kwargs) -> None:
    """Structured log without secrets. Callers must never include tokens."""
    safe = {k: v for k, v in kwargs.items()
            if k not in {"token", "password", "authorization",
                         "access_token", "refresh_token"}}
    logger.info("stage=%s %s", stage,
                " ".join(f"{k}={v}" for k, v in safe.items()))


def _minimal_validate_product(archive_path: Path,
                              product: ProductMetadata) -> dict:
    """Product-level (ingestion) validation only.

    Confirms the archive is a non-empty file, reports size and matches the
    filename against S2 L2A naming conventions. Does NOT open bands.
    """
    warnings: list[str] = []
    if not archive_path.is_file():
        raise IngestionError(
            ErrorCode.PRODUCT_INTEGRITY_FAILED,
            "Downloaded archive is not a file.",
            {"path": str(archive_path)})
    size = archive_path.stat().st_size
    if size <= 0:
        raise IngestionError(
            ErrorCode.PRODUCT_INTEGRITY_FAILED,
            "Downloaded archive is empty.",
            {"path": str(archive_path), "size": size})
    # Sentinel-2 L2A ZIPs start with the standard 4-byte "PK\x03\x04" signature.
    if archive_path.suffix.lower() == ".zip":
        with archive_path.open("rb") as f:
            head = f.read(4)
        if head != b"PK\x03\x04":
            raise IngestionError(
                ErrorCode.PRODUCT_INTEGRITY_FAILED,
                "Downloaded archive is not a valid ZIP.",
                {"first_bytes_hex": head.hex()})
    name = archive_path.stem
    if "MSIL2A" not in name.upper():
        warnings.append(
            f"Archive name '{archive_path.name}' does not contain "
            "'MSIL2A'; verify product type.")
    return {
        "archive_present": True,
        "size_bytes": int(size),
        "zip_magic_ok": True if archive_path.suffix.lower() == ".zip" else None,
        "name_matches_l2a": "MSIL2A" in name.upper(),
        "warnings": warnings,
    }


def _validate_request_or_raise(req: IngestionRequest):
    parse_aoi_wkt(req.aoi_wkt)
    validate_date_range(req.start, req.end)
    validate_cloud_threshold(req.max_cloud_cover)
    if not isinstance(req.max_results, int) or req.max_results <= 0:
        raise IngestionError(
            ErrorCode.INVALID_REQUEST,
            "max_results must be a positive integer.",
            {"got": req.max_results})


def ingest(request: IngestionRequest,
           *,
           data_dir: str | Path = DEFAULT_DATA_DIR,
           auth: CDSEAuth | None = None,
           catalog: CatalogClient | None = None,
           download_cfg: DownloadConfig | None = None,
           secrets_dir: str | Path | None = None,
           session: object | None = None,
           progress_callback: Callable[[str], None] | None = None,
           ) -> IngestionResult:
    """Run the full ingestion pipeline for one request.

    On success the returned IngestionResult includes:
        status=SUCCESS or CACHE_HIT
        product, local_path, checksum, validation, provenance.

    On failure the returned result has status=FAILED and `error` populated,
    with sensitive data scrubbed.
    """
    data_dir = Path(data_dir)
    secrets_dir_p = Path(secrets_dir) if secrets_dir is not None else None

    def _emit(stage: str, **kwargs) -> IngestionResult | None:
        _log_stage(stage, **kwargs)
        if progress_callback:
            progress_callback(stage)
        return None

    try:
        _emit("REQUEST_VALIDATE", aoi_label=request.aoi_label,
              start=request.start, end=request.end,
              max_cloud=request.max_cloud_cover)
        _validate_request_or_raise(request)
        aoi_polygon = parse_aoi_wkt(request.aoi_wkt)

        auth = auth or CDSEAuth(session=session)
        catalog = catalog or CatalogClient(auth=auth, session=session,
                                           secrets_dir=secrets_dir_p)

        _emit("CDSE_AUTH")
        # Trigger token acquisition eagerly so auth errors surface early.
        catalog.auth.get_access_token(secrets_dir_p)

        _emit("CATALOG_SEARCH")
        candidates = catalog.search(request)
        if not candidates:
            raise IngestionError(
                ErrorCode.NO_PRODUCTS_FOUND,
                "CDSE returned no candidate Sentinel-2 L2A products for the "
                "given AOI/date range.",
                {"aoi_label": request.aoi_label,
                 "start": request.start, "end": request.end})
        _emit("PRODUCT_FILTER", raw_count=len(candidates))
        kept, stats = apply_filters(candidates, request, aoi_polygon)
        if not kept:
            code = (ErrorCode.NO_PRODUCTS_WITHIN_CLOUD_LIMIT
                    if stats.get("dropped_cloud", 0) > 0
                    else ErrorCode.NO_PRODUCTS_FOUND)
            raise IngestionError(
                code,
                "No candidate survived post-filtering.",
                {"filter_stats": stats})

        _emit("PRODUCT_RANK", ranking_policy=RANKING_POLICY,
              kept=len(kept))
        ranked = rank_products(kept, request)
        product = ranked[0]

        # Cache lookup
        cache_status = CacheStatus.MISS
        if is_complete(data_dir, product.product_id):
            ok, reason = validate_cached(data_dir, product.product_id)
            if ok:
                cache_status = CacheStatus.HIT
                _emit("CACHE_HIT", product_id=product.product_id,
                      name=product.name)
            else:
                cache_status = CacheStatus.CORRUPTED
                _emit("CACHE_CORRUPTED",
                      product_id=product.product_id, reason=reason)
                clear_complete(data_dir, product.product_id)

        if cache_status != CacheStatus.HIT:
            _emit("DOWNLOAD_START", product_id=product.product_id,
                  name=product.name,
                  size_bytes=product.size_bytes)
            archive_path, sha = download_product(
                product, data_dir, catalog.auth,
                cfg=download_cfg, session=session,
                secrets_dir=secrets_dir_p,
            )
            _emit("DOWNLOAD_COMPLETE", path=str(archive_path),
                  size_bytes=archive_path.stat().st_size)
        else:
            archive_path = locate_archive(data_dir, product.product_id)
            sha = read_checksum(data_dir, product.product_id) or ""

        _emit("PRODUCT_VALIDATE", path=str(archive_path))
        validation = _minimal_validate_product(archive_path, product)

        result = IngestionResult(
            status=IngestionStatus.CACHE_HIT if cache_status == CacheStatus.HIT
                   else IngestionStatus.SUCCESS,
            cache_status=cache_status,
            request=request,
            product=product,
            local_path=str(archive_path),
            file_size_bytes=archive_path.stat().st_size,
            checksum_sha256=sha,
            validation=validation,
            provenance={
                "catalog_url": catalog.base_url,
                "download_url_host": product.download_url.split("/")[2],
                "filter_stats": stats,
                "ranking_policy": RANKING_POLICY,
            },
        )
        _emit("INGESTION_SUCCESS", product_id=product.product_id,
              status=result.status.value,
              cache_status=result.cache_status.value)
        return result

    except IngestionError as e:
        _log_stage("INGESTION_FAILURE", code=e.code.value,
                   message=e.message)
        return IngestionResult(
            status=IngestionStatus.FAILED,
            cache_status=CacheStatus.MISS,
            request=request,
            error=e.to_dict(),
        )


__all__ = ["ingest", "DEFAULT_DATA_DIR"]
