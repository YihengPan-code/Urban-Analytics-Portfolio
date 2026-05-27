"""Write the B8.6g2 feature leakage audit and feature-set registry.

Inputs:
    b86g2_modeling_dataset.csv, B8.6g feature schema, B8.6g quality checks,
    and B8.6g coverage matrix.
Outputs:
    b86g2_feature_leakage_audit.csv and b86g2_feature_set_registry.csv.
Saved metrics:
    Predictor eligibility, leakage exclusion reasons, feature-set definitions,
    proxy/vector counts, and explicit no-target-derived/no-status predictor
    decisions.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86g2_common import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    b86g_feature_schema,
    build_feature_registry,
    forbidden_predictor,
    load_config,
    output_path,
    parse_pipe_list,
    read_csv,
    write_csv,
)


@dataclass(frozen=True)
class FeatureAuditResult:
    """Feature audit result."""

    status: str
    audit_rows: int
    feature_sets: int
    allowed_predictors: int


def exclusion_reason(column: str, role: str, in_feature_sets: bool) -> str:
    """Return a concise leakage-audit reason."""
    name = column.lower()
    if role == "target":
        return "target_column_excluded"
    if role == "target_derived_excluded" or "tmrt" in name or "rank" in name:
        return "target_derived_column_excluded"
    if column in {"cell_id", "forcing_day_id"}:
        return "metadata_group_or_split_only"
    if any(token in name for token in ["status", "method", "source", "path", "notes"]):
        return "status_method_source_or_notes_metadata_only"
    if any(token in name for token in ["wbgt", "risk", "hazard", "observed", "official", "vulnerability", "exposure"]):
        return "claim_boundary_forbidden_domain_column"
    if in_feature_sets and not forbidden_predictor(column):
        return "safe_predictor_registered"
    return "not_registered_as_predictor"


def leakage_audit(dataset: pd.DataFrame, schema_frame: pd.DataFrame, registry: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create the machine-readable feature leakage audit."""
    role_map = schema_frame.set_index("column_name")["role"].to_dict() if not schema_frame.empty else {}
    feature_cols: set[str] = set()
    for value in registry["feature_columns"].fillna(""):
        feature_cols.update(parse_pipe_list(value))
    rows: list[dict[str, Any]] = []
    for column in dataset.columns:
        in_features = column in feature_cols
        role = str(role_map.get(column, "unknown"))
        forbidden = forbidden_predictor(column)
        rows.append(
            {
                "column_name": column,
                "role": role,
                "in_any_feature_set": bool(in_features),
                "predictor_allowed": bool(in_features and not forbidden),
                "forbidden_predictor": bool(forbidden),
                "exclusion_reason": exclusion_reason(column, role, in_features),
                "non_null_count": int(dataset[column].notna().sum()),
                "unique_count": int(dataset[column].nunique(dropna=True)),
                "target_derived": bool(role in {"target", "target_derived_excluded"}),
                "status_method_source_metadata": any(token in column.lower() for token in ["status", "method", "source"]),
                "cell_id_numeric_predictor": False,
                "random_split_main_evidence": bool(config["random_split_diagnostic"]),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> FeatureAuditResult:
    """Write leakage audit and feature-set registry."""
    config = load_config(config_path)
    dataset = read_csv(output_path(config, "modeling_dataset"))
    schema_frame = read_csv(output_path(config, "dataset_schema"))
    registry = build_feature_registry(dataset, b86g_feature_schema(config), config)
    audit = leakage_audit(dataset, schema_frame, registry, config)
    write_csv(audit, output_path(config, "feature_leakage_audit"))
    write_csv(registry, output_path(config, "feature_set_registry"))
    allowed = int(audit["predictor_allowed"].astype(bool).sum()) if not audit.empty else 0
    return FeatureAuditResult("B86G2_FEATURE_AUDIT_READY", len(audit), len(registry), allowed)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Write B8.6g2 feature leakage audit and registered feature-set definitions."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
