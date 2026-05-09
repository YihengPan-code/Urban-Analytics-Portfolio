from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from v09_common import load_config, ensure_dir, to_sgt_series, robust_numeric, station_table_from_archive, haversine_m


def main():
    parser = argparse.ArgumentParser(description="OpenHeat v0.9-alpha: QA NEA archive data.")
    parser.add_argument("--config", default="configs/v09_alpha_config.example.json")
    parser.add_argument("--archive", default=None)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    archive_path = Path(args.archive or cfg["archive_csv"])
    out_dir = ensure_dir(args.out_dir or cfg["outputs_dir"])

    if not archive_path.exists():
        raise FileNotFoundError(f"Archive CSV not found: {archive_path}")

    df = pd.read_csv(archive_path)
    required = ["archive_run_utc", "api_name", "variable", "value", "timestamp", "station_id", "station_lat", "station_lon"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Archive does not look like v0.6.4+ long format. Missing: {missing}")

    df["timestamp_sgt"] = to_sgt_series(df["timestamp"])
    df["value_num"] = robust_numeric(df["value"])

    rows = []
    for (api, var), g in df.groupby(["api_name", "variable"], dropna=False):
        rows.append({
            "api_name": api,
            "variable": var,
            "rows": len(g),
            "stations": g["station_id"].nunique(),
            "timestamps": g["timestamp_sgt"].nunique(),
            "missing_value_rows": int(g["value_num"].isna().sum()),
            "min_value": g["value_num"].min(),
            "mean_value": g["value_num"].mean(),
            "max_value": g["value_num"].max(),
        })
    summary = pd.DataFrame(rows).sort_values(["api_name", "variable"])
    summary_fp = out_dir / "v09_archive_variable_summary.csv"
    summary.to_csv(summary_fp, index=False)

    wbgt = df[df["variable"].eq(cfg.get("pairing", {}).get("wbgt_variable_name", "official_wbgt_c"))].copy()
    if wbgt.empty:
        raise ValueError("No official_wbgt_c rows found in archive.")
    wbgt["official_wbgt_c"] = wbgt["value_num"]

    station_rows = []
    for (sid, sname), g in wbgt.groupby(["station_id", "station_name"], dropna=False):
        station_rows.append({
            "station_id": sid,
            "station_name": sname,
            "station_lat": g["station_lat"].dropna().iloc[0] if g["station_lat"].notna().any() else None,
            "station_lon": g["station_lon"].dropna().iloc[0] if g["station_lon"].notna().any() else None,
            "n": len(g),
            "timestamps": g["timestamp_sgt"].nunique(),
            "wbgt_min": g["official_wbgt_c"].min(),
            "wbgt_mean": g["official_wbgt_c"].mean(),
            "wbgt_max": g["official_wbgt_c"].max(),
            "low_count": int(g["heat_stress_category"].eq("Low").sum()) if "heat_stress_category" in g.columns else None,
            "moderate_count": int(g["heat_stress_category"].eq("Moderate").sum()) if "heat_stress_category" in g.columns else None,
            "high_count": int(g["heat_stress_category"].eq("High").sum()) if "heat_stress_category" in g.columns else None,
        })
    station_summary = pd.DataFrame(station_rows)

    center = cfg.get("toa_payoh_center", {"lat": 1.334, "lon": 103.858})
    if {"station_lat", "station_lon"}.issubset(station_summary.columns):
        station_summary["distance_to_toapayoh_center_m"] = haversine_m(
            center["lat"], center["lon"],
            station_summary["station_lat"].astype(float), station_summary["station_lon"].astype(float)
        )
    station_summary = station_summary.sort_values(["distance_to_toapayoh_center_m", "station_id"])
    station_fp = out_dir / "v09_wbgt_station_summary.csv"
    station_summary.to_csv(station_fp, index=False)

    category_counts = wbgt["heat_stress_category"].value_counts(dropna=False).rename_axis("category").reset_index(name="count") if "heat_stress_category" in wbgt.columns else pd.DataFrame()
    cat_fp = out_dir / "v09_wbgt_category_counts.csv"
    category_counts.to_csv(cat_fp, index=False)

    start = df["timestamp_sgt"].min()
    end = df["timestamp_sgt"].max()
    archive_runs = df["archive_run_utc"].nunique() if "archive_run_utc" in df.columns else None

    nearest = station_summary.head(8)
    focus_ids = cfg.get("report", {}).get("nearest_station_focus", [])
    focus = station_summary[station_summary["station_id"].isin(focus_ids)]

    report_lines = []
    report_lines.append("# OpenHeat v0.9-alpha archive QA report")
    report_lines.append("")
    report_lines.append(f"Archive CSV: `{archive_path}`")
    report_lines.append(f"Rows: **{len(df)}**")
    report_lines.append(f"Archive runs: **{archive_runs}**")
    report_lines.append(f"Time span SGT: **{start} → {end}**")
    report_lines.append("")
    report_lines.append("## Variable summary")
    report_lines.append(summary.to_string(index=False))
    report_lines.append("")
    report_lines.append("## WBGT category counts")
    report_lines.append(category_counts.to_string(index=False))
    report_lines.append("")
    report_lines.append("## Nearest WBGT stations to Toa Payoh centre")
    report_lines.append(nearest[["station_id","station_name","distance_to_toapayoh_center_m","wbgt_min","wbgt_mean","wbgt_max","moderate_count","high_count"]].to_string(index=False))
    if not focus.empty:
        report_lines.append("")
        report_lines.append("## Focus stations")
        report_lines.append(focus[["station_id","station_name","distance_to_toapayoh_center_m","wbgt_min","wbgt_mean","wbgt_max","moderate_count","high_count"]].to_string(index=False))
    report_lines.append("")
    report_lines.append("## Interpretation notes")
    report_lines.append("- This archive is suitable for v0.9-alpha QA and paired-calibration pipeline testing.")
    report_lines.append("- A 24-hour archive is not sufficient for robust ML residual learning; use it as a pilot/smoke test.")
    report_lines.append("- Official WBGT is station-level and should not be interpreted as street-level Toa Payoh validation.")

    report_fp = out_dir / "v09_archive_QA_report.md"
    report_fp.write_text("\n".join(report_lines), encoding="utf-8")

    print("[OK] Archive QA complete")
    print("summary:", summary_fp)
    print("station_summary:", station_fp)
    print("report:", report_fp)


if __name__ == "__main__":
    main()
