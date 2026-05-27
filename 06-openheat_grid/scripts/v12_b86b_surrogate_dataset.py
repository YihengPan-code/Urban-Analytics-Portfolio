"""Build the B8.6b F5 multi-forcing surrogate dataset.

Inputs:
    configs/v12/systemb_b86b_surrogate_promotion.yaml
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_pairwise_delta_by_cell_hour.csv
    outputs/v12_systemb_n150_sample_design/n150_sampling_feature_matrix.csv

Outputs:
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_surrogate_dataset.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_feature_schema.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_target_schema.csv

Saved metrics:
    Dataset row/cell/forcing-day/hour counts, strict F5 shape checks,
    target availability, feature inclusion/exclusion, leakage guards, and
    compact feature source coverage.

This script reads only compact CSV inputs. It does not run QGIS or SOLWEIG,
does not read raster files, does not open svfs.zip, does not create AOI-wide
prediction, and does not create WBGT, hazard_score, risk_score, B9, or
System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86b_surrogate_inventory import DEFAULT_CONFIG, read_config, rel_path, repo_path


@dataclass(frozen=True)
class DatasetResult:
    """Compact return record for the B8.6b dataset step."""

    status: str
    dataset_rows: int
    dataset_columns: int
    unique_cells: int
    forcing_days: int
    hours: int
    feature_count: int
    feature_source_status: str
    available_targets: list[str]


def read_csv(path: Path) -> pd.DataFrame:
    """Read a compact CSV while preserving cell IDs."""
    return pd.read_csv(path, dtype={"cell_id": "string"})


def empty_dataset_outputs(config: dict[str, Any], status: str) -> DatasetResult:
    """Write empty machine-readable outputs when label or feature inputs block the lane."""
    for key in ["surrogate_dataset", "feature_schema", "target_schema"]:
        pd.DataFrame().to_csv(repo_path(config["outputs"][key]), index=False)
    return DatasetResult(status, 0, 0, 0, 0, 0, 0, status, [])


def validate_labels(labels: pd.DataFrame, config: dict[str, Any]) -> None:
    """Validate strict F5 N150 multi-forcing label invariants."""
    required = {
        "cell_id",
        "forcing_day_id",
        "hour_sgt",
        "base_tmrt_p90_c",
        "overhead_tmrt_p90_c",
        "delta_tmrt_p90_c",
    }
    missing = sorted(required - set(labels.columns))
    if missing:
        raise ValueError(f"F5 pairwise labels are missing required columns: {missing}")
    expected = config["expected"]
    rows = len(labels)
    cells = labels["cell_id"].nunique()
    forcing_days = labels["forcing_day_id"].nunique()
    hours = set(pd.to_numeric(labels["hour_sgt"], errors="coerce").dropna().astype(int).unique())
    expected_hours = set(int(hour) for hour in expected["hours_sgt"])
    if rows != int(expected["f5_pairwise_rows"]):
        raise ValueError(f"F5 pairwise labels must have exactly {expected['f5_pairwise_rows']} rows; found {rows}.")
    if cells != int(expected["n150_cells"]):
        raise ValueError(f"F5 pairwise labels must have exactly {expected['n150_cells']} cells; found {cells}.")
    if forcing_days != int(expected["forcing_day_count"]):
        raise ValueError(f"F5 pairwise labels must have {expected['forcing_day_count']} forcing days; found {forcing_days}.")
    if hours != expected_hours:
        raise ValueError(f"F5 pairwise label hours must be {sorted(expected_hours)}; found {sorted(hours)}.")


def normalize_labels(labels: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Normalize F5 pairwise compact labels to B8.6b row IDs and target context."""
    validate_labels(labels, config)
    out = labels.copy()
    out["cell_id"] = out["cell_id"].astype(str)
    out["forcing_day_id"] = out["forcing_day_id"].astype(str)
    out["hour_sgt"] = pd.to_numeric(out["hour_sgt"], errors="coerce").astype(int)
    out["scenario_context"] = config["expected"]["scenario_context"]
    out["row_id"] = (
        out["cell_id"]
        + "|"
        + out["forcing_day_id"]
        + "|h"
        + out["hour_sgt"].astype(str)
        + "|"
        + out["scenario_context"]
    )
    out["b86b_label_source"] = "b85_f5_pairwise_delta_by_cell_hour"
    out["target_definition"] = "delta_tmrt_p90_c = overhead_as_canopy - base; SOLWEIG Tmrt label only."
    keep = [
        "row_id",
        "cell_id",
        "forcing_day_id",
        "hour_sgt",
        "scenario_context",
        "base_tmrt_p90_c",
        "overhead_tmrt_p90_c",
        "delta_tmrt_mean_c",
        "delta_tmrt_p50_c",
        "delta_tmrt_p90_c",
        "delta_tmrt_p95_c",
        "within_slice_rank",
        "rank_direction",
        "label_source",
        "legacy_single_forcing_comparison_source",
        "b86b_label_source",
        "target_definition",
        "notes",
    ]
    return out[[column for column in keep if column in out.columns]].copy()


