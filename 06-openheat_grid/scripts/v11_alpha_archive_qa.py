from __future__ import annotations

import argparse
from pathlib import Path
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
        raise SystemExit(f"[ERROR] paired dataset not found: {pairs_path}. Run v11_alpha_build_pairs.py first.")
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
    if "hour" not in df.columns:
        df["hour"] = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60

    event_thresholds = cfg.get("qa", {}).get("event_thresholds_c", [29, 31, 33])

    # Event counts by station.
    rows = []
    for st, g in df.groupby("station_id", dropna=False):
        row = {
            "station_id": st,
            "n_rows": len(g),
            "n_days": g["date"].nunique(),
            "start": g["timestamp"].min(),
            "end": g["timestamp"].max(),
            "mean_wbgt": g["official_wbgt_c"].mean(),
            "max_wbgt": g["official_wbgt_c"].max(),
            "missing_wbgt_pct": float(g["official_wbgt_c"].isna().mean()),
        }
        for thr in event_thresholds:
            tag = str(thr).replace(".", "_")
            row[f"n_wbgt_ge_{tag}"] = int((g["official_wbgt_c"] >= thr).sum())
            row[f"n_peak_wbgt_ge_{tag}"] = int(((g["official_wbgt_c"] >= thr) & (g["hour"].between(13, 16))).sum())
        rows.append(row)
    station_events = pd.DataFrame(rows)
    station_events_path = out_dir / "v11_event_counts_by_station.csv"
    station_events.to_csv(station_events_path, index=False)

    # Event counts by day.
    day_rows = []
    for day, g in df.groupby("date", dropna=False):
        row = {"date": day, "n_rows": len(g), "n_stations": g["station_id"].nunique(), "max_wbgt": g["official_wbgt_c"].max()}
        for thr in event_thresholds:
            tag = str(thr).replace(".", "_")
            row[f"n_wbgt_ge_{tag}"] = int((g["official_wbgt_c"] >= thr).sum())
        day_rows.append(row)
    day_events = pd.DataFrame(day_rows)
    day_events_path = out_dir / "v11_event_counts_by_day.csv"
    day_events.to_csv(day_events_path, index=False)

    # Missingness.
    miss = pd.DataFrame({"column": df.columns, "missing_pct": [float(df[c].isna().mean()) for c in df.columns], "non_null": [int(df[c].notna().sum()) for c in df.columns]})
    miss_path = out_dir / "v11_missingness_by_column.csv"
    miss.to_csv(miss_path, index=False)

    # Duplicates.
    dup_cols = [c for c in ["station_id", "timestamp"] if c in df.columns]
    n_dups = int(df.duplicated(dup_cols).sum()) if len(dup_cols) == 2 else 0

    # 5.5: Pairing health diagnostic. Surface the 36% pair_used=False breakdown
    # in alpha QA (was previously only in collector per-run QA).
    pairing_diagnostic_lines = []
    if "pair_used_for_calibration" in df.columns:
        n_total = len(df)
        n_used = int(df["pair_used_for_calibration"].sum())
        n_unused = n_total - n_used
        pct_used = n_used * 100.0 / max(n_total, 1)
        pairing_diagnostic_lines.append(f"- **pair_used_for_calibration**: True={n_used:,} ({pct_used:.1f}%) / False={n_unused:,} ({100-pct_used:.1f}%)")
    if "weather_match_mode" in df.columns:
        wmm = df["weather_match_mode"].value_counts(dropna=False)
        wmm_pct = (wmm / max(len(df), 1) * 100).round(1)
        wmm_df = pd.DataFrame({"mode": wmm.index.astype(str), "rows": wmm.values, "pct": wmm_pct.values})
        wmm_path = out_dir / "v11_weather_match_mode_breakdown.csv"
        wmm_df.to_csv(wmm_path, index=False)
        pairing_diagnostic_lines.append("")
        pairing_diagnostic_lines.append("### Weather match mode breakdown")
        pairing_diagnostic_lines.append(df_to_md_table(wmm_df, max_rows=10))
    if "pair_location_source" in df.columns:
        pls = df["pair_location_source"].value_counts(dropna=False)
        pls_df = pd.DataFrame({"source": pls.index.astype(str), "rows": pls.values})
        pairing_diagnostic_lines.append("")
        pairing_diagnostic_lines.append("### Pair location source")
        pairing_diagnostic_lines.append(df_to_md_table(pls_df, max_rows=10))
    if "issue_age_hours" in df.columns:
        age = pd.to_numeric(df["issue_age_hours"], errors="coerce").dropna()
        if len(age) > 0:
            abs_age = age.abs()
            n_within_72 = int((abs_age <= 72).sum())
            n_beyond_72 = int((abs_age > 72).sum())
            age_stats = {
                "min_h": float(age.min()),
                "max_h": float(age.max()),
                "median_h": float(age.median()),
                "p25_h": float(age.quantile(0.25)),
                "p75_h": float(age.quantile(0.75)),
                "mean_abs_h": float(abs_age.mean()),
                "n_within_72h": n_within_72,
                "n_beyond_72h": n_beyond_72,
                "pct_beyond_72h": float(n_beyond_72 * 100.0 / max(len(age), 1)),
            }
            pairing_diagnostic_lines.append("")
            pairing_diagnostic_lines.append("### issue_age_hours distribution (obs - forecast issue time)")
            pairing_diagnostic_lines.append(f"- Range: [{age_stats['min_h']:.1f}, {age_stats['max_h']:.1f}] hours")
            pairing_diagnostic_lines.append(f"- Median: {age_stats['median_h']:.1f} h, IQR: [{age_stats['p25_h']:.1f}, {age_stats['p75_h']:.1f}]")
            pairing_diagnostic_lines.append(f"- Within 72h cutoff: **{n_within_72:,}** rows")
            pairing_diagnostic_lines.append(f"- Beyond 72h cutoff: **{n_beyond_72:,}** rows ({age_stats['pct_beyond_72h']:.1f}%)")
            pairing_diagnostic_lines.append("")
            pairing_diagnostic_lines.append("If `pct_beyond_72h` is large, most excluded rows are stale-archive observations. "
                                           "If small, inspect `weather_match_mode` for `no_weather_match` rows that signal Open-Meteo gaps.")

    report = [
        "# OpenHeat v1.1-alpha archive QA report",
        "",
        f"Paired dataset: `{pairs_path}`",
        f"Rows: **{len(df):,}**",
        f"Stations: **{df['station_id'].nunique(dropna=True)}**",
        f"Days: **{df['date'].nunique(dropna=True)}**",
        f"Duplicate station/timestamp rows: **{n_dups}**",
        "",
        "## Pairing health diagnostic",
        *(pairing_diagnostic_lines if pairing_diagnostic_lines else ["- (no pairing metadata columns found in pairs CSV)"]),
        "",
        "## Event counts by station",
        df_to_md_table(station_events, max_rows=40),
        "",
        "## Event counts by day sample",
        df_to_md_table(day_events.sort_values('date'), max_rows=20),
        "",
        "## Highest-WBGT days",
        df_to_md_table(day_events.sort_values('max_wbgt', ascending=False), max_rows=15),
        "",
        "## Highest-missing columns",
        df_to_md_table(miss.sort_values('missing_pct', ascending=False), max_rows=30),
        "",
        "## Readiness interpretation",
        "- 7 days: smoke-test only.",
        "- 14+ days: baseline calibration replay is useful.",
        "- 30+ days: residual-learning pilot becomes meaningful.",
        "- 60+ days and multiple weather regimes: stronger ML / uncertainty evaluation.",
    ]
    report_path = out_dir / "v11_archive_QA_report.md"
    write_md(report_path, "\n".join(report))
    print(f"[OK] station events: {station_events_path}")
    print(f"[OK] day events: {day_events_path}")
    print(f"[OK] missingness: {miss_path}")
    print(f"[OK] report: {report_path}")


if __name__ == "__main__":
    main()
