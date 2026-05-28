"""Shared B87E N300 surrogate benchmark utilities.

Inputs:
    configs/v12/systemb_b87e_n300_surrogate_benchmark.yaml
    outputs/v12_surrogate/b87d_n300_label_integration/b87d_n300_pairwise_delta_by_cell_hour.csv
    compact static/context feature source candidates listed in the config.

Outputs:
    Required B87E CSV/Markdown artifacts under
    outputs/v12_surrogate/b87e_n300_surrogate_benchmark/ plus the Chinese
    canonical note under docs/v12.

Config path:
    --config configs/v12/systemb_b87e_n300_surrogate_benchmark.yaml

Saved metrics:
    Input/source inventory, N300 feature matrix/schema/missingness/leakage
    audit, target summary, split registry, model registry, split-level metrics,
    OOF/holdout predictions, strata errors, rank/top-k metrics, diagnostic
    feature importance, promotion decision, blockers, and next-lane prompt.

Claim boundaries:
    This is a surrogate/emulator benchmark for SOLWEIG-derived delta Tmrt and
    Tmrt features. It is not empirical WBGT calibration, observed truth,
    AOI/B9 inference, a hazard/risk map, exposure/vulnerability output, or
    causal feature-importance evidence. Random split is diagnostic only.
"""

from __future__ import annotations

import argparse
import math
import os
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error, r2_score
from sklearn.model_selection import GroupKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", message="Could not find the number of physical cores.*")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b87e_n300_surrogate_benchmark.yaml"

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
YES = "yes"
NO = "no"
FAILED = "FAILED"
B87D_PASS = "B87D_N300_LABEL_INTEGRATION_PASS"
B87E_CANDIDATE = "B87E_SURROGATE_BENCHMARK_PASS_CANDIDATE_MODEL"
B87E_NO_PROMOTION = "B87E_SURROGATE_BENCHMARK_PASS_NO_PROMOTION"
B87E_BLOCKED_LABEL_QA = "B87E_BLOCKED_LABEL_QA"
B87E_BLOCKED_FEATURE_QA = "B87E_BLOCKED_FEATURE_QA"
B87E_BLOCKED_SPLIT_QA = "B87E_BLOCKED_SPLIT_QA"

CLAIM_BOUNDARY = (
    "Surrogate/emulator of SOLWEIG-derived delta Tmrt/Tmrt features only; not "
    "observed truth, not WBGT calibration, not AOI/B9 inference, not hazard or "
    "risk mapping, not exposure/vulnerability output, and not causal feature "
    "importance."
)

HEADLINE_MODELS = [
    "featureless_mean",
    "context_mean",
    "ridge",
    "elasticnet",
    "random_forest",
    "extra_trees",
    "hist_gradient_boosting",
]
DIAGNOSTIC_MODELS = ["gradient_boosting"]
TARGET_COLUMNS = {
    "delta_tmrt_mean_c",
    "delta_tmrt_median_c",
    "delta_tmrt_p50_c",
    "delta_tmrt_p90_c",
    "delta_tmrt_p95_c",
    "delta_tmrt_max_c",
    "base_tmrt_mean_c",
    "overhead_tmrt_mean_c",
    "base_tmrt_median_c",
    "overhead_tmrt_median_c",
    "base_tmrt_p90_c",
    "overhead_tmrt_p90_c",
    "base_tmrt_p95_c",
    "overhead_tmrt_p95_c",
    "base_tmrt_max_c",
    "overhead_tmrt_max_c",
}


@dataclass(frozen=True)
class SplitDef:
    """Train/test split definition."""

    split_family: str
    split_name: str
    fold_id: str
    train_idx: np.ndarray
    test_idx: np.ndarray
    main_evidence: str
    notes: str


@dataclass(frozen=True)
class B87EResult:
    """Compact B87E run result."""

    status: str
    feature_matrix_shape: tuple[int, int]
    main_split_count: int
    best_group_model: str
    best_group_mae: float
    best_old_to_new_model: str
    best_old_to_new_mae: float
    best_rank_spearman: float
    promotion_decision: str
    blockers: list[str]
    recommended_next_lane: str


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def now_stamp() -> str:
    """Return a local timestamp."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def repo_path(value: str | Path) -> Path:
    """Resolve repository-relative paths."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def rel(path: str | Path) -> str:
    """Return repository-relative POSIX path when possible."""
    p = repo_path(path)
    try:
        return p.resolve(strict=False).relative_to(ROOT.resolve(strict=False)).as_posix()
    except ValueError:
        return p.as_posix()


def parse_inline_list(text: str) -> list[Any]:
    """Parse a tiny YAML inline list fallback."""
    inner = text.strip()[1:-1].strip()
    if not inner:
        return []
    return [parse_scalar(part.strip()) for part in inner.split(",")]


def parse_scalar(value: str) -> Any:
    """Parse a small YAML scalar fallback."""
    stripped = value.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return parse_inline_list(stripped)
    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none", "~"}:
        return None
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        return stripped.strip("\"'")


def read_simple_yaml(path: Path) -> dict[str, Any]:
    """Read the simple YAML subset used by OpenHeat configs."""
    lines = [
        line.rstrip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for idx, line in enumerate(lines):
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if text.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"Unsupported YAML list placement: {line}")
            parent.append(parse_scalar(text[2:].strip()))
            continue
        key, _, raw_value = text.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            if not isinstance(parent, dict):
                raise ValueError(f"Unsupported YAML parent: {line}")
            parent[key] = parse_scalar(raw_value)
            continue
        next_container: Any = {}
        for future in lines[idx + 1 :]:
            future_indent = len(future) - len(future.lstrip(" "))
            future_text = future.strip()
            if future_indent <= indent:
                break
            next_container = [] if future_text.startswith("- ") else {}
            break
        if not isinstance(parent, dict):
            raise ValueError(f"Unsupported YAML parent: {line}")
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def read_config(path: Path) -> dict[str, Any]:
    """Read YAML with PyYAML or local fallback."""
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Config did not parse to a mapping: {path}")
        return loaded
    except ImportError:
        return read_simple_yaml(path)


def output_path(config: dict[str, Any], name: str) -> Path:
    """Return configured output path."""
    return repo_path(config["outputs"][name])


def ensure_output_dirs(config: dict[str, Any]) -> None:
    """Create compact output directories only."""
    repo_path(config["outputs"]["out_dir"]).mkdir(parents=True, exist_ok=True)
    repo_path(config["outputs"]["canonical_note_cn"]).parent.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read CSV with UTF-8 BOM tolerance."""
    return pd.read_csv(path, encoding="utf-8-sig", **kwargs)


def write_csv(path: Path, frame: pd.DataFrame, columns: Sequence[str] | None = None) -> None:
    """Write compact UTF-8 CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    if columns is not None:
        for column in columns:
            if column not in out.columns:
                out[column] = ""
        out = out.loc[:, list(columns)]
    out.to_csv(path, index=False, encoding="utf-8")


