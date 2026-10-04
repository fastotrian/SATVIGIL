"""SRTMGL1 V003 terrain provider (elevation / slope / aspect).

Matches the frozen Prediction V1 terrain source: NASA SRTMGL1 V003, ~30 m
(1 arc-second). Elevation is the nearest-pixel value (SRTM stores int16
metres). Slope and aspect use Horn's 8-neighbour method — verified against the
frozen dataset to reproduce it to within ~0.02 deg (see the Phase-2 report).
Aspect convention: 0=N, 90=E, 180=S, 270=W (compass, clockwise from north),
matching the frozen dataset's `aspect_convention`.

The exact original slope/aspect algorithm was not retained in the project;
Horn's method is the standard SRTM/gdaldem convention and reproduces the
frozen values closely. Residual differences are reported, never hidden, and
the frozen features are NEVER modified.

Reads a tile from, in order:
    <tiles_dir>/<TILE>/<TILE>.hgt         (already-extracted)
    <tiles_dir>/<TILE>.zip                (zip containing <TILE>.hgt)
    <downloads_dir>/<TILE>.SRTMGL1.hgt.zip
No network access, no new downloads. NoData (-32768) is treated as missing.
"""
from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .base import TerrainProvider, TerrainResult, validate_coordinates
from .errors import AuthenticationError, MissingTerrainError, ProviderError
from .download import atomic_fetch_dir, DiskSpaceError

log = logging.getLogger("landslideguard.srtm")

_SRTM_NODATA = -32768
_METERS_PER_DEG = 111320.0  # spherical approximation used for slope scaling


def tile_name(lat: float, lon: float) -> str:
    """SRTM tile name for the 1x1 degree cell containing (lat, lon)."""
    import math
    ilat = int(math.floor(lat))
    ilon = int(math.floor(lon))
    ns = "N" if ilat >= 0 else "S"
    ew = "E" if ilon >= 0 else "W"
    return f"{ns}{abs(ilat):02d}{ew}{abs(ilon):03d}"


