"""
OpenHeat v0.9-gamma core analysis: compare SOLWEIG-derived Tmrt against
the v0.9-beta empirical globe-term proxy.

Quantifies what SOLWEIG physics captures that the Stull-based proxy
misses:

    T_globe_proxy = T_air + 0.0045 * SW / sqrt(wind + 0.25)

vs

    Tmrt_solweig (per cell, per hour, from raster aggregation)

Outputs:
- per-cell-per-hour delta CSV
- focus-cell pivot table
- by-tile_type summary
- markdown report

Usage:
    python scripts/v09_gamma_analyze_solweig_vs_proxy.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SOLWEIG_CSV = Path(
    "outputs/v09_solweig/v09_solweig_tmrt_grid_summary_overhead_aware.csv"
)
ALPHA_CSV = Path(
    "data/calibration/v09_historical_forecast_by_station_hourly.csv"
)
ANALYSIS_DIR = Path("outputs/v09_gamma_analysis")
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

# Use S128 Bishan as Toa Payoh forcing reference (closest local station)
FORCING_STATION = "S128"
TARGET_DATE = "2026-05-07"


def empirical_globe_term(t_air_c: float, sw_wm2: float, wind_ms: float) -> float:
    """Stull-style empirical black-globe equivalent used in v0.9-beta proxy."""
    return t_air_c + 0.0045 * sw_wm2 / np.sqrt(wind_ms + 0.25)


def main() -> None:
    if not SOLWEIG_CSV.exists():
        raise FileNotFoundError(f"SOLWEIG aggregator output missing: {SOLWEIG_CSV}")
    if not ALPHA_CSV.exists():
        raise FileNotFoundError(f"Alpha forecast CSV missing: {ALPHA_CSV}")

    # -- SOLWEIG aggregator output --
    sol = pd.read_csv(SOLWEIG_CSV)
    sol["tmrt_hour_sgt"] = pd.to_numeric(sol["tmrt_hour_sgt"], errors="coerce").astype("Int64")
    print(f"[INFO] SOLWEIG rows: {len(sol)}, tiles: {sorted(sol['tile_id'].unique())}")
    print(f"[INFO] hours present: {sorted(sol['tmrt_hour_sgt'].dropna().unique().tolist())}")

    # -- Alpha forecast (atmospheric forcing) --
    fc = pd.read_csv(ALPHA_CSV)
    fc["time_sgt"] = pd.to_datetime(fc["time_sgt"])
    s128 = fc[fc["station_id"].astype(str).eq(FORCING_STATION)].copy()
    s128 = s128[s128["time_sgt"].dt.date.astype(str).eq(TARGET_DATE)].copy()
    s128["hour_sgt"] = s128["time_sgt"].dt.hour
    print(f"[INFO] {FORCING_STATION} {TARGET_DATE}: {len(s128)} hourly rows")

    # Compute hourly empirical globe term from S128 forcing
    s128["empirical_T_globe_c"] = s128.apply(
        lambda r: empirical_globe_term(
            r["temperature_2m"], r["shortwave_radiation"], r["wind_speed_10m"]
        ),
        axis=1,
    )

    forcing_lookup = s128.set_index("hour_sgt")[
        ["temperature_2m", "shortwave_radiation", "wind_speed_10m", "empirical_T_globe_c"]
    ]
    print("\n[INFO] S128 forcing at SOLWEIG target hours:")
    print(forcing_lookup.loc[forcing_lookup.index.intersection([10, 12, 13, 15, 16])].round(2))

    # -- Merge SOLWEIG and forcing on hour --
    merged = sol.merge(
        forcing_lookup.reset_index(),
        left_on="tmrt_hour_sgt",
        right_on="hour_sgt",
        how="left",
    )
    merged["delta_solweig_minus_proxy_c"] = (
        merged["tmrt_mean_c"] - merged["empirical_T_globe_c"]
    )
    print(f"\n[INFO] merged rows with delta computed: {merged['delta_solweig_minus_proxy_c'].notna().sum()}")

    # -- Output 1: full per-cell-per-hour delta --
    full_out = ANALYSIS_DIR / "v09_gamma_solweig_vs_proxy_per_cell.csv"
    merged.to_csv(full_out, index=False)
    print(f"[OK] {full_out}")

    # -- Output 2: focus cell pivot (most diagnostic) --
    focus = merged[merged["cell_id"] == merged["focus_cell_id"]].copy()
    focus_pivot = focus.pivot_table(
        index="tmrt_hour_sgt",
        columns="tile_type",
        values=["tmrt_mean_c", "empirical_T_globe_c", "delta_solweig_minus_proxy_c"],
    )
    focus_out = ANALYSIS_DIR / "v09_gamma_focus_cell_solweig_vs_proxy.csv"
    focus_pivot.to_csv(focus_out)
    print(f"[OK] {focus_out}")

    # -- Output 3: tile-type x hour summary --
    summary = merged.groupby(["tile_type", "tmrt_hour_sgt"]).agg(
        n_cells=("cell_id", "nunique"),
        mean_solweig_tmrt=("tmrt_mean_c", "mean"),
        mean_empirical=("empirical_T_globe_c", "mean"),
        mean_delta=("delta_solweig_minus_proxy_c", "mean"),
        std_delta=("delta_solweig_minus_proxy_c", "std"),
    ).round(2).reset_index()
    summary_out = ANALYSIS_DIR / "v09_gamma_tiletype_hour_summary.csv"
    summary.to_csv(summary_out, index=False)
    print(f"[OK] {summary_out}")

    # -- Special comparisons --
    print("\n" + "=" * 70)
    print("KEY DIAGNOSTIC: focus cell Tmrt by tile_type and hour")
    print("=" * 70)
    pivot_mean = focus.pivot_table(
        index="tmrt_hour_sgt", columns="tile_type", values="tmrt_mean_c"
    ).round(1)
    print(pivot_mean.to_string())

    print("\n" + "=" * 70)
    print("KEY DIAGNOSTIC: SOLWEIG_Tmrt - empirical_T_globe per focus cell per hour")
    print("=" * 70)
    pivot_delta = focus.pivot_table(
        index="tmrt_hour_sgt", columns="tile_type", values="delta_solweig_minus_proxy_c"
    ).round(2)
    print(pivot_delta.to_string())
    print()
    print("Interpretation:")
    print("  delta > 0  → SOLWEIG sees MORE radiant load than empirical proxy")
    print("              (likely longwave from heated walls + multi-reflection)")
    print("  delta < 0  → SOLWEIG sees LESS radiant load than empirical proxy")
    print("              (likely shading from buildings/vegetation)")
    print("  delta varies by cell_type → SOLWEIG captures spatial heterogeneity")
    print("              that empirical proxy (uniform per hour) cannot.")

    # -- Vegetation cooling and overhead bias diagnostics --
    cols = pivot_mean.columns
    if "clean_hazard_top" in cols and "clean_shaded_reference" in cols:
        veg_contrast = (pivot_mean["clean_hazard_top"] - pivot_mean["clean_shaded_reference"]).round(1)
        print(f"\nVegetation cooling (T01_clean_hazard - T05_clean_reference) by hour:")
        print(veg_contrast.to_string())
    if "clean_hazard_top" in cols and "overhead_confounded_hazard_case" in cols:
        oh_bias = (pivot_mean["clean_hazard_top"] - pivot_mean["overhead_confounded_hazard_case"]).round(1)
        print(f"\nOverhead infrastructure bias (T01_clean - T06_confounded) by hour:")
        print(oh_bias.to_string())
        print("  Interpretation: small or zero → SOLWEIG cannot distinguish overhead-confounded")
        print("                  from clean cells. This is the v0.9 transport-DSM blind spot.")

    # -- Markdown report --
    report = []
    report.append("# v0.9-gamma analysis: SOLWEIG Tmrt vs empirical globe-term proxy\n")
    report.append(f"Forcing station: **{FORCING_STATION}** ({TARGET_DATE})\n")
    report.append(f"SOLWEIG rows merged: **{merged['delta_solweig_minus_proxy_c'].notna().sum()}**\n")
    report.append("## Hourly forcing values (S128, May 7 2026)\n")
    report.append("```")
    report.append(forcing_lookup.loc[forcing_lookup.index.intersection([10, 12, 13, 15, 16])].round(2).to_string())
    report.append("```\n")
    report.append("## Focus cell Tmrt (mean over cell pixels) by tile_type x hour\n")
    report.append("```")
    report.append(pivot_mean.to_string())
    report.append("```\n")
    report.append("## SOLWEIG_Tmrt minus empirical_T_globe (focus cell, per hour)\n")
    report.append("```")
    report.append(pivot_delta.to_string())
    report.append("```\n")
    report.append("**Reading the delta**: a positive value means SOLWEIG estimates more radiant heat ")
    report.append("than the empirical Stull-style proxy would predict for that hour. Negative ")
    report.append("means SOLWEIG accounts for shading/reflections that lower local Tmrt.\n")
    if "clean_hazard_top" in cols and "clean_shaded_reference" in cols:
        report.append("## Vegetation cooling captured by SOLWEIG\n")
        report.append("`T01_clean_hazard_top - T05_clean_shaded_reference` per hour:\n")
        report.append("```")
        report.append(veg_contrast.to_string())
        report.append("```\n")
        report.append("This contrast cannot be reproduced by an empirical proxy with uniform ")
        report.append("atmospheric forcing per hour - it is a direct fingerprint of vegetation ")
        report.append("morphology being honored by SOLWEIG.\n")
    if "clean_hazard_top" in cols and "overhead_confounded_hazard_case" in cols:
        report.append("## Overhead infrastructure bias\n")
        report.append("`T01_clean_hazard_top - T06_overhead_confounded` per hour:\n")
        report.append("```")
        report.append(oh_bias.to_string())
        report.append("```\n")
        report.append("If this contrast is small, SOLWEIG is unable to distinguish overhead-confounded ")
        report.append("cells from clean cells - confirming the systematic blind spot for transport ")
        report.append("infrastructure documented elsewhere in this work.\n")

    report_out = ANALYSIS_DIR / "v09_gamma_solweig_vs_proxy_REPORT.md"
    report_out.write_text("\n".join(report), encoding="utf-8")
    print(f"\n[OK] {report_out}")


if __name__ == "__main__":
    main()
