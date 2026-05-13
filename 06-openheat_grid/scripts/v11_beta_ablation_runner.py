#!/usr/bin/env python
"""OpenHeat v1.1-beta.1 ablation orchestrator.

Runs 4 calibration ablations to definitively answer:
  "Is the 0.08°C MAE degradation vs v0.9 caused by stale_or_too_far rows,
   or by multi-day weather regime variance?"

Each run uses the same script (v11_beta_calibration_baselines.py) with a
different filter_mode applied to the v0.9-augmented pairs CSV. After all
4 runs complete, generates a comparison summary CSV + report.

Runs:
  A. all                       (no filtering; β.1 smoke test behavior)
  B. retrospective_calibration (proper retrospective filter; β formal pass)
  C. fresh_v11_only            (only fresh collector rows, excludes migrated)
  D. migrated_only             (only migrated v0.9/v10 archive rows)

Compare M3/M4 LOSO MAE across A/B/C/D:
  - If B/C MAE close to v0.9's 0.60°C: stale rows ARE main cause; finding 4.7 confirmed
  - If B/C MAE still ~0.68°C: multi-day weather is main cause; finding 4.7 needs revision

Usage:
    python scripts/v11_beta_ablation_runner.py \\
        --base-config configs/v11/v11_beta_calibration_config_v091.json

This is read-only on the archive; the loop can continue uninterrupted.
"""
from __future__ import annotations

import argparse
import json
import sys
import subprocess
from pathlib import Path

import pandas as pd


ABLATIONS = [
    {
        "name": "A_all",
        "filter_mode": "all",
        "description": "All 5,723 rows (β.1 smoke test behavior, no filter)",
    },
    {
        "name": "B_retrospective",
        "filter_mode": "retrospective_calibration",
        "description": "Valid-time-aligned weather only (proper retrospective filter)",
    },
    {
        "name": "C_fresh_v11",
        "filter_mode": "fresh_v11_only",
        "description": "Only fresh v11 collector rows (excludes migrated v0.9/v10)",
    },
    {
        "name": "D_migrated",
        "filter_mode": "migrated_only",
        "description": "Only migrated v0.9/v10 archive rows",
    },
]


def make_config_variant(base_cfg: dict, name: str, filter_mode: str) -> dict:
    """Build a config variant with a specific filter_mode + output suffix."""
    cfg = json.loads(json.dumps(base_cfg))  # deep copy
    cfg.setdefault("data_filters", {})
    cfg["data_filters"]["filter_mode"] = filter_mode
    cfg["data_filters"]["output_dir_suffix"] = f"ablation_{name}"
    # Disable station exclusion for ablation; we want all stations in each filter
    cfg["data_filters"]["exclude_station_ids"] = []
    return cfg


