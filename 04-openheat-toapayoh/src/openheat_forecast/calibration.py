"""Calibration and validation utilities for OpenHeat v0.6.1.

The calibration target is intentionally explicit:
    Open-Meteo + OpenHeat WBGT_proxy -> official NEA WBGT observation

Official WBGT is the observation target for bias correction and validation only;
it should not be fed back into the WBGT proxy formula as an input variable.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional
import numpy as np
import pandas as pd

from .time_utils import to_singapore_time_series


@dataclass
class LinearCalibration:
    """Simple calibration model: observed = intercept + slope * proxy."""
    intercept: float
    slope: float
    n: int
    rmse_before: float
    rmse_after: float
    mae_before: float
    mae_after: float
    bias_before: float
    bias_after: float

    def to_dict(self) -> dict:
        return asdict(self)


def station_skill_metrics(df: pd.DataFrame, pred_col: str, obs_col: str, group_col: Optional[str] = None) -> pd.DataFrame:
    """Return MAE/RMSE/bias/correlation for predicted vs observed values."""
    x = df.dropna(subset=[pred_col, obs_col]).copy()
    if x.empty:
        return pd.DataFrame(columns=[group_col or "group", "n", "mae", "rmse", "bias", "corr"])

    def _one(g: pd.DataFrame) -> dict:
        err = g[pred_col] - g[obs_col]
        return {
            "n": int(len(g)),
            "mae": float(err.abs().mean()),
            "rmse": float(np.sqrt(np.mean(np.square(err)))),
            "bias": float(err.mean()),
            "corr": float(g[[pred_col, obs_col]].corr().iloc[0, 1]) if len(g) > 2 else np.nan,
        }

    if group_col is None:
        return pd.DataFrame([{ "group": "all", **_one(x)}])
    return pd.DataFrame([{group_col: k, **_one(g)} for k, g in x.groupby(group_col, dropna=False)])


def fit_linear_calibration(df: pd.DataFrame, proxy_col: str = "wbgt_proxy_c", obs_col: str = "official_wbgt_c") -> LinearCalibration:
    """Fit a transparent linear calibration: official WBGT = a + b * proxy."""
    x = df.dropna(subset=[proxy_col, obs_col]).copy()
    if len(x) < 3:
        raise ValueError("Need at least 3 paired observations for linear calibration.")
    pred = x[proxy_col].to_numpy(dtype=float)
    obs = x[obs_col].to_numpy(dtype=float)
    slope, intercept = np.polyfit(pred, obs, 1)
    corrected = intercept + slope * pred
    err_before = pred - obs
    err_after = corrected - obs
    return LinearCalibration(
        intercept=float(intercept),
        slope=float(slope),
        n=int(len(x)),
        rmse_before=float(np.sqrt(np.mean(err_before**2))),
        rmse_after=float(np.sqrt(np.mean(err_after**2))),
        mae_before=float(np.mean(np.abs(err_before))),
        mae_after=float(np.mean(np.abs(err_after))),
        bias_before=float(np.mean(err_before)),
        bias_after=float(np.mean(err_after)),
    )


def apply_linear_calibration(df: pd.DataFrame, model: LinearCalibration | dict, proxy_col: str = "wbgt_proxy_c", out_col: str = "wbgt_calibrated_c") -> pd.DataFrame:
    """Apply a linear calibration object/dict to a dataframe."""
    if isinstance(model, dict):
        intercept = float(model["intercept"])
        slope = float(model["slope"])
    else:
        intercept = model.intercept
        slope = model.slope
    out = df.copy()
    out[out_col] = intercept + slope * out[proxy_col]
    return out


def make_paired_wbgt_table(pred_df: pd.DataFrame, obs_df: pd.DataFrame, time_tolerance: str = "20min") -> pd.DataFrame:
    """Pair modelled WBGT proxy with official WBGT observations by station/time.

    Time columns are converted to tz-aware Asia/Singapore timestamps before the
    nearest-time merge to avoid UTC/SGT drift.
    """
    p = pred_df.copy()
    o = obs_df.copy()
    if "time" not in p.columns or "timestamp" not in o.columns:
        raise ValueError("pred_df must contain 'time' and obs_df must contain 'timestamp'.")
    p["time"] = to_singapore_time_series(p["time"])
    o["timestamp"] = to_singapore_time_series(o["timestamp"])
    p = p.dropna(subset=["time", "station_id"]).sort_values("time")
    o = o.dropna(subset=["timestamp", "station_id"]).sort_values("timestamp")
    rows = []
    for sid, pg in p.groupby("station_id"):
        og = o[o["station_id"] == sid].sort_values("timestamp")
        if og.empty:
            continue
        merged = pd.merge_asof(
            pg.sort_values("time"),
            og.sort_values("timestamp"),
            left_on="time",
            right_on="timestamp",
            by="station_id",
            direction="nearest",
            tolerance=pd.Timedelta(time_tolerance),
        )
        rows.append(merged)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def calibration_readiness_check(paired_df: pd.DataFrame, obs_col: str = "official_wbgt_c") -> dict:
    """Checklist for whether calibration results can be trusted."""
    x = paired_df.dropna(subset=[obs_col]) if obs_col in paired_df.columns else pd.DataFrame()
    days = to_singapore_time_series(x.get("time", pd.Series([], dtype=str))).dt.date.nunique() if "time" in x.columns else 0
    has_high = bool((x[obs_col] >= 33).any()) if obs_col in x.columns and not x.empty else False
    has_moderate = bool((x[obs_col] >= 31).any()) if obs_col in x.columns and not x.empty else False
    regime_count = None
    if {"shortwave_radiation", "cloud_cover"}.issubset(x.columns):
        sw = pd.to_numeric(x["shortwave_radiation"], errors="coerce")
        cc = pd.to_numeric(x["cloud_cover"], errors="coerce")
        regimes = np.select(
            [sw >= 650, cc >= 70],
            ["sunny_high_radiation", "overcast_cloudy"],
            default="mixed_or_transition",
        )
        regime_count = int(pd.Series(regimes).nunique())
    out = {
        "paired_observations": int(len(x)),
        "unique_stations": int(x["station_id"].nunique()) if "station_id" in x.columns else 0,
        "unique_days": int(days),
        "has_high_wbgt_33plus": has_high,
        "has_moderate_wbgt_31plus": has_moderate,
        "regime_count_if_available": regime_count,
    }
    enough_base = out["paired_observations"] >= 30 and out["unique_days"] >= 2
    enough_event = has_moderate
    out["recommendation"] = (
        "OK for preliminary v0.6.1 bias correction; still not an operational public-health warning model"
        if enough_base and enough_event
        else "Not enough event diversity for publishable calibration; use as API/schema/archive test only"
    )
    if not has_high:
        out["high_wbgt_note"] = "No WBGT ≥33°C pairs yet; high-heat performance remains untested."
    return out
