"""
OpenHeat v0.9-beta: WBGT proxy calibration with thermal-inertia features and LOSO-CV.

This script reads v0.9-alpha's paired official WBGT table and evaluates:
  M0 raw physics proxy
  M1 global bias correction
  M1b period-specific bias correction
  M2 linear proxy calibration
  M3 current-weather regime ridge calibration
  M4 thermal-inertia ridge calibration with lagged/cumulative radiation
  M5 M4 + station-nearest morphology diagnostic model

Primary validation is Leave-One-Station-Out CV. Random split is intentionally not used.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def df_to_markdown(df: pd.DataFrame, max_rows: int = 25, floatfmt: str = ".4f") -> str:
    if df is None or len(df) == 0:
        return "_(empty)_"
    d = df.head(max_rows).copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda x: "" if pd.isna(x) else format(float(x), floatfmt))
    cols = list(d.columns)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for _, row in d.iterrows():
        rows.append("| " + " | ".join([str(row[c]) for c in cols]) + " |")
    if len(df) > max_rows:
        rows.append("| ... | " + " | ".join([""] * (len(cols) - 1)) + " |")
    return "\n".join([header, sep] + rows)


def robust_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def safe_fraction(num: pd.Series, den: pd.Series) -> pd.Series:
    den = den.replace(0, np.nan)
    out = num / den
    return out.replace([np.inf, -np.inf], np.nan).fillna(0).clip(0, 1)


def classify_period(hour: float, cfg: dict) -> str:
    if pd.isna(hour):
        return "unknown"
    if cfg["daytime_start_hour"] <= hour < cfg["daytime_end_hour"]:
        return "daytime"
    if hour < cfg["night_end_hour"] or hour >= cfg["night_start_hour"]:
        return "nighttime"
    return "shoulder"


def add_time_and_inertia_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    df = df.copy()
    ts_col = cfg["timestamp_col"]
    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    df["hour_sgt_numeric"] = df[ts_col].dt.hour + df[ts_col].dt.minute / 60.0
    df["date_sgt_derived"] = df[ts_col].dt.strftime("%Y-%m-%d")
    df["hour_sin_beta"] = np.sin(2 * np.pi * df["hour_sgt_numeric"] / 24.0)
    df["hour_cos_beta"] = np.cos(2 * np.pi * df["hour_sgt_numeric"] / 24.0)
    df["period_beta"] = df["hour_sgt_numeric"].apply(lambda h: classify_period(h, cfg))
    df["is_daytime"] = ((df["hour_sgt_numeric"] >= cfg["daytime_start_hour"]) & (df["hour_sgt_numeric"] < cfg["daytime_end_hour"])).astype(int)
    df["is_peak_heat"] = ((df["hour_sgt_numeric"] >= cfg["peak_start_hour"]) & (df["hour_sgt_numeric"] < cfg["peak_end_hour"])).astype(int)
    df["is_nighttime"] = ((df["hour_sgt_numeric"] < cfg["night_end_hour"]) | (df["hour_sgt_numeric"] >= cfg["night_start_hour"])).astype(int)

    numeric_cols = [
        cfg["target_col"], cfg["proxy_col"], "temperature_2m", "relative_humidity_2m",
        "wind_speed_10m", "shortwave_radiation", "direct_radiation", "diffuse_radiation",
        "cloud_cover",
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = robust_numeric(df[c])

    sw = df.get("shortwave_radiation", pd.Series(0.0, index=df.index)).fillna(0)
    direct = df.get("direct_radiation", pd.Series(0.0, index=df.index)).fillna(0)
    diffuse = df.get("diffuse_radiation", pd.Series(0.0, index=df.index)).fillna(0)
    df["direct_fraction"] = safe_fraction(direct, sw)
    df["diffuse_fraction"] = safe_fraction(diffuse, sw)
    df["shortwave_positive"] = (sw > 20).astype(int)

    sort_cols = [cfg["station_col"], "date_sgt_derived", ts_col]
    df = df.sort_values(sort_cols).reset_index(drop=True)
    group_cols = [cfg["station_col"], "date_sgt_derived"]
    grp = df.groupby(group_cols, sort=False, group_keys=False)

    # 15-min archive: 4 samples ≈ 1h, 8 samples ≈ 2h, 12 samples ≈ 3h.
    df["shortwave_lag_1h"] = grp["shortwave_radiation"].shift(4)
    df["shortwave_lag_2h"] = grp["shortwave_radiation"].shift(8)
    df["shortwave_3h_mean"] = grp["shortwave_radiation"].apply(lambda s: s.rolling(window=12, min_periods=1).mean())
    df["cumulative_day_shortwave_whm2"] = grp["shortwave_radiation"].apply(lambda s: s.fillna(0).cumsum() * 0.25)
    df["temperature_lag_1h"] = grp["temperature_2m"].shift(4)
    df["dTair_dt_1h"] = df["temperature_2m"] - df["temperature_lag_1h"]
    df["proxy_lag_1h"] = grp[cfg["proxy_col"]].shift(4)
    df["proxy_3h_mean"] = grp[cfg["proxy_col"]].apply(lambda s: s.rolling(window=12, min_periods=1).mean())

    for c in ["shortwave_lag_1h", "shortwave_lag_2h", "shortwave_3h_mean"]:
        df[c] = df[c].fillna(df.get("shortwave_radiation", 0))
    df["temperature_lag_1h"] = df["temperature_lag_1h"].fillna(df.get("temperature_2m", np.nan))
    df["dTair_dt_1h"] = df["dTair_dt_1h"].fillna(0)
    df["proxy_lag_1h"] = df["proxy_lag_1h"].fillna(df[cfg["proxy_col"]])
    df["proxy_3h_mean"] = df["proxy_3h_mean"].fillna(df[cfg["proxy_col"]])
    df["residual_official_minus_proxy"] = df[cfg["target_col"]] - df[cfg["proxy_col"]]
    return df


@dataclass
class ModelSpec:
    name: str
    kind: str
    features: Optional[List[str]] = None
    description: str = ""


class GlobalBiasModel:
    def fit(self, train: pd.DataFrame, cfg: dict):
        self.bias_ = float((train[cfg["target_col"]] - train[cfg["proxy_col"]]).mean())
        return self
    def predict(self, test: pd.DataFrame, cfg: dict) -> np.ndarray:
        return (test[cfg["proxy_col"]] + self.bias_).to_numpy()


class PeriodBiasModel:
    def fit(self, train: pd.DataFrame, cfg: dict):
        residual = train[cfg["target_col"]] - train[cfg["proxy_col"]]
        tmp = pd.DataFrame({"period_beta": train["period_beta"], "residual": residual})
        self.global_bias_ = float(residual.mean())
        self.bias_by_period_ = tmp.groupby("period_beta")["residual"].mean().to_dict()
        return self
    def predict(self, test: pd.DataFrame, cfg: dict) -> np.ndarray:
        bias = test["period_beta"].map(self.bias_by_period_).fillna(self.global_bias_)
        return (test[cfg["proxy_col"]] + bias).to_numpy()


def available(df: pd.DataFrame, cols: List[str]) -> List[str]:
    return [c for c in cols if c in df.columns]


def model_specs(df: pd.DataFrame, cfg: dict) -> List[ModelSpec]:
    proxy = cfg["proxy_col"]
    current = available(df, [
        proxy, "shortwave_radiation", "diffuse_fraction", "direct_fraction",
        "wind_speed_10m", "cloud_cover", "hour_sin_beta", "hour_cos_beta",
    ])
    inertia = available(df, [
        proxy, "shortwave_radiation", "shortwave_3h_mean", "shortwave_lag_1h",
        "shortwave_lag_2h", "cumulative_day_shortwave_whm2", "diffuse_fraction",
        "direct_fraction", "wind_speed_10m", "cloud_cover", "dTair_dt_1h",
        "hour_sin_beta", "hour_cos_beta",
    ])
    morph = available(df, [
        "station_nearest_grid_svf", "station_nearest_grid_shade_fraction",
        "station_nearest_grid_tree_canopy_fraction", "station_nearest_grid_ndvi_mean",
        "station_nearest_grid_road_fraction", "station_nearest_grid_building_density",
    ])
    return [
        ModelSpec("M0_raw_proxy", "raw", description="Raw physics proxy; no calibration."),
        ModelSpec("M1_global_bias", "global_bias", description="Train-set mean residual added to proxy."),
        ModelSpec("M1b_period_bias", "period_bias", description="Train-set residual correction by period: daytime/nighttime/shoulder."),
        ModelSpec("M2_linear_proxy", "linear", features=[proxy], description="Linear proxy calibration; diagnostic slope model."),
        ModelSpec("M3_regime_current_ridge", "ridge", features=current, description="Ridge calibration with current weather regime."),
        ModelSpec("M4_inertia_ridge", "ridge", features=inertia, description="Ridge calibration with lagged/cumulative shortwave and dTair/dt."),
        ModelSpec("M5_inertia_morphology_ridge", "ridge", features=inertia + morph, description="M4 plus station-nearest morphology; diagnostic where morphology is representative."),
    ]


def clean_frame(df: pd.DataFrame, cfg: dict, features: Optional[List[str]] = None) -> pd.DataFrame:
    out = df.copy()
    req = [cfg["target_col"], cfg["proxy_col"], cfg["station_col"]]
    if features:
        req += features
    for c in req:
        if c in out.columns and c != cfg["station_col"]:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out.dropna(subset=[cfg["target_col"], cfg["proxy_col"], cfg["station_col"]])


def fit_predict(spec: ModelSpec, train: pd.DataFrame, test: pd.DataFrame, cfg: dict) -> tuple[np.ndarray, dict]:
    target = cfg["target_col"]
    proxy = cfg["proxy_col"]
    meta = {}
    if spec.kind == "raw":
        return test[proxy].to_numpy(), meta
    if spec.kind == "global_bias":
        m = GlobalBiasModel().fit(train, cfg)
        meta["bias"] = m.bias_
        return m.predict(test, cfg), meta
    if spec.kind == "period_bias":
        m = PeriodBiasModel().fit(train, cfg)
        meta["global_bias"] = m.global_bias_
        meta.update({f"bias_{k}": v for k, v in m.bias_by_period_.items()})
        return m.predict(test, cfg), meta
    if spec.kind == "linear":
        Xtr = train[spec.features].copy()
        Xte = test[spec.features].copy()
        med = Xtr.median(numeric_only=True)
        Xtr = Xtr.fillna(med).fillna(0)
        Xte = Xte.fillna(med).fillna(0)
        ytr = train[target].to_numpy()
        m = LinearRegression().fit(Xtr, ytr)
        pred = m.predict(Xte)
        meta["intercept"] = float(m.intercept_)
        if len(spec.features) == 1:
            meta["slope"] = float(m.coef_[0])
        else:
            for f, coef in zip(spec.features, m.coef_):
                meta[f"coef_{f}"] = float(coef)
        return pred, meta
    if spec.kind == "ridge":
        Xtr = train[spec.features].copy()
        Xte = test[spec.features].copy()
        med = Xtr.median(numeric_only=True)
        Xtr = Xtr.fillna(med).fillna(0)
        Xte = Xte.fillna(med).fillna(0)
        ytr = train[target].to_numpy()
        m = make_pipeline(StandardScaler(), Ridge(alpha=float(cfg.get("ridge_alpha", 1.0)))).fit(Xtr, ytr)
        pred = m.predict(Xte)
        ridge = m[-1]
        for f, coef in zip(spec.features, ridge.coef_):
            meta[f"coef_std_{f}"] = float(coef)
        return pred, meta
    raise ValueError(spec.kind)


def regression_metrics(y: pd.Series, pred: pd.Series) -> dict:
    err = pred - y
    ae = err.abs()
    return {
        "n": int(len(y)),
        "bias_pred_minus_obs": float(err.mean()) if len(y) else np.nan,
        "mae": float(ae.mean()) if len(y) else np.nan,
        "rmse": float(np.sqrt((err ** 2).mean())) if len(y) else np.nan,
        "p90_abs_error": float(ae.quantile(0.9)) if len(y) else np.nan,
    }


def event_metrics(y: pd.Series, pred: pd.Series, th: float) -> dict:
    obs = y >= th
    pr = pred >= th
    tp = int((obs & pr).sum())
    fp = int((~obs & pr).sum())
    fn = int((obs & ~pr).sum())
    tn = int((~obs & ~pr).sum())
    precision = tp / (tp + fp) if tp + fp else np.nan
    recall = tp / (tp + fn) if tp + fn else np.nan
    f1 = 2 * precision * recall / (precision + recall) if precision == precision and recall == recall and precision + recall else np.nan
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "f1": f1}


def masks(df: pd.DataFrame, cfg: dict) -> dict[str, pd.Series]:
    h = df["hour_sgt_numeric"]
    return {
        "overall": pd.Series(True, index=df.index),
        "daytime_09_18": (h >= cfg["daytime_start_hour"]) & (h < cfg["daytime_end_hour"]),
        "peak_12_16": (h >= cfg["peak_start_hour"]) & (h < cfg["peak_end_hour"]),
        "night_00_07_20_23": (h < cfg["night_end_hour"]) | (h >= cfg["night_start_hour"]),
    }


def build_predictions(df: pd.DataFrame, specs: List[ModelSpec], cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    id_cols = [
        cfg["timestamp_col"], "date_sgt_derived", "hour_sgt_numeric", "period_beta",
        cfg["station_col"], "station_name", "heat_stress_category", cfg["target_col"], cfg["proxy_col"],
    ]
    id_cols = [c for c in id_cols if c in df.columns]
    pred_blocks = []
    meta_rows = []
    stations = sorted(df[cfg["station_col"]].dropna().unique())
    min_train = int(cfg.get("minimum_train_rows_per_fold", 100))
    for spec in specs:
        d = clean_frame(df, cfg, spec.features)
        # Apparent
        pred, meta = fit_predict(spec, d, d, cfg)
        b = d[id_cols].copy()
        b["model"] = spec.name
        b["split_type"] = "apparent"
        b["heldout_station_id"] = "ALL"
        b["y_true"] = d[cfg["target_col"]].to_numpy()
        b["y_pred"] = pred
        b["residual_pred_minus_obs"] = b["y_pred"] - b["y_true"]
        pred_blocks.append(b)
        meta.update({"model": spec.name, "split_type": "apparent", "heldout_station_id": "ALL", "n_train": len(d), "n_test": len(d), "description": spec.description})
        meta_rows.append(meta)
        # LOSO
        for st in stations:
            test = d[d[cfg["station_col"]] == st].copy()
            train = d[d[cfg["station_col"]] != st].copy()
            if len(test) == 0 or len(train) < min_train:
                continue
            try:
                pred, meta = fit_predict(spec, train, test, cfg)
            except Exception as exc:
                pred = np.full(len(test), np.nan)
                meta = {"error": repr(exc)}
            b = test[id_cols].copy()
            b["model"] = spec.name
            b["split_type"] = "LOSO"
            b["heldout_station_id"] = st
            b["y_true"] = test[cfg["target_col"]].to_numpy()
            b["y_pred"] = pred
            b["residual_pred_minus_obs"] = b["y_pred"] - b["y_true"]
            pred_blocks.append(b)
            meta.update({"model": spec.name, "split_type": "LOSO", "heldout_station_id": st, "n_train": len(train), "n_test": len(test), "description": spec.description})
            meta_rows.append(meta)
    return pd.concat(pred_blocks, ignore_index=True, sort=False), pd.DataFrame(meta_rows)


def compute_metrics(pred: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, evrows = [], []
    for (model, split), g in pred.groupby(["model", "split_type"], sort=False):
        for pname, mask in masks(g, cfg).items():
            gg = g[mask].dropna(subset=["y_true", "y_pred"])
            if len(gg) == 0:
                continue
            r = regression_metrics(gg["y_true"], gg["y_pred"])
            r.update({"model": model, "split_type": split, "period": pname})
            rows.append(r)
            for th in [float(x) for x in cfg.get("thresholds", [31.0, 33.0])]:
                e = event_metrics(gg["y_true"], gg["y_pred"], th)
                e.update({"model": model, "split_type": split, "period": pname, "threshold": th})
                evrows.append(e)
    return pd.DataFrame(rows), pd.DataFrame(evrows)


def by_station(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, split, sid), g in pred.groupby(["model", "split_type", "station_id"], sort=False):
        gg = g.dropna(subset=["y_true", "y_pred"])
        if len(gg):
            r = regression_metrics(gg["y_true"], gg["y_pred"])
            r.update({"model": model, "split_type": split, "station_id": sid, "station_name": gg["station_name"].iloc[0] if "station_name" in gg else ""})
            rows.append(r)
    return pd.DataFrame(rows)


def by_hour(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, split, hour), g in pred.groupby(["model", "split_type", "hour_sgt_numeric"], sort=False):
        gg = g.dropna(subset=["y_true", "y_pred"])
        if len(gg):
            err = gg["y_pred"] - gg["y_true"]
            rows.append({"model": model, "split_type": split, "hour_sgt_numeric": hour, "n": len(gg), "bias_pred_minus_obs": err.mean(), "mae": err.abs().mean(), "official_wbgt_mean": gg["y_true"].mean(), "pred_wbgt_mean": gg["y_pred"].mean()})
    return pd.DataFrame(rows)


def focus_timeline(pred: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    focus = cfg.get("focus_stations", [])
    models = ["M0_raw_proxy", "M1_global_bias", "M2_linear_proxy", "M4_inertia_ridge"]
    d = pred[(pred["split_type"] == "LOSO") & (pred["station_id"].isin(focus)) & (pred["model"].isin(models))].copy()
    if len(d) == 0:
        return pd.DataFrame()
    idx = ["timestamp_sgt", "station_id", "station_name", "y_true", "heat_stress_category"]
    idx = [c for c in idx if c in d.columns]
    wide = d.pivot_table(index=idx, columns="model", values="y_pred", aggfunc="first").reset_index()
    wide.columns.name = None
    return wide


def slope_diagnostics(meta: pd.DataFrame) -> pd.DataFrame:
    d = meta[meta["model"] == "M2_linear_proxy"].copy()
    keep = [c for c in ["model", "split_type", "heldout_station_id", "intercept", "slope", "n_train", "n_test"] if c in d.columns]
    d = d[keep]
    if "slope" in d.columns:
        d["slope_warning"] = np.select(
            [d["slope"] > 2.0, d["slope"] > 1.5],
            ["high_slope_gt_2_external_validity_risk", "slope_gt_1_5_range_expansion"],
            default="ok",
        )
    return d


def write_report(out_dir: Path, metrics: pd.DataFrame, events: pd.DataFrame, meta: pd.DataFrame, station_m: pd.DataFrame, hour_m: pd.DataFrame, slope: pd.DataFrame):
    lines = []
    lines.append("# OpenHeat v0.9-beta WBGT calibration report")
    lines.append("")
    lines.append("v0.9-beta evaluates non-ML calibration baselines for the raw physics WBGT proxy using period-specific metrics, thermal-inertia features and leave-one-station-out validation. No random split is used as primary evidence.")
    lines.append("")
    lines.append("## Models")
    model_info = meta[["model", "description"]].drop_duplicates().sort_values("model") if "description" in meta.columns else meta[["model"]].drop_duplicates()
    lines.append(df_to_markdown(model_info, 20))
    lines.append("")
    for split_name, title in [("apparent", "Apparent / in-sample"), ("LOSO", "Leave-One-Station-Out CV")]:
        lines.append(f"## {title}: overall metrics")
        d = metrics[(metrics["split_type"] == split_name) & (metrics["period"] == "overall")].sort_values("mae")
        lines.append(df_to_markdown(d[["model", "n", "bias_pred_minus_obs", "mae", "rmse", "p90_abs_error"]], 20))
        lines.append("")
    lines.append("## LOSO-CV metrics by period")
    d = metrics[metrics["split_type"] == "LOSO"].sort_values(["period", "mae"])
    lines.append(df_to_markdown(d[["model", "period", "n", "bias_pred_minus_obs", "mae", "rmse", "p90_abs_error"]], 80))
    lines.append("")
    lines.append("## LOSO-CV WBGT>=31 event detection")
    d = events[(events["split_type"] == "LOSO") & (events["threshold"] == 31.0)].sort_values(["period", "recall", "precision"], ascending=[True, False, False])
    lines.append(df_to_markdown(d[["model", "period", "tp", "fp", "fn", "tn", "precision", "recall", "f1"]], 80))
    lines.append("")
    lines.append("## LOSO-CV WBGT>=33 event detection")
    d = events[(events["split_type"] == "LOSO") & (events["threshold"] == 33.0)].sort_values(["period", "recall", "precision"], ascending=[True, False, False])
    lines.append(df_to_markdown(d[["model", "period", "tp", "fp", "fn", "tn", "precision", "recall", "f1"]], 80))
    lines.append("")
    lines.append("## Linear slope diagnostics")
    lines.append(df_to_markdown(slope, 60) if len(slope) else "No linear slope diagnostics available.")
    lines.append("")
    lines.append("## Station-level LOSO preview")
    d = station_m[station_m["split_type"] == "LOSO"].sort_values(["model", "mae"])
    lines.append(df_to_markdown(d[["model", "station_id", "station_name", "n", "bias_pred_minus_obs", "mae", "rmse", "p90_abs_error"]], 60))
    lines.append("")
    lines.append("## Interpretation notes")
    lines.append("- M1 global bias correction must be interpreted with day/night metrics because it may improve daytime underprediction while worsening night-time overprediction.")
    lines.append("- M2 linear proxy calibration is diagnostic; large slopes indicate proxy dynamic-range compression and can be unsafe for external operation.")
    lines.append("- M4/M5 include lagged/cumulative shortwave features to represent thermal inertia and afternoon residual peaks.")
    lines.append("- LOSO-CV is the primary validation because random splits leak station/time structure and are not appropriate for deployment to unobserved grid cells.")
    lines.append("- This remains a 24h pilot archive, not final ML/calibration validation.")
    path = out_dir / "v09_beta_calibration_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] report: {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v09_beta_config.example.json")
    ap.add_argument("--input", default=None)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.input:
        cfg["input_pairs_csv"] = args.input
    if args.out_dir:
        cfg["output_dir"] = args.out_dir
    out_dir = ensure_dir(cfg["output_dir"])
    input_path = Path(cfg["input_pairs_csv"])
    if not input_path.exists():
        raise FileNotFoundError(f"Paired CSV not found: {input_path}")
    df = pd.read_csv(input_path)
    print(f"[INFO] loaded pairs: {input_path} rows={len(df)} cols={len(df.columns)}")
    df = add_time_and_inertia_features(df, cfg)
    df = clean_frame(df, cfg)
    print(f"[INFO] usable rows after cleaning: {len(df)} stations={df[cfg['station_col']].nunique()}")
    df.to_csv(out_dir / "v09_beta_engineered_pairs.csv", index=False)
    specs = model_specs(df, cfg)
    print("[INFO] model specs:")
    for s in specs:
        print(f"  - {s.name}: {s.kind}, features={s.features}")
    pred, meta = build_predictions(df, specs, cfg)
    pred.to_csv(out_dir / "v09_beta_predictions_long.csv", index=False)
    meta.to_csv(out_dir / "v09_beta_model_metadata.csv", index=False)
    metrics, events = compute_metrics(pred, cfg)
    metrics.to_csv(out_dir / "v09_beta_model_metrics.csv", index=False)
    events.to_csv(out_dir / "v09_beta_event_detection_metrics.csv", index=False)
    st_m = by_station(pred)
    hour_m = by_hour(pred)
    slope = slope_diagnostics(meta)
    st_m.to_csv(out_dir / "v09_beta_metrics_by_station.csv", index=False)
    hour_m.to_csv(out_dir / "v09_beta_residual_by_hour.csv", index=False)
    slope.to_csv(out_dir / "v09_beta_linear_slope_diagnostics.csv", index=False)
    focus = focus_timeline(pred, cfg)
    if len(focus):
        focus.to_csv(out_dir / "v09_beta_focus_station_timeline.csv", index=False)
    write_report(out_dir, metrics, events, meta, st_m, hour_m, slope)
    print("\n[SUMMARY] LOSO overall metrics sorted by MAE")
    loso = metrics[(metrics["split_type"] == "LOSO") & (metrics["period"] == "overall")].sort_values("mae")
    print(loso[["model", "n", "bias_pred_minus_obs", "mae", "rmse", "p90_abs_error"]].to_string(index=False))
    print("\n[SUMMARY] LOSO WBGT>=31 overall")
    ev31 = events[(events["split_type"] == "LOSO") & (events["period"] == "overall") & (events["threshold"] == 31.0)].sort_values("recall", ascending=False)
    print(ev31[["model", "tp", "fp", "fn", "tn", "precision", "recall", "f1"]].to_string(index=False))


if __name__ == "__main__":
    main()
