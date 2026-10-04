"""CLI for CDSE Sentinel-2 L2A ingestion (Module 1).

Usage:
    # Live smoke on the pre-configured Wayanad AOI:
    python scripts/ingest_sentinel2.py --smoke

    # Custom bbox + date:
    python scripts/ingest_sentinel2.py \
        --bbox 75.70 11.50 76.20 11.95 \
        --start 2024-07-25T00:00:00Z --end 2024-08-10T23:59:59Z \
        --max-cloud 30

    # Dry run (no download; catalog search only) - handy without live creds:
    python scripts/ingest_sentinel2.py --smoke --dry-run

Credentials:
    Set CDSE_USERNAME + CDSE_PASSWORD in the environment, OR place a
    KEY=VALUE cdse.env file in <repo>/secrets/. Nothing about credentials
    is ever accepted on the command line.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import yaml

from src.ingestion import (
    ingest, IngestionRequest, IngestionStatus,
)
from src.ingestion.aoi import bbox_to_wkt
from src.ingestion.auth import CDSEAuth
from src.ingestion.catalog import CatalogClient


def _load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _build_request_from_config(cfg: dict) -> IngestionRequest:
    smoke = cfg["smoke_test"]
    aoi = cfg["aois"][smoke["aoi_ref"]]
    bx = aoi["bbox"]
    wkt = bbox_to_wkt(bx["west"], bx["south"], bx["east"], bx["north"])
    return IngestionRequest(
        aoi_wkt=wkt,
        start=smoke["start"], end=smoke["end"],
        max_cloud_cover=float(smoke.get("max_cloud_cover", 30.0)),
        target_date=smoke.get("target_date"),
        aoi_label=aoi.get("label", smoke["aoi_ref"]),
    )


def _build_request_from_cli(args, cfg: dict) -> IngestionRequest:
    if args.bbox is None:
        raise SystemExit("--bbox WEST SOUTH EAST NORTH is required "
                         "unless --smoke is used")
    w, s, e, n = args.bbox
    wkt = bbox_to_wkt(w, s, e, n)
    defaults = cfg.get("request_defaults", {})
    return IngestionRequest(
        aoi_wkt=wkt,
        start=args.start, end=args.end,
        max_cloud_cover=float(args.max_cloud
                              or defaults.get("max_cloud_cover", 30.0)),
        target_date=args.target_date,
        aoi_label=args.aoi_label or "cli",
    )


def main():
    ap = argparse.ArgumentParser(description="CDSE Sentinel-2 L2A ingestion (Module 1)")
    ap.add_argument("--config", default=str(REPO / "configs" / "ingestion.yaml"))
    ap.add_argument("--smoke", action="store_true",
                    help="Use the pre-configured smoke-test AOI + date range")
    ap.add_argument("--bbox", type=float, nargs=4, metavar=("W", "S", "E", "N"))
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--max-cloud", type=float, default=None)
    ap.add_argument("--target-date", default=None)
    ap.add_argument("--aoi-label", default=None)
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="Search catalog + rank; do NOT download.")
    ap.add_argument("--output",
                    default=str(REPO / "outputs" / "integration"
                                / "phase_detection_live_ingestion_last_result.json"))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cfg = _load_config(Path(args.config))
    data_dir = Path(args.data_dir or cfg["data_dir"])
    secrets_dir = REPO / "secrets"

    request = (_build_request_from_config(cfg) if args.smoke
               else _build_request_from_cli(args, cfg))

    if args.dry_run:
        # Search-only path: rank, print the top candidate, exit.
        from src.ingestion.aoi import parse_aoi_wkt
        from src.ingestion.catalog import apply_filters
        from src.ingestion.ranking import rank_products
        auth = CDSEAuth()
        catalog = CatalogClient(auth=auth, secrets_dir=secrets_dir)
        try:
            candidates = catalog.search(request)
        except Exception as e:
            print(f"[dry-run] catalog search failed: {e}", file=sys.stderr)
            sys.exit(2)
        aoi = parse_aoi_wkt(request.aoi_wkt)
        kept, stats = apply_filters(candidates, request, aoi)
        ranked = rank_products(kept, request)
        report = {
            "aoi_label": request.aoi_label,
            "start": request.start, "end": request.end,
            "candidates": len(candidates),
            "kept_after_filter": len(kept),
            "filter_stats": stats,
            "top": ranked[0].to_dict() if ranked else None,
        }
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2, default=str))
        return

    result = ingest(
        request,
        data_dir=data_dir,
        secrets_dir=secrets_dir,
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        json.dumps(result.to_dict(), indent=2, default=str), encoding="utf-8")
    if result.status == IngestionStatus.FAILED:
        print(f"[FAILED] {result.error.get('code')}: {result.error.get('message')}",
              file=sys.stderr)
        sys.exit(1)
    print(f"[{result.status.value}] "
          f"cache={result.cache_status.value} "
          f"path={result.local_path} "
          f"size={result.file_size_bytes} bytes")


if __name__ == "__main__":
    main()
