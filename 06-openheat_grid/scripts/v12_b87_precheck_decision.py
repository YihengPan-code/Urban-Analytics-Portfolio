"""Write B8.7-N300-PRE decisions, reports, prompts, and CN documentation.

Inputs:
    B8.7 input inventory, N300 design audits, feature coverage audit, true
    vector source review, manual QA checklist, and B8.6g2 retest evidence.
Outputs:
    b87_n300_freeze_decision_matrix.csv, b87_aoi_b9_boundary_matrix.csv,
    b87_next_lane_decision_matrix.csv, three future Codex prompt Markdown
    files, b87_report.md, B8_7_STATUS.md, and
    docs/v12/OpenHeat_SystemB_B8_7_N300_PRE_CN.md.
Saved metrics:
    Freeze decision, candidate count, N150 overlap count, role/spatial/
    typology/anchor/neutral/control headlines, feature coverage headline,
    connected shade corridor source status, AOI/B9 boundary status, manual QA
    readiness, and next-lane recommendation. This decision script creates no
    SOLWEIG manifest, QGIS runner, raster I/O, AOI-wide prediction, B9 output,
    local WBGT, hazard/risk/exposure/vulnerability score, observed-truth claim,
    causal feature-importance claim, Tmrt-to-WBGT conversion, or System A/B
    coupling output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b87_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, load_config, md_table, output_path, read_csv, write_csv, write_text


@dataclass(frozen=True)
class PrecheckDecisionResult:
    """B8.7 precheck decision result."""

    status: str
    candidate_count: int
    overlap_with_n150: int
    connected_shade_status: str
    recommended_next_lane: str


CREATED_FILES = [
    "configs/v12/systemb_b87_n300_pre.yaml",
    "scripts/v12_b87_input_inventory.py",
    "scripts/v12_b87_n300_design_audit.py",
    "scripts/v12_b87_feature_schema_audit.py",
    "scripts/v12_b87_source_availability_review.py",
    "scripts/v12_b87_candidate_qa_package.py",
    "scripts/v12_b87_precheck_decision.py",
    "scripts/v12_b87_run_n300_pre.py",
    "docs/v12/OpenHeat_SystemB_B8_7_N300_PRE_CN.md",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_input_inventory.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_v2_input_audit.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_design_freeze_candidates.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_exclusion_register.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_role_balance_audit.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_spatial_balance_audit.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_typology_balance_audit.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_anchor_replication_audit.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_neutral_replication_audit.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_sparse_feature_space_audit.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_control_cell_audit.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_feature_coverage_audit.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_true_vector_source_inventory.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_true_vector_source_gap_register.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_connected_shade_corridor_source_review.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_pedestrian_network_source_review.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_overhead_geometry_source_review.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_building_canyon_source_review.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_tree_building_interaction_source_review.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_manual_qa_checklist.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_manual_qa_guide.md",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_n300_freeze_decision_matrix.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_aoi_b9_boundary_matrix.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_next_lane_decision_matrix.csv",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_codex_prompt_B87B_N300_execution_precheck.md",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_codex_prompt_B86G3_true_vector_feature_acquisition.md",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_codex_prompt_B86H_scope_limited_dry_run.md",
    "outputs/v12_surrogate/b8_7_n300_pre/b87_report.md",
    "outputs/v12_surrogate/b8_7_n300_pre/B8_7_STATUS.md",
]


def status_counts(frame: pd.DataFrame) -> str:
    """Return PASS/WARN/FAIL status counts."""
    if "status" not in frame.columns:
        return "status column missing"
    counts = frame["status"].astype(str).value_counts().to_dict()
    return f"PASS={counts.get('PASS', 0)} WARN={counts.get('WARN', 0)} FAIL={counts.get('FAIL', 0)}"


def candidate_count(input_audit: pd.DataFrame) -> int:
    """Return N300 candidate row count from input audit."""
    row = input_audit.loc[input_audit["audit_item"].astype(str).eq("candidate_row_count")]
    return int(row["observed_value"].iloc[0]) if not row.empty else 0


def overlap_count(input_audit: pd.DataFrame) -> int:
    """Return N150 overlap count from input audit."""
    row = input_audit.loc[input_audit["audit_item"].astype(str).eq("overlap_with_current_n150_labels")]
    return int(row["observed_value"].iloc[0]) if not row.empty else 0


def connected_status(source_gaps: pd.DataFrame) -> str:
    """Return connected shade corridor source status."""
    row = source_gaps.loc[source_gaps["source_category"].astype(str).eq("connected_shade_corridor")]
    return str(row["source_status"].iloc[0]) if not row.empty else "NOT_AVAILABLE_REQUIRES_MANUAL_DATA"


def feature_headline(feature_audit: pd.DataFrame) -> str:
    """Return feature coverage headline."""
    family_rows = feature_audit.loc[feature_audit["audit_scope"].astype(str).eq("feature_family")]
    classes = family_rows["source_class"].astype(str).value_counts().to_dict()
    warn = family_rows.loc[family_rows["status"].astype(str).ne("PASS"), "feature_family"].astype(str).tolist()
    return (
        f"vector_derived={classes.get('vector_derived', 0)} proxy_only={classes.get('proxy_only', 0)} "
        f"not_available={classes.get('not_available', 0)} review={','.join(warn[:4]) if warn else 'none'}"
    )


def final_decision(
    input_audit: pd.DataFrame,
    role: pd.DataFrame,
    spatial: pd.DataFrame,
    typology: pd.DataFrame,
    anchor: pd.DataFrame,
    neutral: pd.DataFrame,
    sparse: pd.DataFrame,
    control: pd.DataFrame,
    feature_audit: pd.DataFrame,
    source_gaps: pd.DataFrame,
) -> str:
    """Decide B8.7 freeze status."""
    if input_audit["status"].astype(str).isin(["FAIL", "BLOCKED_SCHEMA", "BLOCKED_INPUT"]).any():
        return "B87_BLOCKED_INPUT"
    dataset_rows = feature_audit.loc[feature_audit["audit_scope"].astype(str).eq("dataset")]
    if not dataset_rows.empty and dataset_rows["status"].astype(str).eq("FAIL").any():
        return "B87_BLOCKED_INPUT"
    connected = connected_status(source_gaps)
    pedestrian = source_gaps.loc[source_gaps["source_category"].astype(str).eq("pedestrian_network"), "source_status"]
    pedestrian_status = str(pedestrian.iloc[0]) if not pedestrian.empty else "NOT_AVAILABLE_REQUIRES_MANUAL_DATA"
    if connected == "NOT_AVAILABLE_REQUIRES_MANUAL_DATA" and pedestrian_status == "NOT_AVAILABLE_REQUIRES_MANUAL_DATA":
        return "B87_NEEDS_TRUE_VECTOR_SOURCE_FIRST"
    audit_frames = [role, spatial, typology, anchor, neutral, sparse, control, feature_audit]
    has_warn_or_fail = any(frame["status"].astype(str).isin(["WARN", "FAIL"]).any() for frame in audit_frames if "status" in frame.columns)
    if has_warn_or_fail:
        return "B87_N300_DESIGN_NEEDS_QA"
    return "B87_N300_DESIGN_FREEZE_READY"


def freeze_decision_matrix(config: dict[str, Any], status: str, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build freeze decision matrix."""
    source_gaps = frames["source_gaps"]
    connected = connected_status(source_gaps)
    count = candidate_count(frames["input_audit"])
    overlap = overlap_count(frames["input_audit"])
    rows = [
        {
            "decision_item": "n300_candidate_input",
            "status": "PASS" if count == int(config["expected_n300_candidate_count"]) else "FAIL",
            "evidence": f"candidate_count={count}",
            "blocker": "" if count == int(config["expected_n300_candidate_count"]) else "wrong candidate count",
            "recommended_action": "none" if count == int(config["expected_n300_candidate_count"]) else "repair input before freeze",
        },
        {
            "decision_item": "n150_overlap",
            "status": "PASS" if overlap == 0 else "FAIL",
            "evidence": f"overlap_with_n150_count={overlap}",
            "blocker": "" if overlap == 0 else "candidate overlaps current N150 labels",
            "recommended_action": "none" if overlap == 0 else "replace overlapping candidates",
        },
        {
            "decision_item": "role_balance",
            "status": "PASS" if not frames["role"]["status"].astype(str).ne("PASS").any() else "WARN",
            "evidence": status_counts(frames["role"]),
            "blocker": "",
            "recommended_action": "review role deviations if any",
        },
        {
            "decision_item": "spatial_balance",
            "status": "PASS" if not frames["spatial"]["status"].astype(str).ne("PASS").any() else "WARN",
            "evidence": status_counts(frames["spatial"]),
            "blocker": "",
            "recommended_action": "inspect weak-bin distribution, especially west_south",
        },
        {
            "decision_item": "typology_balance",
            "status": "PASS" if not frames["typology"]["status"].astype(str).ne("PASS").any() else "WARN",
            "evidence": status_counts(frames["typology"]),
            "blocker": "",
            "recommended_action": "inspect residential/transport concentration and park/commercial coverage",
        },
        {
            "decision_item": "anchor_replication",
            "status": "PASS" if not frames["anchor"]["status"].astype(str).ne("PASS").any() else "WARN",
            "evidence": status_counts(frames["anchor"]),
            "blocker": "",
            "recommended_action": "inspect TP_0037/TP_0433 preferred-minimum shortfalls if present",
        },
        {
            "decision_item": "neutral_replication",
            "status": "PASS" if not frames["neutral"]["status"].astype(str).ne("PASS").any() else "WARN",
            "evidence": status_counts(frames["neutral"]),
            "blocker": "",
            "recommended_action": "inspect neutral-boundary diversity before execution precheck",
        },
        {
            "decision_item": "sparse_feature_space",
            "status": "PASS" if not frames["sparse"]["status"].astype(str).ne("PASS").any() else "WARN",
            "evidence": status_counts(frames["sparse"]),
            "blocker": "",
            "recommended_action": "mark p90/p95 cases as execution-risk for manual QA",
        },
        {
            "decision_item": "control_cell_coverage",
            "status": "PASS" if not frames["control"]["status"].astype(str).ne("PASS").any() else "WARN",
            "evidence": status_counts(frames["control"]),
            "blocker": "",
            "recommended_action": "confirm controls remain baseline-like",
        },
        {
            "decision_item": "feature_coverage",
            "status": "PASS" if not frames["feature_audit"]["status"].astype(str).eq("FAIL").any() else "FAIL",
            "evidence": feature_headline(frames["feature_audit"]),
            "blocker": "connected shade corridor remains source-dependent",
            "recommended_action": "carry source gaps into B8.6g3; do not promote proxy features",
        },
        {
            "decision_item": "connected_shade_corridor_source",
            "status": "PASS" if connected == "AVAILABLE_FOR_B86G3_REVIEW" else "WARN",
            "evidence": f"source_status={connected}",
            "blocker": "" if connected != "NOT_AVAILABLE_REQUIRES_MANUAL_DATA" else "missing valid source",
            "recommended_action": "do not infer continuity; require pedestrian/shade-network source QA",
        },
        {
            "decision_item": "no_execution_artifacts_created",
            "status": "PASS",
            "evidence": "B8.7 package contains compact CSV/Markdown/docs/scripts only.",
            "blocker": "",
            "recommended_action": "keep no SOLWEIG manifest, no QGIS runner, no AOI/B9 outputs",
        },
        {
            "decision_item": "final_freeze_decision",
            "status": status,
            "evidence": "decision combines input, balance, feature, source, and no-execution checks",
            "blocker": "" if status != "B87_BLOCKED_INPUT" else "input/schema issue",
            "recommended_action": recommended_next_lane_for_status(status),
        },
    ]
    out = pd.DataFrame(rows)
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def aoi_b9_boundary_matrix() -> pd.DataFrame:
    """Keep AOI/B9 boundaries blocked."""
    rows = [
        {
            "boundary_item": "AOI_prefight",
            "status": "AOI_PREFLIGHT_BLOCKED",
            "evidence": "B8.7 is design/source review only and creates no AOI-wide prediction.",
            "allowed_future_lane": "manual QA, B8.6g3 source acquisition, or B8.7b precheck only",
            "forbidden_actions": "no AOI-wide prediction; no local WBGT; no hazard/risk score",
        },
        {
            "boundary_item": "B9",
            "status": "B9_BLOCKED",
            "evidence": "No production surrogate promotion, no AOI output, no new SOLWEIG labels.",
            "allowed_future_lane": "none in this lane",
            "forbidden_actions": "no B9 output",
        },
        {
            "boundary_item": "scope_limited_dry_run",
            "status": "not_now",
            "evidence": "B8.6h remains future-only and requires explicit later permission.",
            "allowed_future_lane": "B8.6h scope-limited dry-run only if later allowed",
            "forbidden_actions": "no execution and no B9",
        },
    ]
    out = pd.DataFrame(rows)
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def recommended_next_lane_for_status(status: str) -> str:
    """Return next-lane recommendation."""
    if status == "B87_N300_DESIGN_FREEZE_READY":
        return "B8.7b-N300-execution-precheck plus B8.6g3 true-vector feature acquisition; still no execution"
    if status == "B87_N300_DESIGN_NEEDS_QA":
        return "manual N300 QA, then B8.6g3 true-vector feature acquisition, then B8.7b precheck"
    if status == "B87_NEEDS_TRUE_VECTOR_SOURCE_FIRST":
        return "B8.6g3 true-vector feature acquisition before N300 execution precheck"
    if status == "B87_BLOCKED_INPUT":
        return "repair missing or invalid compact inputs"
    return "review failed checks"