def parse_metrics(metrics_path: Path) -> pd.DataFrame:
    """Read a metrics CSV from one baseline run. Return summary keyed on (model, cv_scheme)."""
    if not metrics_path.exists():
        return pd.DataFrame()
    return pd.read_csv(metrics_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ablation orchestrator for β.1 post-mortem.")
    parser.add_argument(
        "--base-config",
        default="configs/v11/v11_beta_calibration_config_v091.json",
        help="base β config to use as template",
    )
    parser.add_argument(
        "--baseline-script",
        default="scripts/v11_beta_calibration_baselines.py",
        help="path to v11_beta_calibration_baselines.py",
    )
    parser.add_argument(
        "--ablation-config-dir",
        default="configs/v11/_ablation",
        help="directory to write per-ablation config files",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/v11_beta_calibration",
        help="base output directory (each ablation writes to a sub-folder)",
    )
    parser.add_argument(
        "--skip-runs",
        action="store_true",
        help="skip the subprocess runs (assume metrics already exist); only aggregate",
    )
    args = parser.parse_args()

    base_cfg_path = Path(args.base_config)
    if not base_cfg_path.exists():
        print(f"[ERROR] base config not found: {base_cfg_path}", file=sys.stderr)
        return 2

    base_cfg = json.loads(base_cfg_path.read_text())
    ablation_dir = Path(args.ablation_config_dir)
    ablation_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: write per-ablation configs
    print("=" * 70)
    print("OpenHeat v1.1-β.1 ablation orchestrator")
    print("=" * 70)
    print()
    cfg_paths = []
    for ab in ABLATIONS:
        cfg = make_config_variant(base_cfg, ab["name"], ab["filter_mode"])
        cfg_path = ablation_dir / f"v11_beta_ablation_{ab['name']}.json"
        cfg_path.write_text(json.dumps(cfg, indent=2))
        cfg_paths.append((ab, cfg_path))
        print(f"  [config] {cfg_path}")

    # Step 2: run baselines for each ablation
    if not args.skip_runs:
        print()
        for ab, cfg_path in cfg_paths:
            print()
            print(f"--- Ablation {ab['name']}: {ab['description']} ---")
            cmd = [sys.executable, args.baseline_script, "--config", str(cfg_path)]
            print(f"  cmd: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            # Show the tail of stdout for the row-count + output info
            tail_lines = result.stdout.strip().split("\n")[-12:]
            for ln in tail_lines:
                print(f"  {ln}")
            if result.returncode != 0:
                print(f"  [ERROR] return code {result.returncode}")
                if result.stderr:
                    print(f"  stderr: {result.stderr[:500]}")
    else:
        print()
        print("[INFO] --skip-runs set; assuming metrics CSVs already exist")

    # Step 3: aggregate metrics
    print()
    print("=" * 70)
    print("Aggregating metrics across ablations")
    print("=" * 70)
    rows = []
    for ab, cfg_path in cfg_paths:
        metrics_path = Path(args.output_dir) / f"ablation_{ab['name']}" / "v11_beta_calibration_metrics.csv"
        m = parse_metrics(metrics_path)
        if m.empty:
            print(f"  [WARN] no metrics for {ab['name']}: {metrics_path}")
            continue
        n_rows = int(m["n"].iloc[0]) if "n" in m.columns and len(m) > 0 else 0
        for _, r in m.iterrows():
            rows.append({
                "ablation": ab["name"],
                "filter_mode": ab["filter_mode"],
                "description": ab["description"],
                "n_rows": n_rows,
                "model": r["model"],
                "cv_scheme": r["cv_scheme"],
                "mae": r["mae"],
                "rmse": r["rmse"],
                "bias": r["bias"],
                "r2": r["r2"],
            })

    if not rows:
        print("[ERROR] no ablation metrics found; cannot summarize")
        return 1

    summary = pd.DataFrame(rows)
    summary_path = Path(args.output_dir) / "v11_beta_ablation_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"  [write] {summary_path}")

    # Focused comparison: M3/M4 LOSO MAE across ablations
    focus_models = ["M0_raw_proxy", "M1_global_bias", "M1b_period_bias",
                    "M3_weather_ridge", "M4_inertia_ridge",
                    "M5_v10_morphology_ridge"]
    focus = summary[
        (summary["cv_scheme"] == "loso") &
        (summary["model"].isin(focus_models))
    ].copy()
    pivot = focus.pivot(index="model", columns="ablation", values="mae").round(3)
    # Reorder ablations for readability
    ordered_cols = ["A_all", "B_retrospective", "C_fresh_v11", "D_migrated"]
    pivot = pivot.reindex(columns=[c for c in ordered_cols if c in pivot.columns])
    # Reorder rows
    pivot = pivot.reindex([m for m in focus_models if m in pivot.index])

    pivot_path = Path(args.output_dir) / "v11_beta_ablation_loso_mae_pivot.csv"
    pivot.to_csv(pivot_path)

    print()
    print("=" * 70)
    print("LOSO MAE (°C) by model × ablation")
    print("=" * 70)
    print()
    print(pivot.to_string())
    print()

    # n_rows summary
    n_rows_by_ab = summary[["ablation", "n_rows"]].drop_duplicates().set_index("ablation")["n_rows"]
    print("Row counts per ablation:")
    for ab_name in ordered_cols:
        if ab_name in n_rows_by_ab.index:
            print(f"  {ab_name:<20}: {int(n_rows_by_ab[ab_name]):>6,} rows")
    print()

    # Verdict
    print("=" * 70)
    print("Verdict (auto-interpretation)")
    print("=" * 70)
    if "M3_weather_ridge" in pivot.index:
        m3_row = pivot.loc["M3_weather_ridge"]
        v09_target = 0.595  # v0.9-beta reported M3 MAE
        print(f"  v0.9-beta target for M3 LOSO MAE: {v09_target}°C")
        for ab_name in ordered_cols:
            if ab_name in m3_row.index and pd.notna(m3_row[ab_name]):
                delta = m3_row[ab_name] - v09_target
                marker = "✓ close" if abs(delta) <= 0.03 else ("↑ higher" if delta > 0 else "↓ lower")
                print(f"  {ab_name:<20}: M3 MAE = {m3_row[ab_name]:.3f}°C  (Δ = {delta:+.3f}, {marker})")
        print()
        # Comparison logic
        if "A_all" in m3_row.index and "B_retrospective" in m3_row.index:
            ba_delta = m3_row["B_retrospective"] - m3_row["A_all"]
            print(f"  B - A delta: {ba_delta:+.3f}°C")
            if abs(ba_delta) < 0.01:
                print("    → A and B nearly identical: stale-rows do NOT dominate the difference")
                print("    → finding 4.7 needs revision: multi-day weather regime is main cause")
            elif ba_delta < -0.03:
                print("    → B significantly better than A: stale rows DO contaminate training")
                print("    → finding 4.7 confirmed: stale-dilution is real")
            else:
                print("    → ambiguous: B is somewhat better but not dramatically so")
        if "C_fresh_v11" in m3_row.index and pd.notna(m3_row["C_fresh_v11"]):
            cv09_delta = m3_row["C_fresh_v11"] - v09_target
            if abs(cv09_delta) <= 0.03:
                print()
                print("    → Fresh-v11-only result IS close to v0.9 baseline")
                print("    → v0.9 framework transfers cleanly to fresh v11 archive")

    print()
    print("[DONE] Compare full table at:", summary_path)
    print("       Pivot for dissertation reference:", pivot_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