def forbidden_predictor(column: str, config: dict[str, Any]) -> bool:
    """Return whether a column is blocked by the B8.6b feature contract."""
    lower = column.lower()
    if column in set(config["feature_contract"]["forbidden_predictor_columns"]):
        return True
    return any(str(token).lower() in lower for token in config["feature_contract"]["forbidden_predictor_tokens"])


def selected_feature_frame(config: dict[str, Any], label_cells: set[str]) -> tuple[pd.DataFrame, list[str], str]:
    """Load compact N150 features and return selected non-leaky predictor columns."""
    source_key = config["feature_contract"]["selected_source"]
    feature_path = repo_path(config["inputs"]["feature_candidates"][source_key])
    if not feature_path.exists():
        raise FileNotFoundError(str(feature_path))
    features = read_csv(feature_path)
    if "cell_id" not in features.columns:
        raise ValueError("Feature table has no cell_id column.")
    features["cell_id"] = features["cell_id"].astype(str)
    source_cells = set(features["cell_id"].dropna().astype(str))
    if len(label_cells & source_cells) != int(config["expected"]["n150_cells"]):
        raise ValueError("Feature table does not cover all 150 F5 label cells.")

    requested = list(config["feature_contract"]["predictor_columns"])
    selected = [
        column
        for column in requested
        if column != "hour_sgt" and column in features.columns and not forbidden_predictor(column, config)
    ]
    metadata = [
        column
        for column in config["feature_contract"]["metadata_columns"]
        if column not in {"cell_id", "forcing_day_id", "hour_sgt"} and column in features.columns
    ]
    compact = features[["cell_id", *metadata, *selected]].drop_duplicates("cell_id")
    return compact, selected, rel_path(feature_path)


def build_dataset(config: dict[str, Any]) -> tuple[pd.DataFrame, list[str], str]:
    """Build the F5 label-feature dataset for surrogate promotion review."""
    labels_path = repo_path(config["inputs"]["label_candidates"]["f5_pairwise_delta"])
    if not labels_path.exists():
        raise FileNotFoundError(str(labels_path))
    labels = normalize_labels(read_csv(labels_path), config)
    label_cells = set(labels["cell_id"].astype(str).unique())
    feature_frame, selected_features, feature_source = selected_feature_frame(config, label_cells)
    dataset = labels.merge(feature_frame, on="cell_id", how="left", validate="many_to_one")
    dataset["feature_source"] = feature_source
    dataset["forcing_day_predictor_status"] = "excluded_from_all_primary_models"
    dataset["cell_id_predictor_status"] = "group_metadata_only"
    dataset = dataset.sort_values(["cell_id", "forcing_day_id", "hour_sgt"]).reset_index(drop=True)
    return dataset, [*selected_features, "hour_sgt"], feature_source