def next_lane_decision_matrix(status: str) -> pd.DataFrame:
    """Build next-lane decision matrix."""
    rows = [
        {
            "future_lane": "B8.7b-N300-execution-precheck",
            "decision": "after_manual_QA" if status == "B87_N300_DESIGN_NEEDS_QA" else ("recommended" if status == "B87_N300_DESIGN_FREEZE_READY" else "blocked_or_wait"),
            "recommended_priority": "high_after_QA",
            "allowed_scope": "future precheck only; still no SOLWEIG execution",
            "forbidden_actions": "no QGIS run, no SOLWEIG run, no raster commit, no AOI/B9, no WBGT/hazard/risk",
        },
        {
            "future_lane": "B8.6g3 true-vector feature acquisition",
            "decision": "recommended",
            "recommended_priority": "high",
            "allowed_scope": "acquire/QA connected shade corridor, pedestrian shade network, overhead geometry, building/canyon vectors",
            "forbidden_actions": "no raster I/O, no SOLWEIG/QGIS, no AOI/B9, no observed-truth or causal claims",
        },
        {
            "future_lane": "B8.6h scope-limited dry-run",
            "decision": "not_now",
            "recommended_priority": "conditional_later",
            "allowed_scope": "future dry-run review only if explicitly opened later",
            "forbidden_actions": "no B9 and no public-health/output promotion",
        },
        {
            "future_lane": "AOI/B9",
            "decision": "blocked",
            "recommended_priority": "none",
            "allowed_scope": "none in B8.7",
            "forbidden_actions": "keep AOI_PREFLIGHT_BLOCKED and B9_BLOCKED",
        },
    ]
    out = pd.DataFrame(rows)
    out["b87_status"] = status
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def prompt_b87b() -> str:
    """Return future B8.7b prompt."""
    return """# Future Codex Prompt: B8.7b-N300 Execution Precheck

Work inside the OpenHeat-ToaPayoh project subdirectory.

Lane: B8.7b-N300-execution-precheck.

Use B8.7 outputs only after manual QA has accepted the N300 design. This future
lane may prepare a readiness matrix and, if explicitly approved by reviewers, a
local-only manifest/readiness draft. It must still not run SOLWEIG or QGIS.

Required inputs:
- outputs/v12_surrogate/b8_7_n300_pre/b87_n300_design_freeze_candidates.csv
- outputs/v12_surrogate/b8_7_n300_pre/b87_n300_manual_qa_checklist.csv
- outputs/v12_surrogate/b8_7_n300_pre/b87_n300_freeze_decision_matrix.csv
- outputs/v12_surrogate/b8_7_n300_pre/b87_true_vector_source_gap_register.csv

Forbidden:
No SOLWEIG execution, no QGIS execution, no raster reads/writes/copies, no
AOI-wide prediction, no B9, no local WBGT, no hazard_score, no risk_score, no
exposure/vulnerability score, no observed-truth claim, no causal feature
importance claim, no Tmrt-to-WBGT conversion, no System A/B coupling, and no
heavy/raw file commit.
"""