class SRTM30mTerrainProvider(TerrainProvider):
    provider_name = "SRTM30mTerrainProvider"
    dataset_version = "NASA_SRTMGL1_V003"
    resolution = "~30 m (1 arc-second)"

    _TILE_CACHE_MAX = 4

    def __init__(self, tiles_dir: str | Path, downloads_dir: Optional[str | Path] = None):
        self.tiles_dir = Path(tiles_dir)
        self.downloads_dir = Path(downloads_dir) if downloads_dir else None
        # Per-instance DEM cache holding the NATIVE int16 tile (~26 MB), not a
        # float64 copy (~104 MB). (A method-level lru_cache would also pin every
        # instance against GC -> leak.) The 3x3 Horn window is cast to float64
        # on demand, so terrain values are identical at a quarter of the RAM.
        self._tile_cache: dict[str, np.ndarray] = {}

    # ---- tile IO ----

    def _hgt_bytes(self, tile: str) -> bytes:
        extracted = self.tiles_dir / tile / f"{tile}.hgt"
        if extracted.exists():
            return extracted.read_bytes()
        candidates = [self.tiles_dir / f"{tile}.zip"]
        if self.downloads_dir:
            candidates.append(self.downloads_dir / f"{tile}.SRTMGL1.hgt.zip")
        for zp in candidates:
            if zp.exists():
                try:
                    with zipfile.ZipFile(zp) as z:
                        names = [n for n in z.namelist() if n.lower().endswith(".hgt")]
                        if not names:
                            raise ProviderError(f"no .hgt in {zp.name}")
                        return z.read(names[0])
                except zipfile.BadZipFile as e:
                    raise ProviderError(f"bad zip {zp.name}: {e}") from e
        raise MissingTerrainError(f"SRTM tile {tile} not found locally", tile=tile)

    def _load_tile(self, tile: str) -> np.ndarray:
        cached = self._tile_cache.get(tile)
        if cached is not None:
            return cached
        raw = self._hgt_bytes(tile)
        data = np.frombuffer(raw, dtype=">i2")
        n = int(round(len(data) ** 0.5))
        if n * n != len(data):
            raise ProviderError(f"tile {tile} not square ({len(data)} samples)")
        # Keep native int16 (little copy to make it writable/contiguous, ~26 MB).
        arr = np.ascontiguousarray(data.reshape(n, n))
        if len(self._tile_cache) >= self._TILE_CACHE_MAX:
            self._tile_cache.clear()   # simple bound; freed with the instance
        self._tile_cache[tile] = arr
        return arr

    # ---- terrain extraction ----

    def get_terrain(self, latitude: float, longitude: float) -> TerrainResult:
        lat, lon = validate_coordinates(latitude, longitude)
        tile = tile_name(lat, lon)
        dem = self._load_tile(tile)
        n = dem.shape[0]
        samples = n - 1  # posts per degree (e.g. 3600 for 3601x3601)

        ilat_floor = float(np.floor(lat))
        ilon_floor = float(np.floor(lon))
        # Row 0 = north edge (lat = floor+1); last row = south edge (lat = floor).
        row_f = (ilat_floor + 1.0 - lat) * samples
        col_f = (lon - ilon_floor) * samples
        r = int(round(row_f))
        c = int(round(col_f))
        r = min(max(r, 0), n - 1)
        c = min(max(c, 0), n - 1)

        elev = float(dem[r, c])
        if elev == _SRTM_NODATA or not np.isfinite(elev):
            raise MissingTerrainError(f"NoData elevation at ({lat},{lon})", tile=tile)

        slope, aspect = self._slope_aspect(dem, r, c, lat, samples, n)

        return TerrainResult(
            elevation_m=float(elev),
            slope_degrees=float(slope) if slope is not None else float("nan"),
            aspect_degrees=float(aspect) if aspect is not None else float("nan"),
            source="NASA",
            dataset_version=self.dataset_version,
            resolution=self.resolution,
            tile=tile,
            extra={"row": r, "col": c, "grid": n,
                   "aspect_convention": "0=N,90=E,180=S,270=W",
                   "method": "horn_8neighbour",
                   "meters_per_degree": _METERS_PER_DEG},
        )

    def _slope_aspect(self, dem, r, c, lat, samples, n):
        # Need a full 3x3 neighbourhood; edge pixels -> undefined (matches the
        # small number of NaN slope/aspect in the frozen dataset).
        if r <= 0 or c <= 0 or r >= n - 1 or c >= n - 1:
            return None, None
        z = dem[r - 1:r + 2, c - 1:c + 2].astype(np.float64)   # cast only the 3x3 window
        if np.any(z == _SRTM_NODATA):
            return None, None

        arc = 1.0 / samples
        dy = arc * _METERS_PER_DEG
        dx = arc * _METERS_PER_DEG * np.cos(np.radians(lat))

        a, b, cc = z[0]
        d, e, f = z[1]
        g, h, i = z[2]
        # Row 0 is north (higher lat); row index increases southward.
        dzdx = ((cc + 2 * f + i) - (a + 2 * d + g)) / (8 * dx)
        dzdy = ((g + 2 * h + i) - (a + 2 * b + cc)) / (8 * dy)

        slope = float(np.degrees(np.arctan(np.hypot(dzdx, dzdy))))
        aspect = float(np.degrees(np.arctan2(dzdy, -dzdx)))
        aspect = 90.0 - aspect
        if aspect < 0.0:
            aspect += 360.0
        elif aspect >= 360.0:
            aspect -= 360.0
        return slope, aspect


def validate_hgt_zip(path: Path) -> None:
    """Validate that a zip contains a square int16 .hgt. Raises on failure."""
    p = Path(path)
    if not p.exists():
        raise MissingTerrainError(f"tile file missing: {p}", path=str(p))
    try:
        with zipfile.ZipFile(p) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".hgt")]
            if not names:
                raise ProviderError(f"{p.name}: no .hgt inside zip")
            size = z.getinfo(names[0]).file_size
    except zipfile.BadZipFile as e:
        raise ProviderError(f"{p.name}: bad zip ({e})", path=str(p)) from e
    n_samples = size // 2
    root = int(round(n_samples ** 0.5))
    if root * root != n_samples:
        raise ProviderError(f"{p.name}: .hgt not square ({n_samples} samples)")


def _default_earthaccess_auth():
    import earthaccess
    for strategy in ("environment", "netrc"):
        try:
            auth = earthaccess.login(strategy=strategy, persist=False)
        except Exception:  # noqa: BLE001 (strategy unavailable -> try the next)
            continue
        if getattr(auth, "authenticated", False):
            return auth
    return None


