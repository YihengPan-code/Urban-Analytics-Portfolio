"""Prepare the B8.0 System B surrogate-ready dataset audit.

Inputs:
    Explicit paths from configs/v12/systemb_surrogate_b8_config.yaml:
    B7 N150 label tables, v10 cell feature tables, and optional reference /
    typology metadata.

Outputs:
    outputs/v12_surrogate/b8_dataset_audit/surrogate_label_feature_matrix.csv
    outputs/v12_surrogate/b8_dataset_audit/feature_schema.csv
    outputs/v12_surrogate/b8_dataset_audit/feature_missingness.csv
    outputs/v12_surrogate/b8_dataset_audit/target_distribution_summary.csv
    outputs/v12_surrogate/b8_dataset_audit/leakage_check_report.md
    outputs/v12_surrogate/b8_dataset_audit/b8_dataset_audit_report.md

Saved metrics:
    Input inventory, row/cell/scenario/hour checks, target/reference version
    checks, missing label columns, selected non-leaky feature inventory,
    missingness and constant-column diagnostics, leakage exclusions, and
    PASS/BLOCKED/FAILED status for B8.0.

This script does not train models, does not create AOI-wide maps, does not
compute local WBGT, and does not create hazard_score or risk_score outputs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_surrogate_b8_config.yaml"


@dataclass(frozen=True)
class AuditResult:
    status: str
    row_count: int
    unique_cells: int
    scenario_values: list[str]
    hour_values: list[int]
    selected_feature_count: int
    excluded_nonphysical_count: int
    excluded_metadata_count: int
    leakage_excluded_count: int
    report_path: Path


def repo_path(value: str | Path) -> Path:
    """Resolve a config path relative to the OpenHeat project directory."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def parse_scalar(value: str) -> Any:
    """Parse a small YAML scalar without pulling in a runtime dependency."""
    stripped = value.strip()
    if stripped in {"true", "True"}:
        return True
    if stripped in {"false", "False"}:
        return False
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        return stripped.strip("\"'")