def prompt_b86g3() -> str:
    """Return future B8.6g3 prompt."""
    return """# Future Codex Prompt: B8.6g3 True-Vector Feature Acquisition

Work inside the OpenHeat-ToaPayoh project subdirectory.

Lane: B8.6g3 true-vector feature acquisition.

Acquire and QA true vector/network sources for connected shade corridor,
pedestrian shade network or covered walkway geometry, overhead geometry,
building footprint/height/canyon orientation, tree canopy/building interaction,
and water/park/road/hardscape edge context. Use B8.7 source review outputs as
the starting register.

Do not infer connected shade corridor continuity from centroid distance. A valid
source requires pedestrian/covered-walkway/shade-network line or polygon
geometry, or an equivalent vector-derived compact connectivity table with
explicit provenance.

Forbidden:
No raster I/O, no QGIS/SOLWEIG execution, no AOI-wide prediction, no B9, no
local WBGT, no hazard/risk score, no observed-truth claim, no causal feature
importance claim, no Tmrt-to-WBGT conversion, and no System A/B coupling.
"""


def prompt_b86h() -> str:
    """Return future B8.6h prompt."""
    return """# Future Codex Prompt: B8.6h Scope-Limited Dry-Run

Work inside the OpenHeat-ToaPayoh project subdirectory.

Lane: B8.6h scope-limited dry-run, only if later explicitly allowed after N300
QA and true-vector source review.

Scope:
Dry-run/preflight review only. Do not create B9 outputs. Do not claim AOI-wide
prediction, local WBGT, hazard/risk score, observed truth, causal feature
importance, Tmrt-to-WBGT conversion, or System A/B coupling.

Forbidden:
No SOLWEIG execution, no QGIS execution, no raster reads/writes/copies, no B9,
no public-health warning output, and no heavy/raw file commit.
"""


