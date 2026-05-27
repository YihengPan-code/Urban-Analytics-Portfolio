"""Inventory B8.6b surrogate-promotion compact inputs.

Inputs:
    configs/v12/systemb_b86b_surrogate_promotion.yaml plus the compact CSV
    and Markdown paths declared in the config.

Outputs:
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_input_inventory.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_label_source_inventory.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_feature_source_inventory.csv

Saved metrics:
    Existence, suffix, file size, row count, column count, required label
    columns, exact F5 row/cell/forcing-day/hour counts, feature cell coverage,
    compact feature availability, and explicit label/feature blocker status.

This script reads only compact CSV/Markdown/YAML inputs. It does not run QGIS
or SOLWEIG, does not read raster files, does not open or copy svfs.zip, does
not create AOI-wide prediction, and does not create WBGT, hazard_score,
risk_score, B9, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b86b_surrogate_promotion.yaml"
FORBIDDEN_SUFFIXES = {".tif", ".tiff"}


@dataclass(frozen=True)
class InventoryResult:
    """Compact return record for the B8.6b inventory step."""

    status: str
    f5_label_rows: int
    f5_unique_cells: int
    f5_forcing_days: int
    f5_hours: int
    feature_rows: int
    feature_unique_cells: int
    selected_label_source: str
    selected_feature_source: str
    label_status: str
    feature_status: str


def repo_path(value: str | Path) -> Path:
    """Resolve a config path relative to the OpenHeat project directory."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def rel_path(path: Path) -> str:
    """Return a stable project-relative path string when possible."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_config(path: Path) -> dict[str, Any]:
    """Read the explicit B8.6b YAML config."""
    return yaml.safe_load(repo_path(path).read_text(encoding="utf-8"))


def assert_not_forbidden(path: Path) -> None:
    """Fail fast if a configured path points at a raster or svfs.zip."""
    suffixes = {suffix.lower() for suffix in path.suffixes}
    if suffixes & FORBIDDEN_SUFFIXES or path.name.lower() == "svfs.zip":
        raise ValueError(f"Forbidden file path configured for B8.6b: {path}")


def table_columns(path: Path) -> tuple[list[str], str]:
    """Read compact table headers without touching forbidden file types."""
    assert_not_forbidden(path)
    if not path.exists():
        return [], "MISSING"
    try:
        if ".csv" in [suffix.lower() for suffix in path.suffixes]:
            return pd.read_csv(path, nrows=0).columns.astype(str).tolist(), "READABLE_CSV_HEADER"
        if path.suffix.lower() in {".md", ".yaml", ".yml", ".json"}:
            return [], "TEXT_OR_CONFIG"
    except Exception as exc:  # pragma: no cover - inventories should record failures.
        return [], f"HEADER_ERROR:{type(exc).__name__}"
    return [], "UNSUPPORTED_COMPACT_SUFFIX"


def table_shape(path: Path) -> tuple[int, int, str]:
    """Read compact CSV shape for configured candidates."""
    assert_not_forbidden(path)
    if not path.exists():
        return 0, 0, "MISSING"
    if ".csv" not in [suffix.lower() for suffix in path.suffixes]:
        columns, status = table_columns(path)
        return 0, len(columns), status
    try:
        frame = pd.read_csv(path, dtype={"cell_id": "string"})
        return int(len(frame)), int(frame.shape[1]), "READABLE_CSV"
    except Exception as exc:  # pragma: no cover - inventories should record failures.
        return 0, 0, f"TABLE_ERROR:{type(exc).__name__}"


def input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Inventory every explicit compact input path in the B8.6b config."""
    rows: list[dict[str, Any]] = []
    groups = ["label_candidates", "feature_candidates", "f4_context", "b86_context"]
    for group in groups:
        for name, value in config["inputs"].get(group, {}).items():
            path = repo_path(value)
            assert_not_forbidden(path)
            columns, read_status = table_columns(path)
            row_count, column_count, table_status = table_shape(path)
            rows.append(
                {
                    "input_group": group,
                    "candidate_name": name,
                    "path": rel_path(path),
                    "exists": path.exists(),
                    "suffix": "".join(path.suffixes).lower(),
                    "size_bytes": path.stat().st_size if path.exists() else 0,
                    "read_status": read_status,
                    "table_status": table_status,
                    "row_count": row_count,
                    "column_count": column_count,
                    "columns": "|".join(columns),
                    "has_cell_id": "cell_id" in {column.lower() for column in columns},
                    "has_forcing_day_id": "forcing_day_id" in {column.lower() for column in columns},
                    "has_hour_sgt": "hour_sgt" in {column.lower() for column in columns},
                    "has_primary_target": config["targets"]["primary"] in columns,
                    "compact_only_status": "PASS",
                }
            )
    return pd.DataFrame(rows)


