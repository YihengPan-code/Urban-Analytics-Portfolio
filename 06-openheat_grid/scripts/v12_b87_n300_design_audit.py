"""Audit and freeze-review the B8.6f N300 v2 candidate design.

Inputs:
    B8.6f N300 v2 candidate design, B8.6g N300 feature dataset,
    B8.6g2 retest evidence, current N150 label-cell sources, N150 sampling
    feature matrix, and candidate universe declared in the B8.7 config.
Outputs:
    b87_n300_v2_input_audit.csv, b87_n300_design_freeze_candidates.csv,
    b87_n300_exclusion_register.csv, and role/spatial/typology/anchor/neutral/
    sparse/control audit CSVs under outputs/v12_surrogate/b8_7_n300_pre/.
Saved metrics:
    Candidate row count, duplicate cell IDs, required-schema recovery status,
    N150 overlap count, role quotas, weak-bin spatial balance, typology
    concentration and feasible undercoverage, anchor/neutral replication,
    sparse feature-space/OOD flags, and control-cell coverage. This is a
    design freeze/precheck audit only: no SOLWEIG manifest, QGIS runner,
    raster I/O, AOI-wide prediction, B9, local WBGT, hazard/risk score,
    observed truth, causal feature importance, Tmrt-to-WBGT conversion, or
    System A/B coupling is created.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b87_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    as_float,
    current_n150_label_cells,
    load_config,
    output_path,
    read_csv,
    status_from_checks,
    write_csv,
)


@dataclass(frozen=True)
class N300DesignAuditResult:
    """B8.7 N300 design audit result."""

    status: str
    candidate_count: int
    overlap_with_n150: int
    role_headline: str
    spatial_headline: str
    typology_headline: str
    anchor_headline: str
    neutral_headline: str


REQUIRED_N300_COLUMNS = [
    "cell_id",
    "selected_priority_rank",
    "primary_role",
    "secondary_roles",
    "rationale",
    "spatial_bin",
    "typology",
    "nearest_anchor_cell",
    "nearest_neutral_cell",
    "nearest_n150_distance",
    "nearest_n150_distance_percentile",
    "coverage_gap",
    "expected_learning_value",
    "sampling_boundary",
    "claim_boundary",
]

TYPOLOGY_UNDERCOVERAGE_TARGETS = ["park_open_space", "civic_institutional", "commercial"]


def n300_design(config: dict[str, Any]) -> pd.DataFrame:
    """Load N300 v2 and recover a small number of schema columns if possible."""
    design = read_csv(config["b86f_n300_v2_path"])
    universe = read_csv(config["candidate_universe_path"])
    recover_map = {
        "typology": "typology_label",
    }
    for missing_column, universe_column in recover_map.items():
        if missing_column not in design.columns and universe_column in universe.columns:
            design = design.merge(universe[["cell_id", universe_column]].drop_duplicates("cell_id"), on="cell_id", how="left")
            design[missing_column] = design[universe_column]
            design = design.drop(columns=[universe_column], errors="ignore")
    return design


def input_audit(config: dict[str, Any], design: pd.DataFrame, n150_cells: set[str]) -> pd.DataFrame:
    """Build N300 v2 input/schema/overlap audit rows."""
    expected_count = int(config["expected_n300_candidate_count"])
    missing_columns = [column for column in REQUIRED_N300_COLUMNS if column not in design.columns]
    duplicate_count = int(design["cell_id"].duplicated().sum()) if "cell_id" in design.columns else len(design)
    overlap = sorted(set(design["cell_id"].dropna().astype(str)).intersection(n150_cells)) if "cell_id" in design.columns else []
    rows = [
        {
            "audit_item": "candidate_row_count",
            "observed_value": len(design),
            "expected_value": expected_count,
            "status": "PASS" if len(design) == expected_count else "FAIL",
            "recoverable": False,
            "recovered_columns": "",
            "evidence": f"rows={len(design)} expected={expected_count}",
            "recommended_manual_qa": "none" if len(design) == expected_count else "recover or regenerate B8.6f N300 v2 input",
        },
        {
            "audit_item": "duplicate_cell_id",
            "observed_value": duplicate_count,
            "expected_value": 0,
            "status": "PASS" if duplicate_count == 0 else "FAIL",
            "recoverable": False,
            "recovered_columns": "",
            "evidence": f"duplicate_cell_id_count={duplicate_count}",
            "recommended_manual_qa": "none" if duplicate_count == 0 else "deduplicate or replace candidate rows",
        },
        {
            "audit_item": "required_columns",
            "observed_value": len(REQUIRED_N300_COLUMNS) - len(missing_columns),
            "expected_value": len(REQUIRED_N300_COLUMNS),
            "status": "PASS" if not missing_columns else "BLOCKED_SCHEMA",
            "recoverable": False,
            "recovered_columns": "",
            "evidence": "missing=" + ("|".join(missing_columns) if missing_columns else "none"),
            "recommended_manual_qa": "none" if not missing_columns else "repair required N300 v2 schema before interpreting audits",
        },
        {
            "audit_item": "overlap_with_current_n150_labels",
            "observed_value": len(overlap),
            "expected_value": 0,
            "status": "PASS" if not overlap else "FAIL",
            "recoverable": False,
            "recovered_columns": "",
            "evidence": "overlap_cell_ids=" + ("|".join(overlap[:25]) if overlap else "none"),
            "recommended_manual_qa": "none" if not overlap else "replace overlapping N300 candidates",
        },
    ]
    out = pd.DataFrame(rows)
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def role_balance_audit(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Audit primary role quotas."""
    quotas = dict(config["required_n300_roles"])
    counts = design["primary_role"].astype(str).value_counts().to_dict() if "primary_role" in design.columns else {}
    rows = []
    for role, quota in quotas.items():
        observed = int(counts.get(role, 0))
        difference = observed - int(quota)
        status = "PASS" if difference == 0 else ("WARN" if abs(difference) <= 3 else "FAIL")
        rows.append(
            {
                "primary_role": role,
                "observed_count": observed,
                "quota": int(quota),
                "difference": difference,
                "status": status,
                "recommended_manual_qa": "none" if status == "PASS" else "review quota deviation before freeze",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    extra_roles = sorted(set(counts).difference(quotas))
    for role in extra_roles:
        rows.append(
            {
                "primary_role": role,
                "observed_count": int(counts[role]),
                "quota": 0,
                "difference": int(counts[role]),
                "status": "FAIL",
                "recommended_manual_qa": "unexpected role; map to approved role or remove",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def spatial_balance_audit(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Audit spatial-bin coverage and weak-bin support."""
    weak_bins = set(str(item) for item in config["weak_spatial_bins"])
    counts = design["spatial_bin"].astype(str).value_counts().to_dict() if "spatial_bin" in design.columns else {}
    minimum = int(config["spatial_bin_minimum"])
    maximum = int(config["spatial_bin_maximum"])
    rows = []
    for spatial_bin in sorted(weak_bins.union(counts)):
        observed = int(counts.get(spatial_bin, 0))
        if observed < minimum or observed > maximum:
            status = "WARN"
        else:
            status = "PASS"
        qa = "none"
        if spatial_bin == "west_south" and observed <= max(minimum, 30):
            qa = "west_south is the low-support weak bin; inspect candidate quality before freeze"
            status = "WARN"
        elif status != "PASS":
            qa = "rebalance weak-bin representation or document infeasibility"
        rows.append(
            {
                "spatial_bin": spatial_bin,
                "observed_count": observed,
                "minimum_preferred": minimum,
                "maximum_preferred": maximum,
                "weak_spatial_bin": spatial_bin in weak_bins,
                "status": status,
                "recommended_manual_qa": qa,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def typology_balance_audit(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Audit typology representation against feasible candidate universe counts."""
    universe = read_csv(config["candidate_universe_path"])
    universe_type = universe.get("typology_label", pd.Series("unknown", index=universe.index)).astype(str)
    universe_counts = universe_type.value_counts().to_dict()
    counts = design["typology"].astype(str).value_counts().to_dict() if "typology" in design.columns else {}
    total = max(1, len(design))
    rows = []
    typologies = sorted(set(counts).union(TYPOLOGY_UNDERCOVERAGE_TARGETS))
    for typology in typologies:
        observed = int(counts.get(typology, 0))
        feasible = int(universe_counts.get(typology, 0))
        share = observed / total
        status = "PASS"
        qa = "none"
        if typology in {"residential", "transport"} and observed > 50:
            status = "WARN"
            qa = "inspect overconcentration against role rationale and replacement feasibility"
        if typology in TYPOLOGY_UNDERCOVERAGE_TARGETS and feasible >= 20 and observed < 5:
            status = "WARN"
            qa = "review undercoverage because candidate universe appears feasible"
        rows.append(
            {
                "typology": typology,
                "observed_count": observed,
                "observed_share": share,
                "candidate_universe_count": feasible,
                "status": status,
                "recommended_manual_qa": qa,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    combined = int(counts.get("residential", 0)) + int(counts.get("transport", 0))
    rows.append(
        {
            "typology": "residential_plus_transport",
            "observed_count": combined,
            "observed_share": combined / total,
            "candidate_universe_count": int(universe_counts.get("residential", 0)) + int(universe_counts.get("transport", 0)),
            "status": "WARN" if combined / total > 0.70 else "PASS",
            "recommended_manual_qa": "inspect concentration in residential/transport before freeze" if combined / total > 0.70 else "none",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )
    return pd.DataFrame(rows)


def anchor_replication_audit(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Audit nearest-anchor replication."""
    counts = design["nearest_anchor_cell"].astype(str).value_counts().to_dict() if "nearest_anchor_cell" in design.columns else {}
    preferred = dict(config["anchor_preferred_minimums"])
    rows = []
    for anchor_cell in config["anchor_cells"]:
        observed = int(counts.get(str(anchor_cell), 0))
        minimum = int(preferred.get(str(anchor_cell), 15))
        if observed >= minimum:
            status = "PASS"
            qa = "none"
        elif observed > 0:
            status = "WARN"
            qa = "review whether feature-space/geographic feasibility explains preferred-minimum shortfall"
        else:
            status = "FAIL"
            qa = "replace or add candidates near this anchor before freeze"
        rows.append(
            {
                "nearest_anchor_cell": str(anchor_cell),
                "observed_count": observed,
                "preferred_minimum": minimum,
                "difference": observed - minimum,
                "status": status,
                "recommended_manual_qa": qa,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def neutral_replication_audit(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Audit neutral-boundary replication by nearest neutral cell."""
    neutral_role = design.loc[design["primary_role"].astype(str).eq("neutral_boundary_replication")].copy()
    counts = neutral_role["nearest_neutral_cell"].astype(str).value_counts().to_dict() if not neutral_role.empty else {}
    total = max(1, len(neutral_role))
    min_count = int(config["neutral_group_min_count"])
    min_groups = int(config["neutral_min_groups_at_min_count"])
    max_share = float(config["neutral_max_single_group_share"])
    groups_at_min = sum(1 for value in counts.values() if int(value) >= min_count)
    rows = []
    for neutral_cell in config["known_neutral_cells"]:
        observed = int(counts.get(str(neutral_cell), 0))
        share = observed / total
        status = "PASS"
        qa = "none"
        if share > max_share:
            status = "WARN"
            qa = "review overconcentration in neutral-boundary role"
        if str(neutral_cell) in {"TP_0676", "TP_0326", "TP_0115"} and observed >= min_count:
            status = "WARN"
            qa = "known false-promotion-prone neutral group; inspect candidate rationale"
        rows.append(
            {
                "nearest_neutral_cell": str(neutral_cell),
                "neutral_boundary_role_count": observed,
                "share_of_neutral_boundary_role": share,
                "preferred_group_minimum": min_count,
                "status": status,
                "recommended_manual_qa": qa,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    rows.append(
        {
            "nearest_neutral_cell": "summary_groups_at_minimum",
            "neutral_boundary_role_count": groups_at_min,
            "share_of_neutral_boundary_role": "",
            "preferred_group_minimum": min_groups,
            "status": "PASS" if groups_at_min >= min_groups else "WARN",
            "recommended_manual_qa": "increase diversity across known neutral contexts" if groups_at_min < min_groups else "none",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )
    return pd.DataFrame(rows)


def sparse_feature_space_audit(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Audit sparse/OOD nearest-N150 distance percentiles."""
    values = pd.to_numeric(design.get("nearest_n150_distance_percentile"), errors="coerce")
    p90 = float(config["sparse_p90_threshold"])
    p95 = float(config["sparse_p95_threshold"])
    sparse_role = design["primary_role"].astype(str).eq("sparse_feature_space") if "primary_role" in design.columns else pd.Series(False, index=design.index)
    rows = [
        {
            "audit_item": "p90_or_higher_candidates",
            "observed_count": int((values >= p90).sum()),
            "threshold": p90,
            "status": "WARN" if int((values >= p90).sum()) > int(config["required_n300_roles"]["sparse_feature_space"]) else "PASS",
            "recommended_manual_qa": "many non-sparse-role candidates are high-distance/OOD; inspect before execution precheck",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "audit_item": "p95_or_higher_candidates",
            "observed_count": int((values >= p95).sum()),
            "threshold": p95,
            "status": "WARN" if int((values >= p95).sum()) > 0 else "PASS",
            "recommended_manual_qa": "mark p95 candidates as execution-risk but keep sparse role if intentionally selected",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "audit_item": "sparse_feature_space_role_count",
            "observed_count": int(sparse_role.sum()),
            "threshold": int(config["required_n300_roles"]["sparse_feature_space"]),
            "status": "PASS" if int(sparse_role.sum()) == int(config["required_n300_roles"]["sparse_feature_space"]) else "WARN",
            "recommended_manual_qa": "none" if int(sparse_role.sum()) == int(config["required_n300_roles"]["sparse_feature_space"]) else "review sparse-feature-space quota",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    return pd.DataFrame(rows)


def control_cell_audit(design: pd.DataFrame) -> pd.DataFrame:
    """Audit control-cell diversity and baseline-like status."""
    controls = design.loc[design["primary_role"].astype(str).eq("control_cell")].copy()
    rows = []
    if controls.empty:
        rows.append(
            {
                "audit_item": "control_cell_presence",
                "observed_value": 0,
                "status": "FAIL",
                "recommended_manual_qa": "add control-cell candidates",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
        return pd.DataFrame(rows)
    spatial_counts = controls["spatial_bin"].astype(str).value_counts()
    typology_counts = controls["typology"].astype(str).value_counts()
    expected_learning = controls["expected_learning_value"].astype(str).str.contains("control|baseline", case=False, na=False)
    rows.extend(
        [
            {
                "audit_item": "control_spatial_diversity",
                "observed_value": int(spatial_counts.max()),
                "status": "PASS" if spatial_counts.nunique() > 1 and int(spatial_counts.max()) < len(controls) else "WARN",
                "recommended_manual_qa": "none" if spatial_counts.nunique() > 1 and int(spatial_counts.max()) < len(controls) else "avoid all controls from one spatial bin",
                "claim_boundary": CLAIM_BOUNDARY,
            },
            {
                "audit_item": "control_typology_diversity",
                "observed_value": int(typology_counts.max()),
                "status": "PASS" if typology_counts.nunique() > 1 and int(typology_counts.max()) < len(controls) else "WARN",
                "recommended_manual_qa": "none" if typology_counts.nunique() > 1 and int(typology_counts.max()) < len(controls) else "avoid all controls from one typology",
                "claim_boundary": CLAIM_BOUNDARY,
            },
            {
                "audit_item": "control_expected_learning_value",
                "observed_value": int(expected_learning.sum()),
                "status": "PASS" if bool(expected_learning.all()) else "WARN",
                "recommended_manual_qa": "none" if bool(expected_learning.all()) else "confirm controls are low-learning-value or baseline-like cases",
                "claim_boundary": CLAIM_BOUNDARY,
            },
        ]
    )
    return pd.DataFrame(rows)


def exclusion_register(design: pd.DataFrame, n150_cells: set[str]) -> pd.DataFrame:
    """Build candidate exclusion/register rows for duplicates and N150 overlaps."""
    rows = []
    if "cell_id" not in design.columns:
        return pd.DataFrame(
            [
                {
                    "cell_id": "",
                    "exclusion_reason": "missing_cell_id_column",
                    "recommended_action": "repair_schema",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            ]
        )
    duplicate_ids = set(design.loc[design["cell_id"].duplicated(keep=False), "cell_id"].dropna().astype(str))
    for _, row in design.iterrows():
        cell_id = str(row["cell_id"])
        reasons = []
        if cell_id in n150_cells:
            reasons.append("overlap_with_current_n150_label")
        if cell_id in duplicate_ids:
            reasons.append("duplicate_cell_id")
        if reasons:
            rows.append(
                {
                    "cell_id": cell_id,
                    "primary_role": row.get("primary_role", ""),
                    "exclusion_reason": "|".join(reasons),
                    "recommended_action": "replace_candidate",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
    return pd.DataFrame(rows, columns=["cell_id", "primary_role", "exclusion_reason", "recommended_action", "claim_boundary"])


def candidate_flags(
    design: pd.DataFrame,
    n150_cells: set[str],
    anchor_audit: pd.DataFrame,
    neutral_audit: pd.DataFrame,
    spatial_audit: pd.DataFrame,
) -> pd.DataFrame:
    """Attach candidate-level review flags without removing rows."""
    out = design.copy()
    weak_anchor_cells = set(anchor_audit.loc[anchor_audit["status"].astype(str).ne("PASS"), "nearest_anchor_cell"].astype(str))
    weak_neutral_cells = set(neutral_audit.loc[neutral_audit["status"].astype(str).ne("PASS"), "nearest_neutral_cell"].astype(str))
    weak_spatial_bins = set(spatial_audit.loc[spatial_audit["status"].astype(str).ne("PASS"), "spatial_bin"].astype(str))

    def flags(row: pd.Series) -> str:
        items: list[str] = []
        if str(row.get("cell_id")) in n150_cells:
            items.append("overlap_with_n150")
        if str(row.get("nearest_anchor_cell")) in weak_anchor_cells:
            items.append("anchor_preferred_minimum_shortfall")
        if str(row.get("nearest_neutral_cell")) in weak_neutral_cells and str(row.get("primary_role")) == "neutral_boundary_replication":
            items.append("neutral_boundary_diversity_review")
        if str(row.get("spatial_bin")) in weak_spatial_bins:
            items.append("spatial_bin_balance_review")
        if as_float(row.get("nearest_n150_distance_percentile"), 0.0) >= 0.95:
            items.append("p95_sparse_feature_space_execution_risk")
        elif as_float(row.get("nearest_n150_distance_percentile"), 0.0) >= 0.90:
            items.append("p90_sparse_feature_space_review")
        return "|".join(items) if items else "none"

    out["manual_qa_flags"] = out.apply(flags, axis=1)
    out["candidate_audit_status"] = out["manual_qa_flags"].apply(lambda text: "PASS" if text == "none" else "REVIEW")
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def headline(frame: pd.DataFrame, key_col: str, status_col: str = "status") -> str:
    """Build a terse audit headline."""
    counts = frame[status_col].astype(str).value_counts().to_dict() if status_col in frame.columns else {}
    warn_items = frame.loc[frame[status_col].astype(str).ne("PASS"), key_col].astype(str).tolist() if key_col in frame.columns and status_col in frame.columns else []
    suffix = f"; review={','.join(warn_items[:5])}" if warn_items else ""
    return f"PASS={counts.get('PASS', 0)} WARN={counts.get('WARN', 0)} FAIL={counts.get('FAIL', 0)}{suffix}"


def run(config_path: Path = DEFAULT_CONFIG) -> N300DesignAuditResult:
    """Run the full B8.7 N300 design audit."""
    config = load_config(config_path)
    design = n300_design(config)
    n150_cells = current_n150_label_cells(config)
    audit = input_audit(config, design, n150_cells)
    role = role_balance_audit(config, design)
    spatial = spatial_balance_audit(config, design)
    typology = typology_balance_audit(config, design)
    anchor = anchor_replication_audit(config, design)
    neutral = neutral_replication_audit(config, design)
    sparse = sparse_feature_space_audit(config, design)
    control = control_cell_audit(design)
    exclusions = exclusion_register(design, n150_cells)
    candidates = candidate_flags(design, n150_cells, anchor, neutral, spatial)

    write_csv(audit, output_path(config, "n300_v2_input_audit_path"))
    write_csv(candidates, output_path(config, "n300_design_freeze_candidates_path"))
    write_csv(exclusions, output_path(config, "n300_exclusion_register_path"))
    write_csv(role, output_path(config, "n300_role_balance_audit_path"))
    write_csv(spatial, output_path(config, "n300_spatial_balance_audit_path"))
    write_csv(typology, output_path(config, "n300_typology_balance_audit_path"))
    write_csv(anchor, output_path(config, "n300_anchor_replication_audit_path"))
    write_csv(neutral, output_path(config, "n300_neutral_replication_audit_path"))
    write_csv(sparse, output_path(config, "n300_sparse_feature_space_audit_path"))
    write_csv(control, output_path(config, "n300_control_cell_audit_path"))

    overlap = int(audit.loc[audit["audit_item"].eq("overlap_with_current_n150_labels"), "observed_value"].iloc[0])
    blocking = status_from_checks(audit["status"])
    if blocking == "FAIL":
        status = "B87_BLOCKED_SCHEMA"
    else:
        audit_statuses = pd.concat(
            [role["status"], spatial["status"], typology["status"], anchor["status"], neutral["status"], sparse["status"], control["status"]],
            ignore_index=True,
        )
        status = "B87_N300_DESIGN_PASS" if status_from_checks(audit_statuses) == "PASS" else "B87_N300_DESIGN_NEEDS_QA"
    return N300DesignAuditResult(
        status=status,
        candidate_count=len(design),
        overlap_with_n150=overlap,
        role_headline=headline(role, "primary_role"),
        spatial_headline=headline(spatial, "spatial_bin"),
        typology_headline=headline(typology, "typology"),
        anchor_headline=headline(anchor, "nearest_anchor_cell"),
        neutral_headline=headline(neutral, "nearest_neutral_cell"),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Audit the B8.6f N300 v2 candidate design for B8.7-N300-PRE. "
            "Writes compact audit CSVs only; no SOLWEIG/QGIS/raster/AOI/B9/"
            "WBGT/hazard/risk/manifest/execution output is created."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
