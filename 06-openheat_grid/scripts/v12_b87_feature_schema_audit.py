"""Audit B8.6g feature schema and N300 candidate feature coverage for B8.7.

Inputs:
    B8.6g feature schema, B8.6g feature coverage matrix, B8.6g feature-gap
    closure matrix, B8.6g N300 candidate feature dataset, and B8.6f N300 v2
    candidate design declared in the B8.7 config.
Outputs:
    outputs/v12_surrogate/b8_7_n300_pre/b87_n300_feature_coverage_audit.csv.
Saved metrics:
    N300 feature row completeness, one-row-per-candidate checks, feature-family
    coverage by proxy/vector/not-available status, missing high-priority
    candidate coverage, connected shade corridor status, and feature-schema
    claim-boundary checks. This script creates no model output, no AOI/B9
    product, no N300 execution manifest, no QGIS/SOLWEIG runner, no raster I/O,
    no WBGT/hazard/risk/exposure/vulnerability score, no observed truth, no
    causal feature importance, and no System A/B coupling output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b87_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, load_config, output_path, read_csv, write_csv


@dataclass(frozen=True)
class FeatureSchemaAuditResult:
    """B8.7 feature schema audit result."""

    status: str
    feature_rows: int
    candidate_rows: int
    connected_shade_status: str
    feature_coverage_headline: str


HIGH_PRIORITY_FAMILIES = {
    "pedestrian-accessible shaded fraction",
    "connected shade corridor / shade continuity",
    "overhead geometry shape descriptors",
    "sunlit-hot-pocket area fraction",
    "tree/building shadow interaction",
    "canyon orientation / height roughness",
}

STATUS_OR_METHOD_TOKENS = ("status", "method", "version", "source")


def source_class(source_status: str, proxy_status: str, closure_status: str) -> str:
    """Classify a feature family as proxy, vector-derived, or unavailable."""
    text = f"{source_status} {proxy_status} {closure_status}".upper()
    if "NOT_AVAILABLE" in text or "REQUIRES_SOURCE" in text:
        return "not_available"
    if "VECTOR" in text and "PROXY_ONLY" not in text:
        return "vector_derived"
    if "PROXY" in text:
        return "proxy_only"
    return "compact_available"


def feature_columns_for(schema: pd.DataFrame, family: str) -> list[str]:
    """Return data-bearing feature columns for a family."""
    subset = schema.loc[schema["feature_family"].astype(str).eq(family)].copy()
    names = []
    for name in subset["feature_name"].dropna().astype(str):
        lowered = name.lower()
        if any(token in lowered for token in STATUS_OR_METHOD_TOKENS):
            continue
        names.append(name)
    return names


def family_audit_rows(config: dict[str, Any]) -> pd.DataFrame:
    """Build feature-family coverage audit rows."""
    design = read_csv(config["b86f_n300_v2_path"])
    features = read_csv(config["b86g_n300_feature_dataset_path"])
    schema = read_csv(config["b86g_feature_schema_path"])
    coverage = read_csv(config["b86g_feature_coverage_matrix_path"])
    gap = read_csv(config["b86g_feature_gap_closure_matrix_path"])

    design_ids = [str(cell_id) for cell_id in design["cell_id"].dropna().astype(str)]
    feature_ids = set(features["cell_id"].dropna().astype(str))
    missing_feature_rows = [cell_id for cell_id in design_ids if cell_id not in feature_ids]
    rows: list[dict[str, Any]] = [
        {
            "audit_scope": "dataset",
            "feature_family": "n300_candidate_feature_rows",
            "feature_coverage_status": "complete" if not missing_feature_rows else "missing_rows",
            "source_class": "compact_table",
            "n300_coverage_fraction": 1.0 - len(missing_feature_rows) / max(1, len(design_ids)),
            "candidate_rows_with_any_feature": len(feature_ids.intersection(design_ids)),
            "candidate_missing_count": len(missing_feature_rows),
            "candidate_missing_examples": "|".join(missing_feature_rows[:20]),
            "status": "PASS" if not missing_feature_rows and len(features) == len(design_ids) else "FAIL",
            "recommended_manual_qa": "none" if not missing_feature_rows and len(features) == len(design_ids) else "repair N300 feature dataset row coverage",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    ]

    coverage_map = {row["feature_family"]: row for _, row in coverage.iterrows()}
    gap_map = {row["gap_family"]: row for _, row in gap.iterrows()}
    for family in sorted(set(schema["feature_family"].dropna().astype(str)).union(set(coverage["feature_family"].dropna().astype(str)))):
        columns = feature_columns_for(schema, family)
        present = [column for column in columns if column in features.columns]
        missing_columns = [column for column in columns if column not in features.columns]
        subset = features.loc[features["cell_id"].astype(str).isin(design_ids)].copy()
        if present:
            has_family = subset[present].notna().any(axis=1)
            covered_count = int(has_family.sum())
            candidate_missing = subset.loc[~has_family, "cell_id"].dropna().astype(str).tolist()
        else:
            covered_count = 0
            candidate_missing = subset["cell_id"].dropna().astype(str).tolist()
        coverage_row = coverage_map.get(family, {})
        gap_row = gap_map.get(family, {})
        proxy_status = str(coverage_row.get("proxy_status", "unknown")) if isinstance(coverage_row, pd.Series) else "unknown"
        source_status = str(coverage_row.get("source_status", "unknown")) if isinstance(coverage_row, pd.Series) else "unknown"
        closure_status = str(gap_row.get("closure_status", "unknown")) if isinstance(gap_row, pd.Series) else "unknown"
        family_source_class = source_class(source_status, proxy_status, closure_status)
        n300_fraction = covered_count / max(1, len(design_ids))
        if family_source_class == "not_available":
            coverage_status = "not_available"
            status = "WARN" if family in HIGH_PRIORITY_FAMILIES else "PASS"
            qa = "acquire true vector/compact source before promoting feature coverage"
        elif n300_fraction >= 0.99:
            coverage_status = "complete"
            status = "PASS"
            qa = "none"
        elif n300_fraction >= 0.80:
            coverage_status = "partial"
            status = "WARN"
            qa = "review candidates missing this feature family"
        else:
            coverage_status = "insufficient"
            status = "WARN" if family in HIGH_PRIORITY_FAMILIES else "PASS"
            qa = "feature coverage too sparse for design-freeze confidence"
        rows.append(
            {
                "audit_scope": "feature_family",
                "feature_family": family,
                "priority": str(gap_row.get("B8.6f_priority", "")) if isinstance(gap_row, pd.Series) else "",
                "feature_coverage_status": coverage_status,
                "source_class": family_source_class,
                "n300_coverage_fraction": n300_fraction,
                "b86g_reported_n300_coverage_fraction": coverage_row.get("n300_coverage_fraction", "") if isinstance(coverage_row, pd.Series) else "",
                "source_status": source_status,
                "proxy_status": proxy_status,
                "closure_status": closure_status,
                "feature_columns": "|".join(columns),
                "missing_feature_columns": "|".join(missing_columns),
                "candidate_rows_with_any_feature": covered_count,
                "candidate_missing_count": len(candidate_missing),
                "candidate_missing_examples": "|".join(candidate_missing[:20]),
                "status": status,
                "recommended_manual_qa": qa,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def headline(audit: pd.DataFrame) -> str:
    """Return a concise feature coverage headline."""
    family_rows = audit.loc[audit["audit_scope"].astype(str).eq("feature_family")]
    classes = family_rows["source_class"].astype(str).value_counts().to_dict()
    warn = family_rows.loc[family_rows["status"].astype(str).ne("PASS"), "feature_family"].astype(str).tolist()
    return (
        f"vector_derived={classes.get('vector_derived', 0)} proxy_only={classes.get('proxy_only', 0)} "
        f"not_available={classes.get('not_available', 0)} review={','.join(warn[:4]) if warn else 'none'}"
    )


def run(config_path: Path = DEFAULT_CONFIG) -> FeatureSchemaAuditResult:
    """Run B8.7 feature schema and N300 coverage audit."""
    config = load_config(config_path)
    audit = family_audit_rows(config)
    write_csv(audit, output_path(config, "n300_feature_coverage_audit_path"))
    dataset_row = audit.loc[audit["audit_scope"].astype(str).eq("dataset")].iloc[0]
    family_rows = audit.loc[audit["audit_scope"].astype(str).eq("feature_family")]
    connected = family_rows.loc[family_rows["feature_family"].astype(str).eq("connected shade corridor / shade continuity")]
    connected_status = connected["feature_coverage_status"].iloc[0] if not connected.empty else "missing_schema"
    status = "B87_FEATURE_COVERAGE_PASS" if not audit["status"].astype(str).eq("FAIL").any() else "B87_BLOCKED_INPUT"
    return FeatureSchemaAuditResult(
        status=status,
        feature_rows=int(dataset_row["candidate_rows_with_any_feature"]),
        candidate_rows=int(dataset_row["candidate_rows_with_any_feature"]) + int(dataset_row["candidate_missing_count"]),
        connected_shade_status=str(connected_status),
        feature_coverage_headline=headline(audit),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Audit B8.6g feature schema and N300 candidate feature coverage for B8.7. "
            "Writes compact CSV only; no raster/QGIS/SOLWEIG/AOI/B9/WBGT/"
            "hazard/risk/manifest/execution outputs."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
