#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from v11_archive_collect_once import cleanup_old_raw_json


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean old v11 raw JSON archive folders.")
    parser.add_argument("--config", default="configs/v11/v11_longterm_archive_config.example.json")
    parser.add_argument("--keep-days", type=int, default=None)
    args = parser.parse_args()
    cfg = read_json(Path(args.config))
    acfg = cfg.get("archive", {})
    raw_dir = Path(acfg.get("raw_json_dir", "data/archive/v11_longterm/raw_json"))
    keep_days = args.keep_days if args.keep_days is not None else int(acfg.get("max_raw_json_days_to_keep", 14))
    deleted = cleanup_old_raw_json(raw_dir, keep_days)
    print(f"[OK] deleted {deleted} old raw-json date directories from {raw_dir} (keep_days={keep_days})")


if __name__ == "__main__":
    main()