class SRTM30mLiveTerrainProvider(SRTM30mTerrainProvider):
    """Live SRTMGL1 V003 provider: downloads exactly the one required tile from
    NASA Earthdata into a small cache, then extracts elevation + Horn slope/
    aspect via the frozen Phase-2 logic.

    STRICT no-bulk: one tile per requested coordinate, disk-checked, staged,
    validated, atomically cached. Neighbouring tiles are NOT prefetched. Auth
    uses earthaccess; credentials never read/logged/stored. Missing credentials
    -> AuthenticationError. Download step injectable for offline testing.
    """

    provider_name = "SRTM30mLiveTerrainProvider"
    dataset_version = "NASA_SRTMGL1_V003"
    resolution = "~30 m (1 arc-second)"

    def __init__(self, cache_dir: str | Path, *,
                 tile_fetcher: Optional[Callable[[str, Path], Path]] = None,
                 authenticator: Optional[Callable[[], object]] = None,
                 min_free_mb: float = 300.0,
                 cache_manager: Optional[object] = None):
        tiles = Path(cache_dir) / "srtm" / "srtmgl1_v003"
        tiles.mkdir(parents=True, exist_ok=True)
        super().__init__(tiles_dir=tiles, downloads_dir=None)
        self.cache_dir = tiles
        self.min_free_mb = min_free_mb
        self._tile_fetcher = tile_fetcher
        self._authenticator = authenticator
        self._auth = None
        # Optional Phase-7 cache manager (None -> unchanged behaviour).
        self.cache_manager = cache_manager
        # Phase-5 retrieval instrumentation.
        self.download_count = 0
        self.cache_hit_count = 0
        self.last_retrieval_mode = None

    @property
    def uses_default_remote(self) -> bool:
        return self._tile_fetcher is None

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

    def _default_fetch(self, tile: str, staging: Path) -> Path:
        import earthaccess
        # SRTM tile centre for a point-in-tile search.
        ns = tile[0]; lat = int(tile[1:3]) * (1 if ns == "N" else -1)
        ew = tile[3]; lon = int(tile[4:7]) * (1 if ew == "E" else -1)
        clon, clat = lon + 0.5, lat + 0.5
        results = earthaccess.search_data(
            short_name="SRTMGL1", version="003",
            bounding_box=(clon, clat, clon, clat))
        if not results:
            raise MissingTerrainError(f"no SRTMGL1 granule for tile {tile}")
        files = earthaccess.download(results[:1], str(staging))
        zips = [Path(f) for f in files if str(f).lower().endswith(".zip")]
        if not zips:
            raise ProviderError(f"download produced no zip for tile {tile}")
        return zips[0]

    def _ensure_tile(self, tile: str) -> None:
        extracted = self.tiles_dir / tile / f"{tile}.hgt"
        cached_zip = self.tiles_dir / f"{tile}.zip"
        if extracted.exists():
            self.cache_hit_count += 1
            self.last_retrieval_mode = "CACHE_HIT"
            return
        if cached_zip.exists():
            try:
                validate_hgt_zip(cached_zip)
                self.cache_hit_count += 1
                self.last_retrieval_mode = "CACHE_HIT"
                if self.cache_manager is not None:
                    self.cache_manager.record_access(cached_zip)
                log.info("srtm cache hit %s", cached_zip.name)
                return
            except (ProviderError, MissingTerrainError):
                log.warning("srtm cache entry invalid, refetching %s", cached_zip.name)
                try:
                    cached_zip.unlink()
                except OSError:
                    pass
        self._ensure_auth()
        if self.cache_manager is not None:
            est = int(self.cache_manager.policy.srtm_tile_mb * 1e6)
            res = self.cache_manager.ensure_space_for(est, pinned={str(cached_zip)}, dry_run=False)
            if not res["ok"]:
                raise DiskSpaceError(
                    f"cannot free enough space for SRTM tile {tile} while keeping "
                    f"{self.cache_manager.policy.min_free_disk_gb} GB free")
        log.info("srtm cache miss, downloading tile %s", tile)
        fetcher = self._tile_fetcher or self._default_fetch
        atomic_fetch_dir(
            cached_zip,
            lambda staging: fetcher(tile, staging),
            validate_hgt_zip,
            min_free_mb=self.min_free_mb,
        )
        self.download_count += 1
        self.last_retrieval_mode = ("REMOTE_DOWNLOAD" if self.uses_default_remote
                                    else "CONTROLLED_FETCH")
        if self.cache_manager is not None:
            self.cache_manager.record_download(cached_zip)

    def _hgt_bytes(self, tile: str) -> bytes:
        self._ensure_tile(tile)
        return super()._hgt_bytes(tile)


__all__ = ["SRTM30mTerrainProvider", "SRTM30mLiveTerrainProvider",
           "tile_name", "validate_hgt_zip"]
