"""Create B8.6b validation split manifests.

Inputs:
    configs/v12/systemb_b86b_surrogate_promotion.yaml
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_surrogate_dataset.csv

Outputs:
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_validation_splits.csv

Saved metrics:
    Train/test row counts, unique cell counts, split family, fold ID, role,
    and reason for forcing-day, cell-group, hour, spatial, typology, and
    diagnostic random splits.

This script reads only compact CSV inputs. It does not run QGIS or SOLWEIG,
does not read raster files, does not create AOI-wide prediction, and does not
create WBGT, hazard_score, risk_score, B9, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86b_surrogate_inventory import DEFAULT_CONFIG, read_config, repo_path


SPLIT_COLUMNS = [
    "split_family",
    "split_name",
    "fold_id",
    "role",
    "row_id",
    "cell_id",
    "forcing_day_id",
    "hour_sgt",
    "split_status",
    "reason",
    "notes",
]


@dataclass(frozen=True)
class SplitResult:
    """Compact return record for the B8.6b split step."""

    status: str
    split_rows: int
    available_split_families: list[str]
    forcing_day_folds: int
    random_split_role: str


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
    """Create manifest rows for one split role."""
    out = frame[["row_id", "cell_id", "forcing_day_id", "hour_sgt"]].copy()
    out.insert(0, "role", role)
    out.insert(0, "fold_id", fold_id)
    out.insert(0, "split_name", split_name)
    out.insert(0, "split_family", split_family)
    out["split_status"] = split_status
    out["reason"] = reason
    out["notes"] = notes
    return out[SPLIT_COLUMNS]


def make_train_test(
    dataset: pd.DataFrame,
    test_mask: pd.Series,
    split_family: str,
    split_name: str,
    fold_id: str,
    split_status: str,
    reason: str,
    notes: str,
) -> pd.DataFrame:
    """Build paired train/test split rows."""
    return pd.concat(
        [
            split_rows(dataset.loc[~test_mask], split_family, split_name, fold_id, "train", split_status, reason, notes),
            split_rows(dataset.loc[test_mask], split_family, split_name, fold_id, "test", split_status, reason, notes),
        ],
        ignore_index=True,
    )


def blocked_split(split_family: str, split_name: str, reason: str, fold_id: str = "1") -> pd.DataFrame:
    """Create a blocked split marker row."""
    return pd.DataFrame(
        [
            {
                "split_family": split_family,
                "split_name": split_name,
                "fold_id": fold_id,
                "role": "blocked",
                "row_id": "",
                "cell_id": "",
                "forcing_day_id": "",
                "hour_sgt": "",
                "split_status": "BLOCKED_DEGENERATE",
                "reason": reason,
                "notes": "No evaluation fold was created for this split.",
            }
        ],
        columns=SPLIT_COLUMNS,
    )


def forcing_day_holdout(dataset: pd.DataFrame) -> pd.DataFrame:
    """Create train-FD01/test-FD02 and train-FD02/test-FD01 folds."""
    rows: list[pd.DataFrame] = []
    for idx, forcing_day in enumerate(sorted(dataset["forcing_day_id"].astype(str).unique()), start=1):
        mask = dataset["forcing_day_id"].astype(str) == forcing_day
        rows.append(
            make_train_test(
                dataset,
                mask,
                "forcing_day_holdout",
                f"holdout_{forcing_day}",
                str(idx),
                "AVAILABLE",
                f"Hold out forcing day {forcing_day}.",
                "Primary evidence. forcing_day_id is excluded from predictors.",
            )
        )
    return pd.concat(rows, ignore_index=True)


def cell_group_holdout(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create deterministic grouped-by-cell folds."""
    cells = np.array(sorted(dataset["cell_id"].astype(str).unique()))
    rng = np.random.default_rng(int(config["random_seed"]))
    rng.shuffle(cells)
    chunks = np.array_split(cells, int(config["validation"]["cell_group_folds"]))
    rows: list[pd.DataFrame] = []
    for idx, test_cells in enumerate(chunks, start=1):
        mask = dataset["cell_id"].astype(str).isin(set(test_cells.tolist()))
        rows.append(
            make_train_test(
                dataset,
                mask,
                "cell_group_holdout",
                "cell_group_5fold",
                str(idx),
                "AVAILABLE",
                "Hold out cell_id groups across both forcing days and all hours.",
                "Main evidence; cell_id is never used as a numeric predictor.",
            )
        )
    return pd.concat(rows, ignore_index=True)


def hour_holdout(dataset: pd.DataFrame) -> pd.DataFrame:
    """Create leave-one-hour-out folds."""
    rows: list[pd.DataFrame] = []
    for idx, hour in enumerate(sorted(pd.to_numeric(dataset["hour_sgt"], errors="coerce").dropna().astype(int).unique()), start=1):
        mask = pd.to_numeric(dataset["hour_sgt"], errors="coerce") == hour
        rows.append(
            make_train_test(
                dataset,
                mask,
                "hour_holdout",
                f"leave_h{hour}_out",
                str(idx),
                "AVAILABLE",
                f"Hold out hour_sgt {hour}.",
                "Main transfer evidence; hour_sgt may be a predictor in hour-aware models, so this tests hour transfer directly.",
            )
        )
    return pd.concat(rows, ignore_index=True)


def coordinate_pair(dataset: pd.DataFrame, config: dict[str, Any]) -> tuple[str, str] | None:
    """Find a compact coordinate pair for spatial holdout."""
    for x_col, y_col in config["feature_contract"]["coordinate_pairs"]:
        if x_col in dataset.columns and y_col in dataset.columns:
            x = pd.to_numeric(dataset[x_col], errors="coerce")
            y = pd.to_numeric(dataset[y_col], errors="coerce")
            if x.nunique(dropna=True) > 1 and y.nunique(dropna=True) > 1:
                return x_col, y_col
    return None


