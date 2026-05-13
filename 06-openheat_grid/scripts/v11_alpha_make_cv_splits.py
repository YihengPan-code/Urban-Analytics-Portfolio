from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from v11_lib import read_json, ensure_dir, write_md, df_to_md_table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v11/v11_alpha_archive_config.example.json")
    args = ap.parse_args()
    cfg = read_json(args.config)
    out_dir = ensure_dir(cfg["paths"].get("output_dir", "outputs/v11_alpha_archive"))
    pairs_path = Path(cfg["paths"].get("paired_dataset_csv", "data/calibration/v11/v11_station_weather_pairs.csv"))
    if not pairs_path.exists():
        raise SystemExit(f"[ERROR] paired dataset not found: {pairs_path}")
    df = pd.read_csv(pairs_path, low_memory=False)
    # Accept both legacy build_pairs ("timestamp") and v11 collector ("timestamp_sgt") outputs.
    if "timestamp" not in df.columns and "timestamp_sgt" in df.columns:
        df["timestamp"] = df["timestamp_sgt"]
    elif "timestamp" not in df.columns:
        raise SystemExit(
            f"[ERROR] paired dataset {pairs_path} has neither 'timestamp' nor 'timestamp_sgt' column. "
            f"Columns: {list(df.columns)[:20]}..."
        )
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["date"] = df["timestamp"].dt.date.astype(str)
    df = df.reset_index().rename(columns={"index": "row_id"})

    splits = df[["row_id", "station_id", "timestamp", "date"]].copy()
    # LOSO fold: one held-out station per fold.
    splits["fold_loso"] = splits["station_id"].astype(str)

    # Chronological blocked folds by date.
    n_blocks = int(cfg.get("cv", {}).get("n_time_blocks", 5))
    days = sorted(splits["date"].dropna().unique().tolist())
    day_to_block = {}
    if days:
        chunks = np.array_split(np.arange(len(days)), min(n_blocks, len(days)))
        for i, idxs in enumerate(chunks):
            for j in idxs:
                day_to_block[days[int(j)]] = f"time_block_{i+1:02d}"
    splits["fold_time_block"] = splits["date"].map(day_to_block).fillna("time_block_unknown")

    # Last block as a simple holdout suggestion; not used automatically by beta unless chosen.
    last_block = sorted(set(day_to_block.values()))[-1] if day_to_block else "time_block_unknown"
    splits["suggested_holdout"] = (splits["fold_time_block"] == last_block).astype(int)

    split_path = Path(cfg["paths"].get("cv_splits_csv", "data/calibration/v11/v11_cv_splits.csv"))
    ensure_dir(split_path.parent)
    out = splits.copy()
    out["timestamp"] = out["timestamp"].astype(str)
    out.to_csv(split_path, index=False)

    summary = pd.concat([
        splits.groupby("fold_loso").size().reset_index(name="n_rows").assign(cv_scheme="loso").rename(columns={"fold_loso": "fold"}),
        splits.groupby("fold_time_block").size().reset_index(name="n_rows").assign(cv_scheme="time_block").rename(columns={"fold_time_block": "fold"}),
    ], ignore_index=True)
    report = [
        "# OpenHeat v1.1-alpha CV split plan",
        "",
        f"Pairs: `{pairs_path}`",
        f"CV splits: `{split_path}`",
        "",
        "## Fold summary",
        df_to_md_table(summary, max_rows=60),
        "",
        "## Interpretation",
        "- `fold_loso`: leave-one-station-out; best for testing spatial generalization.",
        "- `fold_time_block`: chronological blocked time split; best for testing temporal generalization.",
        "- Avoid random split because adjacent 15-min/hourly observations are highly autocorrelated.",
    ]
    report_path = out_dir / "v11_cv_split_plan.md"
    write_md(report_path, "\n".join(report))
    print(f"[OK] CV splits: {split_path}")
    print(f"[OK] report: {report_path}")


if __name__ == "__main__":
    main()
