"""
OpenHeat v0.9-gamma: split the multi-hour UMEP met forcing file into 5
single-hour met files.

v2 hotfix: duplicates each data row to keep the metdata array 2D in
SOLWEIG v2025a (the algorithm crashes with `IndexError: too many indices`
on a 1D array because np.loadtxt collapses single-row files to 1D).

Two identical rows produce two identical Tmrt computations whose average
equals the single-hour Tmrt - no information loss.

Usage:
    python scripts/v09_gamma_split_met_per_hour.py
"""
from __future__ import annotations

from pathlib import Path

SRC = Path("data/solweig/v09_met_forcing_2026_05_07_S128.txt")
OUT_DIR = SRC.parent


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(f"Source met file not found: {SRC}")

    text = SRC.read_text().splitlines()
    if not text:
        raise ValueError(f"Source met file empty: {SRC}")

    header = text[0]
    if not header.startswith("%"):
        raise ValueError(f"Header line does not start with '%': {header[:40]}")

    data_rows = [line for line in text[1:] if line.strip() and not line.startswith("%")]
    print(f"[INFO] header: {header}")
    print(f"[INFO] {len(data_rows)} data rows in source")

    for line in data_rows:
        parts = line.split()
        if len(parts) < 4:
            print(f"[WARN] skipping malformed row: {line[:60]}")
            continue
        try:
            hh = int(parts[2])
        except ValueError:
            print(f"[WARN] cannot parse hour from row: {line[:60]}")
            continue

        out_fp = OUT_DIR / f"v09_met_forcing_2026_05_07_S128_h{hh:02d}.txt"
        # Duplicate the data row so SOLWEIG sees a 2D metdata array.
        # Identical rows -> identical per-step Tmrt -> average equals single-hour Tmrt.
        out_fp.write_text(header + "\n" + line + "\n" + line + "\n")
        print(f"[OK] {out_fp.name} (hour {hh:02d}, 2 identical rows)")

    print(f"\n[DONE] wrote {len(data_rows)} single-hour met files to {OUT_DIR}")
    print("Each file contains 2 identical data rows to avoid the SOLWEIG v2025a 1D-array bug.")


if __name__ == "__main__":
    main()
