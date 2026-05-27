"""Build the B8.6 System B surrogate dataset and validation splits.

Inputs:
    configs/v12/systemb_b86_surrogate_protocol.yaml
    outputs/v12_solweig_n150_execution/n150_base_vs_overhead_delta_merged.csv
    outputs/v12_systemb_n150_sample_design/n150_sampling_feature_matrix.csv
    optional compact B7/B8 label tables and B8.5-F4 N24 stress-validation
    CSV/Markdown outputs declared in the config.

Outputs:
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_surrogate_dataset.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_feature_schema.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_target_schema.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_validation_splits.csv
    outputs/v12_surrogate/b8_6_surrogate_protocol/b86_n24_stress_validation_bridge.csv

Saved metrics:
    Dataset shape, unique cell/hour counts, target availability, feature
    availability, leakage exclusions, validation split row/cell counts,
    unavailable future holdouts, and N24 stress-validation bridge membership.

This script reads only compact tables. It does not run QGIS or SOLWEIG, does
not read raster files, does not copy svfs.zip, does not create an N150
execution runner or SOLWEIG manifest, and does not create local WBGT,
hazard_score, risk_score, AOI-wide prediction, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86_surrogate_inventory import DEFAULT_CONFIG, read_config, rel_path, repo_path


COMMON_SPLIT_COLUMNS = [
    "split_family",
    "split_name",
    "fold_id",
    "role",
    "row_id",
    "cell_id",
    "hour_sgt",
    "scenario_context",
    "split_status",
    "reason",
    "notes",
]


@dataclass(frozen=True)
class DatasetResult:
    """Compact return record for the B8.6 dataset step."""

    status: str
    dataset_rows: int
    dataset_columns: int
    unique_cells: int
    available_targets: list[str]
    baseline_feature_count: int
    main_split_families_available: list[str]
    future_required_splits: list[str]
    n24_bridge_rows: int


def read_csv(path: Path) -> pd.DataFrame:
    """Read a compact CSV while preserving cell IDs."""
    return pd.read_csv(path, dtype={"cell_id": "string"})


def empty_outputs(config: dict[str, Any], status: str) -> DatasetResult:
    """Write empty machine-readable outputs for a blocked dataset step."""
    pd.DataFrame().to_csv(repo_path(config["outputs"]["surrogate_dataset"]), index=False)
    pd.DataFrame().to_csv(repo_path(config["outputs"]["feature_schema"]), index=False)
    pd.DataFrame().to_csv(repo_path(config["outputs"]["target_schema"]), index=False)
    pd.DataFrame(columns=COMMON_SPLIT_COLUMNS).to_csv(repo_path(config["outputs"]["validation_splits"]), index=False)
    pd.DataFrame().to_csv(repo_path(config["outputs"]["n24_stress_validation_bridge"]), index=False)
    return DatasetResult(status, 0, 0, 0, [], 0, [], config["validation"]["future_required_split_families"], 0)


def normalize_pairwise_labels(labels: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Normalize N150 pairwise overhead-minus-base labels to B8.6 target rows."""
    required = {"cell_id", "delta_tmrt_p90_c"}
    if "hour_sgt" not in labels.columns and "hour" in labels.columns:
        labels = labels.copy()
        labels["hour_sgt"] = labels["hour"]
    required.add("hour_sgt")
    missing = sorted(required - set(labels.columns))
    if missing:
        raise ValueError(f"Pairwise label source is missing required columns: {missing}")
    out = labels.copy()
    out["cell_id"] = out["cell_id"].astype(str)
    out["hour_sgt"] = pd.to_numeric(out["hour_sgt"], errors="coerce").astype("Int64")
    out["scenario_context"] = config["expected"]["scenario_context"]
    out["row_id"] = out["cell_id"] + "|" + out["scenario_context"].astype(str) + "|h" + out["hour_sgt"].astype(str)
    if "tmrt_p90_c" not in out.columns and "tmrt_p90_c_base" in out.columns:
        out["tmrt_p90_c"] = out["tmrt_p90_c_base"]
    out["label_source"] = "n150_base_vs_overhead_delta_merged"
    out["target_definition"] = "delta_tmrt_p90_c = tmrt_p90_c_overhead_as_canopy - tmrt_p90_c_base"
    keep = [
        "row_id",
        "cell_id",
        "hour_sgt",
        "scenario_context",
        "source",
        "label_source",
        "target_definition",
        "tmrt_p90_c",
        "tmrt_p90_c_base",
        "tmrt_p90_c_overhead_as_canopy",
        "delta_tmrt_mean_c",
        "delta_tmrt_p75_c",
        "delta_tmrt_p90_c",
        "delta_tmrt_p95_c",
        "delta_tmrt_max_c",
        "delta_pct_pixels_ge_40",
        "delta_pct_pixels_ge_45",
        "delta_pct_pixels_ge_50",
        "delta_pct_pixels_ge_55",
    ]
    return out[[column for column in keep if column in out.columns]].copy()


