"""Provider-independent, bounded, deterministic cache manager.

Manages the operational live-provider cache (IMERG granules + SRTM tiles) so it
cannot grow without bound or push free disk below the safety guard. It does NOT
touch any frozen model/dataset artifact — only the operational cache tree.

Safety invariants (see phase7 report):
  1. Free disk is never intentionally pushed below `min_free_disk_gb`. (Eviction
     only frees space; downloads are refused if space can't be guaranteed.)
  2. Pinned (in-use) paths are never evicted.
  3. Incomplete/staging artifacts (.part / .tmp / .part_* dirs) are never treated
     as valid cache and are always eligible for cleanup.
  4. Eviction is deterministic (documented order, stable tie-break).
  5. The manager never fabricates or edits scientific data; it only deletes whole
     eligible cache files.

Last-access tracking uses a JSON sidecar (`cache_index.json`); when an entry has
no sidecar record, filesystem mtime is used (documented: mtime == download time).
"""
from __future__ import annotations

import json
import os
import re
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from .config import CachePolicy, DEFAULT_POLICY

_IMERG_RE = re.compile(r"3B-DAY\.MS\.MRG\.3IMERG\.(\d{8})-.*\.V07B\.nc4$", re.IGNORECASE)
_SRTM_RE = re.compile(r"([NS]\d{2}[EW]\d{3})\.zip$", re.IGNORECASE)
_GB = 1024 ** 3
_INDEX_NAME = "cache_index.json"


@dataclass
class CacheEntry:
    path: Path
    kind: str            # "imerg" | "srtm" | "orphan"
    size: int
    created_at: float
    last_accessed: float
    key: Optional[str]   # IMERG date (YYYYMMDD) or SRTM tile, or None
    status: str          # "valid" | "orphan" | "zero_byte" | "corrupt" | "unexpected"

    def to_dict(self) -> dict:
        return {"path": str(self.path), "kind": self.kind, "size": self.size,
                "created_at": self.created_at, "last_accessed": self.last_accessed,
                "key": self.key, "status": self.status}


@dataclass
class EvictionPlan:
    to_remove: list[CacheEntry] = field(default_factory=list)
    bytes_freed: int = 0
    reasons: dict = field(default_factory=dict)   # path -> reason

    def summary(self) -> dict:
        return {"n_files": len(self.to_remove),
                "bytes_freed": self.bytes_freed,
                "mb_freed": round(self.bytes_freed / 1e6, 2),
                "files": [{"path": str(e.path), "kind": e.kind, "key": e.key,
                           "size": e.size, "reason": self.reasons.get(str(e.path))}
                          for e in self.to_remove]}


