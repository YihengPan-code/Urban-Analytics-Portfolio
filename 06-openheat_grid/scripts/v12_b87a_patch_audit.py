"""Audit B8.7a patched N300 design and write reports/prompts.

Inputs:
    B8.7a v3 patched design, B8.7a manual status/scoring/replacement outputs,
    B8.7 feature coverage audit, B8.6g feature table, current N150 compact cell
    sources, and candidate universe declared in the B8.7a config.
Outputs:
    B8.7a after-patch audit CSVs, manual QA summary, freeze readiness matrix,
    next-lane matrix, future prompts, English report, lane status, and valid
    UTF-8 Chinese documentation.
Saved metrics:
    v3 row count, duplicate cell count, N150 overlap count, role/spatial/
    typology/anchor/neutral/sparse/control/feature coverage status, water queue
    count, replacement count, manual source-review blockers, freeze readiness,
    and next-lane recommendation. This script creates only compact QA/design
    outputs and no raster, QGIS/SOLWEIG, N300 execution manifest, AOI-wide
    prediction, B9, local WBGT, hazard/risk/exposure/vulnerability score,
    observed truth, causal feature importance, Tmrt-to-WBGT conversion, or
    System A/B coupling.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b87a_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    current_n150_cells,
    load_config,
    manual_input_found,
    md_table,
    output_path,
    read_csv,
    read_status_count,
    write_csv,
    write_text,
)


@dataclass(frozen=True)
class PatchAuditResult:
    """B8.7a patch-audit result."""

    status: str
    manual_input_found: bool
    water_queue_count: int
    auto_replacement_candidates: int
    v3_rows: int
    n150_overlap_count: int
    duplicate_cell_count: int
    role_headline: str
    spatial_typology_anchor_neutral_headline: str
    source_review_blocker_headline: str
    next_lane_recommendation: str


def load_v3(config: dict[str, Any]) -> pd.DataFrame:
    """Load B8.7a v3 patched design."""
    path = output_path(config, "n300_design_v3_patched_path")
    if not path.exists():
        raise FileNotFoundError(f"Missing v3 patched design: {path}")
    return read_csv(path)


def status_counts(frame: pd.DataFrame, status_col: str = "status") -> str:
    """Return a PASS/WARN/FAIL headline."""
    if frame.empty or status_col not in frame.columns:
        return "PASS=0 WARN=0 FAIL=0"
    counts = frame[status_col].astype(str).str.upper().value_counts().to_dict()
    return f"PASS={counts.get('PASS', 0)} WARN={counts.get('WARN', 0)} FAIL={counts.get('FAIL', 0)}"


def role_balance(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Recompute required role quota balance."""
    quotas = dict(config["required_role_quota"])
    counts = design["primary_role"].astype(str).value_counts().to_dict() if "primary_role" in design.columns else {}
    rows = []
    for role, quota in quotas.items():
        observed = int(counts.get(role, 0))
        diff = observed - int(quota)
        rows.append(
            {
                "primary_role": role,
                "observed_count": observed,
                "quota": int(quota),
                "difference": diff,
                "status": "PASS" if diff == 0 else "FAIL",
                "recommended_manual_qa": "none" if diff == 0 else "repair role quota before any future precheck",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def spatial_balance(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Recompute target spatial minimums."""
    minimums = dict(config["target_spatial_minimum"])
    counts = design["spatial_bin"].astype(str).value_counts().to_dict() if "spatial_bin" in design.columns else {}
    rows = []
    for spatial_bin, minimum in minimums.items():
        observed = int(counts.get(spatial_bin, 0))
        rows.append(
            {
                "spatial_bin": spatial_bin,
                "observed_count": observed,
                "target_minimum": int(minimum),
                "difference": observed - int(minimum),
                "status": "PASS" if observed >= int(minimum) else "WARN",
                "recommended_manual_qa": "none" if observed >= int(minimum) else f"{spatial_bin} remains below B8.7a target minimum",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def typology_balance(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Recompute typology concentration/undercoverage checks."""
    counts = design["typology"].astype(str).value_counts().to_dict() if "typology" in design.columns else {}
    total = max(1, len(design))
    typologies = sorted(set(counts).union({"park_open_space", "commercial", "residential", "transport", "water"}))
    rows = []
    for typology in typologies:
        observed = int(counts.get(typology, 0))
        status = "PASS"
        qa = "none"
        if typology in {"residential", "transport"} and observed > 50:
            status = "WARN"
            qa = "residential/transport concentration remains for reviewer acceptance"
        if typology == "park_open_space" and observed < 5:
            status = "WARN"
            qa = "park_open_space remains undercovered; review feasibility and pure-surface exclusions"
        rows.append(
            {
                "typology": typology,
                "observed_count": observed,
                "observed_share": observed / total,
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
            "status": "WARN" if combined / total > 0.70 else "PASS",
            "recommended_manual_qa": "combined residential+transport remains concentrated" if combined / total > 0.70 else "none",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )
    return pd.DataFrame(rows)


def anchor_balance(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Recompute preferred anchor replication support."""
    minimums = dict(config["preferred_anchor_minimum"])
    counts = design["nearest_anchor_cell"].astype(str).value_counts().to_dict() if "nearest_anchor_cell" in design.columns else {}
    rows = []
    for anchor, minimum in minimums.items():
        observed = int(counts.get(anchor, 0))
        rows.append(
            {
                "nearest_anchor_cell": anchor,
                "observed_count": observed,
                "preferred_minimum": int(minimum),
                "difference": observed - int(minimum),
                "status": "PASS" if observed >= int(minimum) else "WARN",
                "recommended_manual_qa": "none" if observed >= int(minimum) else "anchor preferred-minimum shortfall remains",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def neutral_balance(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Recompute neutral diversity support."""
    neutral_role = design.loc[design["primary_role"].astype(str).eq("neutral_boundary_replication")].copy() if "primary_role" in design.columns else design.iloc[0:0].copy()
    counts = neutral_role["nearest_neutral_cell"].astype(str).value_counts().to_dict() if "nearest_neutral_cell" in neutral_role.columns else {}
    min_count = int(config.get("neutral_group_min_count", 5))
    min_groups = int(config.get("preferred_neutral_minimum_groups_at_minimum", 3))
    groups_at_min = sum(1 for value in counts.values() if int(value) >= min_count)
    cells = sorted(set(config.get("neutral_underrepresented_cells", [])).union(counts.keys()))
    rows = []
    for cell in cells:
        observed = int(counts.get(cell, 0))
        rows.append(
            {
                "nearest_neutral_cell": cell,
                "neutral_boundary_role_count": observed,
                "preferred_group_minimum": min_count,
                "status": "PASS",
                "recommended_manual_qa": "review low/zero support for neutral diversity context" if cell in set(config.get("neutral_underrepresented_cells", [])) and observed < min_count else "none",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    rows.append(
        {
            "nearest_neutral_cell": "summary_groups_at_minimum",
            "neutral_boundary_role_count": groups_at_min,
            "preferred_group_minimum": min_groups,
            "status": "PASS" if groups_at_min >= min_groups else "WARN",
            "recommended_manual_qa": "neutral diversity preferred minimum not met" if groups_at_min < min_groups else "none",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )
    return pd.DataFrame(rows)


def sparse_audit(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Recompute sparse feature-space checks."""
    values = pd.to_numeric(design.get("nearest_n150_distance_percentile"), errors="coerce")
    p90 = float(config.get("sparse_p90_threshold", 0.90))
    p95 = float(config.get("sparse_p95_threshold", 0.95))
    sparse_role_count = int(design.get("primary_role", pd.Series(dtype=str)).astype(str).eq("sparse_feature_space").sum())
    rows = [
        {
            "audit_item": "p90_or_higher_candidates",
            "observed_count": int((values >= p90).sum()),
            "threshold": p90,
            "status": "WARN" if int((values >= p90).sum()) > int(config["required_role_quota"]["sparse_feature_space"]) else "PASS",
            "recommended_manual_qa": "many high-distance candidates remain; keep as design QA risk",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "audit_item": "p95_or_higher_candidates",
            "observed_count": int((values >= p95).sum()),
            "threshold": p95,
            "status": "WARN" if int((values >= p95).sum()) > 0 else "PASS",
            "recommended_manual_qa": "p95 candidates should remain manual-review items",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "audit_item": "sparse_feature_space_role_count",
            "observed_count": sparse_role_count,
            "threshold": int(config["required_role_quota"]["sparse_feature_space"]),
            "status": "PASS" if sparse_role_count == int(config["required_role_quota"]["sparse_feature_space"]) else "FAIL",
            "recommended_manual_qa": "none" if sparse_role_count == int(config["required_role_quota"]["sparse_feature_space"]) else "restore sparse-feature role quota",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    return pd.DataFrame(rows)


def control_audit(design: pd.DataFrame) -> pd.DataFrame:
    """Recompute control-cell diversity checks."""
    controls = design.loc[design["primary_role"].astype(str).eq("control_cell")].copy() if "primary_role" in design.columns else design.iloc[0:0].copy()
    if controls.empty:
        return pd.DataFrame(
            [
                {
                    "audit_item": "control_cell_presence",
                    "observed_value": 0,
                    "status": "FAIL",
                    "recommended_manual_qa": "restore control cells",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            ]
        )
    spatial_diversity = int(controls["spatial_bin"].astype(str).nunique()) if "spatial_bin" in controls.columns else 0
    typology_diversity = int(controls["typology"].astype(str).nunique()) if "typology" in controls.columns else 0
    rows = [
        {
            "audit_item": "control_spatial_diversity",
            "observed_value": spatial_diversity,
            "status": "PASS" if spatial_diversity >= 2 else "WARN",
            "recommended_manual_qa": "none" if spatial_diversity >= 2 else "review control spatial concentration",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "audit_item": "control_typology_diversity",
            "observed_value": typology_diversity,
            "status": "PASS" if typology_diversity >= 2 else "WARN",
            "recommended_manual_qa": "none" if typology_diversity >= 2 else "review control typology concentration",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "audit_item": "control_cell_count",
            "observed_value": len(controls),
            "status": "PASS" if len(controls) == 10 else "FAIL",
            "recommended_manual_qa": "none" if len(controls) == 10 else "restore control-cell quota",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    return pd.DataFrame(rows)


def feature_coverage(config: dict[str, Any], design: pd.DataFrame) -> pd.DataFrame:
    """Audit compact feature coverage for v3 design rows."""
    features = read_csv(config["b86g_n300_feature_dataset_path"])
    feature_ids = set(features["cell_id"].astype(str)) if "cell_id" in features.columns else set()
    design_ids = set(design["cell_id"].astype(str)) if "cell_id" in design.columns else set()
    missing = sorted(design_ids - feature_ids)
    b87_coverage = read_csv(config["b87_feature_coverage_path"])
    connected = b87_coverage.loc[b87_coverage["feature_family"].astype(str).str.contains("connected shade corridor", case=False, na=False)].head(1)
    rows = [
        {
            "audit_scope": "v3_design",
            "feature_family": "b86g_compact_candidate_feature_rows",
            "observed_value": len(design_ids) - len(missing),
            "expected_value": len(design_ids),
            "status": "PASS" if not missing else "WARN",
            "evidence": "missing_cell_ids=" + ("|".join(missing[:20]) if missing else "none"),
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "audit_scope": "source_gap",
            "feature_family": "connected shade corridor / shade continuity",
            "observed_value": connected.iloc[0].get("feature_coverage_status", "not_available") if not connected.empty else "not_reviewed",
            "expected_value": "future B86G3 source acquisition",
            "status": "WARN",
            "evidence": "known source gap; not a candidate-design execution blocker in B8.7a",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    return pd.DataFrame(rows)


def freeze_status(
    config: dict[str, Any],
    design: pd.DataFrame,
    role: pd.DataFrame,
    spatial: pd.DataFrame,
    typology: pd.DataFrame,
    anchor: pd.DataFrame,
    neutral: pd.DataFrame,
    feature: pd.DataFrame,
) -> tuple[str, pd.DataFrame, str]:
    """Compute freeze readiness status and matrix."""
    manual_found = manual_input_found(config)
    n150_overlap = len(set(design["cell_id"].astype(str)).intersection(current_n150_cells(config)))
    duplicate_count = int(design["cell_id"].duplicated().sum())
    role_ok = bool(role["status"].astype(str).eq("PASS").all())
    candidate_count_ok = len(design) == int(config["expected_candidate_count"])
    patch_log = read_csv(output_path(config, "candidate_patch_log_path")) if output_path(config, "candidate_patch_log_path").exists() else pd.DataFrame()
    blocked = int(patch_log.get("patch_action", pd.Series(dtype=str)).astype(str).eq("blocked_no_replacement").sum()) if not patch_log.empty else 0
    manual_source_blockers = int(design.get("patch_source", pd.Series(dtype=str)).astype(str).eq("manual_source_review_kept").sum())
    critical_ok = candidate_count_ok and n150_overlap == 0 and duplicate_count == 0 and role_ok and blocked == 0
    warning_frames = [spatial, typology, anchor, neutral]
    warning_count = sum(int(frame["status"].astype(str).str.upper().eq("WARN").sum()) for frame in warning_frames if not frame.empty)
    feature_known_gap = int(feature["status"].astype(str).str.upper().eq("WARN").sum()) if not feature.empty else 0

    if not manual_found:
        status = "B87A_WAITING_FOR_MANUAL_QA"
    elif not critical_ok:
        status = "B87A_PATCH_BLOCKED"
    elif warning_count == 0 and manual_source_blockers == 0:
        status = "B87A_N300_DESIGN_FREEZE_READY"
    else:
        status = "B87A_PATCHED_DESIGN_READY_FOR_REVIEW"

    rows = [
        ("manual_input", "PASS" if manual_found else "WAITING", "manual input found" if manual_found else "manual input missing; template produced"),
        ("candidate_count", "PASS" if candidate_count_ok else "FAIL", f"rows={len(design)} expected={config['expected_candidate_count']}"),
        ("n150_overlap", "PASS" if n150_overlap == 0 else "FAIL", f"overlap_count={n150_overlap}"),
        ("duplicate_cell_id", "PASS" if duplicate_count == 0 else "FAIL", f"duplicate_count={duplicate_count}"),
        ("role_quota", "PASS" if role_ok else "FAIL", status_counts(role)),
        ("manual_patch_blockers", "PASS" if blocked == 0 else "FAIL", f"blocked_replacements={blocked}"),
        ("spatial_balance", "PASS" if not spatial["status"].astype(str).eq("WARN").any() else "WARN", status_counts(spatial)),
        ("typology_balance", "PASS" if not typology["status"].astype(str).eq("WARN").any() else "WARN", status_counts(typology)),
        ("anchor_replication", "PASS" if not anchor["status"].astype(str).eq("WARN").any() else "WARN", status_counts(anchor)),
        ("neutral_replication", "PASS" if not neutral["status"].astype(str).eq("WARN").any() else "WARN", status_counts(neutral)),
        ("feature_source_gap", "WARN" if feature_known_gap else "PASS", "connected shade corridor source remains future B86G3 item"),
        ("final_freeze_readiness", status, "B8.7a remains design QA only; even freeze-ready does not allow SOLWEIG execution"),
    ]
    matrix = pd.DataFrame(
        [
            {
                "decision_item": item,
                "status": row_status,
                "evidence": evidence,
                "claim_boundary": CLAIM_BOUNDARY,
            }
            for item, row_status, evidence in rows
        ]
    )
    source_headline = (
        f"manual_source_review_blockers={manual_source_blockers}; "
        "known_connected_shade_corridor_gap=carried_to_B86G3"
    )
    return status, matrix, source_headline


def next_lane_matrix(status: str) -> pd.DataFrame:
    """Create B8.7a next-lane decision matrix."""
    b87b_decision = "wait_for_manual_QA" if status == "B87A_WAITING_FOR_MANUAL_QA" else "review_then_B8.7b_execution_precheck"
    rows = [
        {
            "future_lane": "B8.7b-N300-execution-precheck",
            "decision": b87b_decision,
            "recommended_priority": "after_manual_QA_and_review_acceptance",
            "allowed_scope": "future precheck only; no SOLWEIG execution in B8.7a",
            "forbidden_actions": "no QGIS run, no SOLWEIG run, no raster, no AOI/B9, no WBGT/hazard/risk",
            "b87a_status": status,
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "B8.6g3 true-vector feature acquisition",
            "decision": "recommended",
            "recommended_priority": "high",
            "allowed_scope": "connected shade corridor, pedestrian network, covered walkway, building/canyon vector geometry",
            "forbidden_actions": "no raster I/O, no SOLWEIG/QGIS, no AOI/B9, no observed-truth or causal claims",
            "b87a_status": status,
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "AOI/B9",
            "decision": "blocked",
            "recommended_priority": "none",
            "allowed_scope": "none",
            "forbidden_actions": "keep AOI and B9 blocked",
            "b87a_status": status,
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    return pd.DataFrame(rows)


def prompt_b87b(status: str) -> str:
    """Return future B8.7b prompt text."""
    return f"""# Future Prompt: B8.7b N300 Execution Precheck

Use only after B8.7a manual QA and reviewer acceptance.

Status entering prompt: `{status}`.

Scope: future execution precheck only. Do not run SOLWEIG, do not run QGIS, do
not read or write rasters, and do not create AOI-wide prediction, B9, local
WBGT, hazard_score, risk_score, exposure/vulnerability score, observed-truth,
causal feature-importance, Tmrt-to-WBGT conversion, or System A/B coupling
outputs.

Allowed future work: check compact design readiness and, only after manual QA
acceptance, prepare a reviewable readiness/manifest draft. Do not include local
runner instructions for actual execution.
"""


def prompt_b86g3(status: str) -> str:
    """Return future B8.6g3 true-vector feature acquisition prompt."""
    return f"""# Future Prompt: B8.6g3 True-Vector Feature Acquisition

Status entering prompt: `{status}`.

Focus on source-backed compact vector features for connected shade corridors,
pedestrian network, covered walkway geometry, overhead geometry, and
building/canyon vector geometry.

Do not use rasters. Do not run QGIS or SOLWEIG. Do not create AOI-wide
prediction, B9, local WBGT, hazard_score, risk_score, exposure/vulnerability
score, observed-truth, causal feature-importance, Tmrt-to-WBGT conversion, or
System A/B coupling outputs.
"""


def manual_summary(
    config: dict[str, Any],
    status: str,
    water_count: int,
    replacement_count: int,
    v3_rows: int,
    n150_overlap: int,
    duplicate_count: int,
) -> str:
    """Build the manual QA summary Markdown."""
    manual_found = manual_input_found(config)
    manual_status = read_csv(output_path(config, "manual_review_status_path")) if output_path(config, "manual_review_status_path").exists() else pd.DataFrame()
    return f"""# B8.7a Manual QA Summary

Status: `{status}`

- Manual input found: `{'yes' if manual_found else 'no'}`
- Water / pure-river review queue count: `{water_count}`
- Auto replacement candidates: `{replacement_count}`
- v3 design row count: `{v3_rows}`
- N150 overlap count: `{n150_overlap}`
- Duplicate cell count: `{duplicate_count}`

## Manual Review Status

{md_table(manual_status, ['status_item', 'value', 'status', 'evidence'])}

If manual input is missing, this is AUTO_ONLY and waiting for human review. It
is acceptable to review only obvious exclusions such as pure river/water-only
cells or cells mostly outside pedestrian-relevant land.

## Guardrails

No raster, no QGIS/SOLWEIG, no N300 execution manifest, no AOI-wide prediction,
no B9, no local WBGT, no hazard/risk/exposure/vulnerability score, no observed
truth, no causal feature importance, no Tmrt-to-WBGT conversion, and no System
A/B coupling were created.
"""


def report_text(
    status: str,
    manual_found: bool,
    water_count: int,
    replacement_count: int,
    v3_rows: int,
    role: pd.DataFrame,
    spatial: pd.DataFrame,
    typology: pd.DataFrame,
    anchor: pd.DataFrame,
    neutral: pd.DataFrame,
    freeze: pd.DataFrame,
    source_headline: str,
) -> str:
    """Build the English B8.7a report."""
    return f"""# B8.7a N300 Design QA Patch Report

Status: `{status}`

## 1. Why B8.7a follows B8.7

B8.7 ended as `B87_N300_DESIGN_NEEDS_QA`: the N300 design had 150 candidate
rows, zero overlap with current N150 labels, exact role quotas, and several
manual-review warnings. B8.7a reduces manual QA burden and prepares a patched
candidate-design table without creating execution artifacts.

## 2. B8.7 Warning Summary

- Spatial: west_south was below the B8.7a target minimum.
- Typology: residential/transport concentration remains a review item, and
  park_open_space remains sparse.
- Anchor replication: TP_0037 and TP_0433 remain review contexts unless patched.
- Neutral replication: diversity across preferred neutral groups remains a
  review context.
- Sparse/OOD: high nearest-N150 distance candidates remain review items.
- Connected shade corridor source remains unavailable for this lane.

## 3. Manual QA Workflow

Manual input found: `{'yes' if manual_found else 'no'}`. The template and
instructions support quick review of obvious exclusions, especially pure
river/water-only cells and pedestrian-relevance mismatches.

## 4. Auto QA Scoring

The auto scoring flags water/pure-river risk, outside-pedestrian relevance,
west_south, residential/transport concentration, park/commercial context,
anchor/neutral contexts, sparse/OOD risk, connected-shade source absence, and
feature coverage gaps.

## 5. Water / Pure River Review Queue

Queue count: `{water_count}`.

## 6. Candidate Replacements

Auto replacement candidates ranked: `{replacement_count}`. Replacements are
candidate-design rows only and are not run-ready.

## 7. v3 Design Status

v3 design row count: `{v3_rows}`.

## 8. After-Patch Audit

Role balance: {status_counts(role)}

Spatial balance: {status_counts(spatial)}

Typology balance: {status_counts(typology)}

Anchor replication: {status_counts(anchor)}

Neutral replication: {status_counts(neutral)}

Source-review blockers: {source_headline}

## 9. Freeze Readiness

{md_table(freeze, ['decision_item', 'status', 'evidence'])}

## 10. Next Lane Recommendation

If manual QA is absent, finish manual QA first. After manual QA and review
acceptance, the next lane can be B8.7b execution precheck only. B8.6g3
true-vector feature acquisition remains recommended for connected shade
corridor and pedestrian/covered-walkway source gaps.

## 11. Claim Boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not risk / hazard score.
- Not exposure/vulnerability scoring.
- Not observed truth.
- Not causal feature importance.
- No raster.
- No QGIS / SOLWEIG.
- No N300 execution manifest.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
"""


def status_text(
    status: str,
    manual_found: bool,
    water_count: int,
    replacement_count: int,
    v3_rows: int,
    n150_overlap: int,
    duplicate_count: int,
    role_headline: str,
    combined_headline: str,
    source_headline: str,
) -> str:
    """Build B8.7a status Markdown."""
    return f"""# B8.7a Status

Status: {status}
Branch: codex/b87a-n300-design-qa-patch
Scope: N300 candidate-design QA reducer and patch package only; no execution artifacts.

## Commands Run By Suite

- `python scripts/v12_b87a_run_design_qa_patch.py --config configs/v12/systemb_b87a_n300_design_qa_patch.yaml`

## Key Results

- Manual input found: {'yes' if manual_found else 'no'}
- Water / pure-river review queue count: {water_count}
- Auto replacement candidates count: {replacement_count}
- v3 design row count: {v3_rows}
- N150 overlap count: {n150_overlap}
- Duplicate cell count: {duplicate_count}
- Role balance: {role_headline}
- Spatial/typology/anchor/neutral: {combined_headline}
- Source-review blockers: {source_headline}

## Caveats

This lane is AUTO_ONLY when manual input is missing and must remain waiting for
manual QA. Even a future freeze-ready status would not authorize SOLWEIG or
QGIS execution.

## Not Created

No raster, QGIS/SOLWEIG run, N300 execution manifest, local runner, AOI-wide
prediction, B9 output, local WBGT, hazard_score, risk_score,
exposure/vulnerability score, observed-truth claim, causal feature-importance
claim, Tmrt-to-WBGT conversion, or System A/B coupling.
"""


def cn_doc_text(status: str, manual_found: bool, water_count: int, replacement_count: int, v3_rows: int, source_headline: str) -> str:
    """Build valid UTF-8 Chinese documentation."""
    return f"""# OpenHeat System B B8.7a N300 设计 QA 降负与补丁说明

## 结论

- B8.7a 状态：`{status}`
- 是否发现人工 QA 输入：`{'yes' if manual_found else 'no'}`
- 水体 / 纯河道快速复核队列：`{water_count}` 行
- 自动替换候选池：`{replacement_count}` 行
- v3 设计表行数：`{v3_rows}` 行

## 为什么 B8.7a 接在 B8.7 后面

B8.7 已经生成 150 个 N300 候选单元，并确认与当前 N150 标签没有重叠，角色配额也保持严格平衡。但它仍然存在 west_south 支持不足、住宅 / 交通类型集中、TP_0037 与 TP_0433 锚点复核、中性边界多样性、稀疏特征空间以及 connected shade corridor 来源缺口等人工 QA 问题。因此 B8.7a 只做 QA 降负、人工模板、自动复核标记、候选替换池和 v3 设计草案。

## 人工 QA 工作流

优先检查水体、河道或纯表面候选；其次检查 west_south；然后检查 TP_0037 / TP_0433 锚点类候选；再检查中性多样性；最后检查 park_open_space / commercial 覆盖不足以及 residential / transport 集中。只检查明显应排除的单元也可以；不确定的行会保留为 REVIEW，而不是自动排除。

## 当前状态解释

如果人工 QA 输入缺失，v3 表是 `DRAFT_AUTO_ONLY`，候选集合与 B8.7 保持一致，只增加补丁状态和 QA 标记。人工输入提供后，脚本会按 `exclude` / `replace` / `source_review` 等决策应用补丁，并尽量保持 150 行、无 N150 重叠、无重复、角色配额不变。

## 来源复核

{source_headline}。connected shade corridor 仍需未来 B8.6g3 获取或核查行人遮阴网络、covered walkway 或等价矢量来源；本轮不会从质心距离推断连通性。

## 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 hazard score 或 risk score。
- 不是 exposure / vulnerability score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 QGIS 或 SOLWEIG。
- 没有创建 N300 execution manifest。
- 没有 Tmrt-to-WBGT 转换。
- 没有 System A/B coupling。
"""


def run(config_path: Path = DEFAULT_CONFIG) -> PatchAuditResult:
    """Run B8.7a after-patch audits and write reports."""
    config = load_config(config_path)
    design = load_v3(config)
    role = role_balance(config, design)
    spatial = spatial_balance(config, design)
    typology = typology_balance(config, design)
    anchor = anchor_balance(config, design)
    neutral = neutral_balance(config, design)
    sparse = sparse_audit(config, design)
    control = control_audit(design)
    feature = feature_coverage(config, design)

    write_csv(role, output_path(config, "role_balance_after_patch_path"))
    write_csv(spatial, output_path(config, "spatial_balance_after_patch_path"))
    write_csv(typology, output_path(config, "typology_balance_after_patch_path"))
    write_csv(anchor, output_path(config, "anchor_replication_after_patch_path"))
    write_csv(neutral, output_path(config, "neutral_replication_after_patch_path"))
    write_csv(sparse, output_path(config, "sparse_feature_space_after_patch_path"))
    write_csv(control, output_path(config, "control_cell_after_patch_path"))
    write_csv(feature, output_path(config, "feature_coverage_after_patch_path"))

    status, freeze, source_headline = freeze_status(config, design, role, spatial, typology, anchor, neutral, feature)
    next_lane = next_lane_matrix(status)
    write_csv(freeze, output_path(config, "freeze_readiness_matrix_path"))
    write_csv(next_lane, output_path(config, "next_lane_decision_matrix_path"))

    water_count = len(read_csv(output_path(config, "water_pure_river_review_queue_path"))) if output_path(config, "water_pure_river_review_queue_path").exists() else 0
    replacement_count = len(read_csv(output_path(config, "auto_replacement_pool_path"))) if output_path(config, "auto_replacement_pool_path").exists() else 0
    n150_overlap = len(set(design["cell_id"].astype(str)).intersection(current_n150_cells(config)))
    duplicate_count = int(design["cell_id"].duplicated().sum())
    role_headline = status_counts(role)
    combined_headline = f"spatial {status_counts(spatial)}; typology {status_counts(typology)}; anchor {status_counts(anchor)}; neutral {status_counts(neutral)}"
    next_recommendation = "manual QA first, then B8.7b execution precheck only" if status == "B87A_WAITING_FOR_MANUAL_QA" else "review patched design, then B8.7b execution precheck only"

    write_text(prompt_b87b(status), output_path(config, "codex_prompt_b87b_path"))
    write_text(prompt_b86g3(status), output_path(config, "codex_prompt_b86g3_path"))
    write_text(manual_summary(config, status, water_count, replacement_count, len(design), n150_overlap, duplicate_count), output_path(config, "manual_qa_summary_path"))
    write_text(
        report_text(status, manual_input_found(config), water_count, replacement_count, len(design), role, spatial, typology, anchor, neutral, freeze, source_headline),
        output_path(config, "report_path"),
    )
    write_text(status_text(status, manual_input_found(config), water_count, replacement_count, len(design), n150_overlap, duplicate_count, role_headline, combined_headline, source_headline), output_path(config, "status_path"))
    write_text(cn_doc_text(status, manual_input_found(config), water_count, replacement_count, len(design), source_headline), output_path(config, "cn_doc_path"))

    return PatchAuditResult(
        status=status,
        manual_input_found=manual_input_found(config),
        water_queue_count=water_count,
        auto_replacement_candidates=replacement_count,
        v3_rows=len(design),
        n150_overlap_count=n150_overlap,
        duplicate_cell_count=duplicate_count,
        role_headline=role_headline,
        spatial_typology_anchor_neutral_headline=combined_headline,
        source_review_blocker_headline=source_headline,
        next_lane_recommendation=next_recommendation,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Audit B8.7a patched N300 design and write compact reports/prompts. "
            "No QGIS/SOLWEIG/raster/manifest/AOI/B9/WBGT/hazard/risk output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
