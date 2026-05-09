"""
OpenHeat v0.9-gamma hotfix
Compare SOLWEIG Tmrt selected-tile summaries with forecast proxy Tmrt if available.

Hotfixes:
- reports whether comparison is time-matched or diagnostic only
- uses tmrt_hour_sgt from aggregation if available
- if forecast Tmrt proxy is unavailable, still produces SOLWEIG summary report
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

DEFAULT_CONFIG = "configs/v09_gamma_solweig_config.example.json"
DEFAULT_SOLWEIG_SUMMARY = "outputs/v09_solweig/v09_solweig_tmrt_grid_summary.csv"
DEFAULT_FORECAST_HOURLY = "outputs/v08_umep_with_veg_forecast_live/v06_live_hourly_grid_heatstress_forecast.csv"
DEFAULT_OUT_CSV = "outputs/v09_solweig/v09_tmrt_proxy_vs_solweig_comparison.csv"
DEFAULT_REPORT = "outputs/v09_solweig/v09_solweig_tmrt_comparison_report.md"


def read_json(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def get_path(cfg: Dict[str, Any], *keys: str, default: str) -> str:
    paths = cfg.get("paths", {}) if isinstance(cfg, dict) else {}
    for key in keys:
        if key in paths and paths[key]:
            return str(paths[key])
        if key in cfg and cfg[key]:
            return str(cfg[key])
    return default


def pick_tmrt_proxy_col(df: pd.DataFrame) -> Optional[str]:
    candidates = [
        "tmrt_proxy_c",
        "tmrt_c",
        "tr_c",
        "mean_radiant_temperature_c",
        "mrt_c",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    # Fuzzy fallback
    for c in df.columns:
        lc = c.lower()
        if "tmrt" in lc or "radiant" in lc:
            return c
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--solweig-summary", default=None)
    parser.add_argument("--forecast-hourly", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    cfg = read_json(args.config)
    solweig_fp = Path(args.solweig_summary or get_path(cfg, "solweig_tmrt_grid_summary_csv", "tmrt_summary_csv", default=DEFAULT_SOLWEIG_SUMMARY))
    forecast_fp = Path(args.forecast_hourly or get_path(cfg, "forecast_hourly_csv", "hourly_forecast_csv", default=DEFAULT_FORECAST_HOURLY))
    out_fp = Path(args.out or get_path(cfg, "tmrt_comparison_csv", default=DEFAULT_OUT_CSV))
    report_fp = Path(args.report or get_path(cfg, "tmrt_comparison_report", default=DEFAULT_REPORT))

    if not solweig_fp.exists():
        raise FileNotFoundError(f"SOLWEIG summary not found: {solweig_fp}")
    sol = pd.read_csv(solweig_fp)
    if sol.empty:
        raise ValueError("SOLWEIG summary is empty")

    lines = ["# v0.9-gamma SOLWEIG Tmrt comparison report", ""]
    lines.append(f"SOLWEIG summary: `{solweig_fp}`")
    lines.append(f"SOLWEIG rows: **{len(sol)}**")
    if "tmrt_time_label" in sol.columns:
        lines.append(f"Tmrt time labels: {sorted(sol['tmrt_time_label'].dropna().astype(str).unique().tolist())}")
    if "tmrt_hour_sgt" in sol.columns:
        lines.append(f"Tmrt hour labels: {sorted(sol['tmrt_hour_sgt'].dropna().astype(int).unique().tolist())}")
    lines.append("")

    # Basic SOLWEIG summary always available.
    group_cols = [c for c in ["tile_id", "tile_type", "tmrt_time_label", "tmrt_hour_sgt"] if c in sol.columns]
    summary = sol.groupby(group_cols, dropna=False).agg(
        n_cells=("cell_id", "nunique"),
        tmrt_mean_c=("tmrt_mean_c", "mean"),
        tmrt_p90_mean_c=("tmrt_p90_c", "mean"),
        tmrt_mean_min=("tmrt_mean_c", "min"),
        tmrt_mean_max=("tmrt_mean_c", "max"),
    ).reset_index() if group_cols else pd.DataFrame()

    comparison = sol.copy()
    comparison["comparison_mode"] = "solweig_only_no_forecast_proxy"
    tmrt_col = None

    if forecast_fp.exists():
        fc = pd.read_csv(forecast_fp)
        tmrt_col = pick_tmrt_proxy_col(fc)
        if tmrt_col:
            if "time" in fc.columns:
                fc["time_dt"] = pd.to_datetime(fc["time"], errors="coerce")
                fc["hour_sgt"] = fc["time_dt"].dt.hour
            elif "hour_sgt" in fc.columns:
                fc["hour_sgt"] = pd.to_numeric(fc["hour_sgt"], errors="coerce")
            else:
                fc["hour_sgt"] = np.nan

            # Time-matched if both sides have hours.
            if "tmrt_hour_sgt" in sol.columns and fc["hour_sgt"].notna().any():
                fc_small = fc[["cell_id", "hour_sgt", tmrt_col]].copy()
                fc_small = fc_small.dropna(subset=["cell_id", "hour_sgt", tmrt_col])
                fc_small["hour_sgt"] = fc_small["hour_sgt"].astype(int)
                comparison = sol.merge(
                    fc_small,
                    left_on=["cell_id", "tmrt_hour_sgt"],
                    right_on=["cell_id", "hour_sgt"],
                    how="left",
                )
                comparison["comparison_mode"] = "time_matched_by_cell_and_hour"
                comparison["tmrt_proxy_c"] = comparison[tmrt_col]
                comparison["delta_tmrt_solweig_minus_proxy"] = comparison["tmrt_mean_c"] - comparison["tmrt_proxy_c"]
                matched = comparison["tmrt_proxy_c"].notna().sum()
                lines.append("## Forecast proxy comparison")
                lines.append(f"Forecast hourly CSV: `{forecast_fp}`")
                lines.append(f"Tmrt proxy column: `{tmrt_col}`")
                lines.append(f"Time-matched rows with proxy: **{matched} / {len(comparison)}**")
                lines.append("")
            else:
                # Non-time-matched diagnostic: cell-level mean proxy over forecast period.
                fc_mean = fc.groupby("cell_id", as_index=False)[tmrt_col].mean().rename(columns={tmrt_col: "tmrt_proxy_period_mean_c"})
                comparison = sol.merge(fc_mean, on="cell_id", how="left")
                comparison["comparison_mode"] = "diagnostic_solweig_selected_times_vs_proxy_period_mean"
                comparison["delta_tmrt_solweig_minus_proxy"] = comparison["tmrt_mean_c"] - comparison["tmrt_proxy_period_mean_c"]
                matched = comparison["tmrt_proxy_period_mean_c"].notna().sum()
                lines.append("## Forecast proxy comparison")
                lines.append(f"Forecast hourly CSV: `{forecast_fp}`")
                lines.append(f"Tmrt proxy column: `{tmrt_col}`")
                lines.append(f"Strict time matching unavailable. Matched against forecast-period cell mean proxy: **{matched} / {len(comparison)}**")
                lines.append("**Interpretation warning:** SOLWEIG selected times vs proxy period-mean is diagnostic, not strict hourly validation.")
                lines.append("")
        else:
            lines.append("## Forecast proxy comparison")
            lines.append(f"Forecast hourly CSV found, but no Tmrt proxy column detected: `{forecast_fp}`")
            lines.append("SOLWEIG summary is still valid, but proxy-vs-SOLWEIG delta is not computed.")
            lines.append("")
    else:
        lines.append("## Forecast proxy comparison")
        lines.append(f"Forecast hourly CSV not found: `{forecast_fp}`")
        lines.append("SOLWEIG summary is still valid, but proxy-vs-SOLWEIG delta is not computed.")
        lines.append("")

    if "delta_tmrt_solweig_minus_proxy" in comparison.columns:
        vals = comparison["delta_tmrt_solweig_minus_proxy"].dropna()
        if len(vals):
            lines.append("## Delta summary")
            lines.append(f"Delta mean: **{vals.mean():.3f} °C**")
            lines.append(f"Delta median: **{vals.median():.3f} °C**")
            lines.append(f"Delta p10/p90: **{vals.quantile(0.1):.3f} / {vals.quantile(0.9):.3f} °C**")
            lines.append("")

    lines.append("## SOLWEIG Tmrt summary by tile/time")
    if not summary.empty:
        lines.append(summary.head(50).to_string(index=False))
    else:
        lines.append("No groupable tile/time columns found.")
    lines.append("")
    lines.append("## Interpretation note")
    lines.append("- If `comparison_mode` is `time_matched_by_cell_and_hour`, deltas are strict hourly comparisons.")
    lines.append("- If `comparison_mode` is `diagnostic_solweig_selected_times_vs_proxy_period_mean`, deltas compare selected SOLWEIG times against the forecast-period proxy mean and should not be interpreted as strict time-matched validation.")
    lines.append("- If no Tmrt proxy exists in the forecast output, use this report as a SOLWEIG-only Tmrt tile diagnostic.")

    out_fp.parent.mkdir(parents=True, exist_ok=True)
    report_fp.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(out_fp, index=False)
    report_fp.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] comparison CSV: {out_fp}")
    print(f"[OK] report: {report_fp}")
    if tmrt_col:
        print(f"[INFO] Tmrt proxy column: {tmrt_col}")
    print(f"[INFO] comparison modes: {comparison['comparison_mode'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