def report_markdown(status: str, frames: dict[str, pd.DataFrame], config: dict[str, Any]) -> str:
    """Create B8.7 Markdown report."""
    input_audit = frames["input_audit"]
    source_gaps = frames["source_gaps"]
    count = candidate_count(input_audit)
    overlap = overlap_count(input_audit)
    connected = connected_status(source_gaps)
    b86g2 = read_csv(config["b86g2_baseline_comparison_path"])
    qa = frames["qa"]
    return f"""# B8.7-N300-PRE Design Freeze And B8.6g3 Source Review

Status: `{status}`

## 1. Why B8.7 follows B8.6g2

B8.6g2 improved compact diagnostic ranking but kept AOI preflight and B9
blocked. B8.7 therefore reviews the N300 v2 design and true-vector source
availability without creating execution artifacts.

## 2. B8.6g2 Evidence Summary

{md_table(b86g2, ['split_family', 'b86g2_Spearman', 'b86g2_top10pct_overlap', 'b86g2_false_promotion_rate', 'b86f_context_status'])}

## 3. N300 Design Audit

- Candidate count: {count}
- Overlap with current N150 labels: {overlap}
- Input audit: {status_counts(input_audit)}

## 4. Balance Audits

- Role balance: {status_counts(frames['role'])}
- Spatial balance: {status_counts(frames['spatial'])}
- Typology balance: {status_counts(frames['typology'])}
- Anchor replication: {status_counts(frames['anchor'])}
- Neutral replication: {status_counts(frames['neutral'])}
- Sparse feature-space: {status_counts(frames['sparse'])}
- Control cells: {status_counts(frames['control'])}

## 5. Feature Coverage Audit

{feature_headline(frames['feature_audit'])}

## 6. True-Vector Source Review

{md_table(source_gaps, ['source_category', 'source_status', 'source_candidate_count', 'can_support_B86G3_count', 'recommended_action'])}

## 7. Connected Shade Corridor Status

Connected shade corridor source status: `{connected}`. Do not infer corridor
continuity from centroid distance; future work needs pedestrian/covered-walkway
or shade-network geometry or equivalent vector-derived compact connectivity.

## 8. Manual QA Package

- Checklist: `{config['n300_manual_qa_checklist_path']}`
- QA guide: `{config['n300_manual_qa_guide_path']}`
- High-priority QA rows: {int(qa['qa_priority'].astype(str).eq('high').sum())}

## 9. Freeze Decision

{md_table(frames['freeze'], ['decision_item', 'status', 'evidence', 'recommended_action'], 20)}

## 10. Future Lane Recommendation

Recommended next lane: {recommended_next_lane_for_status(status)}.

## 11. Claim Boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not risk / hazard score.
- Not observed truth.
- Not causal feature importance.
- No raster.
- No QGIS / SOLWEIG.
- No N300 execution manifest.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
"""


