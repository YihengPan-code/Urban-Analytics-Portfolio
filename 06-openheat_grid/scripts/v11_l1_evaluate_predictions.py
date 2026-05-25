#!/usr/bin/env python
"""Evaluate Level 1 reproduction predictions.

Inputs:
    - configs/v11/level1_model_registry.yaml
    - outputs/v11_level1/reproduction/oof_predictions_reproduction.csv
    - Existing previous metric CSVs declared in the registry, when present.

Outputs:
    - outputs/v11_level1/reproduction/metrics_reproduction_table.csv
    - outputs/v11_level1/reproduction/reproduction_report.md

Saved metrics:
    - OOF-only MAE, RMSE, bias, R2.
    - Fixed WBGT >=31 and >=33 threshold precision/recall/F1/counts.
    - Row count, station count, fold count, target, filter mode, input path.
    - Difference against previous metrics when a matching previous metric row
      is available.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_registry(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def metric_summary(y_true: pd.Series, y_pred: pd.Series) -> dict[str, float | int]:
    y = pd.to_numeric(y_true, errors="coerce")
    p = pd.to_numeric(y_pred, errors="coerce")
    mask = y.notna() & p.notna()
    if not mask.any():
        return {"n": 0, "mae": np.nan, "rmse": np.nan, "bias": np.nan, "r2": np.nan}
    yy = y[mask].to_numpy(float)
    pp = p[mask].to_numpy(float)
    err = pp - yy
    ss_res = float(np.sum((yy - pp) ** 2))
    ss_tot = float(np.sum((yy - yy.mean()) ** 2))
    return {
        "n": int(mask.sum()),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "bias": float(np.mean(err)),
        "r2": float(1 - ss_res / ss_tot) if ss_tot > 0 else np.nan,
    }


def event_metrics(y_true: pd.Series, y_score: pd.Series, threshold: float) -> dict[str, float | int]:
    y = pd.to_numeric(y_true, errors="coerce")
    s = pd.to_numeric(y_score, errors="coerce")
    mask = y.notna() & s.notna()
    if not mask.any():
        return {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "precision": np.nan, "recall": np.nan, "f1": np.nan}
    obs = (y[mask] >= threshold).to_numpy(bool)
    pred = (s[mask] >= threshold).to_numpy(bool)
    tp = int(np.sum(obs & pred))
    fp = int(np.sum(~obs & pred))
    tn = int(np.sum(~obs & ~pred))
    fn = int(np.sum(obs & ~pred))
    precision = tp / (tp + fp) if (tp + fp) else np.nan
    recall = tp / (tp + fn) if (tp + fn) else np.nan
    f1 = 2 * precision * recall / (precision + recall) if pd.notna(precision) and pd.notna(recall) and (precision + recall) else np.nan
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def previous_metric(spec: dict, model: str) -> dict[str, object]:
    path_value = spec.get("previous_metrics_csv")
    if not path_value:
        return {}
    path = ROOT / path_value
    if not path.exists():
        return {}
    try:
        df = pd.read_csv(path)
    except Exception:
        return {}
    if "model" not in df.columns:
        return {}
    cv = df["cv_scheme"].astype(str).eq("loso") if "cv_scheme" in df.columns else pd.Series(True, index=df.index)
    match = df["model"].astype(str).eq(model) & cv
    if not match.any():
        return {}
    row = df.loc[match].iloc[0]
    return {
        "previous_metrics_csv": path_value,
        "previous_mae": row.get("mae", np.nan),
        "previous_rmse": row.get("rmse", np.nan),
        "previous_bias": row.get("bias", np.nan),
        "previous_r2": row.get("r2", np.nan),
    }


def evaluate(registry: dict, preds: pd.DataFrame) -> pd.DataFrame:
    thresholds = registry.get("event_thresholds_c", [31, 33])
    spec_by_label = {spec["dataset_label"]: spec for spec in registry["datasets"]}
    rows: list[dict[str, object]] = []
    for (dataset_label, model), group in preds.groupby(["dataset_label", "model"], dropna=False):
        spec = spec_by_label[str(dataset_label)]
        row: dict[str, object] = {
            "dataset_label": dataset_label,
            "model": model,
            "cv_scheme": "loso",
            "target_col": spec["target_col"],
            "raw_proxy_col": spec["raw_proxy_col"],
            "filter_mode": spec.get("filter_mode", ""),
            "input_csv": spec.get("input_csv", ""),
            "row_count": len(group),
            "station_count": group["station_id"].nunique(dropna=True) if "station_id" in group.columns else np.nan,
            "fold_count": group["fold"].nunique(dropna=True) if "fold" in group.columns else np.nan,
            "n_features": group["n_features"].dropna().iloc[0] if "n_features" in group.columns and group["n_features"].notna().any() else np.nan,
            "ridge_backend": ";".join(sorted(group["ridge_backend"].dropna().astype(str).unique())) if "ridge_backend" in group.columns else "",
            "ridge_backend_requested": ";".join(sorted(group["ridge_backend_requested"].dropna().astype(str).unique())) if "ridge_backend_requested" in group.columns else "",
            "imputation_method": ";".join(sorted(group["imputation_method"].dropna().astype(str).unique())) if "imputation_method" in group.columns else "",
            "scaling_method": ";".join(sorted(group["scaling_method"].dropna().astype(str).unique())) if "scaling_method" in group.columns else "",
            "alpha_used": group["alpha_used"].dropna().iloc[0] if "alpha_used" in group.columns and group["alpha_used"].notna().any() else np.nan,
            "sklearn_failed": bool(group["sklearn_failed"].astype(str).str.lower().isin(["true", "1"]).any()) if "sklearn_failed" in group.columns else False,
            "fallback_used": bool(group["fallback_used"].astype(str).str.lower().isin(["true", "1"]).any()) if "fallback_used" in group.columns else False,
            "sklearn_failure_message": " | ".join(sorted(set(
                msg for msg in group.get("sklearn_failure_message", pd.Series(dtype=str)).dropna().astype(str).unique() if msg
            )))[:4000],
            "sys_executable": ";".join(sorted(group["sys_executable"].dropna().astype(str).unique())) if "sys_executable" in group.columns else sys.executable,
            "command_run": ";".join(sorted(group["command_run"].dropna().astype(str).unique())) if "command_run" in group.columns else "",
        }
        row.update(metric_summary(group["observed_wbgt_c"], group["prediction_wbgt_c"]))
        for threshold in thresholds:
            em = event_metrics(group["observed_wbgt_c"], group["prediction_wbgt_c"], float(threshold))
            prefix = f"wbgt_ge_{int(threshold)}"
            for key, value in em.items():
                row[f"{prefix}_{key}"] = value
        row.update(previous_metric(spec, str(model)))
        for metric in ["mae", "rmse", "bias", "r2"]:
            prev = pd.to_numeric(pd.Series([row.get(f"previous_{metric}")]), errors="coerce").iloc[0]
            cur = pd.to_numeric(pd.Series([row.get(metric)]), errors="coerce").iloc[0]
            row[f"delta_{metric}_minus_previous"] = float(cur - prev) if pd.notna(prev) and pd.notna(cur) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["dataset_label", "model"])


def write_report(registry: dict, metrics: pd.DataFrame, out_dir: Path) -> None:
    created = [
        out_dir / "metrics_reproduction_table.csv",
        out_dir / "oof_predictions_reproduction.csv",
    ]
    material_diffs = metrics[
        pd.to_numeric(metrics.get("delta_mae_minus_previous", pd.Series(np.nan, index=metrics.index)), errors="coerce").abs() > 1e-6
    ]
    lines = [
        "# Level 1 Reproduction Report",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Scope",
        "",
        "Reproduces existing System A Level 1 Ridge baselines M3, M4, and M7 using LOSO out-of-fold predictions only.",
        "No ElasticNet, GBM, XGBoost, formula-v2, SOLWEIG, System B, or new feature groups were added.",
        "",
        "## Outputs",
        "",
        "\n".join(f"- `{str(path.relative_to(ROOT)).replace(chr(92), '/')}`" for path in created),
        "",
        "## Run Provenance",
        "",
        f"- Evaluation sys.executable: `{sys.executable}`",
        f"- Model sys.executable: `{'; '.join(sorted(metrics['sys_executable'].dropna().astype(str).unique())) if 'sys_executable' in metrics.columns else ''}`",
        f"- Model command(s): `{'; '.join(sorted(metrics['command_run'].dropna().astype(str).unique())) if 'command_run' in metrics.columns else ''}`",
        "- Required Codex execution wrapper: `C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat --no-capture-output python -X faulthandler -u ...`",
        "",
        "## Metrics",
        "",
        metrics.to_csv(index=False),
        "",
        "## Reproduction Comparison",
        "",
    ]
    non_sklearn = metrics[
        metrics.get("ridge_backend", pd.Series("", index=metrics.index)).astype(str).ne("sklearn")
    ]
    fallback_oof = out_dir / "oof_predictions_reproduction_fallback_noncanonical.csv"
    if non_sklearn.empty:
        lines.append("Canonical reproduction used `ridge_backend=sklearn` for every metric row.")
        lines.append("")
    else:
        lines.append("WARNING: non-canonical metric rows were detected and should not be treated as reproduction.")
        lines.append("")
        lines.append(non_sklearn[["dataset_label", "model", "ridge_backend"]].to_csv(index=False))
        lines.append("")
    if fallback_oof.exists():
        lines.append(f"Non-canonical fallback OOF preserved separately: `{str(fallback_oof.relative_to(ROOT)).replace(chr(92), '/')}`.")
        lines.append("")
    if material_diffs.empty and non_sklearn.empty:
        lines.append("All rows with available previous metrics match to within 1e-6 MAE.")
    elif not material_diffs.empty:
        lines.append("Some reproduced metrics differ from previous metric CSVs. Do not proceed to new models until reviewed.")
        lines.append("")
        lines.append(material_diffs[[
            "dataset_label", "model", "mae", "previous_mae", "delta_mae_minus_previous",
            "rmse", "previous_rmse", "delta_rmse_minus_previous", "ridge_backend", "sklearn_failed",
        ]].to_csv(index=False))
        lines.extend([
            "",
            "Possible causes include a different frozen input snapshot, hourly aggregation vintage, dependency version differences, or prior outputs generated from a different config path.",
        ])
    lines.extend([
        "",
        "## Caveats",
        "",
        "- Metrics are calibration reproduction diagnostics for WBGT_A(hour), not validated 100m local WBGT prediction.",
        "- Threshold metrics are fixed-threshold OOF diagnostics only.",
    ])
    (out_dir / "reproduction_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Level 1 reproduction OOF predictions.")
    parser.add_argument("--registry", default="configs/v11/level1_model_registry.yaml")
    parser.add_argument(
        "--command-run",
        default=" ".join(sys.argv),
        help="Exact evaluation command string to record in the report.",
    )
    args = parser.parse_args()
    registry = load_registry(ROOT / args.registry)
    out_dir = ROOT / registry.get("output_dir", "outputs/v11_level1/reproduction")
    preds_path = out_dir / "oof_predictions_reproduction.csv"
    if not preds_path.exists():
        raise SystemExit(f"[ERROR] predictions not found: {preds_path}")
    preds = pd.read_csv(preds_path, low_memory=False)
    if "ridge_backend" in preds.columns:
        bad_backends = sorted(set(preds["ridge_backend"].dropna().astype(str)) - {"sklearn"})
        if bad_backends:
            raise SystemExit(
                "[ERROR] non-canonical ridge_backend values in reproduction predictions: "
                + ", ".join(bad_backends)
            )
    metrics = evaluate(registry, preds)
    metrics["evaluation_sys_executable"] = sys.executable
    metrics["evaluation_command_run"] = args.command_run
    metrics.to_csv(out_dir / "metrics_reproduction_table.csv", index=False)
    write_report(registry, metrics, out_dir)
    print(f"[OK] wrote {out_dir / 'metrics_reproduction_table.csv'}")
    print(f"[OK] wrote {out_dir / 'reproduction_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
