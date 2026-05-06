"""Hotspot ranking engine for OpenHeat.

Recent changes:
- Keep UTCI and WBGT alerts separate, then create a combined alert.
- Make hotspot hazard scoring continuous, so rankings still differentiate cells
  when no WBGT threshold is exceeded.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .thermal_indices import (
    estimate_local_microclimate,
    calculate_utci_or_proxy,
    wbgt_screening_proxy,
    classify_wbgt_sg,
    classify_utci,
)


def _safe_rank_pct(s: pd.Series) -> pd.Series:
    """Percentile rank that remains finite when values are tied/missing."""
    out = pd.to_numeric(s, errors="coerce").rank(pct=True, method="average")
    return out.fillna(0.0).clip(0, 1)


def _score_clip(s: pd.Series, low: float, high: float) -> pd.Series:
    """Scale a numeric series to 0-1 using a fixed low/high range."""
    x = pd.to_numeric(s, errors="coerce")
    if high <= low:
        return pd.Series(0.0, index=s.index)
    return ((x - low) / (high - low)).clip(0, 1).fillna(0.0)


def run_grid_forecast(forecast_df: pd.DataFrame, grid_df: pd.DataFrame) -> pd.DataFrame:
    """Expand background forecast over grid cells and calculate heat-stress metrics."""
    df = estimate_local_microclimate(forecast_df, grid_df)
    df["utci_c"] = calculate_utci_or_proxy(
        df["tair_local_c"], df["tmrt_proxy_c"], df["wind_local_ms"], df["relative_humidity_2m"]
    )
    df["wbgt_proxy_c"] = wbgt_screening_proxy(
        df["tair_local_c"], df["tmrt_proxy_c"], df["wind_local_ms"], df["relative_humidity_2m"]
    )
    df["wbgt_category_sg"] = df["wbgt_proxy_c"].apply(classify_wbgt_sg)
    df["utci_category"] = df["utci_c"].apply(classify_utci)

    # Threshold flags. WBGT follows Singapore public advisory categories;
    # UTCI follows standard UTCI heat-stress classes.
    df["wbgt_moderate_or_high"] = df["wbgt_proxy_c"] >= 31
    df["wbgt_high"] = df["wbgt_proxy_c"] >= 33
    df["utci_moderate_or_higher"] = df["utci_c"] >= 26
    df["utci_strong_or_higher"] = df["utci_c"] >= 32
    df["utci_very_strong_or_higher"] = df["utci_c"] >= 38
    df["utci_extreme"] = df["utci_c"] >= 46
    return df


def summarize_hotspots(grid_forecast_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse hourly grid forecast to hotspot ranking per cell.

    v0.6.3 used a threshold-heavy hazard score that could become constant
    during non-WBGT-advisory days. v0.6.4 adds continuous UTCI/WBGT intensity
    and relative-ranking components. This makes the hotspot ranking useful for
    screening even when every cell remains below WBGT 31 °C.
    """
    if grid_forecast_df.empty:
        return pd.DataFrame()

    hours_per_cell = grid_forecast_df.groupby("cell_id").size().rename("forecast_hours")

    g = grid_forecast_df.groupby("cell_id", as_index=False).agg(
        lat=("lat", "first"),
        lon=("lon", "first"),
        land_use_hint=("land_use_hint", "first"),
        max_utci_c=("utci_c", "max"),
        mean_utci_c=("utci_c", "mean"),
        p90_utci_c=("utci_c", lambda x: x.quantile(0.9)),
        max_wbgt_proxy_c=("wbgt_proxy_c", "max"),
        mean_wbgt_proxy_c=("wbgt_proxy_c", "mean"),
        p90_wbgt_proxy_c=("wbgt_proxy_c", lambda x: x.quantile(0.9)),
        moderate_wbgt_hours=("wbgt_moderate_or_high", "sum"),
        high_wbgt_hours=("wbgt_high", "sum"),
        strong_utci_hours=("utci_strong_or_higher", "sum"),
        very_strong_utci_hours=("utci_very_strong_or_higher", "sum"),
        extreme_utci_hours=("utci_extreme", "sum"),
        gvi_percent=("gvi_percent", "first"),
        svf=("svf", "first"),
        shade_fraction=("shade_fraction", "first"),
        building_density=("building_density", "first"),
        road_fraction=("road_fraction", "first"),
        elderly_proxy=("elderly_proxy", "first"),
        outdoor_exposure_proxy=("outdoor_exposure_proxy", "first"),
    )
    g = g.merge(hours_per_cell.reset_index(), on="cell_id", how="left")
    g["forecast_hours"] = g["forecast_hours"].replace(0, np.nan)

    # Continuous/absolute components. These are screening ranges, not clinical thresholds.
    # v0.6.4.1 leans more strongly on percentile ranks so non-advisory days
    # still produce a differentiated hotspot ranking, while retaining absolute
    # threshold terms for genuine moderate/high WBGT regimes.
    g["hazard_utci_intensity_score"] = _score_clip(g["max_utci_c"], 26, 46)
    g["hazard_utci_duration_score"] = (
        pd.to_numeric(g["strong_utci_hours"], errors="coerce") / g["forecast_hours"]
    ).clip(0, 1).fillna(0.0)
    g["hazard_utci_relative_score"] = (
        0.50 * _safe_rank_pct(g["max_utci_c"])
        + 0.30 * _safe_rank_pct(g["p90_utci_c"])
        + 0.20 * _safe_rank_pct(g["mean_utci_c"])
    ).clip(0, 1)

    g["hazard_wbgt_relative_score"] = _safe_rank_pct(g["max_wbgt_proxy_c"])
    # WBGT proxy score starts below Singapore's moderate threshold so that
    # sub-threshold but relatively hotter conditions still influence ranking.
    g["hazard_wbgt_intensity_score"] = _score_clip(g["max_wbgt_proxy_c"], 27, 35)
    g["hazard_wbgt_moderate_duration_score"] = (
        pd.to_numeric(g["moderate_wbgt_hours"], errors="coerce") / 18.0
    ).clip(0, 1).fillna(0.0)
    g["hazard_wbgt_high_duration_score"] = (
        pd.to_numeric(g["high_wbgt_hours"], errors="coerce") / 6.0
    ).clip(0, 1).fillna(0.0)
    g["hazard_wbgt_duration_score"] = (
        0.65 * g["hazard_wbgt_moderate_duration_score"]
        + 0.35 * g["hazard_wbgt_high_duration_score"]
    ).clip(0, 1)

    g["hazard_score"] = (
        0.30 * g["hazard_wbgt_relative_score"]
        + 0.25 * g["hazard_utci_relative_score"]
        + 0.15 * g["hazard_utci_intensity_score"]
        + 0.10 * g["hazard_wbgt_intensity_score"]
        + 0.10 * g["hazard_utci_duration_score"]
        + 0.06 * g["hazard_wbgt_moderate_duration_score"]
        + 0.04 * g["hazard_wbgt_high_duration_score"]
    ).clip(0, 1)

    g["vulnerability_score"] = _safe_rank_pct(g["elderly_proxy"])
    g["exposure_score"] = _safe_rank_pct(g["outdoor_exposure_proxy"])
    g["risk_priority_score"] = (
        0.62 * g["hazard_score"]
        + 0.23 * g["vulnerability_score"]
        + 0.15 * g["exposure_score"]
    ).clip(0, 1)

    g["peak_utci_category"] = g["max_utci_c"].apply(classify_utci)
    g["peak_wbgt_category_sg"] = g["max_wbgt_proxy_c"].apply(classify_wbgt_sg)

    g = g.sort_values(["risk_priority_score", "hazard_score", "max_utci_c"], ascending=False)
    g["rank"] = range(1, len(g) + 1)
    return g


