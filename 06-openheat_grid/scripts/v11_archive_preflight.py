#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def exists_msg(path: str) -> str:
    p = Path(path)
    return "OK" if p.exists() else "MISSING"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v11/v11_longterm_archive_config.example.json")
    args = parser.parse_args()
    cfg = read_json(Path(args.config))
    print("OpenHeat v1.1 archive preflight")
    print("=" * 60)
    print("Config:", args.config)
    print("Archive root:", cfg["archive"]["root_dir"])
    print("Data.gov.sg API key env:", cfg.get("data_gov_sg", {}).get("api_key_env"), "=", "SET" if os.getenv(cfg.get("data_gov_sg", {}).get("api_key_env", "")) else "not set")
    print("\nConfigured NEA endpoints:")
    for ep in cfg.get("data_gov_sg", {}).get("endpoints", []):
        print(f"  - {ep.get('name'):<18} enabled={ep.get('enabled', True)} variable={ep.get('variable')} url={ep.get('url')}")
    print("\nV10 feature inputs:")
    for k, v in cfg.get("v10_features", {}).items():
        if k.endswith("_csv"):
            print(f"  - {k:<24} {exists_msg(v):<8} {v}")
    stmap = cfg.get("v10_features", {}).get("station_to_cell_csv")
    if stmap and Path(stmap).exists():
        df = pd.read_csv(stmap)
        print(f"\nstation_to_cell rows: {len(df)}")
        print(df.head(10).to_string(index=False))
    print("\nOpen-Meteo:")
    om = cfg.get("openmeteo", {})
    print("  enabled:", om.get("enabled"))
    print("  min_minutes_between_runs:", om.get("min_minutes_between_runs"))
    print("  explicit locations:", len(om.get("locations") or []))
    print("  station locations from WBGT:", om.get("fetch_station_locations_from_wbgt"))
    print("\n[OK] Preflight complete. Run scripts\\v11_archive_collect_once.bat for one snapshot.")


if __name__ == "__main__":
    main()
