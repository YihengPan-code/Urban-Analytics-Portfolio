#!/usr/bin/env python
"""Build frozen Level 1 feature matrices from the model registry.

Inputs:
    - configs/v11/level1_model_registry.yaml
    - Dataset CSVs declared in the registry.

Outputs:
    - outputs/v11_level1/reproduction/feature_matrix_<dataset_label>.csv
    - outputs/v11_level1/reproduction/feature_matrix_manifest.csv

Saved metrics:
    - Input path, target, filter mode, row count, station count, timestamp range,
      and available feature counts per dataset.

This is a data-preparation script only; it does not train models.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_registry(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_input(spec: dict) -> Path | None:
    primary = ROOT / spec["input_csv"]
    if primary.exists():
        return primary
    fallback = spec.get("fallback_input_csv")
    if fallback and (ROOT / fallback).exists():
        return ROOT / fallback
    return None


def boolish(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def prepare_dataset(df: pd.DataFrame, spec: dict) -> pd.DataFrame:
    out = df.copy()
    if "timestamp" not in out.columns and "timestamp_sgt" in out.columns:
        out["timestamp"] = out["timestamp_sgt"]
    if "timestamp_sgt" not in out.columns and "hour_bucket" in out.columns:
        out["timestamp_sgt"] = out["hour_bucket"]
    if "timestamp" not in out.columns and "hour_bucket" in out.columns:
        out["timestamp"] = out["hour_bucket"]
    if "timestamp" not in out.columns:
        raise SystemExit(f"[ERROR] no timestamp-like column for {spec['dataset_label']}")
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    out = out[out["timestamp"].notna()].copy()
    if "date" not in out.columns:
        out["date"] = out["timestamp"].dt.date.astype(str)
    if "hour" not in out.columns:
        out["hour"] = out["timestamp"].dt.hour + out["timestamp"].dt.minute / 60.0
    for legacy, om in [
        ("air_temperature_c", "temperature_2m"),
        ("relative_humidity_pct", "relative_humidity_2m"),
        ("wind_speed_m_s", "wind_speed_10m"),
        ("shortwave_w_m2", "shortwave_radiation"),
        ("cloud_cover_pct", "cloud_cover"),
        ("precipitation_mm", "precipitation"),
    ]:
        if legacy not in out.columns and om in out.columns:
            out[legacy] = out[om]
        if om not in out.columns and legacy in out.columns:
            out[om] = out[legacy]
    filter_mode = spec.get("filter_mode", "retrospective_calibration")
    if filter_mode == "retrospective_calibration" and "pair_used_for_retrospective_calibration" in out.columns:
        out = out[boolish(out["pair_used_for_retrospective_calibration"])].copy()
    elif filter_mode == "collector_pair_used" and "pair_used_for_calibration" in out.columns:
        out = out[boolish(out["pair_used_for_calibration"])].copy()
    target = spec["target_col"]
    proxy = spec["raw_proxy_col"]
    if target not in out.columns:
        raise SystemExit(f"[ERROR] target column {target} missing for {spec['dataset_label']}")
    if proxy not in out.columns:
        raise SystemExit(f"[ERROR] proxy column {proxy} missing for {spec['dataset_label']}")
    out = out[out[target].notna() & out[proxy].notna()].copy()
    out = out.reset_index(drop=True)
    out.insert(0, "row_id", np.arange(len(out), dtype=int))
    return out


def feature_count(df: pd.DataFrame, registry: dict) -> int:
    features: set[str] = set()
    for model in registry["models"]:
        group = registry["feature_groups"].get(model["feature_group"], [])
        features.update(c for c in group if c in df.columns)
    return len(features)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Level 1 feature matrices from registry datasets.")
    parser.add_argument("--registry", default="configs/v11/level1_model_registry.yaml")
    args = parser.parse_args()
    registry_path = ROOT / args.registry
    registry = load_registry(registry_path)
    out_dir = ROOT / registry.get("output_dir", "outputs/v11_level1/reproduction")
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, object]] = []
    for spec in registry["datasets"]:
        input_path = resolve_input(spec)
        if input_path is None:
            manifest_rows.append({
                "dataset_label": spec["dataset_label"],
                "status": "missing_input",
                "input_csv": spec["input_csv"],
            })
            continue
        df = pd.read_csv(input_path, low_memory=False)
        matrix = prepare_dataset(df, spec)
        matrix_path = out_dir / f"feature_matrix_{spec['dataset_label']}.csv"
        matrix.to_csv(matrix_path, index=False)
        manifest_rows.append({
            "dataset_label": spec["dataset_label"],
            "status": "built",
            "input_csv": str(input_path.relative_to(ROOT)).replace("\\", "/"),
            "feature_matrix_csv": str(matrix_path.relative_to(ROOT)).replace("\\", "/"),
            "target_col": spec["target_col"],
            "raw_proxy_col": spec["raw_proxy_col"],
            "filter_mode": spec.get("filter_mode", ""),
            "row_count": len(matrix),
            "station_count": matrix["station_id"].nunique(dropna=True) if "station_id" in matrix.columns else np.nan,
            "timestamp_min": str(matrix["timestamp"].min()) if "timestamp" in matrix.columns else "",
            "timestamp_max": str(matrix["timestamp"].max()) if "timestamp" in matrix.columns else "",
            "available_registered_feature_count": feature_count(matrix, registry),
        })
        print(f"[OK] built {matrix_path} ({len(matrix):,} rows)")

    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(out_dir / "feature_matrix_manifest.csv", index=False)
    print(f"[OK] wrote {out_dir / 'feature_matrix_manifest.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
