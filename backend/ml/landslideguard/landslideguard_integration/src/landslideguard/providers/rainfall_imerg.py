"""IMERG rainfall providers for the Prediction V1 feature contract.

Reference product (matches the frozen Prediction V1 dataset construction):
    NASA GPM IMERG Final V07  —  GPM_3IMERGDF  —  daily  —  0.1 degree
    nearest grid-cell extraction (NO bilinear interpolation)

Two concrete providers:

  * IMERGFinalV07NetCDFProvider
        Reads real `3B-DAY.MS.MRG.3IMERG.YYYYMMDD-S000000-E235959.V07B.nc4`
        files, nearest grid cell. This is the production/reference path. It
        can only serve dates whose NetCDF is present locally.

  * IMERGFinalV07ReferenceProvider
        Reads the FROZEN per-date extraction record CSVs produced during
        dataset construction (positives + controls). Same product, same
        nearest-cell method, but sourced from the retained extraction record
        rather than re-reading NetCDF (the raw NetCDFs were not all retained
        locally). Used for historical reproducibility.

Near-real-time IMERG Early/Late is a DIFFERENT product and is intentionally
NOT implemented here; do not mix it with the Final V07 reference.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .base import RainfallProvider, validate_coordinates
from .errors import AuthenticationError, MissingRainfallError, ProviderError
from .download import atomic_fetch_dir, DiskSpaceError

log = logging.getLogger("landslideguard.imerg")

_FILE_TMPL = "3B-DAY.MS.MRG.3IMERG.{ymd}-S000000-E235959.V07B.nc4"


class IMERGFinalV07NetCDFProvider(RainfallProvider):
    """Nearest-cell extraction from local GPM IMERG Final V07 daily NetCDFs."""

    provider_name = "IMERGFinalV07NetCDFProvider"
    product = "GPM_3IMERGDF"
    version = "V07 (Final)"
    resolution = "0.1deg"
    extraction_method = "nearest_grid_cell"

    def __init__(self, netcdf_dir: str | Path, precip_var: str = "precipitation"):
        self.netcdf_dir = Path(netcdf_dir)
        self.precip_var = precip_var

    def _file_for(self, d: date) -> Path:
        return self.netcdf_dir / _FILE_TMPL.format(ymd=d.strftime("%Y%m%d"))

    def _read_nearest(self, path: Path, lat: float, lon: float) -> float:
        try:
            import xarray as xr
        except ImportError as e:  # pragma: no cover
            raise ProviderError("xarray is required for NetCDF IMERG reads") from e
        try:
            with xr.open_dataset(path) as ds:
                sel = ds[self.precip_var].sel(lat=lat, lon=lon, method="nearest")
                val = float(np.asarray(sel).squeeze())
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"failed reading {path.name}: {e}", path=str(path)) from e
        if not np.isfinite(val):
            raise MissingRainfallError(f"non-finite precip in {path.name}", path=str(path))
        if val < 0:
            raise MissingRainfallError(f"negative precip ({val}) in {path.name}", path=str(path))
        return val

    def validate_netcdf(self, path: Path, expect_date: Optional[date] = None) -> None:
        """Structural validation of an IMERG daily granule. Raises on failure."""
        import xarray as xr
        p = Path(path)
        if not p.exists():
            raise MissingRainfallError(f"file does not exist: {p}", path=str(p))
        try:
            with xr.open_dataset(p) as ds:
                for coord in ("lat", "lon"):
                    if coord not in ds.variables and coord not in ds.coords:
                        raise ProviderError(f"{p.name}: missing coordinate '{coord}'")
                if self.precip_var not in ds.data_vars:
                    raise ProviderError(f"{p.name}: missing variable '{self.precip_var}'")
                if expect_date is not None and "time" in ds.coords:
                    import pandas as pd
                    got = pd.Timestamp(np.asarray(ds["time"].values).ravel()[0]).date()
                    if got != expect_date:
                        raise ProviderError(
                            f"{p.name}: file date {got} != expected {expect_date}")
        except (OSError, ValueError) as e:
            raise ProviderError(f"{p.name}: unreadable NetCDF ({e})", path=str(p)) from e

    def get_daily_rainfall(self, latitude: float, longitude: float,
                           start_date: date, end_date: date) -> dict[date, float]:
        lat, lon = validate_coordinates(latitude, longitude)
        out: dict[date, float] = {}
        d = start_date
        while d <= end_date:
            path = self._file_for(d)
            if not path.exists():
                raise MissingRainfallError(
                    f"IMERG Final V07 file missing for {d.isoformat()}",
                    date=d.isoformat(), expected_file=str(path))
            out[d] = self._read_nearest(path, lat, lon)
            d = date.fromordinal(d.toordinal() + 1)
        return out

    def get_point(self, latitude: float, longitude: float, day: date) -> dict:
        """Diagnostic helper: nearest cell value + the cell coordinates used."""
        import xarray as xr
        lat, lon = validate_coordinates(latitude, longitude)
        path = self._file_for(day)
        if not path.exists():
            raise MissingRainfallError(f"missing file for {day}", expected_file=str(path))
        with xr.open_dataset(path) as ds:
            sel = ds[self.precip_var].sel(lat=lat, lon=lon, method="nearest")
            return {
                "precipitation_mm_day": float(np.asarray(sel).squeeze()),
                "imerg_lat": float(sel.lat),
                "imerg_lon": float(sel.lon),
            }


class IMERGFinalV07ReferenceProvider(RainfallProvider):
    """Reads the FROZEN per-date IMERG Final V07 extraction record CSVs.

    Each CSV row is one (point, date) nearest-cell extraction with columns:
        latitude, longitude, rainfall_date, precipitation_mm_day
    (plus imerg_lat/imerg_lon and an id column). Values are indexed by
    (rounded latitude, rounded longitude, date).
    """

    provider_name = "IMERGFinalV07ReferenceProvider"
    product = "GPM_3IMERGDF"
    version = "V07 (Final) — frozen extraction record"
    resolution = "0.1deg"
    extraction_method = "nearest_grid_cell (from retained extraction CSV)"

    def __init__(self, csv_paths: list[str | Path], coord_round: int = 6):
        import pandas as pd
        self.coord_round = coord_round
        self._index: dict[tuple[float, float, str], float] = {}
        frames = []
        for p in csv_paths:
            p = Path(p)
            if not p.exists():
                raise ProviderError(f"reference rainfall CSV not found: {p}")
            frames.append(pd.read_csv(p))
        for df in frames:
            need = {"latitude", "longitude", "rainfall_date", "precipitation_mm_day"}
            missing = need - set(df.columns)
            if missing:
                raise ProviderError(f"reference CSV missing columns: {sorted(missing)}")
            for lat, lon, rdate, prec in zip(
                df["latitude"], df["longitude"], df["rainfall_date"], df["precipitation_mm_day"]
            ):
                key = (round(float(lat), coord_round),
                       round(float(lon), coord_round),
                       str(rdate)[:10])
                # First write wins; identical nearest-cell extraction is deterministic.
                self._index.setdefault(key, float(prec))

    def get_daily_rainfall(self, latitude: float, longitude: float,
                           start_date: date, end_date: date) -> dict[date, float]:
        lat, lon = validate_coordinates(latitude, longitude)
        klat, klon = round(lat, self.coord_round), round(lon, self.coord_round)
        out: dict[date, float] = {}
        d = start_date
        while d <= end_date:
            key = (klat, klon, d.isoformat())
            if key not in self._index:
                raise MissingRainfallError(
                    f"no reference extraction for ({klat},{klon}) {d.isoformat()}",
                    date=d.isoformat(), latitude=klat, longitude=klon)
            val = self._index[key]
            if not np.isfinite(val):
                raise MissingRainfallError(f"non-finite reference precip {d.isoformat()}")
            out[d] = val
            d = date.fromordinal(d.toordinal() + 1)
        return out


def _default_earthaccess_auth():
    """Authenticate to NASA Earthdata via earthaccess. Tries environment then
    netrc, tolerating an unavailable strategy. Returns a truthy auth object on
    success, else falsy. Reads NO credentials directly and logs none."""
    import earthaccess
    for strategy in ("environment", "netrc"):
        try:
            auth = earthaccess.login(strategy=strategy, persist=False)
        except Exception:  # noqa: BLE001 (strategy unavailable -> try the next)
            continue
        if getattr(auth, "authenticated", False):
            return auth
    return None


class IMERGFinalV07LiveProvider(IMERGFinalV07NetCDFProvider):
    """Live GPM IMERG Final V07 provider: downloads exactly the required daily
    granules from NASA Earthdata into a small cache, then extracts nearest-cell
    rainfall via the NetCDF path.

    STRICT no-bulk: one granule per required date, disk-checked, staged,
    validated, atomically cached. Authentication uses earthaccess (env/netrc);
    credentials are never read, logged, or stored by this class. Missing
    credentials -> AuthenticationError (never fake data).

    The download step is injectable (`granule_fetcher`) so the caching /
    validation / disk-safety logic is testable offline without network.
    """

    provider_name = "IMERGFinalV07LiveProvider"
    product = "GPM_3IMERGDF"
    version = "V07"
    run = "Final"
    resolution = "0.1deg"
    extraction_method = "nearest_grid_cell (live Earthdata download)"

    def __init__(self, cache_dir: str | Path, *,
                 granule_fetcher: Optional[Callable[[date, Path], Path]] = None,
                 authenticator: Optional[Callable[[], object]] = None,
                 min_free_mb: float = 700.0,
                 precip_var: str = "precipitation",
                 cache_manager: Optional[object] = None):
        cache = Path(cache_dir) / "imerg" / "final_v07"
        cache.mkdir(parents=True, exist_ok=True)
        super().__init__(cache, precip_var=precip_var)
        self.cache_dir = cache
        self.min_free_mb = min_free_mb
        self._granule_fetcher = granule_fetcher
        self._authenticator = authenticator
        self._auth = None
        # Optional Phase-7 cache manager (None -> unchanged Phase-4/5/6 behaviour).
        self.cache_manager = cache_manager
        # Phase-5 retrieval instrumentation (proves REMOTE_DOWNLOAD vs CACHE_HIT).
        self.download_count = 0
        self.cache_hit_count = 0
        self.last_retrieval_mode = None   # "REMOTE_DOWNLOAD" | "CACHE_HIT" | "CONTROLLED_FETCH"

    @property
    def uses_default_remote(self) -> bool:
        """True when the real earthaccess downloader is in use (not an injected
        test fetcher)."""
        return self._granule_fetcher is None

    def _ensure_auth(self):
        if self._auth is not None:
            return self._auth
        auth_fn = self._authenticator or _default_earthaccess_auth
        try:
            self._auth = auth_fn()
        except Exception as e:  # noqa: BLE001
            raise AuthenticationError(f"Earthdata authentication failed: {e}") from e
        if not self._auth:
            raise AuthenticationError(
                "Earthdata authentication unavailable (no credentials in env/netrc)")
        return self._auth

    def _default_fetch(self, d: date, staging: Path) -> Path:
        import earthaccess
        results = earthaccess.search_data(
            short_name=self.product, version="07",
            temporal=(d.isoformat(), d.isoformat()))
        if not results:
            raise MissingRainfallError(f"no IMERG Final granule found for {d.isoformat()}")
        files = earthaccess.download(results[:1], str(staging))
        paths = [Path(f) for f in files if str(f).lower().endswith(".nc4")]
        if not paths:
            raise ProviderError(f"download produced no .nc4 for {d.isoformat()}")
        return paths[0]

    def _ensure_granule(self, d: date, pinned: Optional[set] = None) -> Path:
        path = self._file_for(d)
        if path.exists():
            try:
                self.validate_netcdf(path, expect_date=d)
                self.cache_hit_count += 1
                self.last_retrieval_mode = "CACHE_HIT"
                if self.cache_manager is not None:
                    self.cache_manager.record_access(path)
                log.info("imerg cache hit %s", path.name)
                return path
            except (ProviderError, MissingRainfallError):
                log.warning("imerg cache entry invalid, refetching %s", path.name)
                try:
                    path.unlink()
                except OSError:
                    pass
        self._ensure_auth()
        # Phase-7: make room if needed (never evicting the active window), else refuse.
        if self.cache_manager is not None:
            est = int(self.cache_manager.policy.imerg_granule_mb * 1e6)
            res = self.cache_manager.ensure_space_for(est, pinned=pinned or {path}, dry_run=False)
            if not res["ok"]:
                raise DiskSpaceError(
                    f"cannot free enough space for IMERG {d.isoformat()} while keeping "
                    f"{self.cache_manager.policy.min_free_disk_gb} GB free")
        log.info("imerg cache miss, downloading %s", path.name)
        fetcher = self._granule_fetcher or self._default_fetch
        atomic_fetch_dir(
            path,
            lambda staging: fetcher(d, staging),
            lambda p: self.validate_netcdf(p, expect_date=d),
            min_free_mb=self.min_free_mb,
        )
        self.download_count += 1
        self.last_retrieval_mode = ("REMOTE_DOWNLOAD" if self.uses_default_remote
                                    else "CONTROLLED_FETCH")
        if self.cache_manager is not None:
            self.cache_manager.record_download(path)
        return path

    def get_daily_rainfall(self, latitude, longitude, start_date, end_date):
        validate_coordinates(latitude, longitude)
        # Pin the whole requested window so eviction never removes a granule the
        # active T-14..T-1 request still needs.
        window = []
        d = start_date
        while d <= end_date:
            window.append(d)
            d = date.fromordinal(d.toordinal() + 1)
        pinned = {str(self._file_for(x)) for x in window}
        for x in window:
            self._ensure_granule(x, pinned=pinned)
        return super().get_daily_rainfall(latitude, longitude, start_date, end_date)

    def get_point(self, latitude, longitude, day):
        self._ensure_granule(day, pinned={str(self._file_for(day))})
        return super().get_point(latitude, longitude, day)


__all__ = [
    "IMERGFinalV07NetCDFProvider",
    "IMERGFinalV07ReferenceProvider",
    "IMERGFinalV07LiveProvider",
]