def read_simple_yaml(path: Path) -> dict[str, Any]:
    """Read the simple nested YAML shape used by the B8 config."""
    try:
        import yaml  # type: ignore

        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except ImportError:
        pass

    lines = [
        line.rstrip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for line in lines:
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if text.startswith("- "):
            item = text[2:].strip()
            if not isinstance(parent, list):
                raise ValueError(f"Unsupported YAML list placement: {line}")
            if item.startswith("[") and item.endswith("]"):
                parent.append([parse_scalar(part) for part in item[1:-1].split(",")])
            else:
                parent.append(parse_scalar(item))
            continue
        key, _, raw_value = text.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            parent[key] = parse_scalar(raw_value)
            continue
        next_container: Any = []
        for future in lines[lines.index(line) + 1 :]:
            future_indent = len(future) - len(future.lstrip(" "))
            future_text = future.strip()
            if future_indent <= indent:
                break
            next_container = [] if future_text.startswith("- ") else {}
            break
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def read_config(path: Path) -> dict[str, Any]:
    """Load and normalize config paths."""
    config = read_simple_yaml(path)
    return config


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV and preserve cell IDs as strings."""
    return pd.read_csv(path, dtype={"cell_id": "string"})


def input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Return required/optional file presence and sizes."""
    rows: list[dict[str, Any]] = []
    for requirement, mapping in config["inputs"].items():
        for name, rel_path in mapping.items():
            path = repo_path(rel_path)
            rows.append(
                {
                    "input_name": name,
                    "requirement": requirement,
                    "path": str(path.relative_to(ROOT)),
                    "found": path.exists(),
                    "size_bytes": path.stat().st_size if path.exists() else np.nan,
                }
            )
    return pd.DataFrame(rows)


def normalize_label_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize B7 labels to the B8 row identity."""
    out = df.copy()
    if "hour_sgt" not in out.columns and "hour" in out.columns:
        out["hour_sgt"] = out["hour"]
    out["cell_id"] = out["cell_id"].astype(str)
    out["scenario"] = out["scenario"].astype(str)
    out["hour_sgt"] = pd.to_numeric(out["hour_sgt"], errors="coerce").astype("Int64")
    out["row_id"] = out["cell_id"] + "|" + out["scenario"] + "|" + out["hour_sgt"].astype(str)
    return out


def load_feature_table(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    """Combine required cell feature tables without duplicating shared columns."""
    source_order = [
        ("overhead_features", config["inputs"]["required"]["overhead_features"]),
        ("umep_features", config["inputs"]["required"]["umep_features"]),
        ("morphology_features", config["inputs"]["required"]["morphology_features"]),
    ]
    combined: pd.DataFrame | None = None
    source_guess: dict[str, str] = {}
    for source_name, rel_path in source_order:
        path = repo_path(rel_path)
        df = read_csv(path)
        df["cell_id"] = df["cell_id"].astype(str)
        if combined is None:
            combined = df.copy()
            for column in combined.columns:
                source_guess[column] = str(path.relative_to(ROOT))
            continue
        add_columns = [column for column in df.columns if column not in combined.columns]
        if add_columns:
            combined = combined.merge(df[["cell_id", *add_columns]], on="cell_id", how="left")
            for column in add_columns:
                source_guess[column] = str(path.relative_to(ROOT))
    if combined is None:
        raise ValueError("No feature tables were loaded.")
    return combined, source_guess


def leakage_like(column: str, tokens: list[str]) -> bool:
    """Return whether a name is target/rank/reference/SOLWEIG-like leakage."""
    lower = column.lower()
    return any(token.lower() in lower for token in tokens)


def metadata_like(column: str, config: dict[str, Any]) -> bool:
    """Return whether a column name is provenance/text metadata."""
    lower = column.lower()
    suffixes = [str(value).lower() for value in config.get("metadata_name_suffixes", [])]
    prefixes = [str(value).lower() for value in config.get("metadata_name_prefixes", [])]
    if any(lower.endswith(suffix) for suffix in suffixes):
        return True
    if any(lower.startswith(prefix) for prefix in prefixes):
        return True
    return lower in {"source", "source_run_id", "run_id", "land_use_raw"}


def physical_core_like(column: str, config: dict[str, Any]) -> bool:
    """Return whether a column belongs to the B8.2 physical-core tier."""
    lower = column.lower()
    return any(str(token).lower() in lower for token in config.get("physical_core_name_tokens", []))


def role_for_column(
    column: str,
    series: pd.Series,
    config: dict[str, Any],
    primary: str,
    secondary: str,
    label_companions: set[str],
    metadata: set[str],
    id_columns: set[str],
) -> tuple[str, str, str]:
    """Assign schema role, B8.2 predictor tier, and notes."""
    non_null = int(series.notna().sum())
    unique_non_null = int(series.dropna().nunique())
    lower = column.lower()
    target_contract = set(config.get("target_contract_columns", []))
    excluded_nonphysical = set(config.get("excluded_nonphysical_columns", []))
    spatial_diagnostic = set(config.get("spatial_diagnostic_columns", []))
    if column in id_columns:
        return "id", "excluded_metadata", "row/cell identity; not a model feature"
    if column == primary:
        return "target", "excluded_metadata", "primary physical surrogate target"
    if column == secondary:
        return "target", "excluded_metadata", "secondary physical surrogate target"
    if column in label_companions:
        return "companion_label", "excluded_metadata", "retained label/diagnostic; not a model feature"
    if column in target_contract:
        return "non_predictor_metadata", "excluded_metadata", "target-contract/modifier column excluded from B8.2 predictors"
    if leakage_like(column, config["leakage_name_tokens"]):
        return "forbidden_leakage", "excluded_metadata", "target-, rank-, reference-, or SOLWEIG-like column excluded from selected features"
    if column in metadata:
        return "non_predictor_metadata", "excluded_metadata", "metadata retained for audit/splits; excluded from B8.2 predictors"
    if column in excluded_nonphysical:
        return "non_predictor_metadata", "excluded_nonphysical", "exposure/vulnerability/risk/social field excluded from physical surrogate predictors"
    if column in spatial_diagnostic:
        return "non_predictor_metadata", "spatial_diagnostic", "spatial diagnostic coordinate; may be used only outside headline physical surrogate"
    if metadata_like(column, config):
        return "non_predictor_metadata", "excluded_metadata", "source/version/note/name/method/interpretation or high-cardinality text metadata excluded"
    if "source" in lower or "provenance" in lower:
        return "non_predictor_metadata", "excluded_metadata", "source/provenance field excluded from B8.2 predictors"
    if non_null == 0 or unique_non_null <= 1:
        return "non_predictor_metadata", "excluded_metadata", "constant or all-NaN column excluded from B8.2 predictors"
    if physical_core_like(column, config):
        return "feature", "physical_core", "eligible B8.2 physical-core predictor"
    return "non_predictor_metadata", "excluded_metadata", "not in B8.2 physical-core predictor tier; excluded from headline predictors"


def classify_columns(
    matrix: pd.DataFrame,
    config: dict[str, Any],
    source_guess: dict[str, str],
) -> pd.DataFrame:
    """Build feature_schema.csv with roles and leakage notes."""
    primary = config["primary_target"]
    secondary = config["secondary_target"]
    retained = config["retained_modifier"]
    required_companions = set(config["companion_labels"])
    label_companions = required_companions | {retained}
    metadata = {
        "scenario",
        "hour",
        "hour_sgt",
        "source",
        "run_id",
        "source_run_id",
        "selection_status",
        "reuse_existing_n24_label",
        "n_pixels",
        "valid_pixel_count",
    }
    id_columns = {"row_id", "cell_id"}
    tokens = config["leakage_name_tokens"]
    rows: list[dict[str, Any]] = []
    for column in matrix.columns:
        role, predictor_tier, notes = role_for_column(
            column,
            matrix[column],
            config,
            primary,
            secondary,
            label_companions,
            metadata,
            id_columns,
        )
        non_null = int(matrix[column].notna().sum())
        rows.append(
            {
                "column_name": column,
                "role": role,
                "predictor_tier": predictor_tier,
                "dtype": str(matrix[column].dtype),
                "non_null_count": non_null,
                "missing_fraction": float(1 - non_null / len(matrix)) if len(matrix) else np.nan,
                "source_file_guess": source_guess.get(column, "outputs/v12_solweig_n150_execution/n150_modifier_targets_b5.csv"),
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def missingness_table(matrix: pd.DataFrame, schema: pd.DataFrame) -> pd.DataFrame:
    """Summarize selected feature missingness and constant columns."""
    feature_columns = schema.loc[schema["role"] == "feature", "column_name"].tolist()
    rows: list[dict[str, Any]] = []
    for column in feature_columns:
        series = matrix[column]
        non_null = int(series.notna().sum())
        unique_non_null = int(series.dropna().nunique())
        rows.append(
            {
                "column_name": column,
                "dtype": str(series.dtype),
                "non_null_count": non_null,
                "missing_fraction": float(1 - non_null / len(matrix)) if len(matrix) else np.nan,
                "unique_non_null_count": unique_non_null,
                "is_all_nan": non_null == 0,
                "is_constant": unique_non_null <= 1,
                "missing_gt_20pct": (1 - non_null / len(matrix)) > 0.20 if len(matrix) else False,
                "missing_gt_50pct": (1 - non_null / len(matrix)) > 0.50 if len(matrix) else False,
                "missing_gt_80pct": (1 - non_null / len(matrix)) > 0.80 if len(matrix) else False,
            }
        )
    return pd.DataFrame(rows).sort_values(["missing_fraction", "column_name"], ascending=[False, True])


def summarize_targets(matrix: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Summarize target and companion distributions overall and by split keys."""
    target_columns = [
        config["primary_target"],
        config["secondary_target"],
        config["retained_modifier"],
        *config["companion_labels"],
    ]
    target_columns = [column for column in target_columns if column in matrix.columns]
    group_specs: list[tuple[str, list[str]]] = [
        ("overall", []),
        ("hour_sgt", ["hour_sgt"]),
        ("scenario", ["scenario"]),
        ("hour_sgt_x_scenario", ["hour_sgt", "scenario"]),
    ]
    rows: list[dict[str, Any]] = []
    for group_type, group_cols in group_specs:
        grouped = [((), matrix)] if not group_cols else matrix.groupby(group_cols, dropna=False)
        for key, part in grouped:
            if not isinstance(key, tuple):
                key = (key,)
            group_key = "overall" if not group_cols else "|".join(str(value) for value in key)
            for column in target_columns:
                values = pd.to_numeric(part[column], errors="coerce").dropna()
                quantiles = values.quantile([0.05, 0.25, 0.5, 0.75, 0.95]) if len(values) else pd.Series(dtype=float)
                rows.append(
                    {
                        "group_type": group_type,
                        "group_key": group_key,
                        "target_column": column,
                        "n": int(values.count()),
                        "mean": float(values.mean()) if len(values) else np.nan,
                        "std": float(values.std(ddof=1)) if len(values) > 1 else np.nan,
                        "min": float(values.min()) if len(values) else np.nan,
                        "p05": float(quantiles.loc[0.05]) if len(values) else np.nan,
                        "p25": float(quantiles.loc[0.25]) if len(values) else np.nan,
                        "median": float(quantiles.loc[0.5]) if len(values) else np.nan,
                        "p75": float(quantiles.loc[0.75]) if len(values) else np.nan,
                        "p95": float(quantiles.loc[0.95]) if len(values) else np.nan,
                        "max": float(values.max()) if len(values) else np.nan,
                    }
                )
    return pd.DataFrame(rows)


def markdown_list(values: list[Any]) -> str:
    """Format a short markdown list inline."""
    return ", ".join(str(value) for value in values) if values else "(none)"


def write_leakage_report(path: Path, schema: pd.DataFrame) -> None:
    """Write the B8 leakage report."""
    excluded = schema.loc[schema["role"] == "forbidden_leakage", "column_name"].tolist()
    selected = schema.loc[schema["role"] == "feature", "column_name"].tolist()
    excluded_nonphysical = schema.loc[schema["predictor_tier"] == "excluded_nonphysical", "column_name"].tolist() if "predictor_tier" in schema else []
    excluded_metadata = schema.loc[schema["predictor_tier"] == "excluded_metadata", "column_name"].tolist() if "predictor_tier" in schema else []
    spatial = schema.loc[schema["predictor_tier"] == "spatial_diagnostic", "column_name"].tolist() if "predictor_tier" in schema else []
    lines = [
        "# B8 Dataset Leakage Check",
        "",
        "Feature selection excludes target, target-derived, rank-derived, reference-domain, SOLWEIG-derived output columns, nonphysical/social fields, and metadata/provenance/constant fields.",
        "",
        f"- Selected B8.2 physical-core predictor columns: {len(selected)}",
        f"- Excluded leakage-like columns: {len(excluded)}",
        f"- Excluded nonphysical/social columns: {len(excluded_nonphysical)}",
        f"- Excluded metadata/constant/contract columns: {len(excluded_metadata)}",
        f"- Spatial diagnostic columns excluded from headline physical surrogate: {len(spatial)}",
        "- Leakage status for selected feature columns: PASS",
        "",
        "## Excluded Leakage-Like Columns",
        "",
    ]
    lines.extend(f"- `{column}`" for column in excluded)
    lines.extend(["", "## Excluded Nonphysical / Social Columns", ""])
    lines.extend(f"- `{column}`" for column in excluded_nonphysical)
    lines.extend(["", "## Excluded Metadata / Constant / Contract Columns", ""])
    lines.extend(f"- `{column}`" for column in excluded_metadata)
    lines.extend(["", "## Spatial Diagnostic Columns", ""])
    lines.extend(f"- `{column}`" for column in spatial)
    lines.extend(["", "## Selected Feature Columns", ""])
    lines.extend(f"- `{column}`" for column in selected)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def status_from_checks(checks: dict[str, bool], required_inputs_found: bool) -> str:
    """Derive B8.0 status."""
    if not required_inputs_found:
        return "BLOCKED"
    return "PASS" if all(checks.values()) else "FAILED"


def write_audit_report(
    path: Path,
    inventory: pd.DataFrame,
    matrix: pd.DataFrame,
    schema: pd.DataFrame,
    missingness: pd.DataFrame,
    config: dict[str, Any],
    checks: dict[str, bool],
    missing_labels: list[str],
    status: str,
) -> None:
    """Write the B8.0 Markdown audit report."""
    scenarios = sorted(matrix["scenario"].dropna().astype(str).unique().tolist()) if "scenario" in matrix else []
    hours = sorted(pd.to_numeric(matrix["hour_sgt"], errors="coerce").dropna().astype(int).unique().tolist()) if "hour_sgt" in matrix else []
    versions = sorted(matrix["target_version"].dropna().astype(str).unique().tolist()) if "target_version" in matrix else []
    domains = sorted(matrix["reference_domain_version"].dropna().astype(str).unique().tolist()) if "reference_domain_version" in matrix else []
    selected = schema.loc[schema["role"] == "feature", "column_name"].tolist()
    leakage = schema.loc[schema["role"] == "forbidden_leakage", "column_name"].tolist()
    numeric_count = int(matrix[selected].select_dtypes(include=[np.number]).shape[1]) if selected else 0
    categorical_count = len(selected) - numeric_count
    excluded_nonphysical = schema.loc[schema["predictor_tier"] == "excluded_nonphysical", "column_name"].tolist() if "predictor_tier" in schema else []
    excluded_metadata = schema.loc[schema["predictor_tier"] == "excluded_metadata", "column_name"].tolist() if "predictor_tier" in schema else []
    spatial_diagnostic = schema.loc[schema["predictor_tier"] == "spatial_diagnostic", "column_name"].tolist() if "predictor_tier" in schema else []
    all_nan = missingness.loc[missingness["is_all_nan"], "column_name"].tolist()
    constant = missingness.loc[missingness["is_constant"], "column_name"].tolist()
    high20 = missingness.loc[missingness["missing_gt_20pct"], "column_name"].tolist()
    high50 = missingness.loc[missingness["missing_gt_50pct"], "column_name"].tolist()
    high80 = missingness.loc[missingness["missing_gt_80pct"], "column_name"].tolist()
    found_lines = [
        f"- {row.input_name} ({row.requirement}): {'FOUND' if row.found else 'MISSING'} - `{row.path}`"
        for row in inventory.itertuples(index=False)
    ]
    check_lines = [f"- {name}: {'PASS' if value else 'FAIL'}" for name, value in checks.items()]
    lines = [
        "# B8.0 Surrogate-Ready Dataset Audit",
        "",
        f"Status: **{status}**",
        "",
        "## Input Files",
        "",
        *found_lines,
        "",
        "## Expected N150 Structure",
        "",
        f"- Row count: {len(matrix)}",
        f"- Unique cell count: {matrix['cell_id'].nunique() if 'cell_id' in matrix else 0}",
        f"- Scenario values: {markdown_list(scenarios)}",
        f"- hour_sgt values: {markdown_list(hours)}",
        f"- target_version values: {markdown_list(versions)}",
        f"- reference_domain_version values: {markdown_list(domains)}",
        "",
        "## Required Label Columns",
        "",
        f"- Missing required target / label columns: {markdown_list(missing_labels)}",
        f"- Primary physical surrogate target: `{config['primary_target']}`",
        f"- Secondary target: `{config['secondary_target']}`",
        f"- Retained post-prediction modifier / label: `{config['retained_modifier']}`",
        "",
        "## Checks",
        "",
        *check_lines,
        "",
        "## Missingness Summary",
        "",
        f"- Selected B8.2 physical-core predictor count: {len(selected)}",
        f"- Numeric selected feature count: {numeric_count}",
        f"- Categorical selected feature count: {categorical_count}",
        f"- Spatial diagnostic coordinate count excluded from headline predictors: {len(spatial_diagnostic)}",
        f"- Excluded nonphysical/social feature count: {len(excluded_nonphysical)}",
        f"- Excluded metadata/constant/contract count: {len(excluded_metadata)}",
        f"- All-NaN selected feature columns: {markdown_list(all_nan)}",
        f"- Constant selected feature columns: {markdown_list(constant)}",
        f"- High missingness >20%: {markdown_list(high20)}",
        f"- High missingness >50%: {markdown_list(high50)}",
        f"- High missingness >80%: {markdown_list(high80)}",
        "",
        "## Leakage Summary",
        "",
        f"- Excluded leakage-like columns: {len(leakage)}",
        "- Selected feature columns contain no leakage-like name tokens: PASS",
        "- Raw merged matrix retains audit/label columns; B8.2 should consume only `feature_schema.csv` rows where `role == feature` and `predictor_tier == physical_core` for the headline physical surrogate.",
        "- Spatial diagnostic columns are retained for optional diagnostic models only, not the headline physical surrogate.",
        "",
        "## Caveats",
        "",
        "- `m_rad_pct01` is retained as a reference-domain percentile/rank modifier label, not the only regression target.",
        "- The emphasized B8.2 targets are `delta_tmrt_p90_c` and `tmrt_p90_c`; no Tmrt value is converted to WBGT.",
        "- Hygiene patch B8.1.1 tightened predictor eligibility; exposure/vulnerability/risk/social fields, provenance strings, constants, contract fields, and spatial coordinates are excluded from headline B8.2 predictors.",
        "- No model training or AOI-wide inference is performed in B8.0.",
        "",
        "## Next Recommended Action",
        "",
        "Review the audit outputs and then run B8.1 validation split manifests before any B8.2 benchmark work.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path = DEFAULT_CONFIG) -> AuditResult:
    """Run B8.0 audit and write all configured outputs."""
    config = read_config(config_path)
    audit_dir = repo_path(config["outputs"]["audit_dir"])
    audit_dir.mkdir(parents=True, exist_ok=True)
    inventory = input_inventory(config)
    required_inputs_found = bool(inventory.loc[inventory["requirement"] == "required", "found"].all())
    if not required_inputs_found:
        empty_schema = pd.DataFrame(columns=["column_name", "role", "predictor_tier", "dtype", "non_null_count", "missing_fraction", "source_file_guess", "notes"])
        empty_schema.to_csv(audit_dir / "feature_schema.csv", index=False)
        pd.DataFrame().to_csv(audit_dir / "feature_missingness.csv", index=False)
        pd.DataFrame().to_csv(audit_dir / "target_distribution_summary.csv", index=False)
        pd.DataFrame().to_csv(audit_dir / "surrogate_label_feature_matrix.csv", index=False)
        checks = {"required_inputs_found": False}
        write_leakage_report(audit_dir / "leakage_check_report.md", empty_schema)
        write_audit_report(audit_dir / "b8_dataset_audit_report.md", inventory, pd.DataFrame(), empty_schema, pd.DataFrame(), config, checks, [], "BLOCKED")
        return AuditResult("BLOCKED", 0, 0, [], [], 0, 0, 0, audit_dir / "b8_dataset_audit_report.md")

    labels = normalize_label_frame(read_csv(repo_path(config["inputs"]["required"]["modifier_targets"])))
    features, source_guess = load_feature_table(config)
    matrix = labels.merge(features, on="cell_id", how="left", validate="many_to_one")
    matrix = matrix.sort_values(["cell_id", "scenario", "hour_sgt"]).reset_index(drop=True)
    required_labels = [
        config["secondary_target"],
        config["primary_target"],
        config["retained_modifier"],
        *config["companion_labels"],
    ]
    missing_labels = [column for column in required_labels if column not in matrix.columns]
    schema = classify_columns(matrix, config, source_guess)
    missingness = missingness_table(matrix, schema)
    distribution = summarize_targets(matrix, config)

    matrix.to_csv(audit_dir / "surrogate_label_feature_matrix.csv", index=False)
    schema.to_csv(audit_dir / "feature_schema.csv", index=False)
    missingness.to_csv(audit_dir / "feature_missingness.csv", index=False)
    distribution.to_csv(audit_dir / "target_distribution_summary.csv", index=False)
    write_leakage_report(audit_dir / "leakage_check_report.md", schema)

    expected_scenarios = set(config["expected_scenarios"])
    observed_scenarios = set(matrix["scenario"].dropna().astype(str).unique())
    expected_hours = set(int(value) for value in config["expected_hours_sgt"])
    observed_hours = set(pd.to_numeric(matrix["hour_sgt"], errors="coerce").dropna().astype(int).unique())
    target_versions = set(matrix["target_version"].dropna().astype(str).unique()) if "target_version" in matrix else set()
    domains = set(matrix["reference_domain_version"].dropna().astype(str).unique()) if "reference_domain_version" in matrix else set()
    selected_features = schema.loc[schema["role"] == "feature", "column_name"].tolist()
    selected_leakage = [column for column in selected_features if leakage_like(column, config["leakage_name_tokens"])]
    excluded_nonphysical_count = int((schema["predictor_tier"] == "excluded_nonphysical").sum())
    excluded_metadata_count = int((schema["predictor_tier"] == "excluded_metadata").sum())
    checks = {
        "required_inputs_found": required_inputs_found,
        "row_count_is_1500": len(matrix) == int(config["expected_n_rows"]),
        "unique_cell_count_is_150": matrix["cell_id"].nunique() == int(config["expected_n_cells"]),
        "scenario_set_matches": observed_scenarios == expected_scenarios,
        "hour_sgt_set_matches": observed_hours == expected_hours,
        "target_version_matches": target_versions == {config["target_version"]},
        "reference_domain_version_matches": domains == {config["reference_domain_version"]},
        "primary_target_exists": config["primary_target"] in matrix.columns,
        "primary_target_complete": config["primary_target"] in matrix.columns and matrix[config["primary_target"]].notna().all(),
        "secondary_target_exists": config["secondary_target"] in matrix.columns,
        "retained_modifier_exists": config["retained_modifier"] in matrix.columns,
        "feature_matrix_exists": len(selected_features) > 0,
        "selected_feature_leakage_clean": len(selected_leakage) == 0,
        "required_label_columns_present": not missing_labels,
    }
    status = status_from_checks(checks, required_inputs_found)
    write_audit_report(audit_dir / "b8_dataset_audit_report.md", inventory, matrix, schema, missingness, config, checks, missing_labels, status)
    return AuditResult(
        status=status,
        row_count=len(matrix),
        unique_cells=int(matrix["cell_id"].nunique()),
        scenario_values=sorted(observed_scenarios),
        hour_values=sorted(observed_hours),
        selected_feature_count=len(selected_features),
        excluded_nonphysical_count=excluded_nonphysical_count,
        excluded_metadata_count=excluded_metadata_count,
        leakage_excluded_count=int((schema["role"] == "forbidden_leakage").sum()),
        report_path=audit_dir / "b8_dataset_audit_report.md",
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run the B8.0 surrogate-ready dataset audit.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to the explicit B8 YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps({**result.__dict__, "report_path": str(result.report_path)}, indent=2, default=str))


if __name__ == "__main__":
    main()