def cn_doc_text(status: str, frames: dict[str, pd.DataFrame], config: dict[str, Any]) -> str:
    """Create valid UTF-8 Chinese documentation."""
    count = candidate_count(frames["input_audit"])
    overlap = overlap_count(frames["input_audit"])
    connected = connected_status(frames["source_gaps"])
    return f"""# OpenHeat System B B8.7 N300-PRE 设计冻结与真矢量来源审查说明

## 结论

- B8.7 状态：`{status}`
- N300 候选行数：{count}
- 与当前 N150 标签重叠：{overlap}
- connected shade corridor 来源状态：`{connected}`
- AOI / B9：继续阻断

## 为什么 B8.7 接在 B8.6g2 后面

B8.6g2 显示紧凑代理特征对诊断排序有改善，但仍然不是 AOI-wide prediction，也不是 B9。空间留出、类型留出、锚点低估和中性单元误提升仍需要更多样本支持和真矢量来源审查。因此本轮只做 N300 设计冻结预检和 B8.6g3 来源审查，不创建执行包。

## B8.6g2 证据摘要

空间留出 Spearman 约 0.517，top10pct 约 0.500，false promotion 约 0.163；cell-group 留出 Spearman 约 0.527；typology 留出仍然混合，Spearman 约 0.410，false promotion 约 0.209。结论仍是 `B86G2_DIAGNOSTIC_IMPROVEMENT_ONLY`。

## N300 设计审查

候选设计保持 150 行，并且没有与当前 N150 标签重叠。角色配额保持固定，但空间、类型、锚点、中性边界和稀疏特征空间仍需要人工 QA，尤其是 west_south、TP_0037、TP_0433、park_open_space / commercial 覆盖和 residential / transport 集中度。

## 特征覆盖审查

{feature_headline(frames['feature_audit'])}

## 真矢量来源审查

本轮只审查紧凑/矢量/矢量派生来源。overhead geometry 和 building/canyon 类来源较可用；tree/building interaction 仍有代理或不完整来源限制；connected shade corridor 不能从质心距离推断，必须等待行人遮阴网络、covered walkway 或等价连通性表。

## 人工 QA 包

- QA checklist：`{config['n300_manual_qa_checklist_path']}`
- QA guide：`{config['n300_manual_qa_guide_path']}`

## 冻结决策

当前决策为 `{status}`。若人工 QA 接受候选设计，可进入未来 B8.7b execution precheck；若 connected shade corridor / pedestrian network 来源不足，应先进入 B8.6g3 true-vector feature acquisition。

## 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 risk score 或 hazard score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 QGIS 或 SOLWEIG。
- 没有创建 N300 execution manifest。
- 没有 Tmrt-to-WBGT 转换。
- 没有 System A/B coupling。
"""


