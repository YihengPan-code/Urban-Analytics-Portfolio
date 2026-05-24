from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from v11_lib import read_json, ensure_dir, metric_summary, event_metrics, write_md, df_to_md_table, fallback_wbgt_proxy

try:
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LinearRegression, Ridge
except Exception as e:  # pragma: no cover
    raise SystemExit("[ERROR] scikit-learn is required. Install with: pip install scikit-learn") from e


def available_features(df: pd.DataFrame, features: list[str]) -> list[str]:
    return [f for f in features if f in df.columns]


def get_feature_groups(cfg: dict) -> dict[str, list[str]]:
    fg = cfg.get("feature_groups", {})
    defaults = {
        "proxy_only": ["raw_proxy_wbgt_c"],
        "weather": ["raw_proxy_wbgt_c", "air_temperature_c", "relative_humidity_pct", "wind_speed_m_s", "shortwave_w_m2", "cloud_cover_pct", "precipitation_mm", "hour_sin", "hour_cos", "is_daytime_07_19", "is_peak_13_16"],
        "inertia": ["raw_proxy_wbgt_c", "air_temperature_c", "relative_humidity_pct", "wind_speed_m_s", "shortwave_w_m2", "shortwave_w_m2_lag1", "shortwave_w_m2_roll3_mean", "shortwave_day_cumsum", "air_temperature_c_lag1", "air_temperature_c_roll3_mean", "dtemp_dt", "hour_sin", "hour_cos"],
        "morphology": ["raw_proxy_wbgt_c", "air_temperature_c", "relative_humidity_pct", "wind_speed_m_s", "shortwave_w_m2", "shortwave_w_m2_roll3_mean", "hour_sin", "hour_cos", "svf", "svf_mean", "svf_umep_mean_open_v10", "shade_fraction", "shade_fraction_umep_10_16_open_v10", "building_density", "v10_building_density", "building_pixel_fraction_v10", "mean_building_height", "building_height_p90", "tree_canopy_fraction", "ndvi_mean", "road_fraction", "impervious_fraction"],
        "overhead": ["raw_proxy_wbgt_c", "air_temperature_c", "relative_humidity_pct", "wind_speed_m_s", "shortwave_w_m2", "shortwave_w_m2_roll3_mean", "hour_sin", "hour_cos", "svf", "svf_umep_mean_open_v10", "shade_fraction", "shade_fraction_umep_10_16_open_v10", "building_density", "v10_building_density", "overhead_fraction_total", "overhead_shade_proxy", "transport_deck_fraction", "pedestrian_shelter_fraction"],
    }
    for k, v in fg.items():
        defaults[k] = v
    return defaults


