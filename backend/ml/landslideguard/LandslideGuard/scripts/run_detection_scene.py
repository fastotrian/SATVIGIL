"""Unified entry point: dispatches to H5 or Sentinel-2 pipeline based on input.

Usage:
    # H5:
    python scripts/run_detection_scene.py --input tile.h5

    # Sentinel-2:
    python scripts/run_detection_scene.py --input S2A_*.SAFE --dem dem.tif
"""
from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--input", "-i", required=True)
    ap.add_argument("--dem", "-d", default=None)
    args, unknown = ap.parse_known_args()

    inp = Path(args.input)
    argv = ["<dispatch>"]
    if inp.suffix.lower() in (".h5", ".hdf5"):
        argv += ["--input", str(inp)] + unknown
        sys.argv = argv
        runpy.run_path(str(REPO / "scripts/run_detection_h5.py"),
                       run_name="__main__")
    else:
        if not args.dem:
            raise SystemExit("Sentinel-2 input requires --dem <path>")
        argv += ["--input", str(inp), "--dem", args.dem] + unknown
        sys.argv = argv
        runpy.run_path(str(REPO / "scripts/run_detection_sentinel2.py"),
                       run_name="__main__")


if __name__ == "__main__":
    main()