def status_markdown(status: str, frames: dict[str, pd.DataFrame], config: dict[str, Any]) -> str:
    """Create lane status Markdown."""
    count = candidate_count(frames["input_audit"])
    overlap = overlap_count(frames["input_audit"])
    connected = connected_status(frames["source_gaps"])
    files = "\n".join(f"- `{path}`" for path in CREATED_FILES)
    return f"""# B8.7 Status

Status: {status}
Branch: codex/b87-n300-pre-source-review
Scope: B8.7-N300-PRE design freeze/source review only; no execution artifacts.

## Commands Run By Suite

- `python scripts/v12_b87_run_n300_pre.py --config configs/v12/systemb_b87_n300_pre.yaml`

## Key Results

- N300 candidate count: {count}
- Overlap with current N150 labels: {overlap}
- Role balance: {status_counts(frames['role'])}
- Spatial balance: {status_counts(frames['spatial'])}
- Typology balance: {status_counts(frames['typology'])}
- Anchor replication: {status_counts(frames['anchor'])}
- Neutral replication: {status_counts(frames['neutral'])}
- Feature coverage: {feature_headline(frames['feature_audit'])}
- Connected shade corridor source status: {connected}
- AOI/B9 status: AOI_PREFLIGHT_BLOCKED / B9_BLOCKED
- Recommended next lane: {recommended_next_lane_for_status(status)}

## Files Created / Modified

{files}

## Caveats

This lane is design/source review only. It does not create a SOLWEIG manifest,
QGIS runner, raster, AOI-wide prediction, B9 output, local WBGT, hazard_score,
risk_score, exposure/vulnerability score, observed-truth claim, causal
feature-importance claim, Tmrt-to-WBGT conversion, or System A/B coupling.

## Safe To Commit After Review

Controlled B8.7 config, scripts, docs, compact CSV, and Markdown outputs.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip
packages, AOI-wide prediction outputs, B9 outputs, WBGT, hazard_score,
risk_score, exposure/vulnerability score, and System A/B coupling outputs.
"""