def target_schema(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build B8.6b target schema with role and claim boundaries."""
    targets = [config["targets"]["primary"], *config["targets"]["sensitivity"]]
    for target in config["targets"].get("optional_non_leaky", []):
        if target in dataset.columns:
            targets.append(target)
    definitions = {
        "delta_tmrt_p90_c": "Primary: overhead_as_canopy minus base Tmrt p90 from F5 pairwise compact labels.",
        "delta_tmrt_mean_c": "Sensitivity: overhead_as_canopy minus base Tmrt mean from F5 pairwise compact labels.",
        "delta_tmrt_p50_c": "Sensitivity: overhead_as_canopy minus base Tmrt p50 from F5 pairwise compact labels.",
        "delta_tmrt_p95_c": "Sensitivity: overhead_as_canopy minus base Tmrt p95 from F5 pairwise compact labels.",
        "base_tmrt_p90_c": "Secondary absolute base-scenario Tmrt p90 from F5 labels.",
        "overhead_tmrt_p90_c": "Secondary absolute overhead_as_canopy Tmrt p90 from F5 labels.",
        "m_rad_pct01": "Optional non-leaky compact modifier target only if present in F5-compatible labels.",
    }
    rows: list[dict[str, Any]] = []
    for target in targets:
        available = target in dataset.columns and dataset[target].notna().any()
        rows.append(
            {
                "target_name": target,
                "role": "primary" if target == config["targets"]["primary"] else "secondary_or_sensitivity",
                "available": bool(available),
                "non_null_count": int(dataset[target].notna().sum()) if target in dataset.columns else 0,
                "unit": "deg C Tmrt" if "tmrt" in target else "unknown",
                "source_definition": definitions.get(target, "Compact B8.6b label target."),
                "target_card_use": (
                    "primary promotion card variable"
                    if target == config["targets"]["primary"]
                    else "target sensitivity / companion context"
                ),
                "allowed_interpretation": "SOLWEIG-derived Tmrt surrogate target for local radiative ranking review.",
                "forbidden_interpretation": "Not local WBGT, not risk, not observed truth, not causal feature importance, not B9.",
            }
        )
    return pd.DataFrame(rows)


def feature_schema(dataset: pd.DataFrame, selected_features: list[str], config: dict[str, Any]) -> pd.DataFrame:
    """Build B8.6b feature schema with leakage exclusions."""
    selected = set(selected_features)
    targets = {config["targets"]["primary"], *config["targets"]["sensitivity"], *config["targets"].get("optional_non_leaky", [])}
    coordinate_names = {name for pair in config["feature_contract"]["coordinate_pairs"] for name in pair}
    rows: list[dict[str, Any]] = []
    for column in dataset.columns:
        if column in selected:
            role = "predictor"
            include = True
            notes = "Compact non-target predictor; hour_sgt is included only in hour-aware models and tested by hour holdout."
            leakage = "PASS"
        elif column in {"cell_id", "row_id"}:
            role = "id_or_group_metadata"
            include = False
            notes = "Group identifier only; never a numeric predictor."
            leakage = "PASS_EXCLUDED"
        elif column == "forcing_day_id":
            role = "forcing_day_metadata"
            include = False
            notes = "Allowed for diagnostics only; excluded from primary evidence models including forcing-day holdout."
            leakage = "PASS_EXCLUDED"
        elif column in targets or forbidden_predictor(column, config) or column in {"within_slice_rank", "rank_direction"}:
            role = "target_or_forbidden_leakage"
            include = False
            notes = "Target-derived, rank, or forbidden claim-boundary column; excluded from predictors."
            leakage = "PASS_EXCLUDED"
        elif column in coordinate_names:
            role = "spatial_split_metadata"
            include = False
            notes = "Used for spatial holdout construction only, not a predictor."
            leakage = "PASS_EXCLUDED"
        else:
            role = "metadata"
            include = False
            notes = "Traceability or split metadata only."
            leakage = "PASS_EXCLUDED"
        non_null = int(dataset[column].notna().sum())
        rows.append(
            {
                "column_name": column,
                "role": role,
                "include_in_model": include,
                "dtype": str(dataset[column].dtype),
                "non_null_count": non_null,
                "missing_fraction": float(1 - non_null / len(dataset)) if len(dataset) else np.nan,
                "leakage_guard_status": leakage,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> DatasetResult:
    """Build and write the B8.6b compact surrogate dataset and schemas."""
    config = read_config(config_path)
    repo_path(config["outputs"]["out_dir"]).mkdir(parents=True, exist_ok=True)
    try:
        dataset, selected_features, feature_source = build_dataset(config)
    except FileNotFoundError as exc:
        text = str(exc)
        status = "B86B_BLOCKED_LABEL_INPUT" if "pairwise" in text or "f5" in text.lower() else "B86B_BLOCKED_FEATURE_INPUT"
        return empty_dataset_outputs(config, status)
    except ValueError as exc:
        status = "B86B_BLOCKED_LABEL_INPUT" if "label" in str(exc).lower() else "B86B_BLOCKED_FEATURE_INPUT"
        return empty_dataset_outputs(config, status)

    features = feature_schema(dataset, selected_features, config)
    targets = target_schema(dataset, config)
    dataset.to_csv(repo_path(config["outputs"]["surrogate_dataset"]), index=False)
    features.to_csv(repo_path(config["outputs"]["feature_schema"]), index=False)
    targets.to_csv(repo_path(config["outputs"]["target_schema"]), index=False)
    available_targets = targets.loc[targets["available"], "target_name"].astype(str).tolist()
    status = "B86B_DATASET_READY" if config["targets"]["primary"] in available_targets else "B86B_BLOCKED_LABEL_INPUT"
    return DatasetResult(
        status=status,
        dataset_rows=int(len(dataset)),
        dataset_columns=int(dataset.shape[1]),
        unique_cells=int(dataset["cell_id"].nunique()),
        forcing_days=int(dataset["forcing_day_id"].nunique()),
        hours=int(dataset["hour_sgt"].nunique()),
        feature_count=int(features["include_in_model"].fillna(False).sum()),
        feature_source_status=f"PASS:{feature_source}",
        available_targets=available_targets,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build B8.6b F5 multi-forcing surrogate dataset.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6b YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
