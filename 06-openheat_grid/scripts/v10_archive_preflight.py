"""
scripts/v10_archive_preflight.py

Preflight check for the v1.0 long-term NEA archive collector.

Validates that the configured archive CSV is either:
  (a) absent (first run -- collector will create a fresh long-format file), or
  (b) present AND in long format (has 'variable' and 'value' columns).

Exit codes:
  0  OK -- safe to proceed
  2  Archive exists but is NOT long format (legacy v0.6 wide format detected)
  3  Archive exists but is unreadable / empty / corrupt
  4  Other unexpected error

This is intentionally separate from the v0.9-alpha 24h pilot archive
(`data/archive/nea_realtime_observations.csv`), which is frozen as part of
the v0.9-audit-freeze and must not be appended to during v1.0 development.

Usage:
    python scripts/v10_archive_preflight.py --archive data\archive\nea_realtime_observations_v10_longterm.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REQUIRED_LONG_FORMAT_COLS = {"variable", "value"}
RECOMMENDED_COLS = {"api_name", "station_id", "timestamp_sgt", "variable", "value"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight check for v1.0 long-term NEA archive."
    )
    parser.add_argument(
        "--archive",
        required=True,
        help="Path to the v1.0 long-term archive CSV.",
    )
    args = parser.parse_args()

    archive_path = Path(args.archive)
    print(f"[CHECK] archive path: {archive_path}")

    if not archive_path.exists():
        print("[OK] archive does not exist yet; collector will create it on first round.")
        return 0

    try:
        # Lazy-import pandas so a missing pandas gives a clearer error than the inline -c form.
        import pandas as pd

        # Read header only -- fast and avoids loading huge files.
        header_df = pd.read_csv(archive_path, nrows=0)
        cols = set(header_df.columns)
    except Exception as exc:
        print(f"[ERROR] could not read archive header: {exc!r}")
        return 3

    print(f"[CHECK] columns ({len(cols)}): {sorted(cols)[:12]}...")

    if not REQUIRED_LONG_FORMAT_COLS.issubset(cols):
        print("[STOP] archive is missing required long-format columns "
              f"{sorted(REQUIRED_LONG_FORMAT_COLS)}.")
        print("[STOP] this looks like the legacy v0.6 wide format. "
              "Back it up and remove it before continuing:")
        print(f"       copy {archive_path} {archive_path.with_suffix('.wide_backup.csv')}")
        print(f"       del  {archive_path}")
        return 2

    missing_recommended = RECOMMENDED_COLS - cols
    if missing_recommended:
        print(f"[WARN] archive is long-format but missing recommended cols: "
              f"{sorted(missing_recommended)}")
        print("[WARN] collector will continue, but downstream pairing scripts may break.")

    # Cheap row count via fast c-engine read of a single column.
    try:
        n_rows = sum(1 for _ in open(archive_path, encoding="utf-8")) - 1  # minus header
        n_rows = max(n_rows, 0)
    except Exception:
        n_rows = -1

    print(f"[OK] archive is long format. Approx rows: {n_rows}.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("[ABORT] preflight interrupted by user.")
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] unexpected preflight failure: {exc!r}")
        sys.exit(4)