def format_float(value: Any, digits: int = 6) -> str:
    """Format finite numeric values for stable output."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(numeric):
        return ""
    return f"{numeric:.{digits}f}"


def input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Write B87E input inventory."""
    ensure_output_dirs(config)
    rows: list[dict[str, Any]] = []
    named = {
        "n300_label_path": config["n300_label_path"],
        "b87d_status_path": config.get("b87d_status_path", ""),
    }
    for i, path in enumerate(config.get("feature_source_candidates", []), start=1):
        named[f"feature_source_candidate_{i}"] = path
    for name, value in named.items():
        path = repo_path(value)
        exists = path.exists()
        size = path.stat().st_size if exists and path.is_file() else 0
        rows.append(
            {
                "input_name": name,
                "path": rel(path),
                "exists": YES if exists else NO,
                "file_size_bytes": size,
                "status": PASS if exists and (path.is_dir() or size > 0) else FAIL,
                "notes": "compact source artifact",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    frame = pd.DataFrame(rows)
    write_csv(output_path(config, "input_inventory"), frame)
    return frame


def label_qa_passed(config: dict[str, Any]) -> bool:
    """Return whether B87D status permits B87E."""
    status_path = repo_path(config.get("b87d_status_path", ""))
    if not status_path.exists():
        return False
    return B87D_PASS in status_path.read_text(encoding="utf-8")


def feature_source_inventory(config: dict[str, Any], label_cells: set[str]) -> pd.DataFrame:
    """Write feature source inventory and coverage."""
    rows: list[dict[str, Any]] = []
    for path_text in config.get("feature_source_candidates", []):
        path = repo_path(path_text)
        if not path.exists():
            rows.append({"source_path": rel(path), "exists": NO, "rows": 0, "unique_cells": 0, "n300_cell_coverage": 0, "status": FAIL, "notes": "missing", "claim_boundary": CLAIM_BOUNDARY})
            continue
        frame = read_csv(path, dtype=str)
        cells = set(frame["cell_id"].astype(str)) if "cell_id" in frame.columns else set()
        rows.append(
            {
                "source_path": rel(path),
                "exists": YES,
                "rows": len(frame),
                "unique_cells": len(cells),
                "n300_cell_coverage": len(cells & label_cells),
                "status": PASS if cells & label_cells else WARN,
                "notes": "used for static feature join" if cells & label_cells else "no overlapping N300 cells",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    out = pd.DataFrame(rows)
    write_csv(output_path(config, "feature_source_inventory"), out)
    return out


def combine_static_features(config: dict[str, Any], cells: Sequence[str]) -> pd.DataFrame:
    """Combine static cell features from candidate sources."""
    static = pd.DataFrame({"cell_id": sorted(set(map(str, cells)))})
    for path_text in config.get("feature_source_candidates", []):
        path = repo_path(path_text)
        if not path.exists():
            continue
        source = read_csv(path, dtype=str)
        if "cell_id" not in source.columns:
            continue
        source["cell_id"] = source["cell_id"].astype(str)
        source = source.drop_duplicates("cell_id", keep="first")
        source = source.loc[source["cell_id"].isin(static["cell_id"])]
        if source.empty:
            continue
        for column in source.columns:
            if column == "cell_id":
                continue
            if column not in static.columns:
                static = static.merge(source[["cell_id", column]], on="cell_id", how="left")
            else:
                fill = source[["cell_id", column]].rename(columns={column: f"{column}__new"})
                static = static.merge(fill, on="cell_id", how="left")
                static[column] = static[column].where(static[column].notna() & static[column].astype(str).ne(""), static[f"{column}__new"])
                static = static.drop(columns=[f"{column}__new"])
    return static


def leakage_reason(column: str, config: dict[str, Any]) -> str | None:
    """Return why a column is forbidden from main predictors."""
    lower = column.lower()
    if column in TARGET_COLUMNS:
        return "target_or_tmrt_component"
    if lower == "cell_id":
        return "direct_cell_id"
    for token in config["feature_policy"].get("forbidden_tokens", []):
        if str(token).lower() in lower:
            return f"forbidden_token:{token}"
    for token in config["feature_policy"].get("forbidden_coordinate_tokens", []):
        if str(token).lower() in lower:
            return f"coordinate_token:{token}"
    if column in config["feature_policy"].get("diagnostic_only_columns", []):
        return "diagnostic_only_metadata"
    return None


def build_feature_matrix(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build and save B87E N300 feature matrix/schema."""
    labels = read_csv(repo_path(config["n300_label_path"]), dtype=str)
    labels["cell_id"] = labels["cell_id"].astype(str)
    labels["hour_sgt"] = pd.to_numeric(labels["hour_sgt"], errors="coerce").astype("Int64")
    label_cells = set(labels["cell_id"].astype(str))
    feature_source_inventory(config, label_cells)
    static = combine_static_features(config, labels["cell_id"].unique())
    duplicate_label_columns = [column for column in static.columns if column in labels.columns and column != "cell_id"]
    if duplicate_label_columns:
        static = static.drop(columns=duplicate_label_columns)
    matrix = labels.merge(static, on="cell_id", how="left", validate="many_to_one")
    matrix["row_id"] = matrix["cell_id"].astype(str) + "|" + matrix["forcing_day_id"].astype(str) + "|h" + matrix["hour_sgt"].astype(str)
    first_cols = ["row_id", "cell_id", "forcing_day_id", "date", "hour_sgt", "sample_group", "label_source", "protocol_id"]
    first_cols = [c for c in first_cols if c in matrix.columns]
    matrix = matrix.loc[:, first_cols + [c for c in matrix.columns if c not in first_cols]]

    schema_rows: list[dict[str, Any]] = []
    max_card = int(config["feature_policy"].get("max_categorical_cardinality", 40))
    for column in matrix.columns:
        preferred = set(config["feature_policy"].get("preferred_main_features", []))
        if column in TARGET_COLUMNS or column == config["primary_target"] or column in config.get("secondary_targets", []):
            role = "target"
            include = NO
            reason = "target"
        elif column in {"row_id", "cell_id", "sample_group", "label_source", "protocol_id", "b87d_label_status", "extraction_convention_id", "notes", "claim_boundary"}:
            role = "metadata"
            include = NO
            reason = "metadata_not_predictor"
        elif column in config.get("context_columns", []):
            role = "context"
            include = YES
            reason = ""
        else:
            reason = leakage_reason(column, config)
            role = "static_feature"
            include = NO if reason else YES
            if include == YES and preferred and column not in preferred:
                include = NO
                reason = "not_in_preferred_main_feature_set"
        if include == YES:
            unique = matrix[column].nunique(dropna=True)
            numeric = pd.to_numeric(matrix[column], errors="coerce")
            if numeric.notna().sum() == 0 and unique > max_card:
                include = NO
                reason = "categorical_cardinality_gt_limit"
            elif unique <= 1:
                include = NO
                reason = "constant_or_empty"
        schema_rows.append(
            {
                "column_name": column,
                "role": role,
                "dtype": str(matrix[column].dtype),
                "non_null_count": int(matrix[column].notna().sum()),
                "missing_fraction": format_float(float(matrix[column].isna().mean())),
                "unique_values": int(matrix[column].nunique(dropna=True)),
                "include_in_main_feature_set": include,
                "drop_reason": reason,
                "feature_set": config["feature_policy"]["main_feature_set"],
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    schema = pd.DataFrame(schema_rows)
    missing = schema[["column_name", "role", "non_null_count", "missing_fraction", "include_in_main_feature_set", "drop_reason"]].copy()
    target_summary(config, matrix)
    write_csv(output_path(config, "feature_matrix"), matrix)
    write_csv(output_path(config, "feature_schema"), schema)
    write_csv(output_path(config, "feature_missingness"), missing)
    return matrix, schema


def target_summary(config: dict[str, Any], matrix: pd.DataFrame) -> pd.DataFrame:
    """Write primary and secondary target summaries."""
    rows: list[dict[str, Any]] = []
    for target in [config["primary_target"], *config.get("secondary_targets", [])]:
        if target not in matrix.columns:
            rows.append({"target": target, "status": FAIL, "count": 0, "claim_boundary": CLAIM_BOUNDARY})
            continue
        values = pd.to_numeric(matrix[target], errors="coerce").dropna()
        rows.append(
            {
                "target": target,
                "status": PASS if len(values) == int(config["expected_rows"]) else FAIL,
                "count": int(values.size),
                "mean": format_float(values.mean()),
                "std": format_float(values.std(ddof=0)),
                "min": format_float(values.min()),
                "p05": format_float(values.quantile(0.05)),
                "p50": format_float(values.quantile(0.50)),
                "p90": format_float(values.quantile(0.90)),
                "p95": format_float(values.quantile(0.95)),
                "max": format_float(values.max()),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    out = pd.DataFrame(rows)
    write_csv(output_path(config, "target_summary"), out)
    return out


def leakage_audit(config: dict[str, Any], matrix: pd.DataFrame, schema: pd.DataFrame) -> pd.DataFrame:
    """Audit feature leakage for the main feature set."""
    selected = set(schema.loc[schema["include_in_main_feature_set"].eq(YES), "column_name"].astype(str))
    rows: list[dict[str, Any]] = []
    for column in sorted(selected):
        reason = leakage_reason(column, config)
        rows.append(
            {
                "column_name": column,
                "included_in_main_feature_set": YES,
                "leakage_status": PASS if reason is None or column in config.get("context_columns", []) else FAIL,
                "reason": reason or "allowed",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    for column in sorted(set(matrix.columns) - selected):
        reason = leakage_reason(column, config)
        if reason:
            rows.append({"column_name": column, "included_in_main_feature_set": NO, "leakage_status": PASS, "reason": reason, "claim_boundary": CLAIM_BOUNDARY})
    out = pd.DataFrame(rows)
    write_csv(output_path(config, "feature_leakage_audit"), out)
    return out


def selected_features(matrix: pd.DataFrame, schema: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    """Return selected numeric and categorical features."""
    features = schema.loc[schema["include_in_main_feature_set"].eq(YES), "column_name"].astype(str).tolist()
    numeric: list[str] = []
    categorical: list[str] = []
    for column in features:
        coerced = pd.to_numeric(matrix[column], errors="coerce")
        if coerced.notna().sum() >= max(1, int(matrix[column].notna().sum() * 0.8)) and coerced.nunique(dropna=True) > 1:
            matrix[column] = coerced
            numeric.append(column)
        else:
            categorical.append(column)
    return features, numeric, categorical


def build_splits(config: dict[str, Any], matrix: pd.DataFrame) -> list[SplitDef]:
    """Create leakage-aware split registry."""
    splits: list[SplitDef] = []
    n = len(matrix)
    groups = matrix[config["group_column"]].astype(str).to_numpy()
    gkf = GroupKFold(n_splits=int(config["validation"]["group_kfold_splits"]))
    for fold, (train_idx, test_idx) in enumerate(gkf.split(np.arange(n), groups=groups), start=1):
        splits.append(SplitDef("group_kfold_cell", "group_kfold_5fold", str(fold), train_idx, test_idx, "main_cell_grouped", "Cell-grouped holdout; no cell appears in train and test."))
    sample_group = matrix[config["sample_group_column"]].astype(str)
    existing_idx = matrix.index[sample_group.eq("existing_n150")].to_numpy()
    new_idx = matrix.index[sample_group.eq("new150_b87c")].to_numpy()
    if len(existing_idx) and len(new_idx):
        splits.append(SplitDef("old_to_new_generalization", "train_existing_n150_test_new150_b87c", "1", existing_idx, new_idx, "main_transfer", "Train F5 existing N150, test B87C new150."))
        splits.append(SplitDef("new_to_old_diagnostic", "train_new150_b87c_test_existing_n150", "1", new_idx, existing_idx, "diagnostic_transfer", "Diagnostic reverse transfer."))
    context_groups = list(matrix.groupby(["forcing_day_id", "hour_sgt"], sort=True))
    preferred_hour_order = {13: 0, 12: 1, 15: 2, 10: 3, 16: 4}
    context_groups = sorted(context_groups, key=lambda item: (preferred_hour_order.get(int(item[0][1]), 99), str(item[0][0])))
    for (forcing, hour), part in context_groups[: int(config["validation"].get("max_context_holdouts", len(context_groups)))]:
        test_idx = part.index.to_numpy()
        train_idx = matrix.index.difference(test_idx).to_numpy()
        if len(train_idx) and len(test_idx):
            splits.append(SplitDef("context_holdout", f"holdout_{forcing}_h{hour}", "1", train_idx, test_idx, "supporting_context_transfer", "Leave-one forcing-day/hour context out; cells may repeat across contexts."))
    if "spatial_bin" in matrix.columns:
        spatial_groups = sorted(matrix.groupby("spatial_bin", sort=True), key=lambda item: matrix.loc[item[1].index, "cell_id"].nunique(), reverse=True)
        for value, part in spatial_groups[: int(config["validation"].get("max_spatial_holdouts", 4))]:
            test_cells = set(part["cell_id"].astype(str))
            if len(test_cells) >= int(config["validation"]["spatial_min_test_cells"]):
                test_idx = part.index.to_numpy()
                train_idx = matrix.index.difference(test_idx).to_numpy()
                splits.append(SplitDef("spatial_holdout", f"spatial_{value}", "1", train_idx, test_idx, "main_spatial", "Spatial-bin holdout if available."))
    typology_col = "typology" if "typology" in matrix.columns else "typology_label" if "typology_label" in matrix.columns else ""
    if typology_col:
        typology_groups = sorted(matrix.groupby(typology_col, sort=True), key=lambda item: matrix.loc[item[1].index, "cell_id"].nunique(), reverse=True)
        for value, part in typology_groups[: int(config["validation"].get("max_typology_holdouts", 4))]:
            test_cells = set(part["cell_id"].astype(str))
            train_cells = set(matrix.loc[matrix.index.difference(part.index), "cell_id"].astype(str))
            if len(test_cells) >= int(config["validation"]["typology_min_test_cells"]) and len(train_cells) >= int(config["validation"]["typology_min_train_cells"]):
                splits.append(SplitDef("typology_holdout", f"typology_{value}", "1", matrix.index.difference(part.index).to_numpy(), part.index.to_numpy(), "main_typology", "Typology holdout if available."))
    if "primary_role" in matrix.columns:
        role_groups = sorted(matrix.groupby("primary_role", sort=True), key=lambda item: matrix.loc[item[1].index, "cell_id"].nunique(), reverse=True)
        for value, part in role_groups[: int(config["validation"].get("max_role_holdouts", 3))]:
            test_cells = set(part["cell_id"].astype(str))
            if len(test_cells) >= int(config["validation"]["role_min_test_cells"]):
                splits.append(SplitDef("role_holdout", f"role_{value}", "1", matrix.index.difference(part.index).to_numpy(), part.index.to_numpy(), "main_typology_role", "Primary-role holdout; primary_role is not used as a main predictor."))
    train_idx, test_idx = train_test_split(
        matrix.index.to_numpy(),
        test_size=float(config["validation"]["random_test_fraction"]),
        random_state=int(config["random_state"]),
        shuffle=True,
    )
    splits.append(SplitDef("random_split_diagnostic", "random_row_split", "1", train_idx, test_idx, "diagnostic_only", "Random row split is diagnostic only and cannot be headline evidence."))
    rows = []
    for split in splits:
        rows.append(
            {
                "split_family": split.split_family,
                "split_name": split.split_name,
                "fold_id": split.fold_id,
                "train_rows": int(len(split.train_idx)),
                "test_rows": int(len(split.test_idx)),
                "train_cells": int(matrix.loc[split.train_idx, "cell_id"].nunique()),
                "test_cells": int(matrix.loc[split.test_idx, "cell_id"].nunique()),
                "cell_overlap_count": int(len(set(matrix.loc[split.train_idx, "cell_id"].astype(str)) & set(matrix.loc[split.test_idx, "cell_id"].astype(str)))),
                "main_evidence": split.main_evidence,
                "status": PASS,
                "notes": split.notes,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    write_csv(output_path(config, "split_registry"), pd.DataFrame(rows))
    return splits


def model_registry(config: dict[str, Any]) -> pd.DataFrame:
    """Write the N150-compatible model registry."""
    rows: list[dict[str, Any]] = []
    order = [*HEADLINE_MODELS, *DIAGNOSTIC_MODELS]
    for model in order:
        cfg = config["models"].get(model, {})
        role = "headline_n150_compatible" if model in HEADLINE_MODELS else "diagnostic_only"
        rows.append(
            {
                "model": model,
                "registry_order": order.index(model) + 1,
                "comparison_role": role,
                "prior_candidate_baseline": YES if model == "extra_trees" else NO,
                "hyperparameter_grid_status": config["models"].get("hyperparameter_grid_status", "RECONSTRUCTED_COMPATIBLE"),
                "parameters": str(cfg),
                "status": PASS,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    rows.append(
        {
            "model": "dummy_context_mean",
            "registry_order": len(order) + 1,
            "comparison_role": "alias_for_context_mean_not_refit",
            "prior_candidate_baseline": NO,
            "hyperparameter_grid_status": "alias",
            "parameters": "context_mean alias retained for B87E config compatibility",
            "status": PASS,
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )
    out = pd.DataFrame(rows)
    write_csv(output_path(config, "model_registry"), out)
    return out


def make_preprocessor(numeric: list[str], categorical: list[str], scaled: bool) -> ColumnTransformer:
    """Create a dense sklearn preprocessor."""
    transformers: list[tuple[str, Pipeline, list[str]]] = []
    num_steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scaled:
        num_steps.append(("scaler", StandardScaler()))
    if numeric:
        transformers.append(("num", Pipeline(num_steps), numeric))
    if categorical:
        transformers.append(
            (
                "cat",
                Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]),
                categorical,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop", sparse_threshold=0.0)


def make_model_pipeline(model_name: str, config: dict[str, Any], numeric: list[str], categorical: list[str]) -> Pipeline:
    """Create one sklearn model pipeline."""
    seed = int(config["random_state"])
    specs = config["models"]
    if model_name == "ridge":
        estimator = Ridge(alpha=float(specs["ridge"]["alpha"]), solver="lsqr")
        scaled = True
    elif model_name == "elasticnet":
        estimator = ElasticNet(alpha=float(specs["elasticnet"]["alpha"]), l1_ratio=float(specs["elasticnet"]["l1_ratio"]), max_iter=10000, random_state=seed)
        scaled = True
    elif model_name == "random_forest":
        cfg = specs["random_forest"]
        estimator = RandomForestRegressor(n_estimators=int(cfg["n_estimators"]), max_depth=cfg["max_depth"], min_samples_leaf=int(cfg["min_samples_leaf"]), random_state=seed, n_jobs=int(cfg["n_jobs"]))
        scaled = False
    elif model_name == "extra_trees":
        cfg = specs["extra_trees"]
        estimator = ExtraTreesRegressor(n_estimators=int(cfg["n_estimators"]), max_depth=cfg["max_depth"], min_samples_leaf=int(cfg["min_samples_leaf"]), random_state=seed, n_jobs=int(cfg["n_jobs"]))
        scaled = False
    elif model_name == "hist_gradient_boosting":
        cfg = specs["hist_gradient_boosting"]
        estimator = HistGradientBoostingRegressor(max_iter=int(cfg["max_iter"]), learning_rate=float(cfg["learning_rate"]), max_leaf_nodes=int(cfg["max_leaf_nodes"]), random_state=seed)
        scaled = False
    elif model_name == "gradient_boosting":
        cfg = specs["gradient_boosting"]
        estimator = GradientBoostingRegressor(n_estimators=int(cfg["n_estimators"]), learning_rate=float(cfg["learning_rate"]), max_depth=int(cfg["max_depth"]), random_state=seed)
        scaled = False
    else:
        raise ValueError(f"Unsupported model: {model_name}")
    return Pipeline([("prep", make_preprocessor(numeric, categorical, scaled)), ("model", estimator)])


def finite_corr(y_true: np.ndarray, y_pred: np.ndarray, spearman: bool = False) -> float:
    """Compute finite Pearson/Spearman correlation."""
    frame = pd.DataFrame({"true": y_true, "pred": y_pred}).dropna()
    if len(frame) < 2 or frame["true"].nunique() <= 1 or frame["pred"].nunique() <= 1:
        return float("nan")
    left = frame["true"].rank().to_numpy(dtype=float) if spearman else frame["true"].to_numpy(dtype=float)
    right = frame["pred"].rank().to_numpy(dtype=float) if spearman else frame["pred"].to_numpy(dtype=float)
    left = left - float(np.mean(left))
    right = right - float(np.mean(right))
    denom = math.sqrt(float(np.sum(left * left)) * float(np.sum(right * right)))
    return float(np.sum(left * right) / denom) if denom else float("nan")


def metric_row(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Return regression and ranking metric values."""
    abs_err = np.abs(y_pred - y_true)
    sign_true = y_true < 0
    sign_pred = y_pred < 0
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "bias": float(np.mean(y_pred - y_true)),
        "R2": float(r2_score(y_true, y_pred)) if len(np.unique(y_true)) > 1 else float("nan"),
        "median_absolute_error": float(median_absolute_error(y_true, y_pred)),
        "p90_absolute_error": float(np.percentile(abs_err, 90)),
        "Spearman_rank_correlation": finite_corr(y_true, y_pred, spearman=True),
        "Pearson_correlation": finite_corr(y_true, y_pred, spearman=False),
        "sign_agreement_cooling_non_cooling": float(np.mean(sign_true == sign_pred)),
    }


def context_mean_predict(train: pd.DataFrame, test: pd.DataFrame, target: str) -> np.ndarray:
    """Predict train means by forcing day/hour with global fallback."""
    global_mean = float(pd.to_numeric(train[target], errors="coerce").mean())
    grouped = train.assign(_y=pd.to_numeric(train[target], errors="coerce")).groupby(["forcing_day_id", "hour_sgt"])["_y"].mean().to_dict()
    return np.asarray([grouped.get((row["forcing_day_id"], row["hour_sgt"]), global_mean) for _, row in test.iterrows()], dtype=float)


def topk_overlap(y_true: np.ndarray, y_pred: np.ndarray, k: int) -> float:
    """Return overlap among most negative observed/predicted values."""
    if len(y_true) == 0:
        return float("nan")
    kk = max(1, min(k, len(y_true)))
    true_idx = set(np.argsort(y_true)[:kk].tolist())
    pred_idx = set(np.argsort(y_pred)[:kk].tolist())
    return float(len(true_idx & pred_idx) / kk)


def evaluate_topk(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build top-k and rank metric summaries by model/split family."""
    rows: list[dict[str, Any]] = []
    rank_rows: list[dict[str, Any]] = []
    for (model, family), part in predictions.groupby(["model", "split_family"], sort=True):
        y_true = part["y_true"].to_numpy(dtype=float)
        y_pred = part["y_pred"].to_numpy(dtype=float)
        for k in (10, 20, 30):
            rows.append({"model": model, "split_family": family, "metric": f"top{k}_overlap", "value": topk_overlap(y_true, y_pred, k), "rank_direction": "most_negative_delta_is_top", "claim_boundary": CLAIM_BOUNDARY})
        rows.append({"model": model, "split_family": family, "metric": "top_decile_overlap", "value": topk_overlap(y_true, y_pred, max(1, int(math.ceil(len(y_true) * 0.10)))), "rank_direction": "most_negative_delta_is_top", "claim_boundary": CLAIM_BOUNDARY})
        rank_rows.append({"model": model, "split_family": family, "Spearman_rank_correlation": finite_corr(y_true, y_pred, spearman=True), "n_predictions": len(part), "claim_boundary": CLAIM_BOUNDARY})
    return pd.DataFrame(rows), pd.DataFrame(rank_rows)


def run_models(config: dict[str, Any], matrix: pd.DataFrame, schema: pd.DataFrame, splits: list[SplitDef]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Train/evaluate models over configured splits."""
    _, numeric, categorical = selected_features(matrix, schema)
    target = config["primary_target"]
    models = [*HEADLINE_MODELS]
    metrics_rows: list[dict[str, Any]] = []
    pred_rows: list[dict[str, Any]] = []
    for split in splits:
        train = matrix.loc[split.train_idx].copy()
        test = matrix.loc[split.test_idx].copy()
        y_train = pd.to_numeric(train[target], errors="coerce").to_numpy(dtype=float)
        y_test = pd.to_numeric(test[target], errors="coerce").to_numpy(dtype=float)
        for model in models:
            if model == "featureless_mean":
                y_pred = np.full_like(y_test, float(np.mean(y_train)), dtype=float)
                params = "strategy=train_mean"
            elif model == "context_mean":
                y_pred = context_mean_predict(train, test, target)
                params = "groupby=forcing_day_id+hour_sgt; fallback=train_mean"
            else:
                pipeline = make_model_pipeline(model, config, numeric, categorical)
                pipeline.fit(train, y_train)
                y_pred = pipeline.predict(test)
                params = str(config["models"].get(model, {}))
            row = {
                "target": target,
                "model": model,
                "split_family": split.split_family,
                "split_name": split.split_name,
                "fold_id": split.fold_id,
                "main_evidence": split.main_evidence,
                "n_train_rows": len(train),
                "n_test_rows": len(test),
                "n_train_cells": train["cell_id"].nunique(),
                "n_test_cells": test["cell_id"].nunique(),
                "best_params": params,
                "model_registry_role": "headline_n150_compatible" if model in HEADLINE_MODELS else "diagnostic_only",
                "claim_boundary": CLAIM_BOUNDARY,
            }
            row.update(metric_row(y_test, y_pred))
            metrics_rows.append(row)
            for i, idx in enumerate(test.index):
                pred_rows.append(
                    {
                        "row_id": test.loc[idx, "row_id"],
                        "cell_id": test.loc[idx, "cell_id"],
                        "forcing_day_id": test.loc[idx, "forcing_day_id"],
                        "hour_sgt": test.loc[idx, "hour_sgt"],
                        "sample_group": test.loc[idx, "sample_group"],
                        "model": model,
                        "split_family": split.split_family,
                        "split_name": split.split_name,
                        "fold_id": split.fold_id,
                        "main_evidence": split.main_evidence,
                        "y_true": y_test[i],
                        "y_pred": float(y_pred[i]),
                        "residual": float(y_pred[i] - y_test[i]),
                        "abs_error": float(abs(y_pred[i] - y_test[i])),
                        "claim_boundary": CLAIM_BOUNDARY,
                    }
                )
    metrics = pd.DataFrame(metrics_rows)
    predictions = pd.DataFrame(pred_rows)
    group_oof = predictions.loc[predictions["split_family"].eq("group_kfold_cell")].copy()
    holdout = predictions.loc[~predictions["split_family"].eq("group_kfold_cell")].copy()
    write_csv(output_path(config, "model_metrics_by_split"), metrics)
    summary = summarize_metrics(config, metrics)
    write_csv(output_path(config, "model_metrics_summary"), summary)
    write_csv(output_path(config, "predictions_oof"), group_oof)
    write_csv(output_path(config, "predictions_holdout"), holdout)
    topk, rank = evaluate_topk(predictions)
    write_csv(output_path(config, "topk_overlap_by_model"), topk)
    write_csv(output_path(config, "rank_metrics_by_model"), rank)
    return metrics, group_oof, holdout


def summarize_metrics(config: dict[str, Any], metrics: pd.DataFrame) -> pd.DataFrame:
    """Summarize metrics by model and split family."""
    metric_cols = ["MAE", "RMSE", "bias", "R2", "median_absolute_error", "p90_absolute_error", "Spearman_rank_correlation", "sign_agreement_cooling_non_cooling"]
    rows: list[dict[str, Any]] = []
    for (model, family), part in metrics.groupby(["model", "split_family"], sort=True):
        row = {"model": model, "split_family": family, "n_folds": len(part), "n_test_rows": int(part["n_test_rows"].sum()), "model_registry_role": "headline_n150_compatible" if model in HEADLINE_MODELS else "diagnostic_only", "claim_boundary": CLAIM_BOUNDARY}
        for col in metric_cols:
            row[col] = float(pd.to_numeric(part[col], errors="coerce").mean())
        rows.append(row)
    return pd.DataFrame(rows)


def error_by_strata(config: dict[str, Any], matrix: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute OOF errors by available strata."""
    meta_cols = ["row_id", "primary_role", "spatial_bin", "typology", "typology_label", "source_closeout_status"]
    join_cols = [c for c in meta_cols if c in matrix.columns]
    merged = predictions.merge(matrix[join_cols].drop_duplicates("row_id"), on="row_id", how="left") if join_cols else predictions.copy()
    strata_cols = [c for c in ["sample_group", "forcing_day_id", "hour_sgt", "primary_role", "spatial_bin", "typology", "typology_label", "source_closeout_status"] if c in merged.columns]
    numeric_strata = [c for c in ["water_edge_contact_frac", "overhead_total_area_m2", "tree_near_tall_building_frac", "neighbourhood_overhead_frac"] if c in matrix.columns]
    for col in numeric_strata:
        values = pd.to_numeric(matrix[col], errors="coerce")
        if values.notna().sum() > 0 and values.nunique(dropna=True) > 2:
            bins = pd.qcut(values.rank(method="first"), q=3, labels=["low", "mid", "high"])
            merged = merged.merge(pd.DataFrame({"row_id": matrix["row_id"], f"{col}_tertile": bins.astype(str)}), on="row_id", how="left")
            strata_cols.append(f"{col}_tertile")
    rows: list[dict[str, Any]] = []
    for model, model_part in merged.groupby("model", sort=True):
        for strata in strata_cols:
            for value, part in model_part.groupby(strata, dropna=False, sort=True):
                if len(part) < 5:
                    continue
                rows.append(
                    {
                        "model": model,
                        "strata_column": strata,
                        "strata_value": value,
                        "n": len(part),
                        "MAE": float(part["abs_error"].mean()),
                        "RMSE": float(math.sqrt(float(np.mean(np.square(part["residual"].astype(float)))))),
                        "bias": float(part["residual"].astype(float).mean()),
                        "claim_boundary": CLAIM_BOUNDARY,
                    }
                )
    out = pd.DataFrame(rows)
    write_csv(output_path(config, "error_by_strata"), out)
    return out


def feature_importance(config: dict[str, Any], matrix: pd.DataFrame, schema: pd.DataFrame) -> pd.DataFrame:
    """Write diagnostic non-causal feature importance from extra_trees."""
    _, numeric, categorical = selected_features(matrix, schema)
    target = config["primary_target"]
    pipeline = make_model_pipeline("extra_trees", config, numeric, categorical)
    pipeline.fit(matrix, pd.to_numeric(matrix[target], errors="coerce").to_numpy(dtype=float))
    names: list[str] = []
    if numeric:
        names.extend(numeric)
    if categorical:
        encoder = pipeline.named_steps["prep"].named_transformers_["cat"].named_steps["onehot"]
        names.extend(encoder.get_feature_names_out(categorical).tolist())
    importances = pipeline.named_steps["model"].feature_importances_
    rows = [
        {
            "model": "extra_trees",
            "feature_name": names[i] if i < len(names) else f"feature_{i}",
            "importance": float(value),
            "importance_type": "impurity_diagnostic",
            "caveat": "non-causal; correlated features; compact proxies; small N300; diagnostic only",
            "claim_boundary": CLAIM_BOUNDARY,
        }
        for i, value in enumerate(importances)
    ]
    out = pd.DataFrame(rows).sort_values("importance", ascending=False).head(80)
    write_csv(output_path(config, "feature_importance_diagnostic"), out)
    return out


def promotion_matrix(config: dict[str, Any], summary: pd.DataFrame, rank: pd.DataFrame, leakage: pd.DataFrame) -> tuple[pd.DataFrame, str, str, str]:
    """Decide candidate/promotion status."""
    for column in ["MAE", "RMSE", "Spearman_rank_correlation", "R2", "bias"]:
        if column in summary.columns:
            summary[column] = pd.to_numeric(summary[column], errors="coerce")
    if "Spearman_rank_correlation" in rank.columns:
        rank["Spearman_rank_correlation"] = pd.to_numeric(rank["Spearman_rank_correlation"], errors="coerce")
    leakage_ok = leakage.empty or not leakage["leakage_status"].astype(str).eq(FAIL).any()
    group = summary.loc[summary["split_family"].eq("group_kfold_cell")].copy()
    oldnew = summary.loc[summary["split_family"].eq("old_to_new_generalization")].copy()
    spatial = summary.loc[summary["split_family"].eq("spatial_holdout")].copy()
    context_mae = float(group.loc[group["model"].eq("context_mean"), "MAE"].iloc[0]) if not group.loc[group["model"].eq("context_mean")].empty else math.inf
    extra_group = float(group.loc[group["model"].eq("extra_trees"), "MAE"].iloc[0]) if not group.loc[group["model"].eq("extra_trees")].empty else math.inf
    extra_oldnew = float(oldnew.loc[oldnew["model"].eq("extra_trees"), "MAE"].iloc[0]) if not oldnew.loc[oldnew["model"].eq("extra_trees")].empty else math.inf
    context_oldnew = float(oldnew.loc[oldnew["model"].eq("context_mean"), "MAE"].iloc[0]) if not oldnew.loc[oldnew["model"].eq("context_mean")].empty else math.inf
    non_baseline = group.loc[~group["model"].isin(["featureless_mean", "context_mean", "gradient_boosting"])].sort_values("MAE")
    best_model = str(non_baseline.iloc[0]["model"]) if not non_baseline.empty else ""
    best_group_mae = float(non_baseline.iloc[0]["MAE"]) if not non_baseline.empty else math.inf
    topk = read_csv(output_path(config, "topk_overlap_by_model"), dtype=str) if output_path(config, "topk_overlap_by_model").exists() else pd.DataFrame()
    top30 = pd.to_numeric(topk.loc[(topk["model"].eq(best_model)) & (topk["split_family"].eq("group_kfold_cell")) & (topk["metric"].eq("top30_overlap")), "value"], errors="coerce")
    best_rank = pd.to_numeric(rank.loc[(rank["model"].eq(best_model)) & (rank["split_family"].eq("group_kfold_cell")), "Spearman_rank_correlation"], errors="coerce")
    best_oldnew = float(oldnew.loc[oldnew["model"].eq(best_model), "MAE"].iloc[0]) if not oldnew.loc[oldnew["model"].eq(best_model)].empty else math.inf
    best_spatial = float(spatial.loc[spatial["model"].eq(best_model), "MAE"].mean()) if not spatial.loc[spatial["model"].eq(best_model)].empty else math.inf
    extra_spatial = float(spatial.loc[spatial["model"].eq("extra_trees"), "MAE"].mean()) if not spatial.loc[spatial["model"].eq("extra_trees")].empty else math.inf
    beats_context = best_group_mae < context_mae
    beats_extra = best_group_mae < extra_group and best_oldnew < extra_oldnew and best_spatial <= extra_spatial
    rank_ok = (not best_rank.empty) and float(best_rank.iloc[0]) >= float(config["promotion_gate"]["group_spearman_min"])
    topk_ok = (not top30.empty) and float(top30.iloc[0]) >= float(config["promotion_gate"]["top30_overlap_min"])
    oldnew_ok = best_oldnew <= context_oldnew * float(config["promotion_gate"]["old_to_new_max_context_mae_ratio"])
    extra_remains = leakage_ok and extra_group < context_mae and extra_oldnew <= context_oldnew * float(config["promotion_gate"]["old_to_new_max_context_mae_ratio"])
    promotable = leakage_ok and beats_context and beats_extra and rank_ok and topk_ok and oldnew_ok
    if promotable:
        status = B87E_CANDIDATE
        decision = f"{best_model}_candidate_surrogate"
        next_lane = "B87F_surrogate_patch_then_separate_AOI_preflight_review"
    elif extra_remains:
        status = B87E_NO_PROMOTION
        decision = "B87E_EXTRA_TREES_REMAINS_CANDIDATE"
        next_lane = "B87F_surrogate_patch_stronger_features_before_any_AOI_preflight"
    else:
        status = B87E_NO_PROMOTION
        decision = "B87E_SURROGATE_NO_PROMOTION_YET"
        next_lane = "B87F_patch_stronger_features_or_external_vector_acquisition"
    rows = [
        {"gate": "no_leakage_findings", "observed": leakage_ok, "required": True, "status": PASS if leakage_ok else FAIL, "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "best_group_mae_beats_context_mean", "observed": beats_context, "required": True, "status": PASS if beats_context else FAIL, "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "best_model_supersedes_extra_trees", "observed": beats_extra, "required": True, "status": PASS if beats_extra else WARN, "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "old_to_new_generalization_not_bad", "observed": oldnew_ok, "required": True, "status": PASS if oldnew_ok else WARN, "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "rank_spearman_min", "observed": format_float(best_rank.iloc[0] if not best_rank.empty else math.nan), "required": config["promotion_gate"]["group_spearman_min"], "status": PASS if rank_ok else WARN, "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "top30_overlap_min", "observed": format_float(top30.iloc[0] if not top30.empty else math.nan), "required": config["promotion_gate"]["top30_overlap_min"], "status": PASS if topk_ok else WARN, "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "promotion_decision", "observed": decision, "required": "candidate only if all gates pass", "status": status, "claim_boundary": CLAIM_BOUNDARY},
    ]
    out = pd.DataFrame(rows)
    write_csv(output_path(config, "model_promotion_matrix"), out)
    return out, status, decision, next_lane


def write_reports(config: dict[str, Any], result: B87EResult) -> None:
    """Write B87E status, report, CN note, and next prompt."""
    summary = read_csv(output_path(config, "model_metrics_summary"), dtype=str)
    target = read_csv(output_path(config, "target_summary"), dtype=str)
    status_lines = [
        "# B87E Status",
        "",
        f"Generated: {now_stamp()}",
        "",
        f"Status: `{result.status}`",
        "",
        "## Key Results",
        "",
        f"- Feature matrix shape: `{result.feature_matrix_shape[0]} x {result.feature_matrix_shape[1]}`",
        f"- Main/supporting split count: `{result.main_split_count}`",
        f"- Best GroupKFold model by MAE: `{result.best_group_model}` (`{format_float(result.best_group_mae)}`)",
        f"- Best old-to-new MAE model: `{result.best_old_to_new_model}` (`{format_float(result.best_old_to_new_mae)}`)",
        f"- Best GroupKFold rank Spearman: `{format_float(result.best_rank_spearman)}`",
        f"- Promotion decision: `{result.promotion_decision}`",
        f"- Recommended next lane: `{result.recommended_next_lane}`",
        f"- Blockers: `{', '.join(result.blockers) if result.blockers else 'none'}`",
        "",
        "## Claim Boundary",
        "",
        CLAIM_BOUNDARY,
    ]
    output_path(config, "status").write_text("\n".join(status_lines) + "\n", encoding="utf-8")

    report_lines = [
        "# B87E N300 Surrogate Benchmark Report",
        "",
        f"Generated: {now_stamp()}",
        "",
        f"Status: `{result.status}`",
        "",
        "## 1. Task Definition",
        "",
        "This benchmark tests surrogate models as emulators of SOLWEIG-derived `delta_tmrt_p90_c` and companion delta Tmrt labels. It is not WBGT calibration and not observed truth.",
        "",
        "## 2. N300 Label Table Summary",
        "",
        f"- Rows/cells: `{result.feature_matrix_shape[0]}` rows, `{config['expected_cells']}` expected cells.",
        f"- Primary target: `{config['primary_target']}` (`overhead_as_canopy - base`).",
        "",
        "## 3. Feature Source Summary",
        "",
        "Static compact cell/context features were joined from the configured B86/B87 candidate feature sources. Coordinates, label source, protocol, sample group, cell ID, run/path/status columns, and target/Tmrt columns are excluded from the main feature set.",
        "",
        "## 4. Feature Leakage Audit",
        "",
        "See `b87e_feature_leakage_audit.csv`. Main models do not use label source, protocol ID, sample group, direct cell ID one-hot, target columns, base/overhead Tmrt columns, delta columns, run IDs, raster paths, output dirs, or status/error fields.",
        "",
        "## 5. Validation Split Registry",
        "",
        "Main/supporting evidence includes GroupKFold by `cell_id`, old-to-new generalization, spatial/typology/role holdouts where available, and context holdouts. Random split is diagnostic only.",
        "",
        "## 6. Model Registry",
        "",
        "The headline registry follows the N150-compatible order: featureless mean, context mean, ridge, elasticnet, random forest, extra trees, and hist gradient boosting. `extra_trees` is reported as the prior N150 model-card candidate baseline.",
        "",
        "## 7. Metrics By Split",
        "",
        f"Best GroupKFold model by MAE: `{result.best_group_model}` with MAE `{format_float(result.best_group_mae)}`. Full metrics are in `b87e_model_metrics_by_split.csv` and summaries in `b87e_model_metrics_summary.csv`.",
        "",
        "## 8. Old-To-New And New-To-Old",
        "",
        f"Best old-to-new MAE model: `{result.best_old_to_new_model}` with MAE `{format_float(result.best_old_to_new_mae)}`. Reverse transfer is diagnostic only.",
        "",
        "## 9. Error By Strata",
        "",
        "See `b87e_error_by_strata.csv` for sample group, forcing day, hour, typology/spatial/role, and available water/tree/overhead proxy strata.",
        "",
        "## 10. Ranking / Top-K Performance",
        "",
        f"Best GroupKFold rank Spearman observed among headline models: `{format_float(result.best_rank_spearman)}`. Top-k overlaps are diagnostic ranking evidence, not a hazard/risk planning claim.",
        "",
        "## 11. Promotion Decision",
        "",
        f"Promotion decision: `{result.promotion_decision}`. No AOI/B9 inference is authorized in this lane.",
        "",
        "## 12. Next Lane Recommendation",
        "",
        f"Recommended next lane: `{result.recommended_next_lane}`.",
        "",
        "## 13. Claim Boundaries",
        "",
        "- No AOI/B9 output.",
        "- No WBGT conversion.",
        "- No risk/hazard map.",
        "- No causal feature-importance claim.",
        "- No observed truth claim.",
    ]
    output_path(config, "report").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    cn_lines = [
        "# OpenHeat System B B87E N300 代理模型基准说明",
        "",
        f"生成时间：{now_stamp()}",
        "",
        f"状态：`{result.status}`",
        "",
        "本阶段评估的是 SOLWEIG 派生 `delta_tmrt_p90_c` 的代理模型/仿真器，不是观测 WBGT 校准，也不是全域 AOI/B9 推理。",
        "",
        "## 验证",
        "",
        "主证据包含按 `cell_id` 分组的 GroupKFold、old-to-new 泛化、空间/类型/角色 holdout（如可用）和 context holdout。随机切分只作为诊断，不作为 headline 证据。",
        "",
        "## 模型",
        "",
        "headline 模型注册表沿用 N150 兼容顺序：featureless mean、context mean、ridge、elasticnet、random forest、extra trees、hist gradient boosting。`extra_trees` 作为既有 N150 候选基线单独报告。",
        "",
        "## 决策",
        "",
        f"推广决策：`{result.promotion_decision}`。推荐下一阶段：`{result.recommended_next_lane}`。",
        "",
        "## 边界",
        "",
        "不生成 AOI/B9 输出，不做 WBGT 转换，不生成 hazard/risk/exposure/vulnerability 图层，不声称观测真值，不把特征重要性解释为因果证据。",
    ]
    output_path(config, "canonical_note_cn").write_text("\n".join(cn_lines) + "\n", encoding="utf-8")

    prompt_lines = [
        "# B87F Next-Lane Prompt",
        "",
        f"B87E status: {result.status}",
        f"Promotion decision: {result.promotion_decision}",
        "",
        "Recommended lane:",
        result.recommended_next_lane,
        "",
        "Do not proceed to AOI/B9 inference unless a separate lane explicitly approves it after reviewing B87E metrics, leakage audit, and model card.",
    ]
    output_path(config, "codex_prompt_next_lane").write_text("\n".join(prompt_lines) + "\n", encoding="utf-8")


def run_b87e(config_path: Path = DEFAULT_CONFIG) -> B87EResult:
    """Run the full B87E surrogate benchmark."""
    config = read_config(repo_path(config_path))
    ensure_output_dirs(config)
    input_inventory(config)
    if not label_qa_passed(config):
        blockers = [B87E_BLOCKED_LABEL_QA]
        write_csv(output_path(config, "blocker_register"), pd.DataFrame([{"blocker_id": blockers[0], "status": "ACTIVE", "notes": "B87D status is not PASS.", "claim_boundary": CLAIM_BOUNDARY}]))
        result = B87EResult(B87E_BLOCKED_LABEL_QA, (0, 0), 0, "", math.nan, "", math.nan, math.nan, "blocked", blockers, "return_to_B87D_label_QA")
        write_reports(config, result)
        return result
    matrix, schema = build_feature_matrix(config)
    leakage = leakage_audit(config, matrix, schema)
    feature_fail = matrix["cell_id"].nunique() != int(config["expected_cells"]) or len(matrix) != int(config["expected_rows"]) or leakage["leakage_status"].astype(str).eq(FAIL).any()
    if feature_fail:
        blockers = [B87E_BLOCKED_FEATURE_QA]
    else:
        blockers = []
    splits = build_splits(config, matrix)
    main_split_count = sum(1 for split in splits if split.main_evidence != "diagnostic_only")
    if not splits or not any(split.split_family == "group_kfold_cell" for split in splits):
        blockers.append(B87E_BLOCKED_SPLIT_QA)
    model_registry(config)
    metrics, group_oof, holdout = run_models(config, matrix, schema, splits)
    error_by_strata(config, matrix, group_oof)
    feature_importance(config, matrix, schema)
    summary = read_csv(output_path(config, "model_metrics_summary"), dtype=str)
    rank = read_csv(output_path(config, "rank_metrics_by_model"), dtype=str)
    promo, status, decision, next_lane = promotion_matrix(config, summary, rank, leakage)
    if blockers:
        status = blockers[0]
        decision = "blocked"
        next_lane = "resolve_B87E_QA_blockers"
    blocker_frame = pd.DataFrame([{"blocker_id": b, "status": "ACTIVE", "notes": "See B87E QA artifacts.", "claim_boundary": CLAIM_BOUNDARY} for b in blockers])
    if blocker_frame.empty:
        blocker_frame = pd.DataFrame([{"blocker_id": "none", "status": PASS, "notes": "No B87E blockers.", "claim_boundary": CLAIM_BOUNDARY}])
    write_csv(output_path(config, "blocker_register"), blocker_frame)
    write_csv(
        output_path(config, "next_lane_decision_matrix"),
        pd.DataFrame([{"next_lane": next_lane, "decision": "RECOMMENDED", "b87e_status": status, "promotion_decision": decision, "claim_boundary": CLAIM_BOUNDARY}]),
    )
    group = summary.loc[summary["split_family"].eq("group_kfold_cell") & ~summary["model"].isin(["featureless_mean", "context_mean", "gradient_boosting"])].copy()
    group["MAE"] = pd.to_numeric(group["MAE"], errors="coerce")
    best_group = group.sort_values("MAE").iloc[0]
    oldnew = summary.loc[summary["split_family"].eq("old_to_new_generalization") & ~summary["model"].isin(["featureless_mean", "context_mean", "gradient_boosting"])].copy()
    oldnew["MAE"] = pd.to_numeric(oldnew["MAE"], errors="coerce")
    best_oldnew = oldnew.sort_values("MAE").iloc[0] if not oldnew.empty else best_group
    rank_group = rank.loc[rank["split_family"].eq("group_kfold_cell") & rank["model"].isin(HEADLINE_MODELS)].copy()
    rank_group["Spearman_rank_correlation"] = pd.to_numeric(rank_group["Spearman_rank_correlation"], errors="coerce")
    best_rank = float(rank_group["Spearman_rank_correlation"].max()) if not rank_group.empty else math.nan
    result = B87EResult(
        status=status,
        feature_matrix_shape=matrix.shape,
        main_split_count=main_split_count,
        best_group_model=str(best_group["model"]),
        best_group_mae=float(best_group["MAE"]),
        best_old_to_new_model=str(best_oldnew["model"]),
        best_old_to_new_mae=float(best_oldnew["MAE"]),
        best_rank_spearman=best_rank,
        promotion_decision=decision,
        blockers=blockers,
        recommended_next_lane=next_lane,
    )
    write_reports(config, result)
    return result


def main_runner() -> int:
    """CLI for full B87E benchmark."""
    parser = argparse.ArgumentParser(
        description=(
            "Run B87E N300 surrogate benchmark. Inputs, outputs, config path, "
            "saved metrics, and claim boundaries are declared in the module "
            "docstring. This does not run QGIS/SOLWEIG, read/write rasters, "
            "or create AOI/B9/WBGT/risk outputs."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B87E YAML config path.")
    args = parser.parse_args()
    try:
        result = run_b87e(args.config)
    except Exception as exc:
        print(f"Status: {FAILED}")
        print(f"Error: {exc}")
        return 1
    print(f"Status: {result.status}")
    print(f"Feature matrix shape: {result.feature_matrix_shape[0]} x {result.feature_matrix_shape[1]}")
    print(f"Main split count: {result.main_split_count}")
    print(f"Best model by GroupKFold MAE: {result.best_group_model} ({format_float(result.best_group_mae)})")
    print(f"Best model old-to-new MAE: {result.best_old_to_new_model} ({format_float(result.best_old_to_new_mae)})")
    print(f"Best model rank Spearman: {format_float(result.best_rank_spearman)}")
    print(f"Promotion decision: {result.promotion_decision}")
    print(f"Blockers: {', '.join(result.blockers) if result.blockers else 'none'}")
    print(f"Recommended next lane: {result.recommended_next_lane}")
    print("QGIS/SOLWEIG executed by Codex: no")
    print("Raster outputs read/written: no")
    return 0 if result.status in {B87E_CANDIDATE, B87E_NO_PROMOTION} else 2


def wrapper_cli(function_name: str) -> int:
    """Run one B87E step for thin wrapper scripts."""
    parser = argparse.ArgumentParser(
        description=(
            f"Run B87E step {function_name}. Inputs, outputs, config path, "
            "saved metrics, and claim boundaries are declared in "
            "scripts/v12_b87e_common.py."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B87E YAML config path.")
    args = parser.parse_args()
    config = read_config(repo_path(args.config))
    ensure_output_dirs(config)
    if function_name == "feature_source_inventory":
        labels = read_csv(repo_path(config["n300_label_path"]), dtype=str)
        out = feature_source_inventory(config, set(labels["cell_id"].astype(str)))
    elif function_name == "feature_matrix_builder":
        out, _ = build_feature_matrix(config)
    elif function_name == "feature_leakage_audit":
        matrix = read_csv(output_path(config, "feature_matrix"), dtype=str)
        schema = read_csv(output_path(config, "feature_schema"), dtype=str)
        out = leakage_audit(config, matrix, schema)
    elif function_name == "split_registry":
        matrix = read_csv(output_path(config, "feature_matrix"), dtype=str)
        out = pd.DataFrame([split.__dict__ for split in build_splits(config, matrix)])
    elif function_name == "model_registry":
        out = model_registry(config)
    elif function_name in {"train_surrogates", "evaluate_surrogates", "error_strata", "model_card"}:
        result = run_b87e(args.config)
        out = pd.DataFrame([{"status": result.status}])
    else:
        raise ValueError(function_name)
    print(f"Status: {PASS}")
    print(f"Step: {function_name}")
    print(f"Rows: {len(out)}")
    return 0