def label_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Inventory configured label sources and exact F5 compact-label readiness."""
    rows: list[dict[str, Any]] = []
    required = {"cell_id", "forcing_day_id", "hour_sgt", config["targets"]["primary"]}
    expected_hours = set(int(hour) for hour in config["expected"]["hours_sgt"])
    for name, value in config["inputs"]["label_candidates"].items():
        path = repo_path(value)
        columns, read_status = table_columns(path)
        lower_columns = {column.lower() for column in columns}
        row_count, column_count, table_status = table_shape(path)
        unique_cells = 0
        forcing_days = 0
        hours = 0
        hours_match = False
        exact_f5_shape = False
        if path.exists() and ".csv" in [suffix.lower() for suffix in path.suffixes]:
            try:
                frame = pd.read_csv(path, dtype={"cell_id": "string"})
                unique_cells = int(frame["cell_id"].nunique()) if "cell_id" in frame.columns else 0
                forcing_days = int(frame["forcing_day_id"].nunique()) if "forcing_day_id" in frame.columns else 0
                if "hour_sgt" in frame.columns:
                    observed_hours = set(pd.to_numeric(frame["hour_sgt"], errors="coerce").dropna().astype(int).unique())
                    hours = len(observed_hours)
                    hours_match = observed_hours == expected_hours
                exact_f5_shape = (
                    row_count == int(config["expected"]["f5_pairwise_rows"])
                    and unique_cells == int(config["expected"]["n150_cells"])
                    and forcing_days == int(config["expected"]["forcing_day_count"])
                    and hours_match
                )
            except Exception:
                pass
        rows.append(
            {
                "candidate_name": name,
                "path": rel_path(path),
                "exists": path.exists(),
                "read_status": read_status,
                "table_status": table_status,
                "row_count": row_count,
                "column_count": column_count,
                "unique_cells": unique_cells,
                "forcing_day_count": forcing_days,
                "hour_count": hours,
                "has_required_columns": required.issubset(lower_columns),
                "has_primary_target": config["targets"]["primary"] in lower_columns,
                "has_delta_tmrt_mean_c": "delta_tmrt_mean_c" in lower_columns,
                "has_delta_tmrt_p50_c": "delta_tmrt_p50_c" in lower_columns,
                "has_delta_tmrt_p95_c": "delta_tmrt_p95_c" in lower_columns,
                "has_base_tmrt_p90_c": "base_tmrt_p90_c" in lower_columns,
                "has_overhead_tmrt_p90_c": "overhead_tmrt_p90_c" in lower_columns,
                "exact_f5_pairwise_shape": exact_f5_shape,
                "usable_for_b86b_primary": name == "f5_pairwise_delta" and exact_f5_shape and required.issubset(lower_columns),
                "legacy_single_forcing_metadata_only": name.startswith("legacy_"),
                "notes": "F5 multi-forcing compact pairwise labels are the only training target source for B8.6b.",
            }
        )
    return pd.DataFrame(rows)


def feature_inventory(config: dict[str, Any], label_cells: set[str]) -> pd.DataFrame:
    """Inventory feature sources and compact N150 cell coverage."""
    rows: list[dict[str, Any]] = []
    predictor_set = set(config["feature_contract"]["predictor_columns"]) - {"hour_sgt"}
    forbidden_tokens = [str(token).lower() for token in config["feature_contract"]["forbidden_predictor_tokens"]]
    for name, value in config["inputs"]["feature_candidates"].items():
        path = repo_path(value)
        columns, read_status = table_columns(path)
        lower_columns = {column.lower(): column for column in columns}
        row_count, column_count, table_status = table_shape(path)
        unique_cells = 0
        label_cell_coverage = 0
        available_predictors: list[str] = []
        forbidden_predictor_hits: list[str] = []
        if path.exists() and ".csv" in [suffix.lower() for suffix in path.suffixes]:
            try:
                frame = pd.read_csv(path, dtype={"cell_id": "string"})
                unique_cells = int(frame["cell_id"].nunique()) if "cell_id" in frame.columns else 0
                source_cells = set(frame["cell_id"].dropna().astype(str)) if "cell_id" in frame.columns else set()
                label_cell_coverage = len(label_cells & source_cells)
            except Exception:
                pass
        for predictor in predictor_set:
            if predictor.lower() in lower_columns:
                available_predictors.append(predictor)
                if any(token in predictor.lower() for token in forbidden_tokens):
                    forbidden_predictor_hits.append(predictor)
        rows.append(
            {
                "candidate_name": name,
                "path": rel_path(path),
                "exists": path.exists(),
                "read_status": read_status,
                "table_status": table_status,
                "row_count": row_count,
                "column_count": column_count,
                "unique_cells": unique_cells,
                "label_cell_coverage": label_cell_coverage,
                "available_predictor_count": len(available_predictors),
                "available_predictors": "|".join(sorted(available_predictors)),
                "forbidden_predictor_hits_in_selected_contract": "|".join(forbidden_predictor_hits),
                "has_typology_label": "typology_label" in lower_columns,
                "has_centroid_x_y": "centroid_x" in lower_columns and "centroid_y" in lower_columns,
                "usable_for_b86b_features": (
                    name == config["feature_contract"]["selected_source"]
                    and path.exists()
                    and label_cell_coverage == int(config["expected"]["n150_cells"])
                    and len(available_predictors) >= 5
                    and not forbidden_predictor_hits
                ),
                "notes": "Only compact non-target physical/geometric predictors are allowed; cell_id remains metadata.",
            }
        )
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> InventoryResult:
    """Run B8.6b compact input inventory and write CSV outputs."""
    config = read_config(config_path)
    out_dir = repo_path(config["outputs"]["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    labels_path = repo_path(config["inputs"]["label_candidates"]["f5_pairwise_delta"])
    label_cells: set[str] = set()
    if labels_path.exists():
        label_frame = pd.read_csv(labels_path, dtype={"cell_id": "string"})
        if "cell_id" in label_frame.columns:
            label_cells = set(label_frame["cell_id"].dropna().astype(str))

    inputs = input_inventory(config)
    labels = label_inventory(config)
    features = feature_inventory(config, label_cells)

    inputs.to_csv(repo_path(config["outputs"]["input_inventory"]), index=False)
    labels.to_csv(repo_path(config["outputs"]["label_source_inventory"]), index=False)
    features.to_csv(repo_path(config["outputs"]["feature_source_inventory"]), index=False)

    selected_label = labels.loc[labels["usable_for_b86b_primary"]]
    selected_feature = features.loc[features["usable_for_b86b_features"]]
    label_status = "PASS" if not selected_label.empty else "BLOCKED_LABEL_INPUT"
    feature_status = "PASS" if not selected_feature.empty else "BLOCKED_FEATURE_INPUT"
    if label_status != "PASS":
        status = "B86B_BLOCKED_LABEL_INPUT"
    elif feature_status != "PASS":
        status = "B86B_BLOCKED_FEATURE_INPUT"
    else:
        status = "B86B_INPUTS_READY"

    f5_row = labels.loc[labels["candidate_name"] == "f5_pairwise_delta"].iloc[0]
    feature_row = features.loc[features["candidate_name"] == config["feature_contract"]["selected_source"]].iloc[0]
    return InventoryResult(
        status=status,
        f5_label_rows=int(f5_row["row_count"]),
        f5_unique_cells=int(f5_row["unique_cells"]),
        f5_forcing_days=int(f5_row["forcing_day_count"]),
        f5_hours=int(f5_row["hour_count"]),
        feature_rows=int(feature_row["row_count"]),
        feature_unique_cells=int(feature_row["unique_cells"]),
        selected_label_source=str(selected_label.iloc[0]["path"]) if not selected_label.empty else "",
        selected_feature_source=str(selected_feature.iloc[0]["path"]) if not selected_feature.empty else "",
        label_status=label_status,
        feature_status=feature_status,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Inventory compact B8.6b surrogate-promotion inputs.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6b YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
