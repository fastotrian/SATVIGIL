"""Disk-safety + atomic-staging helpers for live provider downloads.

STRICT no-bulk policy: callers download exactly one required granule/tile at a
time. These helpers enforce a minimum free-space check, stage into a temporary
`.part`/`.tmp` location, validate, then atomically move into the cache. On any
failure the temporary artifact is removed so the cache never holds a partial or
corrupt file.

No credentials are read, logged, or stored here.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable

log = logging.getLogger("landslideguard.download")


class DiskSpaceError(RuntimeError):
    """Raised when there is not enough free disk space to proceed safely."""


def free_mb(path: str | Path) -> float:
    """Free megabytes on the filesystem containing `path` (or its nearest
    existing parent)."""
    p = Path(path)
    while not p.exists():
        if p.parent == p:
            break
        p = p.parent
    return shutil.disk_usage(str(p)).free / (1024 * 1024)


def ensure_free_space(path: str | Path, need_mb: float) -> None:
    avail = free_mb(path)
    if avail < need_mb:
        raise DiskSpaceError(
            f"insufficient free space at {path}: need >= {need_mb:.0f} MB, "
            f"have {avail:.0f} MB")


def atomic_fetch_dir(
    dest: Path,
    fetch_into: Callable[[Path], Path],
    validate: Callable[[Path], None],
    *,
    min_free_mb: float = 500.0,
) -> Path:
    """Fetch a single file into `dest` atomically.

    `fetch_into(staging_dir)` must download exactly one file into the given
    staging directory and return its path. `validate(path)` must raise on an
    invalid file. On success the file is moved to `dest`; on any failure the
    staging directory is removed and `dest` is never created.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    ensure_free_space(dest.parent, min_free_mb)

    staging = Path(tempfile.mkdtemp(prefix=".part_", dir=str(dest.parent)))
    try:
        got = Path(fetch_into(staging))
        if not got.exists():
            raise FileNotFoundError(f"fetch produced no file in {staging}")
        validate(got)
        # Atomic move into place.
        tmp_final = dest.with_suffix(dest.suffix + ".tmp")
        shutil.move(str(got), str(tmp_final))
        os.replace(tmp_final, dest)
        log.info("cached %s", dest.name)
        return dest
    except Exception:
        # never leave a partial/corrupt cache entry
        for leftover in (dest.with_suffix(dest.suffix + ".tmp"),):
            if leftover.exists():
                try:
                    leftover.unlink()
                except OSError:
                    pass
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def cache_stats(cache_dir: str | Path) -> dict:
    cache_dir = Path(cache_dir)
    if not cache_dir.exists():
        return {"location": str(cache_dir), "file_count": 0, "total_bytes": 0,
                "part_files": 0, "tmp_files": 0}
    files = [p for p in cache_dir.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    parts = sum(1 for p in files if p.name.endswith(".part") or ".part_" in str(p))
    tmps = sum(1 for p in files if p.suffix == ".tmp")
    return {
        "location": str(cache_dir),
        "file_count": len(files),
        "total_bytes": int(total),
        "total_mb": round(total / (1024 * 1024), 3),
        "part_files": parts,
        "tmp_files": tmps,
    }


__all__ = ["DiskSpaceError", "free_mb", "ensure_free_space",
           "atomic_fetch_dir", "cache_stats"]
