#!/usr/bin/env python3
"""Phase 9A storage-safety check for the LandslideGuard SAR/InSAR engine.

Read-only. Performs NO SAR processing and installs nothing.

Enforces the Phase 9A safety rule: never let an install proceed on a filesystem
that would be left with less than MIN_FREE_GB of free space.

Usage:
    python storage_safety_check.py [--min-free-gb 5] [--need-gb 8] [--json]

Exit code 0 = SAFE for the requested footprint, 1 = UNSAFE / BLOCKED.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys

MIN_FREE_GB = 5.0  # required reserve on the working disk after any install

# Disks that matter on this host. WSL VHDX and default swap live under C:.
CANDIDATE_PATHS = {
    "C": r"C:\\",
    "D": r"D:\\",
    "E": r"E:\\",
}


def disk_free_gb(path: str) -> dict | None:
    try:
        total, used, free = shutil.disk_usage(path)
    except (FileNotFoundError, OSError):
        return None
    return {
        "path": path,
        "total_gb": round(total / 1024**3, 2),
        "used_gb": round(used / 1024**3, 2),
        "free_gb": round(free / 1024**3, 2),
        "free_pct": round(free / total * 100, 1) if total else 0.0,
    }


def evaluate(min_free_gb: float, need_gb: float) -> dict:
    disks = {}
    for label, path in CANDIDATE_PATHS.items():
        info = disk_free_gb(path)
        if info is None:
            continue
        # A disk is a viable install target only if it can absorb the footprint
        # AND still leave the safety reserve.
        info["can_host_install"] = info["free_gb"] >= (need_gb + min_free_gb)
        info["below_safety_reserve"] = info["free_gb"] < min_free_gb
        disks[label] = info

    viable = [d for d in disks.values() if d.get("can_host_install")]
    result = {
        "min_free_gb": min_free_gb,
        "estimated_install_need_gb": need_gb,
        "disks": disks,
        "viable_install_targets": [d["path"] for d in viable],
        "safe": bool(viable),
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-free-gb", type=float, default=MIN_FREE_GB)
    ap.add_argument("--need-gb", type=float, default=8.0,
                    help="Estimated footprint of an ISCE3+MintPy conda env (GB)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    res = evaluate(args.min_free_gb, args.need_gb)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print("Phase 9A Storage Safety Check")
        print("-" * 44)
        print(f"Safety reserve required : {res['min_free_gb']} GB")
        print(f"Estimated install need  : {res['estimated_install_need_gb']} GB")
        print()
        for label, d in res["disks"].items():
            flag = "OK  " if d["can_host_install"] else ("DANGER" if d["below_safety_reserve"] else "TIGHT")
            print(f"  {label}: free {d['free_gb']:>7} GB / {d['total_gb']:>7} GB "
                  f"({d['free_pct']:>5}%)  [{flag}]")
        print()
        if res["safe"]:
            print("RESULT: SAFE -> viable target(s): " + ", ".join(res["viable_install_targets"]))
        else:
            print("RESULT: UNSAFE / BLOCKED -> no disk can host the install "
                  "while preserving the safety reserve.")

    return 0 if res["safe"] else 1


if __name__ == "__main__":
    sys.exit(main())