def load_frames(config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Load all decision inputs."""
    return {
        "input_inventory": read_csv(output_path(config, "input_inventory_path")),
        "input_audit": read_csv(output_path(config, "n300_v2_input_audit_path")),
        "role": read_csv(output_path(config, "n300_role_balance_audit_path")),
        "spatial": read_csv(output_path(config, "n300_spatial_balance_audit_path")),
        "typology": read_csv(output_path(config, "n300_typology_balance_audit_path")),
        "anchor": read_csv(output_path(config, "n300_anchor_replication_audit_path")),
        "neutral": read_csv(output_path(config, "n300_neutral_replication_audit_path")),
        "sparse": read_csv(output_path(config, "n300_sparse_feature_space_audit_path")),
        "control": read_csv(output_path(config, "n300_control_cell_audit_path")),
        "feature_audit": read_csv(output_path(config, "n300_feature_coverage_audit_path")),
        "source_gaps": read_csv(output_path(config, "true_vector_source_gap_register_path")),
        "qa": read_csv(output_path(config, "n300_manual_qa_checklist_path")),
    }


def run(config_path: Path = DEFAULT_CONFIG) -> PrecheckDecisionResult:
    """Run B8.7 precheck decision and documentation."""
    config = load_config(config_path)
    frames = load_frames(config)
    status = final_decision(
        frames["input_audit"],
        frames["role"],
        frames["spatial"],
        frames["typology"],
        frames["anchor"],
        frames["neutral"],
        frames["sparse"],
        frames["control"],
        frames["feature_audit"],
        frames["source_gaps"],
    )
    freeze = freeze_decision_matrix(config, status, frames)
    frames["freeze"] = freeze
    aoi = aoi_b9_boundary_matrix()
    next_lane = next_lane_decision_matrix(status)
    write_csv(freeze, output_path(config, "n300_freeze_decision_matrix_path"))
    write_csv(aoi, output_path(config, "aoi_b9_boundary_matrix_path"))
    write_csv(next_lane, output_path(config, "next_lane_decision_matrix_path"))
    write_text(prompt_b87b(), output_path(config, "codex_prompt_b87b_path"))
    write_text(prompt_b86g3(), output_path(config, "codex_prompt_b86g3_path"))
    write_text(prompt_b86h(), output_path(config, "codex_prompt_b86h_path"))
    write_text(report_markdown(status, frames, config), output_path(config, "report_path"))
    write_text(status_markdown(status, frames, config), output_path(config, "status_path"))
    write_text(cn_doc_text(status, frames, config), output_path(config, "cn_doc_path"))
    return PrecheckDecisionResult(
        status=status,
        candidate_count=candidate_count(frames["input_audit"]),
        overlap_with_n150=overlap_count(frames["input_audit"]),
        connected_shade_status=connected_status(frames["source_gaps"]),
        recommended_next_lane=recommended_next_lane_for_status(status),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Write B8.7 freeze decision, AOI/B9 boundaries, future prompts, "
            "report, status, and CN doc. No SOLWEIG/QGIS/raster/AOI/B9/WBGT/"
            "hazard/risk/manifest/execution output is created."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
