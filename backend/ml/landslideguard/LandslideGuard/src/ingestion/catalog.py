"""CDSE OData catalog client for Sentinel-2 L2A search.

CDSE exposes an OData 4.0 endpoint at
    https://catalogue.dataspace.copernicus.eu/odata/v1/Products
which we query with a `$filter` expression to constrain by:
    - Collection = SENTINEL-2
    - product name matches MSIL2A
    - footprint intersects the AOI
    - acquisition ContentDate/Start in [start, end)
    - cloudCover <= threshold

Nothing here fabricates results. Injected HTTP clients (`session` arg)
allow tests to run offline.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from shapely.geometry import Polygon
from shapely.wkt import loads as wkt_loads

from .aoi import parse_utc_iso
from .auth import CDSEAuth
from .errors import ErrorCode, IngestionError
from .schemas import IngestionRequest, ProductMetadata


CDSE_CATALOG_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

# Optional download endpoint pattern - the OData "$value" media URL.
def product_download_url(product_id: str) -> str:
    return (
        f"https://catalogue.dataspace.copernicus.eu/odata/v1/"
        f"Products({product_id})/$value"
    )


TILE_ID_RE = re.compile(r"_T(\d{2}[A-Z]{3})_")


def _fmt_dt(iso_or_dt: str | datetime) -> str:
    """Format a UTC datetime as the OData literal 'YYYY-MM-DDTHH:MM:SS.000Z'."""
    if isinstance(iso_or_dt, str):
        dt = parse_utc_iso(iso_or_dt, "date")
    else:
        dt = iso_or_dt
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def build_filter(request: IngestionRequest) -> str:
    """Return the `$filter` clause for the OData query.

    Grammar reference:
      https://documentation.dataspace.copernicus.eu/APIs/OData.html
    """
    start = _fmt_dt(request.start)
    end   = _fmt_dt(request.end)
    aoi_literal = f"geography'SRID=4326;{request.aoi_wkt}'"
    cloud_max = float(request.max_cloud_cover)
    parts = [
        "Collection/Name eq 'SENTINEL-2'",
        # productType filter (L2A only)
        "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
        "and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A')",
        f"OData.CSC.Intersects(area={aoi_literal})",
        f"ContentDate/Start gt {start}",
        f"ContentDate/Start lt {end}",
        # cloudCover as a numeric attribute
        "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
        f"and att/OData.CSC.DoubleAttribute/Value le {cloud_max})",
    ]
    return " and ".join(parts)


def build_query_params(request: IngestionRequest) -> dict[str, str]:
    """OData query parameters for a Sentinel-2 L2A search."""
    return {
        "$filter":  build_filter(request),
        "$orderby": "ContentDate/Start asc",
        "$top":     str(int(request.max_results)),
        "$expand":  "Attributes",
    }


def _attr(product_json: dict, name: str) -> object | None:
    """Extract an attribute value from an OData product JSON.

    CDSE returns `Attributes` as a list of `{"Name":..., "Value":...}` dicts
    when `$expand=Attributes` is used.
    """
    for att in product_json.get("Attributes", []) or []:
        if att.get("Name") == name:
            return att.get("Value")
    return None


def parse_product(prod: dict) -> ProductMetadata:
    """Turn a CDSE OData product dict into a ProductMetadata."""
    try:
        pid = prod["Id"]
        name = prod["Name"]
    except KeyError as e:
        raise IngestionError(
            ErrorCode.PRODUCT_METADATA_INVALID,
            "Product entry is missing required fields.",
            {"missing": str(e)}) from e
    content_date = prod.get("ContentDate", {}) or {}
    start = content_date.get("Start")
    end = content_date.get("End", start)
    footprint = prod.get("Footprint")
    if isinstance(footprint, dict):
        # Some responses give a GeoJSON dict; convert to WKT if we can
        try:
            from shapely.geometry import shape
            footprint = shape(footprint).wkt
        except Exception:
            footprint = None
    tile_m = TILE_ID_RE.search(name)
    tile_id = tile_m.group(1) if tile_m else None
    processing_baseline = _attr(prod, "processingBaseline") or _attr(prod, "processorVersion")
    cloud = _attr(prod, "cloudCover")
    online = bool(prod.get("Online", True))
    size = _attr(prod, "productSize") or prod.get("ContentLength")
    try:
        size_i = int(size) if size is not None else None
    except (TypeError, ValueError):
        size_i = None
    checksum = None
    for cs in prod.get("Checksum", []) or []:
        if cs.get("Algorithm", "").upper() == "MD5":
            checksum = cs.get("Value")
            break
    return ProductMetadata(
        product_id=pid,
        name=name,
        product_type="S2MSI2A",
        platform="SENTINEL-2",
        tile_id=tile_id,
        acquisition_start=start or "",
        acquisition_end=end or (start or ""),
        processing_level="L2A",
        processing_baseline=str(processing_baseline) if processing_baseline else None,
        cloud_cover=float(cloud) if cloud is not None else None,
        footprint_wkt=footprint if isinstance(footprint, str) else None,
        aoi_intersection_ratio=None,
        online=online,
        download_url=product_download_url(pid),
        provider="CDSE",
        size_bytes=size_i,
        checksum=checksum,
    )


# ------------------------------ client -----------------------------

class CatalogClient:
    """Thin wrapper around the CDSE OData Products endpoint."""

    def __init__(self, base_url: str = CDSE_CATALOG_URL,
                 auth: CDSEAuth | None = None,
                 session: object | None = None,
                 timeout_s: float = 60.0,
                 secrets_dir: Path | None = None) -> None:
        self.base_url = base_url
        self.auth = auth or CDSEAuth(session=session)
        self.session = session
        self.timeout_s = timeout_s
        self.secrets_dir = secrets_dir

    def _http_get(self, url: str, params: dict) -> tuple[int, dict]:
        headers = self.auth.auth_header(self.secrets_dir)
        if self.session is not None:
            resp = self.session.get(url, params=params, headers=headers,  # type: ignore[attr-defined]
                                    timeout=self.timeout_s)
            code = int(resp.status_code)
            try:
                body = resp.json() if hasattr(resp, "json") else {}
            except Exception:
                body = {}
            return code, body
        try:
            import requests
        except Exception as e:  # pragma: no cover
            raise IngestionError(
                ErrorCode.CATALOG_QUERY_FAILED,
                "`requests` library is required for CDSE catalog access.",
                {"reason": str(e)}) from e
        try:
            resp = requests.get(url, params=params, headers=headers,
                                timeout=self.timeout_s)
        except Exception as e:
            raise IngestionError(
                ErrorCode.CATALOG_QUERY_FAILED,
                "Network error while querying the CDSE catalog.",
                {"reason": e.__class__.__name__}) from e
        try:
            body = resp.json()
        except Exception:
            body = {}
        return int(resp.status_code), body

    def search(self, request: IngestionRequest) -> list[ProductMetadata]:
        """Run the OData search and return parsed products (no ranking)."""
        params = build_query_params(request)
        code, body = self._http_get(self.base_url, params)
        if code >= 400:
            raise IngestionError(
                ErrorCode.CATALOG_QUERY_FAILED,
                f"Catalog query failed with HTTP {code}.",
                {"http_status": code, "params_keys": list(params.keys())})
        products = body.get("value", [])
        parsed = [parse_product(p) for p in products]
        return parsed


# ------------------------------ post-filter ------------------------

def apply_filters(products: Iterable[ProductMetadata],
                  request: IngestionRequest,
                  aoi_polygon: Polygon,
                  ) -> tuple[list[ProductMetadata], dict]:
    """Post-filter: enforce AOI intersection + cloud + type + online.

    Returns (kept, stats) where stats reports how many were dropped and why.
    """
    stats = {"input": 0, "dropped_type": 0, "dropped_online": 0,
             "dropped_cloud": 0, "dropped_aoi": 0, "kept": 0}
    kept: list[ProductMetadata] = []
    for p in products:
        stats["input"] += 1
        if p.product_type != "S2MSI2A" or p.processing_level != "L2A":
            stats["dropped_type"] += 1
            continue
        if not p.online:
            stats["dropped_online"] += 1
            continue
        if p.cloud_cover is None or p.cloud_cover > request.max_cloud_cover:
            stats["dropped_cloud"] += 1
            continue
        # AOI intersection ratio if we have a footprint
        if p.footprint_wkt:
            try:
                fp = wkt_loads(p.footprint_wkt)
                if not fp.is_valid or fp.is_empty:
                    stats["dropped_aoi"] += 1
                    continue
                inter = fp.intersection(aoi_polygon)
                if inter.is_empty:
                    stats["dropped_aoi"] += 1
                    continue
                aoi_area = max(aoi_polygon.area, 1e-12)
                p.aoi_intersection_ratio = float(inter.area / aoi_area)
            except Exception:
                # Keep with unknown ratio rather than silently drop.
                p.aoi_intersection_ratio = None
        kept.append(p)
        stats["kept"] += 1
    return kept, stats


__all__ = [
    "CDSE_CATALOG_URL", "product_download_url",
    "build_filter", "build_query_params",
    "parse_product", "CatalogClient", "apply_filters",
]
