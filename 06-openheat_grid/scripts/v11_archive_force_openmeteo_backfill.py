"""One-time helper: clear Open-Meteo state and optionally set past_days for hindcast back-fill.

Run BEFORE the next scripts/v11_archive_collect_once.bat to force Open-Meteo
re-fetch with hindcast covering the migrated NEA archive period.

Usage:
  python scripts/v11_archive_force_openmeteo_backfill.py            # default past_days=7
  python scripts/v11_archive_force_openmeteo_backfill.py --past-days 4
  python scripts/v11_archive_force_openmeteo_backfill.py --restore  # restore past_days=1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v11/v11_longterm_archive_config.example.json")
    ap.add_argument("--state", default="data/archive/v11_longterm/archive_state.json")
    ap.add_argument("--past-days", type=int, default=7,
                    help="Open-Meteo past_days to set in config. Use 7 for one-time back-fill, then run --restore.")
    ap.add_argument("--restore", action="store_true",
                    help="Restore past_days to 1 (call this AFTER one back-fill round).")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    state_path = Path(args.state)

    # 1. Update config past_days.
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        new_pd = 1 if args.restore else int(args.past_days)
        old_pd = cfg.get("openmeteo", {}).get("past_days")
        cfg.setdefault("openmeteo", {})["past_days"] = new_pd
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] {cfg_path}: past_days {old_pd} -> {new_pd}")
    else:
        print(f"[WARN] config not found: {cfg_path}")

    # 2. Clear Open-Meteo state lock so next run re-fetches.
    if not args.restore and state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        had = state.pop("last_openmeteo_run_utc", None)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] {state_path}: cleared last_openmeteo_run_utc (was {had})")
    elif args.restore:
        print("[INFO] --restore mode: not clearing state lock (no need to re-fetch).")
    else:
        print(f"[INFO] state file not found yet: {state_path} (will be created on first collect)")

    if args.restore:
        print("\n[NEXT] Run scripts\\v11_archive_collect_once.bat normally; past_days=1 is the steady-state cadence.")
    else:
        print(f"\n[NEXT] Run scripts\\v11_archive_collect_once.bat ONCE to back-fill {new_pd} days of Open-Meteo hindcast.")
        print("       Then: python scripts\\v11_archive_force_openmeteo_backfill.py --restore")


if __name__ == "__main__":
    main()
