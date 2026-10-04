"""Persistent site registry with opaque canonical identifiers.

The canonical `site_id` is an OPAQUE sequential token, `SITE-000001`. It is
deliberately NOT derived from geohash or first-detection date — those are
stored as attributes, not identity, so a site's ID never changes when its
geometry is refined or re-observed.

Scope (Phase 1):
  * explicit `register(...)` and `get(...)` / `find_by_source_ref(...)`.
  * JSON-file persistence (atomic write).
  * NO automatic polygon matching — a caller decides when two observations are
    the same site and passes an existing `site_id` to update it.

This module does not modify any Detection/Monitoring/Prediction artifact. The
registry file lives wherever the caller points it (default: alongside the
integration outputs).
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class SiteRecord:
    site_id: str
    first_detection_time: Optional[str]
    last_seen_time: Optional[str]
    geometry: Optional[dict]
    centroid: Optional[dict]
    status: str = "active"
    source: Optional[str] = None
    # A place to stash the module-local id (e.g. Detection's "LS-001") WITHOUT
    # making it the identity. Never written back into Detection.
    source_ref: Optional[str] = None
    attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class SiteRegistry:
    """File-backed registry of canonical sites."""

    ID_PREFIX = "SITE-"
    ID_WIDTH = 6

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._records: dict[str, SiteRecord] = {}
        self._next_seq: int = 1
        if self.path.exists():
            self._load()

    # ---- persistence ----

    def _load(self) -> None:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._next_seq = int(raw.get("next_seq", 1))
        for rec in raw.get("sites", []):
            self._records[rec["site_id"]] = SiteRecord(**rec)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "landslideguard.site_registry/1.0",
            "next_seq": self._next_seq,
            "updated_at": _utc_now_iso(),
            "sites": [r.to_dict() for r in self._records.values()],
        }
        # Atomic write: temp file in the same dir, then replace.
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    # ---- id allocation ----

    def _mint_id(self) -> str:
        sid = f"{self.ID_PREFIX}{self._next_seq:0{self.ID_WIDTH}d}"
        self._next_seq += 1
        return sid

    # ---- public API ----

    def register(
        self,
        *,
        geometry: Optional[dict] = None,
        centroid: Optional[dict] = None,
        source: Optional[str] = None,
        source_ref: Optional[str] = None,
        first_detection_time: Optional[str] = None,
        status: str = "active",
        attributes: Optional[dict] = None,
        persist: bool = True,
    ) -> SiteRecord:
        """Create and store a new site with a freshly minted opaque id."""
        now = _utc_now_iso()
        rec = SiteRecord(
            site_id=self._mint_id(),
            first_detection_time=first_detection_time or now,
            last_seen_time=now,
            geometry=geometry,
            centroid=centroid,
            status=status,
            source=source,
            source_ref=source_ref,
            attributes=attributes or {},
        )
        self._records[rec.site_id] = rec
        if persist:
            self._save()
        return rec

    def get(self, site_id: str) -> Optional[SiteRecord]:
        return self._records.get(site_id)

    def find_by_source_ref(self, source_ref: str) -> list[SiteRecord]:
        """Look up sites by their module-local reference (e.g. 'LS-001').

        Returns all matches — the caller decides identity; the registry does
        not auto-merge.
        """
        return [r for r in self._records.values() if r.source_ref == source_ref]

    def update_last_seen(self, site_id: str, when: Optional[str] = None,
                         persist: bool = True) -> SiteRecord:
        rec = self._records[site_id]
        rec.last_seen_time = when or _utc_now_iso()
        if persist:
            self._save()
        return rec

    def set_status(self, site_id: str, status: str, persist: bool = True) -> SiteRecord:
        rec = self._records[site_id]
        rec.status = status
        if persist:
            self._save()
        return rec

    def all(self) -> list[SiteRecord]:
        return list(self._records.values())

    def __len__(self) -> int:
        return len(self._records)