def make_cv_folds(df: pd.DataFrame, splits: pd.DataFrame | None, scheme: str) -> list[tuple[str, np.ndarray, np.ndarray]]:
    n = len(df)
    if splits is not None and "row_id" in splits.columns:
        s = splits.copy()
        s["row_id"] = pd.to_numeric(s["row_id"], errors="coerce").astype("Int64")
        s = s[s["row_id"].notna()]
        fold_col = "fold_loso" if scheme == "loso" else "fold_time_block"
        if fold_col in s.columns:
            folds = []
            for fold in sorted(s[fold_col].dropna().unique().tolist()):
                test_ids = set(s.loc[s[fold_col] == fold, "row_id"].astype(int).tolist())
                test_mask = df["row_id"].isin(test_ids).to_numpy()
                train_mask = ~test_mask
                if test_mask.sum() > 0 and train_mask.sum() > 0:
                    folds.append((str(fold), np.where(train_mask)[0], np.where(test_mask)[0]))
            if folds:
                return folds
    # fallback generate on the fly
    if scheme == "loso" and "station_id" in df.columns:
        folds = []
        for st in sorted(df["station_id"].dropna().astype(str).unique().tolist()):
            test_mask = df["station_id"].astype(str).eq(st).to_numpy()
            train_mask = ~test_mask
            if test_mask.sum() > 0 and train_mask.sum() > 0:
                folds.append((st, np.where(train_mask)[0], np.where(test_mask)[0]))
        return folds
    if scheme == "time_block":
        if "date" not in df.columns:
            df["date"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date.astype(str)
        days = sorted(df["date"].dropna().unique().tolist())
        chunks = np.array_split(np.arange(len(days)), min(5, len(days))) if days else []
        folds = []
        for i, idxs in enumerate(chunks):
            hold_days = {days[int(j)] for j in idxs}
            test_mask = df["date"].isin(hold_days).to_numpy()
            train_mask = ~test_mask
            if test_mask.sum() > 0 and train_mask.sum() > 0:
                folds.append((f"time_block_{i+1:02d}", np.where(train_mask)[0], np.where(test_mask)[0]))
        return folds
    raise ValueError(f"No folds for scheme={scheme}")


def fit_predict_model(model_name: str, train: pd.DataFrame, test: pd.DataFrame, y_col: str, proxy_col: str, features: list[str], alpha: float):
    y_train = pd.to_numeric(train[y_col], errors="coerce")
    if model_name == "M0_raw_proxy":
        return pd.to_numeric(test[proxy_col], errors="coerce")
    if model_name == "M1_global_bias":
        bias = (pd.to_numeric(train[y_col], errors="coerce") - pd.to_numeric(train[proxy_col], errors="coerce")).mean()
        return pd.to_numeric(test[proxy_col], errors="coerce") + bias
    if model_name == "M1b_period_bias":
        # v0.9 PeriodBiasModel: per-period (morning/peak/shoulder/night) constant bias.
        # Requires period_v09 column (added by v11_beta_build_features.py).
        if "period_v09" not in train.columns or "period_v09" not in test.columns:
            # Fallback: derive period from hour on the fly
            for fr in (train, test):
                if "period_v09" not in fr.columns:
                    if "hour" in fr.columns:
                        h = pd.to_numeric(fr["hour"], errors="coerce")
                    else:
                        h = pd.to_datetime(fr["timestamp"], errors="coerce").dt.hour + \
                            pd.to_datetime(fr["timestamp"], errors="coerce").dt.minute / 60.0
                    def _classify(hr):
                        if pd.isna(hr): return "night"
                        if 7 <= hr < 12: return "morning"
                        if 12 <= hr < 16: return "peak"
                        if 16 <= hr < 19: return "shoulder"
                        return "night"
                    fr["period_v09"] = h.apply(_classify)
        residual = pd.to_numeric(train[y_col], errors="coerce") - pd.to_numeric(train[proxy_col], errors="coerce")
        global_bias = float(residual.mean())
        bias_by_period = pd.DataFrame({"p": train["period_v09"].values, "r": residual.values}).groupby("p")["r"].mean().to_dict()
        bias = test["period_v09"].map(bias_by_period).fillna(global_bias)
        return pd.to_numeric(test[proxy_col], errors="coerce") + bias.values
    X_train = train[features]
    X_test = test[features]
    if model_name == "M2_linear_proxy":
        pipe = Pipeline([("impute", SimpleImputer(strategy="median")), ("model", LinearRegression())])
    else:
        pipe = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler()), ("model", Ridge(alpha=alpha))])
    pipe.fit(X_train, y_train)
    return pd.Series(pipe.predict(X_test), index=test.index)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v11/v11_beta_calibration_config.example.json")
    args = ap.parse_args()
    cfg = read_json(args.config)
    out_dir = ensure_dir(cfg["paths"].get("output_dir", "outputs/v11_beta_calibration"))
    pairs_path = Path(cfg["paths"].get("paired_dataset_csv", "data/calibration/v11/v11_station_weather_pairs.csv"))
    if not pairs_path.exists():
        raise SystemExit(f"[ERROR] paired dataset not found: {pairs_path}")
    df = pd.read_csv(pairs_path, low_memory=False)
    df = df.reset_index().rename(columns={"index": "row_id"})
    # Accept both legacy build_pairs ("timestamp") and v11 collector ("timestamp_sgt") outputs.
    if "timestamp" not in df.columns and "timestamp_sgt" in df.columns:
        df["timestamp"] = df["timestamp_sgt"]
    elif "timestamp" not in df.columns:
        raise SystemExit(
            f"[ERROR] paired dataset {pairs_path} has neither 'timestamp' nor 'timestamp_sgt' column."
        )
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    # Drop rows with unparseable timestamps (e.g. NaT from incomplete NEA records).
    n_before = len(df)
    df = df[df["timestamp"].notna()].copy()
    if len(df) < n_before:
        print(f"[WARN] dropped {n_before - len(df)} rows with NaT timestamp")
    df["row_id"] = df.index
    if "date" not in df.columns:
        df["date"] = df["timestamp"].dt.date.astype(str)

    # Compute diurnal features (collector pairs don't include these; v11-α legacy did).
    if "hour" not in df.columns:
        df["hour"] = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60.0
    if "hour_sin" not in df.columns:
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0)
    if "hour_cos" not in df.columns:
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    if "is_daytime_07_19" not in df.columns:
        df["is_daytime_07_19"] = ((df["hour"] >= 7) & (df["hour"] < 19)).astype(int)
    if "is_peak_13_16" not in df.columns:
        df["is_peak_13_16"] = ((df["hour"] >= 13) & (df["hour"] <= 16)).astype(int)

    # Alias common weather column names so configs written for either NEA or
    # Open-Meteo naming can find their features. Adds a copy under the alias
    # name only if the alias does not already exist.
    weather_aliases = [
        ("air_temperature_c", "temperature_2m"),
        ("relative_humidity_pct", "relative_humidity_2m"),
        ("wind_speed_m_s", "wind_speed_10m"),
        ("shortwave_w_m2", "shortwave_radiation"),
        ("cloud_cover_pct", "cloud_cover"),
        ("precipitation_mm", "precipitation"),
    ]
    for legacy, om in weather_aliases:
        if legacy not in df.columns and om in df.columns:
            df[legacy] = df[om]
        elif om not in df.columns and legacy in df.columns:
            df[om] = df[legacy]

    y_col = cfg["model"].get("target_col", "official_wbgt_c")
    proxy_col = cfg["model"].get("raw_proxy_col", "raw_proxy_wbgt_c")
    if proxy_col not in df.columns or df[proxy_col].isna().all():
        # Try collector's fallback proxies in order of sophistication.
        for alt in [
            "raw_proxy_wbgt_radiative_fallback_c",  # Stull + SW + wind correction
            "raw_proxy_wbgt_fallback_c",            # Stull-based only
            "wetbulb_stull_c",                      # raw wet-bulb
        ]:
            if alt in df.columns and df[alt].notna().any():
                df[proxy_col] = df[alt]
                print(f"[INFO] proxy `{proxy_col}` not in pairs; aliased from collector column `{alt}`.")
                break
        else:
            if {"air_temperature_c", "relative_humidity_pct"}.issubset(df.columns):
                df[proxy_col] = fallback_wbgt_proxy(df["air_temperature_c"], df["relative_humidity_pct"])
                print("[WARN] raw proxy missing; using simple temp/RH fallback formula.")
            else:
                raise SystemExit(f"[ERROR] raw proxy column `{proxy_col}` missing and fallback temp/RH unavailable.")
    if y_col not in df.columns:
        raise SystemExit(f"[ERROR] target column `{y_col}` missing")

    # 5.2 + β.1 post-mortem: data filtering for retrospective calibration ablation.
    # 
    # The collector's pair_used_for_calibration flag conflates valid-time alignment
    # with forecast issue freshness. For retrospective calibration, only valid-time
    # alignment is needed. Run v11_beta_build_features.py to derive the correct
    # `pair_used_for_retrospective_calibration` and `is_migrated_archive` flags.
    #
    # filter_mode options:
    #   "retrospective_calibration"  → only rows with valid weather forcing (RECOMMENDED for β)
    #   "all"                        → no filtering (β.1 smoke test behavior; not recommended)
    #   "collector_pair_used"        → use collector's conflated flag (for back-compat audit)
    #   "fresh_v11_only"             → exclude migrated v0.9/v10 archive rows
    #   "migrated_only"              → only migrated rows (for ablation)
    filter_mode = cfg.get("data_filters", {}).get("filter_mode", "retrospective_calibration")
    n_before_filter = len(df)
    if filter_mode == "retrospective_calibration":
        if "pair_used_for_retrospective_calibration" in df.columns:
            df = df[df["pair_used_for_retrospective_calibration"].astype(bool)].copy()
            print(f"[INFO] filter_mode=retrospective_calibration: {n_before_filter:,} → {len(df):,} rows")
        else:
            print(f"[WARN] filter_mode=retrospective_calibration but column not found; "
                  f"run v11_beta_build_features.py first. Falling back to 'all'.")
    elif filter_mode == "collector_pair_used":
        if "pair_used_for_calibration" in df.columns:
            df = df[df["pair_used_for_calibration"].astype(bool)].copy()
            print(f"[INFO] filter_mode=collector_pair_used: {n_before_filter:,} → {len(df):,} rows")
    elif filter_mode == "fresh_v11_only":
        if "is_migrated_archive" in df.columns:
            df = df[~df["is_migrated_archive"].astype(bool)].copy()
            print(f"[INFO] filter_mode=fresh_v11_only: {n_before_filter:,} → {len(df):,} rows")
    elif filter_mode == "migrated_only":
        if "is_migrated_archive" in df.columns:
            df = df[df["is_migrated_archive"].astype(bool)].copy()
            print(f"[INFO] filter_mode=migrated_only: {n_before_filter:,} → {len(df):,} rows")
    elif filter_mode == "all":
        print(f"[INFO] filter_mode=all: no filtering, using all {len(df):,} rows")
    else:
        print(f"[WARN] unknown filter_mode='{filter_mode}', using all rows")

    # 5.2: Optional station-level exclusion filter for sensitivity analysis.
    # Configure via:
    #   "data_filters": { "exclude_station_ids": ["S142"] }
    exclude_ids = cfg.get("data_filters", {}).get("exclude_station_ids", [])
    if exclude_ids:
        n_before = len(df)
        df = df[~df["station_id"].astype(str).isin([str(s) for s in exclude_ids])].copy()
        n_excluded = n_before - len(df)
        print(f"[INFO] excluded {n_excluded:,} rows from stations {exclude_ids} "
              f"({n_excluded*100.0/max(n_before,1):.1f}% of input)")

    # Optional output_dir_suffix (e.g. "all_stations" / "no_S142") for parallel runs.
    output_suffix = cfg.get("data_filters", {}).get("output_dir_suffix", "")
    if output_suffix:
        out_dir = ensure_dir(Path(out_dir) / output_suffix)
        print(f"[INFO] using output sub-directory: {out_dir}")

    # Keep rows with target and proxy.
    base_mask = df[y_col].notna() & df[proxy_col].notna()
    df = df[base_mask].reset_index(drop=True)
    df["row_id"] = df.index

    splits_path = Path(cfg["paths"].get("cv_splits_csv", "data/calibration/v11/v11_cv_splits.csv"))
    splits = pd.read_csv(splits_path) if splits_path.exists() else None
    feature_groups = get_feature_groups(cfg)
    alpha = float(cfg["model"].get("ridge_alpha", 1.0))
    schemes = cfg["cv"].get("schemes", ["loso", "time_block"])

    model_defs = [
        ("M0_raw_proxy", []),
        ("M1_global_bias", []),
        ("M1b_period_bias", []),  # v0.9 period-aware bias correction (game-changing baseline per v0.9-beta findings)
        ("M2_linear_proxy", available_features(df, [proxy_col])),
        ("M3_weather_ridge", available_features(df, feature_groups["weather"])),
        ("M4_inertia_ridge", available_features(df, feature_groups["inertia"])),
        ("M5_v10_morphology_ridge", available_features(df, feature_groups["morphology"])),
        ("M6_v10_overhead_ridge", available_features(df, feature_groups["overhead"])),
        # M7 added in v1.1-β.1 third audit response:
        # Friend correctly observed that M5/M6 collapse to an 8-feature weather subset
        # via SimpleImputer dropping all-NaN morphology columns (only S128 has morph data).
        # M5/M6's apparent F1 advantage on hourly_max is therefore a feature-selection
        # artifact, not a morphology signal. M7 makes this baseline explicit: it uses
        # exactly the 8 features that M5/M6 collapse to, with no morph features configured
        # at all. This lets dissertation framing recommend M7 as the operational classifier
        # without falsely attributing the F1 advantage to morphology.
        ("M7_compact_weather_ridge", available_features(df, feature_groups.get("compact_weather", []))),
    ]

    pred_rows = []
    metrics_rows = []
    feature_rows = []
    for scheme in schemes:
        folds = make_cv_folds(df.copy(), splits, scheme)
        for model_name, features in model_defs:
            if model_name not in ["M0_raw_proxy", "M1_global_bias", "M1b_period_bias"] and len(features) == 0:
                print(f"[WARN] skipping {model_name}: no available features")
                continue
            feature_rows.append({"model": model_name, "cv_scheme": scheme, "n_features": len(features), "features": ";".join(features)})
            oof = pd.Series(np.nan, index=df.index)
            fold_used = pd.Series("", index=df.index)
            for fold_name, train_idx, test_idx in folds:
                train = df.iloc[train_idx].copy()
                test = df.iloc[test_idx].copy()
                try:
                    pred = fit_predict_model(model_name, train, test, y_col, proxy_col, features, alpha)
                    oof.iloc[test_idx] = pred.values
                    fold_used.iloc[test_idx] = fold_name
                except Exception as e:
                    print(f"[WARN] model={model_name} scheme={scheme} fold={fold_name} failed: {e}")
            metr = metric_summary(df[y_col], oof)
            metr.update({"model": model_name, "cv_scheme": scheme, "n_folds": len(folds), "n_features": len(features)})
            # fixed-threshold event metrics for first-pass view
            for thr in cfg.get("thresholds", {}).get("event_thresholds_c", [31, 33]):
                em = event_metrics(df[y_col], oof, event_threshold=thr, score_threshold=thr)
                for k in ["precision", "recall", "f1", "tp", "fp", "fn"]:
                    metr[f"wbgt_ge_{thr}_{k}"] = em[k]
            metrics_rows.append(metr)
            pr = df[["row_id", "timestamp", "date", "station_id", y_col, proxy_col]].copy()
            pr["model"] = model_name
            pr["cv_scheme"] = scheme
            pr["fold"] = fold_used.values
            pr["prediction_wbgt_c"] = oof.values
            pr["residual_obs_minus_pred_c"] = pr[y_col] - pr["prediction_wbgt_c"]
            pred_rows.append(pr)

    preds = pd.concat(pred_rows, ignore_index=True, sort=False) if pred_rows else pd.DataFrame()
    metrics = pd.DataFrame(metrics_rows)
    feat_df = pd.DataFrame(feature_rows)
    preds_path = out_dir / "v11_beta_oof_predictions.csv"
    metrics_path = out_dir / "v11_beta_calibration_metrics.csv"
    features_path = out_dir / "v11_beta_model_feature_sets.csv"
    preds.to_csv(preds_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    feat_df.to_csv(features_path, index=False)

    report = [
        "# OpenHeat v1.1-beta calibration baseline report",
        "",
        f"Paired dataset: `{pairs_path}`",
        f"Rows used: **{len(df):,}**",
        f"Predictions: `{preds_path}`",
        f"Metrics: `{metrics_path}`",
        "",
        "## Metrics ranked by MAE",
        df_to_md_table(metrics.sort_values(["cv_scheme", "mae"]), max_rows=50),
        "",
        "## Feature sets",
        df_to_md_table(feat_df, max_rows=50),
        "",
        "## Interpretation notes",
        "- M0 is the raw proxy and should be treated as the baseline to beat.",
        "- M1 tests whether a simple global bias correction is already enough.",
        "- M3/M4 replay the v0.9 weather-regime / inertia idea on the expanded archive.",
        "- M5/M6 test whether v10 corrected morphology and overhead features help station-level WBGT residuals.",
        "- Prefer LOSO and blocked-time CV over random split.",
    ]
    report_path = out_dir / "v11_beta_calibration_baseline_report.md"
    write_md(report_path, "\n".join(report))
    print(f"[OK] predictions: {preds_path}")
    print(f"[OK] metrics: {metrics_path}")
    print(f"[OK] report: {report_path}")


if __name__ == "__main__":
    main()