def _wbgt_alert(row: pd.Series, cell_count: int) -> str:
    if row["cells_high"] > 0 or row["max_wbgt_proxy_c"] >= 33:
        return "high"
    moderate_cell_trigger = max(1, int(np.ceil(0.10 * cell_count)))
    if row["cells_moderate_or_high"] >= moderate_cell_trigger or row["max_wbgt_proxy_c"] >= 31:
        return "moderate"
    return "low"


def _utci_alert(row: pd.Series, cell_count: int) -> str:
    if row["cells_extreme_utci"] > 0 or row["max_utci_c"] >= 46:
        return "extreme"
    if row["cells_very_strong_utci"] > 0 or row["max_utci_c"] >= 38:
        return "very_strong"
    strong_cell_trigger = max(1, int(np.ceil(0.25 * cell_count)))
    if row["cells_strong_utci"] >= strong_cell_trigger or row["max_utci_c"] >= 32:
        return "strong"
    if row["cells_moderate_utci"] > 0 or row["max_utci_c"] >= 26:
        return "moderate"
    return "low"


def _combined_alert(wbgt_alert: str, utci_alert: str) -> str:
    # WBGT is the Singapore public-warning-aligned signal; UTCI is kept as a
    # thermal-comfort/urban-design signal. The combined label is deliberately
    # conservative and should not be represented as an official advisory.
    if wbgt_alert == "high" or utci_alert in {"very_strong", "extreme"}:
        return "high"
    if wbgt_alert == "moderate" or utci_alert == "strong":
        return "elevated"
    if utci_alert == "moderate":
        return "watch"
    return "low"


def detect_event_windows(grid_forecast_df: pd.DataFrame) -> pd.DataFrame:
    """Summarise heat-stress event timing across the neighbourhood.

    Outputs separate WBGT and UTCI alerts because these indices answer different
    questions and can legitimately disagree.
    """
    if grid_forecast_df.empty:
        return pd.DataFrame()

    h = grid_forecast_df.groupby("time", as_index=False).agg(
        cell_count=("cell_id", "nunique"),
        max_wbgt_proxy_c=("wbgt_proxy_c", "max"),
        p90_wbgt_proxy_c=("wbgt_proxy_c", lambda x: x.quantile(0.9)),
        cells_moderate_or_high=("wbgt_moderate_or_high", "sum"),
        cells_high=("wbgt_high", "sum"),
        max_utci_c=("utci_c", "max"),
        p90_utci_c=("utci_c", lambda x: x.quantile(0.9)),
        cells_moderate_utci=("utci_moderate_or_higher", "sum"),
        cells_strong_utci=("utci_strong_or_higher", "sum"),
        cells_very_strong_utci=("utci_very_strong_or_higher", "sum"),
        cells_extreme_utci=("utci_extreme", "sum"),
    )

    h["wbgt_alert"] = h.apply(lambda r: _wbgt_alert(r, int(r["cell_count"])), axis=1)
    h["utci_alert"] = h.apply(lambda r: _utci_alert(r, int(r["cell_count"])), axis=1)
    h["combined_alert"] = [
        _combined_alert(w, u) for w, u in zip(h["wbgt_alert"], h["utci_alert"])
    ]
    # Backward-compatible alias. In v0.6.4 this is no longer WBGT-only.
    h["neighbourhood_alert"] = h["combined_alert"]
    return h
