"""Shared utilities for OpenHeat v1.1/v11 archive QA and calibration.

These helpers are deliberately defensive: v0.9/v10 archive exports may use
slightly different column names, so the v11 scripts infer common columns and
write explicit reports instead of failing silently.
"""
from __future__ import annotations

import glob
import json
import math
import re
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None


def read_json(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def expand_globs(patterns: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for pat in patterns or []:
        for p in glob.glob(str(pat), recursive=True):
            pp = Path(p)
            if pp.is_file() and pp.suffix.lower() in {".csv", ".txt", ".json", ".jsonl"}:
                paths.append(pp)
    # preserve deterministic order and remove duplicates
    seen = set()
    out = []
    for p in sorted(paths):
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def read_table(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() == ".jsonl":
        return pd.read_json(p, lines=True)
    if p.suffix.lower() == ".json":
        try:
            return pd.read_json(p)
        except Exception:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                # common wrappers: records/data/items/observations
                for k in ["records", "data", "items", "observations", "results"]:
                    if k in data and isinstance(data[k], list):
                        return pd.DataFrame(data[k])
                return pd.DataFrame([data])
            return pd.DataFrame(data)
    # CSV/TXT
    try:
        return pd.read_csv(p)
    except UnicodeDecodeError:
        return pd.read_csv(p, encoding="utf-8-sig")


def read_many(paths: Iterable[Path], kind: str) -> pd.DataFrame:
    frames = []
    for p in paths:
        try:
            df = read_table(p)
            if len(df) == 0:
                continue
            df["_source_file"] = str(p)
            df["_source_kind"] = kind
            frames.append(df)
        except Exception as e:
            print(f"[WARN] failed reading {p}: {e}")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def norm_col_name(c: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_")


def normalized_columns(df: pd.DataFrame) -> dict[str, str]:
    """Map normalized col name -> original col name."""
    return {norm_col_name(c): c for c in df.columns}


def first_present(df: pd.DataFrame, candidates: Iterable[str], override: Optional[str] = None) -> Optional[str]:
    if override and override in df.columns:
        return override
    nmap = normalized_columns(df)
    for c in candidates:
        if c in df.columns:
            return c
        nc = norm_col_name(c)
        if nc in nmap:
            return nmap[nc]
    return None


def parse_timestamp_series(s: pd.Series, timezone: str = "Asia/Singapore", round_freq: Optional[str] = None) -> pd.Series:
    ts = pd.to_datetime(s, errors="coerce")
    # pandas returns object if mixed tz; normalize by converting individually only if needed.
    try:
        if getattr(ts.dt, "tz", None) is None:
            ts = ts.dt.tz_localize(timezone, nonexistent="shift_forward", ambiguous="NaT")
        else:
            ts = ts.dt.tz_convert(timezone)
    except Exception:
        # Fallback: parse utc then convert. This is intentionally conservative.
        ts = pd.to_datetime(s, errors="coerce", utc=True).dt.tz_convert(timezone)
    if round_freq:
        ts = ts.dt.round(round_freq)
    return ts


def safe_numeric(df: pd.DataFrame, col: str | None) -> pd.Series:
    if col is None or col not in df.columns:
        return pd.Series(np.nan, index=df.index)
    return pd.to_numeric(df[col], errors="coerce")


def normalize_station_id(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.upper().replace({"NAN": np.nan, "NONE": np.nan, "": np.nan})


def infer_station_from_file(path_series: pd.Series) -> pd.Series:
    # Try extracting NEA-like station IDs e.g. S128, S121, station_S128.
    vals = []
    for p in path_series.astype(str):
        m = re.search(r"\b(S\d{2,4})\b", p, flags=re.I)
        vals.append(m.group(1).upper() if m else np.nan)
    return pd.Series(vals, index=path_series.index)


def vapor_pressure_hpa(temp_c: pd.Series, rh_pct: pd.Series) -> pd.Series:
    temp_c = pd.to_numeric(temp_c, errors="coerce")
    rh_pct = pd.to_numeric(rh_pct, errors="coerce")
    return (rh_pct / 100.0) * 6.105 * np.exp((17.27 * temp_c) / (237.7 + temp_c))


def fallback_wbgt_proxy(temp_c: pd.Series, rh_pct: pd.Series) -> pd.Series:
    """Simple shaded WBGT-like fallback; use only when project proxy is absent."""
    e = vapor_pressure_hpa(temp_c, rh_pct)
    return 0.567 * pd.to_numeric(temp_c, errors="coerce") + 0.393 * e + 3.94


def add_time_features(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    out = df.copy()
    ts = pd.to_datetime(out[timestamp_col], errors="coerce")
    # Use local displayed hour from timezone-aware timestamps.
    out["date"] = ts.dt.date.astype(str)
    out["hour"] = ts.dt.hour + ts.dt.minute / 60.0
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24.0)
    out["is_daytime_07_19"] = ((out["hour"] >= 7) & (out["hour"] < 19)).astype(int)
    out["is_peak_13_16"] = ((out["hour"] >= 13) & (out["hour"] <= 16)).astype(int)
    return out


def add_weather_lags(df: pd.DataFrame, station_col: str = "station_id") -> pd.DataFrame:
    out = df.sort_values([station_col, "timestamp"]).copy() if station_col in df.columns else df.sort_values("timestamp").copy()
    groups = out.groupby(station_col, dropna=False) if station_col in out.columns else [(None, out)]
    pieces = []
    for _, g in groups:
        g = g.sort_values("timestamp").copy()
        for col in ["air_temperature_c", "relative_humidity_pct", "wind_speed_m_s", "shortwave_w_m2", "cloud_cover_pct"]:
            if col in g.columns:
                g[f"{col}_lag1"] = g[col].shift(1)
                g[f"{col}_roll3_mean"] = g[col].rolling(3, min_periods=1).mean()
        if "shortwave_w_m2" in g.columns:
            # approximate cumulative same-day shortwave signal
            g["shortwave_day_cumsum"] = g.groupby("date")["shortwave_w_m2"].cumsum()
        if "air_temperature_c" in g.columns:
            g["dtemp_dt"] = g["air_temperature_c"].diff()
        pieces.append(g)
    return pd.concat(pieces, ignore_index=True, sort=False)


def metric_summary(y_true, y_pred) -> dict:
    y = pd.to_numeric(pd.Series(y_true), errors="coerce")
    p = pd.to_numeric(pd.Series(y_pred), errors="coerce")
    mask = y.notna() & p.notna()
    if mask.sum() == 0:
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


def event_metrics(y_true, y_score, event_threshold: float, score_threshold: float) -> dict:
    y = pd.to_numeric(pd.Series(y_true), errors="coerce")
    s = pd.to_numeric(pd.Series(y_score), errors="coerce")
    mask = y.notna() & s.notna()
    if mask.sum() == 0:
        return {"n": 0, "tp": 0, "fp": 0, "tn": 0, "fn": 0, "precision": np.nan, "recall": np.nan, "f1": np.nan}
    obs = (y[mask] >= event_threshold).to_numpy(bool)
    pred = (s[mask] >= score_threshold).to_numpy(bool)
    tp = int(np.sum(obs & pred)); fp = int(np.sum(~obs & pred)); tn = int(np.sum(~obs & ~pred)); fn = int(np.sum(obs & ~pred))
    precision = tp / (tp + fp) if (tp + fp) else np.nan
    recall = tp / (tp + fn) if (tp + fn) else np.nan
    f1 = 2 * precision * recall / (precision + recall) if np.isfinite(precision) and np.isfinite(recall) and (precision + recall) else np.nan
    return {"n": int(mask.sum()), "tp": tp, "fp": fp, "tn": tn, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def write_md(path: str | Path, text: str) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    p.write_text(text, encoding="utf-8")


def df_to_md_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df is None or df.empty:
        return "_No data._"
    return df.head(max_rows).to_markdown(index=False)
