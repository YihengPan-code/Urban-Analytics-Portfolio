#!/usr/bin/env python
"""OpenHeat v1.1-β.1 fourth audit (4.3): bootstrap M4 - M3 inertia advantage CI.

Resolves friend-audit point 4.3 from the fourth audit: the M4 inertia advantage
shows a monotonic pattern with archive regime diversity (v0.9 +0.000, C_fresh
-0.001, hourly_max -0.008, hourly_mean -0.010, A_all -0.011, D_migrated -0.018),
but each value is a single point estimate without uncertainty.

This script:
  (1) Reads OOF prediction CSVs from one or more v11-β baseline runs
  (2) Recomputes per-fold M3 and M4 LOSO MAE from the predictions
  (3) Computes per-fold delta = M4_MAE - M3_MAE
  (4) Block-bootstraps over folds (n_iter=5000, default) to derive 95% CI
  (5) Outputs:
        outputs/v11_beta_calibration/bootstrap_M4_minus_M3.csv      (CI summary)
        outputs/v11_beta_calibration/fold_level_M3_M4_delta_by_dataset.csv

Block resampling at fold level is appropriate because LOSO folds are the
independent units of evaluation; resampling at row level would conflate
within-fold autocorrelation with between-fold variance.

USAGE:
    python scripts/v11_beta_bootstrap_advantage.py
        [--output-dir outputs/v11_beta_calibration]
        [--n-iter 5000]
        [--seed 42]
        [--datasets all_stations,no_S142,hourly_mean,hourly_max,...]

If --datasets is omitted, scans output-dir for any sub-folder containing
v11_beta_oof_predictions.csv.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def per_fold_mae(preds: pd.DataFrame, y_col: str, pred_col: str = "prediction_wbgt_c") -> pd.DataFrame:
    """Compute per-fold MAE for one model. Expects columns: fold, model, y_col, pred_col."""
    work = preds.copy()
    work["abs_err"] = (pd.to_numeric(work[y_col], errors="coerce")
                       - pd.to_numeric(work[pred_col], errors="coerce")).abs()
    work = work[work["abs_err"].notna()]
    return (
        work.groupby(["model", "fold"], dropna=False)["abs_err"]
            .agg(["mean", "count"])
            .reset_index()
            .rename(columns={"mean": "fold_mae", "count": "fold_n"})
    )


def loso_only(df: pd.DataFrame) -> pd.DataFrame:
    """Restrict to LOSO scheme rows."""
    if "cv_scheme" in df.columns:
        return df[df["cv_scheme"] == "loso"].copy()
    return df.copy()


def block_bootstrap_delta(per_fold: pd.DataFrame, n_iter: int = 5000, seed: int = 42) -> dict:
    """Block bootstrap (resample folds with replacement) → CI on mean(delta)."""
    deltas = per_fold["delta"].dropna().to_numpy()
    n_folds = len(deltas)
    if n_folds < 2:
        return {
            "n_folds": n_folds,
            "mean_delta": float(np.mean(deltas)) if n_folds else float("nan"),
            "ci_low_95": float("nan"),
            "ci_high_95": float("nan"),
            "p_two_sided": float("nan"),
            "note": "insufficient folds for bootstrap (need ≥ 2)",
        }
    rng = np.random.default_rng(seed)
    means = np.empty(n_iter, dtype=np.float64)
    for i in range(n_iter):
        sample = rng.choice(deltas, size=n_folds, replace=True)
        means[i] = sample.mean()
    mean_delta = float(np.mean(deltas))
    ci_low, ci_high = np.quantile(means, [0.025, 0.975])
    # Two-sided p-value for "delta = 0" via fraction of bootstrap means with opposite sign
    if mean_delta < 0:
        p = 2 * float(np.mean(means >= 0))
    elif mean_delta > 0:
        p = 2 * float(np.mean(means <= 0))
    else:
        p = 1.0
    p = min(p, 1.0)
    return {
        "n_folds": n_folds,
        "mean_delta": mean_delta,
        "ci_low_95": float(ci_low),
        "ci_high_95": float(ci_high),
        "p_two_sided": p,
        "note": "",
    }


def find_y_col(preds: pd.DataFrame) -> str:
    """OOF predictions CSV uses the calibration target column. Auto-detect."""
    candidates = ["official_wbgt_c", "official_wbgt_c_mean", "official_wbgt_c_max",
                  "official_wbgt_c_p90", "official_wbgt_c_min"]
    for c in candidates:
        if c in preds.columns:
            return c
    # fallback: any column starting with official_wbgt
    for c in preds.columns:
        if c.startswith("official_wbgt"):
            return c
    raise SystemExit("[ERROR] cannot identify target column in OOF predictions CSV")


def discover_datasets(out_dir: Path) -> list[str]:
    """Find sub-folders containing v11_beta_oof_predictions.csv."""
    found = []
    for sub in sorted(out_dir.iterdir()):
        if sub.is_dir() and (sub / "v11_beta_oof_predictions.csv").exists():
            found.append(sub.name)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description="Bootstrap M4 - M3 advantage CI from OOF predictions.")
    ap.add_argument("--output-dir", default="outputs/v11_beta_calibration",
                    help="root directory containing per-dataset sub-folders")
    ap.add_argument("--datasets", default="",
                    help="comma-separated dataset names; default: auto-discover")
    ap.add_argument("--n-iter", type=int, default=5000,
                    help="bootstrap iterations (default 5000)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--m3-model", default="M3_weather_ridge")
    ap.add_argument("--m4-model", default="M4_inertia_ridge")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    if not out_dir.exists():
        print(f"[ERROR] output-dir not found: {out_dir}", file=sys.stderr)
        return 2

    if args.datasets.strip():
        datasets = [s.strip() for s in args.datasets.split(",") if s.strip()]
    else:
        datasets = discover_datasets(out_dir)

    if not datasets:
        print(f"[ERROR] no datasets found under {out_dir}", file=sys.stderr)
        print("        looked for sub-folders containing v11_beta_oof_predictions.csv")
        return 2

    print(f"[bootstrap] datasets: {datasets}")
    print(f"            n_iter:  {args.n_iter}")
    print(f"            comparing {args.m4_model} vs {args.m3_model}")
    print()

    summary_rows = []
    fold_rows = []
    rng_seed = args.seed

    for ds in datasets:
        preds_path = out_dir / ds / "v11_beta_oof_predictions.csv"
        if not preds_path.exists():
            print(f"  [skip] {ds}: no OOF predictions CSV")
            continue

        preds = pd.read_csv(preds_path)
        preds = loso_only(preds)
        y_col = find_y_col(preds)

        models_present = preds["model"].unique().tolist()
        if args.m3_model not in models_present or args.m4_model not in models_present:
            print(f"  [skip] {ds}: missing {args.m3_model} or {args.m4_model} "
                  f"(have: {models_present})")
            continue

        fold_mae = per_fold_mae(preds, y_col=y_col)
        m3 = fold_mae[fold_mae["model"] == args.m3_model][["fold", "fold_mae", "fold_n"]] \
                .rename(columns={"fold_mae": "M3_MAE", "fold_n": "n_M3"})
        m4 = fold_mae[fold_mae["model"] == args.m4_model][["fold", "fold_mae", "fold_n"]] \
                .rename(columns={"fold_mae": "M4_MAE", "fold_n": "n_M4"})
        merged = m3.merge(m4, on="fold", how="inner")
        merged["delta"] = merged["M4_MAE"] - merged["M3_MAE"]  # negative = M4 better
        merged["dataset"] = ds
        fold_rows.append(merged[["dataset", "fold", "n_M3", "n_M4", "M3_MAE", "M4_MAE", "delta"]])

        boot = block_bootstrap_delta(merged, n_iter=args.n_iter, seed=rng_seed)
        rng_seed += 1  # reproducible but distinct per dataset

        summary_rows.append({
            "dataset": ds,
            "n_folds": boot["n_folds"],
            "n_obs": int(merged["n_M3"].sum()),
            "M3_overall_MAE": float((merged["M3_MAE"] * merged["n_M3"]).sum() / merged["n_M3"].sum()),
            "M4_overall_MAE": float((merged["M4_MAE"] * merged["n_M4"]).sum() / merged["n_M4"].sum()),
            "mean_per_fold_delta": boot["mean_delta"],
            "ci_low_95": boot["ci_low_95"],
            "ci_high_95": boot["ci_high_95"],
            "p_two_sided": boot["p_two_sided"],
            "ci_excludes_zero": (boot["ci_low_95"] > 0) or (boot["ci_high_95"] < 0)
                if not (np.isnan(boot["ci_low_95"]) or np.isnan(boot["ci_high_95"])) else False,
            "note": boot["note"],
        })
        print(f"  [{ds}] n_folds={boot['n_folds']}, mean_delta={boot['mean_delta']:+.4f}°C, "
              f"95% CI=[{boot['ci_low_95']:+.4f}, {boot['ci_high_95']:+.4f}], "
              f"p={boot['p_two_sided']:.4f}")

    if not summary_rows:
        print("[ERROR] no datasets produced bootstrap output", file=sys.stderr)
        return 3

    summary_df = pd.DataFrame(summary_rows)
    fold_df = pd.concat(fold_rows, ignore_index=True) if fold_rows else pd.DataFrame()

    summary_path = out_dir / "bootstrap_M4_minus_M3.csv"
    fold_path = out_dir / "fold_level_M3_M4_delta_by_dataset.csv"
    summary_df.to_csv(summary_path, index=False)
    fold_df.to_csv(fold_path, index=False)

    print()
    print(f"[write] {summary_path}")
    print(f"[write] {fold_path}")
    print()
    print("=" * 78)
    print("Bootstrap CI summary:")
    print("=" * 78)
    cols_show = ["dataset", "n_folds", "M3_overall_MAE", "M4_overall_MAE",
                 "mean_per_fold_delta", "ci_low_95", "ci_high_95", "ci_excludes_zero"]
    show = summary_df[cols_show].copy()
    for c in ["M3_overall_MAE", "M4_overall_MAE", "mean_per_fold_delta",
              "ci_low_95", "ci_high_95"]:
        show[c] = show[c].astype(float).round(4)
    print(show.to_string(index=False))
    print()
    print("Interpretation:")
    print("  ci_excludes_zero=True → M4 improvement is statistically distinguishable")
    print("                          from zero at α=0.05 (block-bootstrap fold level)")
    print("  ci_excludes_zero=False → directional pattern only; await more archive")
    print()
    print("Friend-audit threshold (fourth audit, 4.3):")
    print("  |mean_delta| ≥ 0.03°C → meaningful inertia contribution")
    print("  |mean_delta| <  0.03°C → directional evidence only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
