"""Phase-6 verification location matrix (data only, no logic).

Five geographically separated, REAL Indian locations taken from the frozen GLC
positive-event set (real coordinates + real event dates). Shared by the Phase-6
pytest suite (offline reference path) and the live verification script (genuine
Earthdata path) so the matrix is defined once.

These are verification coordinates, not chosen to produce any particular score.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationLocation:
    location_id: str
    sample_id: str
    region: str
    latitude: float
    longitude: float
    target_date: str      # T (event day, EXCLUDED from features)
    srtm_tile: str


PHASE6_LOCATIONS: list[VerificationLocation] = [
    VerificationLocation("location_01", "POS_4764", "Himalaya / Kashmir (North)",
                         33.4372, 75.2027, "2013-02-22", "N33E075"),
    VerificationLocation("location_02", "POS_4411", "Northeast (Sikkim)",
                         27.3390, 88.6065, "2012-06-14", "N27E088"),
    VerificationLocation("location_03", "POS_4536", "Western Ghats (Maharashtra)",
                         19.6241, 72.9084, "2012-09-04", "N19E072"),
    VerificationLocation("location_04", "POS_6250", "Central/East (Odisha border)",
                         18.3297, 82.9565, "2014-10-12", "N18E082"),
    VerificationLocation("location_05", "POS_4981", "South (Tamil Nadu / W. Ghats)",
                         10.9628, 77.5947, "2013-06-25", "N10E077"),
]


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    import math
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def pairwise_distances_km(locs=None) -> list[tuple[str, str, float]]:
    locs = locs or PHASE6_LOCATIONS
    out = []
    for i in range(len(locs)):
        for j in range(i + 1, len(locs)):
            out.append((locs[i].location_id, locs[j].location_id,
                        haversine_km(locs[i].latitude, locs[i].longitude,
                                     locs[j].latitude, locs[j].longitude)))
    return out


__all__ = ["VerificationLocation", "PHASE6_LOCATIONS",
           "haversine_km", "pairwise_distances_km"]