def attach_optional_m_rad(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Attach the existing overhead-scenario reference percentile label if present."""
    path = repo_path(config["inputs"]["label_candidates"]["modifier_targets"])
    if not path.exists():
        return dataset
    columns = ["cell_id", "hour_sgt", "scenario", "m_rad_pct01"]
    modifier = pd.read_csv(path, usecols=lambda column: column in columns, dtype={"cell_id": "string"})
    if "hour_sgt" not in modifier.columns or "m_rad_pct01" not in modifier.columns:
        return dataset
    modifier = modifier.loc[modifier.get("scenario", "") == "overhead_as_canopy"].copy()
    modifier = modifier[["cell_id", "hour_sgt", "m_rad_pct01"]].drop_duplicates(["cell_id", "hour_sgt"])
    out = dataset.merge(modifier, on=["cell_id", "hour_sgt"], how="left", validate="many_to_one")
    return out


def load_feature_source(config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    """Load the preferred compact feature source."""
    candidates = config["inputs"]["feature_candidates"]
    for name in config["feature_contract"]["source_preference"]:
        path = repo_path(candidates[name])
        if path.exists():
            frame = read_csv(path)
            return frame, rel_path(path)
    raise FileNotFoundError("No configured compact feature source exists.")


def leakage_like(column: str, config: dict[str, Any]) -> bool:
    """Return whether a feature name is blocked by the leakage contract."""
    lower = column.lower()
    return any(str(token).lower() in lower for token in config["feature_contract"]["blocked_feature_name_tokens"])


def build_dataset(config: dict[str, Any]) -> pd.DataFrame:
    """Build the compact B8.6 label-feature dataset."""
    label_path = repo_path(config["inputs"]["label_candidates"]["pairwise_delta"])
    feature_frame, feature_source = load_feature_source(config)
    labels = normalize_pairwise_labels(read_csv(label_path), config)
    labels = attach_optional_m_rad(labels, config)

    feature_frame["cell_id"] = feature_frame["cell_id"].astype(str)
    selected_feature_columns = [
        column
        for column in config["feature_contract"]["baseline_feature_columns"]
        if column in feature_frame.columns and not leakage_like(column, config)
    ]
    metadata_columns = [
        column
        for column in config["feature_contract"]["metadata_columns"]
        if column in feature_frame.columns and column != "cell_id"
    ]
    features = feature_frame[["cell_id", *metadata_columns, *selected_feature_columns]].drop_duplicates("cell_id")
    out = labels.merge(features, on="cell_id", how="left", validate="many_to_one")
    out["feature_source"] = feature_source
    out["forcing_setup"] = "n150_single_forcing_pairwise"
    out = out.sort_values(["cell_id", "hour_sgt"]).reset_index(drop=True)
    return out


def target_schema(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build target schema and B8.6 interpretation boundaries."""
    target_units = {
        "delta_tmrt_p90_c": "deg C Tmrt difference",
        "delta_tmrt_mean_c": "deg C Tmrt difference",
        "delta_tmrt_p95_c": "deg C Tmrt difference",
        "tmrt_p90_c": "deg C Tmrt",
        "m_rad_pct01": "0-1 reference percentile label",
    }
    rows: list[dict[str, Any]] = []
    for target in [config["targets"]["primary"], *config["targets"]["secondary"]]:
        rows.append(
            {
                "target_name": target,
                "role": "primary" if target == config["targets"]["primary"] else "secondary_or_sensitivity",
                "available": target in dataset.columns and dataset[target].notna().any(),
                "non_null_count": int(dataset[target].notna().sum()) if target in dataset.columns else 0,
                "unit": target_units.get(target, "unknown"),
                "source_definition": (
                    "overhead_as_canopy - base pairwise SOLWEIG Tmrt p90"
                    if target == "delta_tmrt_p90_c"
                    else "compact N150 label retained for sensitivity/context"
                ),
                "allowed_interpretation": "SOLWEIG-derived radiative target for surrogate protocol stress testing.",
                "forbidden_interpretation": "Not WBGT, not risk, not observed truth, not causal installed-overhead effect.",
            }
        )
    return pd.DataFrame(rows)


def feature_schema(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build a feature schema with explicit non-leakage and metadata roles."""
    baseline_features = set(config["feature_contract"]["baseline_feature_columns"])
    metadata = set(config["feature_contract"]["metadata_columns"])
    targets = {config["targets"]["primary"], *config["targets"]["secondary"]}
    coordinate_names = {name for pair in config["feature_contract"]["coordinate_pairs"] for name in pair}
    rows: list[dict[str, Any]] = []
    for column in dataset.columns:
        if column == "cell_id" or column == "row_id":
            role = "id"
            tier = "excluded_identifier"
            include = False
            notes = "Group identifier only; never a numeric predictor."
        elif column in targets or column.startswith("delta_pct_pixels") or column.endswith("_base") or column.endswith("_overhead_as_canopy"):
            role = "target_or_companion_label"
            tier = "excluded_target"
            include = False
            notes = "SOLWEIG-derived label/target context; excluded from predictors."
        elif column == config["feature_contract"]["hour_feature"]:
            role = "hour_feature"
            tier = "hour_aware"
            include = True
            notes = "Allowed only for hour-aware baseline models; hour_holdout remains mandatory."
        elif column in baseline_features and not leakage_like(column, config):
            role = "feature"
            tier = "physical_core"
            include = True
            notes = "Compact physical feature selected for B8.6 baseline."
        elif column in coordinate_names:
            role = "metadata"
            tier = "spatial_diagnostic_only"
            include = False
            notes = "Coordinate metadata for spatial holdout only, not a prediction target or headline predictor."
        elif column in metadata or column in {"scenario_context", "source", "label_source", "target_definition", "feature_source", "forcing_setup"}:
            role = "metadata"
            tier = "excluded_metadata"
            include = False
            notes = "Metadata retained for traceability/splits."
        elif leakage_like(column, config):
            role = "forbidden_leakage"
            tier = "excluded_leakage"
            include = False
            notes = "Blocked by target/leakage name contract."
        else:
            role = "metadata"
            tier = "excluded_metadata"
            include = False
            notes = "Not selected for B8.6 baseline."
        non_null = int(dataset[column].notna().sum())
        rows.append(
            {
                "column_name": column,
                "role": role,
                "predictor_tier": tier,
                "dtype": str(dataset[column].dtype),
                "non_null_count": non_null,
                "missing_fraction": float(1 - non_null / len(dataset)) if len(dataset) else np.nan,
                "include_in_baseline": include,
                "leakage_status": "PASS_EXCLUDED" if role in {"target_or_companion_label", "forbidden_leakage"} else "PASS",
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def split_rows(
    frame: pd.DataFrame,
    split_family: str,
    split_name: str,
    fold_id: str,
    role: str,
    split_status: str,
    reason: str,
    notes: str,
) -> pd.DataFrame:
    """Create split manifest rows from a subset of the dataset."""
    out = frame[["row_id", "cell_id", "hour_sgt", "scenario_context"]].copy()
    out.insert(0, "role", role)
    out.insert(0, "fold_id", fold_id)
    out.insert(0, "split_name", split_name)
    out.insert(0, "split_family", split_family)
    out["split_status"] = split_status
    out["reason"] = reason
    out["notes"] = notes
    return out[COMMON_SPLIT_COLUMNS]


def make_train_test_split(
    frame: pd.DataFrame,
    mask: pd.Series,
    split_family: str,
    split_name: str,
    fold_id: str,
    split_status: str,
    reason: str,
    notes: str,
) -> pd.DataFrame:
    """Create train/test rows for one validation fold."""
    train = split_rows(frame.loc[~mask], split_family, split_name, fold_id, "train", split_status, reason, notes)
    test = split_rows(frame.loc[mask], split_family, split_name, fold_id, "test", split_status, reason, notes)
    return pd.concat([train, test], ignore_index=True)


def make_cell_group_holdout(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create deterministic cell-group holdouts."""
    cells = np.array(sorted(dataset["cell_id"].astype(str).unique()))
    rng = np.random.default_rng(int(config["random_seed"]))
    rng.shuffle(cells)
    chunks = np.array_split(cells, int(config["validation"]["cell_group_folds"]))
    rows: list[pd.DataFrame] = []
    for idx, test_cells in enumerate(chunks, start=1):
        mask = dataset["cell_id"].astype(str).isin(set(test_cells.tolist()))
        rows.append(
            make_train_test_split(
                dataset,
                mask,
                "cell_group_holdout",
                "cell_group_5fold",
                str(idx),
                "AVAILABLE",
                "Same cell_id held out across all hours.",
                "Main evidence; group-safe by cell_id.",
            )
        )
    return pd.concat(rows, ignore_index=True)


def detect_coordinate_pair(dataset: pd.DataFrame, config: dict[str, Any]) -> tuple[str, str] | None:
    """Find a usable coordinate pair for spatial holdout construction."""
    for x_col, y_col in config["feature_contract"]["coordinate_pairs"]:
        if x_col in dataset.columns and y_col in dataset.columns:
            x = pd.to_numeric(dataset[x_col], errors="coerce")
            y = pd.to_numeric(dataset[y_col], errors="coerce")
            if x.notna().sum() and y.notna().sum() and x.nunique(dropna=True) > 1 and y.nunique(dropna=True) > 1:
                return x_col, y_col
    return None


def make_spatial_holdout(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create quadrant spatial holdouts using compact coordinate metadata."""
    pair = detect_coordinate_pair(dataset, config)
    if pair is None:
        return blocked_split("spatial_holdout", "spatial_quadrants", "FUTURE_REQUIRED", "No compact coordinate pair found.")
    x_col, y_col = pair
    cells = dataset.drop_duplicates("cell_id")[["cell_id", x_col, y_col]].copy()
    cells[x_col] = pd.to_numeric(cells[x_col], errors="coerce")
    cells[y_col] = pd.to_numeric(cells[y_col], errors="coerce")
    x_mid = float(cells[x_col].median())
    y_mid = float(cells[y_col].median())
    cells["spatial_block"] = np.where(cells[x_col] <= x_mid, "west", "east") + "_" + np.where(cells[y_col] <= y_mid, "south", "north")
    rows: list[pd.DataFrame] = []
    for idx, block in enumerate(sorted(cells["spatial_block"].dropna().unique()), start=1):
        test_cells = set(cells.loc[cells["spatial_block"] == block, "cell_id"].astype(str))
        mask = dataset["cell_id"].astype(str).isin(test_cells)
        rows.append(
            make_train_test_split(
                dataset,
                mask,
                "spatial_holdout",
                f"spatial_{block}",
                str(idx),
                "AVAILABLE",
                f"Hold out compact coordinate quadrant {block} using {x_col}/{y_col}.",
                "Main evidence; group-safe by cell_id and coordinates are not predictors.",
            )
        )
    return pd.concat(rows, ignore_index=True)


def make_typology_holdout(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create typology holdouts from compact sample-design typology labels."""
    if "typology_label" not in dataset.columns:
        return blocked_split("typology_holdout", "typology_label", "FUTURE_REQUIRED", "No compact typology_label feature metadata found.")
    min_test = int(config["validation"]["typology_min_test_cells"])
    min_train = int(config["validation"]["typology_min_train_cells"])
    cell_typology = dataset.drop_duplicates("cell_id")[["cell_id", "typology_label"]].dropna()
    rows: list[pd.DataFrame] = []
    fold_id = 1
    for typology in sorted(cell_typology["typology_label"].astype(str).unique()):
        test_cells = set(cell_typology.loc[cell_typology["typology_label"].astype(str) == typology, "cell_id"].astype(str))
        mask = dataset["cell_id"].astype(str).isin(test_cells)
        train_cells = int(dataset.loc[~mask, "cell_id"].nunique())
        test_cell_count = len(test_cells)
        if train_cells < min_train or test_cell_count < min_test:
            rows.append(
                blocked_split(
                    "typology_holdout",
                    f"typology_{typology}",
                    "BLOCKED_DEGENERATE",
                    f"train cells={train_cells}, test cells={test_cell_count}; min train={min_train}, min test={min_test}.",
                    str(fold_id),
                )
            )
        else:
            rows.append(
                make_train_test_split(
                    dataset,
                    mask,
                    "typology_holdout",
                    f"typology_{typology}",
                    str(fold_id),
                    "AVAILABLE",
                    f"Hold out typology_label {typology}.",
                    "Main evidence; group-safe by cell_id and based on compact sample-design typology.",
                )
            )
        fold_id += 1
    return pd.concat(rows, ignore_index=True)


def make_hour_holdout(dataset: pd.DataFrame) -> pd.DataFrame:
    """Create leave-one-hour-out validation folds."""
    rows: list[pd.DataFrame] = []
    for idx, hour in enumerate(sorted(pd.to_numeric(dataset["hour_sgt"], errors="coerce").dropna().astype(int).unique()), start=1):
        mask = pd.to_numeric(dataset["hour_sgt"], errors="coerce") == hour
        rows.append(
            make_train_test_split(
                dataset,
                mask,
                "hour_holdout",
                f"leave_hour_{hour}_out",
                str(idx),
                "AVAILABLE",
                f"Leave hour_sgt {hour} out.",
                "Main transfer evidence; hour_sgt is available to hour-aware baselines but this fold tests hour transfer.",
            )
        )
    return pd.concat(rows, ignore_index=True)


def make_random_split(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create a diagnostic-only random row split."""
    rng = np.random.default_rng(int(config["random_seed"]))
    mask = pd.Series(rng.random(len(dataset)) < float(config["validation"]["random_test_fraction"]), index=dataset.index)
    return make_train_test_split(
        dataset,
        mask,
        "random_split",
        "random_row_diagnostic",
        "1",
        "DIAGNOSTIC_ONLY",
        "Random row split is diagnostic only and is not main evidence.",
        "May leak static cell features across train/test; do not use for promotion.",
    )


def blocked_split(
    split_family: str,
    split_name: str,
    split_status: str,
    reason: str,
    fold_id: str = "1",
) -> pd.DataFrame:
    """Create a machine-readable blocked/future-required split row."""
    return pd.DataFrame(
        [
            {
                "split_family": split_family,
                "split_name": split_name,
                "fold_id": fold_id,
                "role": "blocked",
                "row_id": "",
                "cell_id": "",
                "hour_sgt": "",
                "scenario_context": "",
                "split_status": split_status,
                "reason": reason,
                "notes": "No training/evaluation fold is created for this split family in B8.6.",
            }
        ],
        columns=COMMON_SPLIT_COLUMNS,
    )


def make_validation_splits(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create B8.6 validation split manifest."""
    frames = [
        make_cell_group_holdout(dataset, config),
        make_spatial_holdout(dataset, config),
        make_typology_holdout(dataset, config),
        make_hour_holdout(dataset),
        make_random_split(dataset, config),
        blocked_split(
            "scenario_holdout",
            "scenario_holdout_for_pairwise_delta",
            "FUTURE_REQUIRED",
            "Primary delta target is already overhead_as_canopy - base, so scenario is not a predictor or holdout axis.",
        ),
        blocked_split(
            "forcing_day_holdout",
            "n150_multi_forcing_required",
            "FUTURE_REQUIRED",
            "Existing N150 pairwise labels are single-forcing; forcing-day holdout requires future controlled N150 multi-forcing labels.",
        ),
    ]
    return pd.concat(frames, ignore_index=True)


def make_n24_bridge(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build the N24 stress-validation bridge table from F4 compact outputs."""
    bridge_inputs = config["inputs"]["n24_bridge"]
    n150_cells = set(dataset["cell_id"].astype(str).unique())
    rows: list[dict[str, Any]] = []
    sources = [
        ("robust_priority_anchor", bridge_inputs["robust_priority_cells"], "recommended_role"),
        ("neutral_boundary", bridge_inputs["neutral_boundary_cells"], "caveats"),
        ("unstable_review", bridge_inputs["unstable_priority_cells"], "stability_class"),
    ]
    for bridge_role, rel_source, note_col in sources:
        path = repo_path(rel_source)
        if not path.exists():
            continue
        frame = read_csv(path)
        for item in frame.itertuples(index=False):
            cell_id = str(getattr(item, "cell_id"))
            rows.append(
                {
                    "cell_id": cell_id,
                    "bridge_role": bridge_role,
                    "n150_label_present": cell_id in n150_cells,
                    "f4_source": rel_source,
                    "f4_note": str(getattr(item, note_col, "")),
                    "h10_caveat": config["n24_bridge"]["h10_caveat"],
                    "what_n24_can_validate": "Stress-test ranking stability, neutral-boundary handling, and h10 caveat interpretation against compact N24/F4 evidence.",
                    "what_n24_cannot_validate": "Cannot validate N150 generalisation, observed truth, local WBGT, risk, causal installed-overhead effect, B9 readiness, or AOI-wide prediction.",
                    "training_role": "stress_validation_context_only_not_training",
                }
            )
    anchor_cells = config["n24_bridge"]["robust_priority_anchor_cells"]
    for cell_id in anchor_cells:
        if cell_id not in {row["cell_id"] for row in rows}:
            rows.append(
                {
                    "cell_id": cell_id,
                    "bridge_role": "configured_anchor_not_in_f4_table",
                    "n150_label_present": cell_id in n150_cells,
                    "f4_source": "config_anchor_cells",
                    "f4_note": "Anchor cell named in B8.6 config.",
                    "h10_caveat": config["n24_bridge"]["h10_caveat"],
                    "what_n24_can_validate": "Anchor traceability only.",
                    "what_n24_cannot_validate": "Cannot validate N150 generalisation or any WBGT/risk/causal claim.",
                    "training_role": "stress_validation_context_only_not_training",
                }
            )
    return pd.DataFrame(rows).sort_values(["bridge_role", "cell_id"]).reset_index(drop=True)


def available_main_split_families(splits: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    """Return main split families with at least one available train/test fold."""
    rows = splits.loc[(splits["split_status"] == "AVAILABLE") & (splits["role"].isin(["train", "test"]))]
    observed = sorted(rows["split_family"].unique().tolist())
    return [family for family in config["validation"]["main_split_families"] if family in observed]


def run(config_path: Path = DEFAULT_CONFIG) -> DatasetResult:
    """Run B8.6 dataset and validation split creation."""
    config = read_config(config_path)
    out_dir = repo_path(config["outputs"]["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    label_path = repo_path(config["inputs"]["label_candidates"]["pairwise_delta"])
    if not label_path.exists():
        return empty_outputs(config, "BLOCKED_LABEL_INPUT")
    try:
        dataset = build_dataset(config)
    except FileNotFoundError:
        return empty_outputs(config, "BLOCKED_FEATURE_INPUT")
    except ValueError:
        return empty_outputs(config, "BLOCKED_LABEL_INPUT")

    schema = feature_schema(dataset, config)
    targets = target_schema(dataset, config)
    splits = make_validation_splits(dataset, config)
    bridge = make_n24_bridge(dataset, config)

    dataset.to_csv(repo_path(config["outputs"]["surrogate_dataset"]), index=False)
    schema.to_csv(repo_path(config["outputs"]["feature_schema"]), index=False)
    targets.to_csv(repo_path(config["outputs"]["target_schema"]), index=False)
    splits.to_csv(repo_path(config["outputs"]["validation_splits"]), index=False)
    bridge.to_csv(repo_path(config["outputs"]["n24_stress_validation_bridge"]), index=False)

    available_targets = targets.loc[targets["available"], "target_name"].astype(str).tolist()
    baseline_feature_count = int(schema["include_in_baseline"].fillna(False).sum())
    main_splits = available_main_split_families(splits, config)
    status = "DATASET_READY" if config["targets"]["primary"] in available_targets and baseline_feature_count > 0 else "BLOCKED_FEATURE_INPUT"
    return DatasetResult(
        status=status,
        dataset_rows=len(dataset),
        dataset_columns=dataset.shape[1],
        unique_cells=int(dataset["cell_id"].nunique()),
        available_targets=available_targets,
        baseline_feature_count=baseline_feature_count,
        main_split_families_available=main_splits,
        future_required_splits=config["validation"]["future_required_split_families"],
        n24_bridge_rows=len(bridge),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build B8.6 surrogate dataset and validation splits.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6 YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