def spatial_holdout(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create coordinate-quadrant spatial holdouts if compact coordinates exist."""
    pair = coordinate_pair(dataset, config)
    if pair is None:
        return blocked_split("spatial_holdout", "coordinate_quadrant", "No compact coordinate pair exists.")
    x_col, y_col = pair
    cells = dataset.drop_duplicates("cell_id")[["cell_id", x_col, y_col]].copy()
    cells[x_col] = pd.to_numeric(cells[x_col], errors="coerce")
    cells[y_col] = pd.to_numeric(cells[y_col], errors="coerce")
    x_mid = float(cells[x_col].median())
    y_mid = float(cells[y_col].median())
    cells["spatial_block"] = np.where(cells[x_col] <= x_mid, "west", "east") + "_" + np.where(cells[y_col] <= y_mid, "south", "north")
    rows: list[pd.DataFrame] = []
    for idx, block in enumerate(sorted(cells["spatial_block"].unique()), start=1):
        test_cells = set(cells.loc[cells["spatial_block"] == block, "cell_id"].astype(str))
        mask = dataset["cell_id"].astype(str).isin(test_cells)
        rows.append(
            make_train_test(
                dataset,
                mask,
                "spatial_holdout",
                f"spatial_{block}",
                str(idx),
                "AVAILABLE",
                f"Hold out compact coordinate bin {block} from {x_col}/{y_col}.",
                "Main evidence; coordinates are split metadata and not predictors.",
            )
        )
    return pd.concat(rows, ignore_index=True)


def typology_holdout(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create typology-label holdouts if compact typology labels are sufficient."""
    if "typology_label" not in dataset.columns:
        return blocked_split("typology_holdout", "typology_label", "No compact typology_label column exists.")
    min_test = int(config["validation"]["typology_min_test_cells"])
    min_train = int(config["validation"]["typology_min_train_cells"])
    cells = dataset.drop_duplicates("cell_id")[["cell_id", "typology_label"]].dropna()
    rows: list[pd.DataFrame] = []
    fold_id = 1
    for typology in sorted(cells["typology_label"].astype(str).unique()):
        test_cells = set(cells.loc[cells["typology_label"].astype(str) == typology, "cell_id"].astype(str))
        mask = dataset["cell_id"].astype(str).isin(test_cells)
        train_cells = int(dataset.loc[~mask, "cell_id"].nunique())
        if len(test_cells) < min_test or train_cells < min_train:
            rows.append(
                blocked_split(
                    "typology_holdout",
                    f"typology_{typology}",
                    f"Degenerate typology fold: test_cells={len(test_cells)}, train_cells={train_cells}.",
                    str(fold_id),
                )
            )
        else:
            rows.append(
                make_train_test(
                    dataset,
                    mask,
                    "typology_holdout",
                    f"typology_{typology}",
                    str(fold_id),
                    "AVAILABLE",
                    f"Hold out compact typology_label {typology}.",
                    "Main evidence; typology_label is split metadata and not a predictor.",
                )
            )
        fold_id += 1
    return pd.concat(rows, ignore_index=True)


def random_split(dataset: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create a diagnostic-only random row split."""
    rng = np.random.default_rng(int(config["random_seed"]))
    mask = pd.Series(rng.random(len(dataset)) < float(config["validation"]["random_test_fraction"]), index=dataset.index)
    return make_train_test(
        dataset,
        mask,
        "random_split",
        "random_row_diagnostic",
        "1",
        "DIAGNOSTIC_ONLY",
        "Random row split is diagnostic only and not promotion evidence.",
        "Static cell features can cross train/test here; do not use as main evidence.",
    )


def run(config_path: Path = DEFAULT_CONFIG) -> SplitResult:
    """Build and write B8.6b validation split manifest."""
    config = read_config(config_path)
    dataset_path = repo_path(config["outputs"]["surrogate_dataset"])
    if not dataset_path.exists():
        pd.DataFrame(columns=SPLIT_COLUMNS).to_csv(repo_path(config["outputs"]["validation_splits"]), index=False)
        return SplitResult("B86B_BLOCKED_LABEL_INPUT", 0, [], 0, "not_created")
    dataset = pd.read_csv(dataset_path, dtype={"cell_id": "string", "row_id": "string", "forcing_day_id": "string"})
    if dataset.empty:
        pd.DataFrame(columns=SPLIT_COLUMNS).to_csv(repo_path(config["outputs"]["validation_splits"]), index=False)
        return SplitResult("B86B_BLOCKED_LABEL_INPUT", 0, [], 0, "not_created")
    frames = [
        forcing_day_holdout(dataset),
        cell_group_holdout(dataset, config),
        hour_holdout(dataset),
        spatial_holdout(dataset, config),
        typology_holdout(dataset, config),
        random_split(dataset, config),
    ]
    splits = pd.concat(frames, ignore_index=True)
    splits.to_csv(repo_path(config["outputs"]["validation_splits"]), index=False)
    available = sorted(splits.loc[splits["split_status"] == "AVAILABLE", "split_family"].unique().tolist())
    forcing_folds = int(splits.loc[(splits["split_family"] == "forcing_day_holdout") & (splits["role"] == "test"), "fold_id"].nunique())
    return SplitResult(
        status="B86B_SPLITS_READY",
        split_rows=int(len(splits)),
        available_split_families=available,
        forcing_day_folds=forcing_folds,
        random_split_role="diagnostic_only",
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Create B8.6b validation split manifests.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6b YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