class CacheManager:
    def __init__(self, cache_root, policy: CachePolicy = DEFAULT_POLICY):
        self.root = Path(cache_root)
        self.policy = policy
        self.policy.validate()
        self.imerg_dir = self.root / "imerg" / "final_v07"
        self.srtm_dir = self.root / "srtm" / "srtmgl1_v003"
        self.index_path = self.root / _INDEX_NAME
        self._index = self._load_index()

    # ---------- sidecar index ----------

    def _load_index(self) -> dict:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {}
        return {}

    def _save_index(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.index_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._index, indent=2), encoding="utf-8")
        os.replace(tmp, self.index_path)

    def record_access(self, path, when: Optional[float] = None) -> None:
        """Update last-access for a file that was actually used (cache hit/read)."""
        p = Path(path)
        rel = self._rel(p)
        when = when if when is not None else time.time()
        rec = self._index.get(rel, {})
        rec.setdefault("created_at", p.stat().st_mtime if p.exists() else when)
        rec["last_accessed"] = when
        self._index[rel] = rec
        self._save_index()

    def record_download(self, path, when: Optional[float] = None) -> None:
        p = Path(path)
        rel = self._rel(p)
        when = when if when is not None else time.time()
        self._index[rel] = {"created_at": when, "last_accessed": when}
        self._save_index()

    def _rel(self, p: Path) -> str:
        try:
            return str(p.resolve().relative_to(self.root.resolve())).replace("\\", "/")
        except ValueError:
            return str(p)

    # ---------- scanning / classification ----------

    def _classify(self, p: Path) -> CacheEntry:
        rel = self._rel(p)
        try:
            st = p.stat()
            size, mtime = st.st_size, st.st_mtime
        except OSError:
            size, mtime = 0, time.time()
        idx = self._index.get(rel, {})
        created = float(idx.get("created_at", mtime))
        accessed = float(idx.get("last_accessed", mtime))
        name = p.name.lower()

        # orphan / incomplete
        if name.endswith(".part") or name.endswith(".tmp") or ".part_" in str(p):
            return CacheEntry(p, "orphan", size, created, accessed, None, "orphan")
        if size == 0:
            return CacheEntry(p, "orphan", size, created, accessed, None, "zero_byte")

        m = _IMERG_RE.search(p.name)
        if m and "imerg" in str(p).lower():
            status = "valid" if self._imerg_ok(p) else "corrupt"
            return CacheEntry(p, "imerg", size, created, accessed, m.group(1), status)
        m = _SRTM_RE.search(p.name)
        if m and "srtm" in str(p).lower():
            status = "valid" if self._srtm_ok(p) else "corrupt"
            return CacheEntry(p, "srtm", size, created, accessed, m.group(1).upper(), status)
        return CacheEntry(p, "orphan", size, created, accessed, None, "unexpected")

    @staticmethod
    def _imerg_ok(p: Path) -> bool:
        # Cheap header check: NetCDF classic ('CDF') or HDF5 ('\x89HDF').
        try:
            with open(p, "rb") as f:
                head = f.read(8)
            return head[:3] == b"CDF" or head[:4] == b"\x89HDF"
        except OSError:
            return False

    @staticmethod
    def _srtm_ok(p: Path) -> bool:
        try:
            return zipfile.is_zipfile(p)
        except OSError:
            return False

    def scan(self) -> list[CacheEntry]:
        entries = []
        for base in (self.imerg_dir, self.srtm_dir):
            if base.exists():
                for p in base.rglob("*"):
                    if p.is_file() and p.name != _INDEX_NAME:
                        entries.append(self._classify(p))
        return entries

    # ---------- inspection ----------

    def free_gb(self) -> float:
        import shutil
        pth = self.root if self.root.exists() else self.root.parent
        while not pth.exists() and pth.parent != pth:
            pth = pth.parent
        return shutil.disk_usage(str(pth)).free / _GB

    def inspect(self) -> dict:
        entries = self.scan()
        imerg = [e for e in entries if e.kind == "imerg" and e.status == "valid"]
        srtm = [e for e in entries if e.kind == "srtm" and e.status == "valid"]
        orphan = [e for e in entries if e.kind == "orphan" or e.status in ("corrupt", "zero_byte")]
        isz = sum(e.size for e in imerg)
        ssz = sum(e.size for e in srtm)
        osz = sum(e.size for e in orphan)
        lru = min(entries, key=lambda e: e.last_accessed, default=None)
        oldest = min(entries, key=lambda e: e.created_at, default=None)
        return {
            "cache_root": str(self.root),
            "imerg": {"count": len(imerg), "bytes": isz, "mb": round(isz / 1e6, 2),
                      "limit_gb": self.policy.imerg_cache_limit_gb},
            "srtm": {"count": len(srtm), "bytes": ssz, "mb": round(ssz / 1e6, 2),
                     "limit_gb": self.policy.srtm_cache_limit_gb},
            "orphan_invalid": {"count": len(orphan), "bytes": osz, "mb": round(osz / 1e6, 2)},
            "total": {"count": len(imerg) + len(srtm), "bytes": isz + ssz,
                      "mb": round((isz + ssz) / 1e6, 2), "gb": round((isz + ssz) / _GB, 3)},
            "max_cache_gb": self.policy.max_cache_size_gb,
            "min_free_disk_gb": self.policy.min_free_disk_gb,
            "free_disk_gb": round(self.free_gb(), 2),
            "over_max_cache": (isz + ssz) / _GB > self.policy.max_cache_size_gb,
            "oldest_entry": oldest.to_dict() if oldest else None,
            "lru_entry": lru.to_dict() if lru else None,
            "eviction_candidates": len(orphan),
        }

    # ---------- eviction planning ----------

    def _eligible_order(self, entries, pinned, retention_now, extra_pressure) -> list[tuple[CacheEntry, str]]:
        """Return (entry, reason) list in deterministic eviction order."""
        pinned = {str(Path(p).resolve()) for p in (pinned or set())}

        def is_pinned(e):
            try:
                return str(e.path.resolve()) in pinned
            except OSError:
                return False

        orphans = [e for e in entries if (e.kind == "orphan" or e.status in ("corrupt", "zero_byte"))
                   and not is_pinned(e)]
        imerg = [e for e in entries if e.kind == "imerg" and e.status == "valid" and not is_pinned(e)]
        srtm = [e for e in entries if e.kind == "srtm" and e.status == "valid" and not is_pinned(e)]

        # stable sort: oldest last_accessed first, then path
        keyf = lambda e: (e.last_accessed, str(e.path))
        imerg.sort(key=keyf)
        srtm.sort(key=keyf)
        orphans.sort(key=keyf)

        imerg_exp = self.policy.imerg_retention_days * 86400
        srtm_exp = self.policy.srtm_retention_days * 86400

        ordered: list[tuple[CacheEntry, str]] = []
        # 1. orphans / invalid always first
        ordered += [(e, f"orphan/invalid:{e.status}") for e in orphans]
        # 2. expired IMERG
        ordered += [(e, "imerg_expired") for e in imerg
                    if retention_now - e.last_accessed > imerg_exp]
        # 3. LRU IMERG (remaining)
        ordered += [(e, "imerg_lru") for e in imerg
                    if retention_now - e.last_accessed <= imerg_exp]
        # 4/5. SRTM only under stronger pressure: expired first, then LRU
        if extra_pressure:
            ordered += [(e, "srtm_expired") for e in srtm
                        if retention_now - e.last_accessed > srtm_exp]
            ordered += [(e, "srtm_lru") for e in srtm
                        if retention_now - e.last_accessed <= srtm_exp]
        return ordered

    def plan_eviction(self, *, pinned: Optional[Iterable] = None,
                      needed_free_bytes: int = 0,
                      now: Optional[float] = None) -> EvictionPlan:
        """Deterministic plan to (a) satisfy the max-cache soft cap and per-dataset
        limits, and (b) free `needed_free_bytes` for a pending download while
        keeping >= min_free. Never includes pinned paths. Dry by nature — applying
        is a separate step."""
        now = now if now is not None else time.time()
        entries = self.scan()
        isz = sum(e.size for e in entries if e.kind == "imerg" and e.status == "valid")
        ssz = sum(e.size for e in entries if e.kind == "srtm" and e.status == "valid")
        total = isz + ssz
        free = self.free_gb() * _GB

        max_bytes = self.policy.max_cache_size_gb * _GB
        imerg_limit = self.policy.imerg_cache_limit_gb * _GB
        srtm_limit = self.policy.srtm_cache_limit_gb * _GB
        min_free = self.policy.min_free_disk_gb * _GB

        # Bytes a pending download needs freed on DISK to keep min_free.
        need_for_dl = max(0, needed_free_bytes + min_free - free)

        def build(extra_pressure):
            p = EvictionPlan()
            ordered = self._eligible_order(entries, pinned, now, extra_pressure)
            # Two independent accumulators:
            #   disk_freed : all removals (counts toward the download min-free need)
            #   cap_freed  : valid-entry removals only (counts toward the size cap)
            disk_freed = 0
            imerg_removed = 0
            srtm_removed = 0
            for e, reason in ordered:
                if reason.startswith("orphan/invalid"):
                    p.to_remove.append(e); p.reasons[str(e.path)] = reason
                    disk_freed += e.size
                    continue
                cap_freed = imerg_removed + srtm_removed
                total_valid_remaining = total - cap_freed
                cap_unmet = total_valid_remaining > max_bytes
                dl_unmet = disk_freed < need_for_dl
                imerg_over = (isz - imerg_removed) > imerg_limit
                srtm_over = (ssz - srtm_removed) > srtm_limit
                if e.kind == "imerg":
                    if cap_unmet or imerg_over or dl_unmet:
                        p.to_remove.append(e); p.reasons[str(e.path)] = reason
                        disk_freed += e.size; imerg_removed += e.size
                elif e.kind == "srtm" and extra_pressure:
                    if cap_unmet or srtm_over or dl_unmet:
                        p.to_remove.append(e); p.reasons[str(e.path)] = reason
                        disk_freed += e.size; srtm_removed += e.size
            p.bytes_freed = disk_freed
            return p

        plan = build(extra_pressure=False)
        valid_removed = sum(e.size for e in plan.to_remove
                            if e.kind in ("imerg", "srtm"))
        still_over_cap = (total - valid_removed) > max_bytes
        still_need_dl = (need_for_dl > 0) and (plan.bytes_freed < need_for_dl)
        if still_over_cap or still_need_dl:
            plan = build(extra_pressure=True)   # escalate: allow SRTM eviction
        return plan

    def apply_eviction(self, plan: EvictionPlan, *, dry_run: bool = True) -> dict:
        removed, removed_bytes = [], 0
        for e in plan.to_remove:
            if dry_run:
                removed.append(str(e.path)); removed_bytes += e.size
                continue
            try:
                e.path.unlink()
                rel = self._rel(e.path)
                self._index.pop(rel, None)
                removed.append(str(e.path)); removed_bytes += e.size
            except OSError:
                pass
        if not dry_run and removed:
            self._save_index()
        return {"dry_run": dry_run, "removed_count": len(removed),
                "removed_bytes": removed_bytes, "removed_mb": round(removed_bytes / 1e6, 2),
                "removed": removed}

    # ---------- high-level operations ----------

    def run_maintenance(self, *, pinned=None, dry_run: bool = True, now=None) -> dict:
        plan = self.plan_eviction(pinned=pinned, now=now)
        applied = self.apply_eviction(plan, dry_run=dry_run)
        return {"plan": plan.summary(), "applied": applied,
                "inspect_after": None if dry_run else self.inspect()}

    def ensure_space_for(self, needed_bytes: int, *, pinned=None, dry_run: bool = False,
                         now=None) -> dict:
        """Guarantee a pending download of `needed_bytes` keeps free >= min_free,
        evicting eligible non-pinned entries per policy if necessary. Returns
        {ok, freed_bytes, plan, free_after_estimate_gb}."""
        min_free = self.policy.min_free_disk_gb * _GB
        free = self.free_gb() * _GB
        if free - needed_bytes >= min_free:
            return {"ok": True, "evicted": False, "freed_bytes": 0,
                    "free_after_estimate_gb": round((free - needed_bytes) / _GB, 2),
                    "plan": EvictionPlan().summary()}
        plan = self.plan_eviction(pinned=pinned, needed_free_bytes=needed_bytes, now=now)
        applied = self.apply_eviction(plan, dry_run=dry_run)
        freed = applied["removed_bytes"]
        free_after = free + freed - needed_bytes
        return {"ok": free_after >= min_free, "evicted": bool(applied["removed_count"]),
                "freed_bytes": freed, "dry_run": dry_run,
                "free_after_estimate_gb": round(free_after / _GB, 2),
                "plan": plan.summary()}


__all__ = ["CacheManager", "CacheEntry", "EvictionPlan"]
