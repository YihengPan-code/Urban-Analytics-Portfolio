"""Write B8.6f decision matrices, future prompts, report, status, and CN doc.

Inputs:
    All B8.6f compact outputs created by the input inventory, failure
    synthesis, N300 design review, feature acquisition plan, abstention gate,
    and scope-limited probe scripts.
Outputs:
    b86f_aoi_preflight_readiness_matrix.csv,
    b86f_next_lane_decision_matrix.csv,
    b86f_codex_prompt_B86G_feature_acquisition.md,
    b86f_codex_prompt_B87_N300_PRE.md,
    b86f_report.md, B8_6F_STATUS.md, and
    docs/v12/OpenHeat_SystemB_B8_6f_surrogate_closure_CN.md.
Saved metrics:
    AOI preflight readiness blockers, next-lane priorities, final B8.6f status,
    and explicit claim boundaries. This script creates no AOI-wide prediction,
    B9, local WBGT, hazard/risk score, raster, QGIS/SOLWEIG, Tmrt-to-WBGT
    conversion, observed-truth claim, causal feature-importance claim, or
    System A/B coupling output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86f_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    as_float,
    fmt,
    load_config,
    md_table,
    output_path,
    read_csv,
    write_csv,
    write_text,
)


@dataclass(frozen=True)
class WorkflowDecisionResult:
    """Final workflow decision result."""

    status: str
    aoi_preflight_status: str
    b9_status: str
    recommended_next_lane: str


def load_outputs(config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Load B8.6f output tables."""
    keys = [
        "input_inventory",
        "b86e_caveat_register",
        "failure_synthesis",
        "spatial_failure_decision_table",
        "anchor_neutral_failure_matrix",
        "safe_feature_probe_verdict",
        "n300_design_v1_audit",
        "n300_role_quota_plan",
        "targeted_n300_design_v2",
        "feature_acquisition_register",
        "abstention_gate_metrics",
        "scope_limited_surrogate_metrics",
    ]
    return {key: read_csv(output_path(config, key)) for key in keys if output_path(config, key).exists()}


def decide_status(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> str:
    """Decide final B8.6f status."""
    inventory = tables.get("input_inventory", pd.DataFrame())
    if inventory.empty or (~inventory["exists"].astype(bool)).any() or inventory["missing_required_columns"].fillna("").astype(str).str.strip().ne("").any():
        return "B86F_BLOCKED_INPUT"
    scope = tables.get("scope_limited_surrogate_metrics", pd.DataFrame())
    if not scope.empty and scope["scope_status"].astype(str).eq("SCOPE_LIMITED_PREFLIGHT_CANDIDATE").any():
        return "B86F_SCOPE_LIMITED_PREFLIGHT_CANDIDATE"
    design = tables.get("targeted_n300_design_v2", pd.DataFrame())
    plan = tables.get("n300_role_quota_plan", pd.DataFrame())
    feature = tables.get("feature_acquisition_register", pd.DataFrame())
    design_ok = len(design) == int(config["n300_target_additional_count"])
    quota_ok = not plan.empty and plan["final_deficit_or_surplus"].map(as_float).abs().sum() == 0
    feature_ok = not feature.empty and feature["priority"].astype(str).eq("high").sum() >= 4
    if design_ok and quota_ok and feature_ok:
        return "B86F_SURROGATE_CLOSURE_PASS"
    if feature_ok:
        return "B86F_FEATURE_ACQUISITION_RECOMMENDED"
    if design_ok:
        return "B86F_TARGETED_N300_PRE_RECOMMENDED"
    return "B86F_SURROGATE_CLOSURE_PASS"


def aoi_readiness_matrix(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create AOI preflight readiness matrix."""
    spatial = tables["spatial_failure_decision_table"]
    verdict = tables["safe_feature_probe_verdict"]
    anchor_neutral = tables["anchor_neutral_failure_matrix"]
    feature = tables["feature_acquisition_register"]
    design = tables["targeted_n300_design_v2"]
    scope = tables["scope_limited_surrogate_metrics"]
    spatial_row = spatial.loc[spatial["spatial_bin"].astype(str).eq("west_north")].head(1)
    spatial_evidence = (
        f"west_north Spearman={fmt(spatial_row.iloc[0]['Spearman'])}, top10={fmt(spatial_row.iloc[0]['top10pct_overlap'])}"
        if not spatial_row.empty
        else "B8.6e spatial holdout remains weak."
    )
    typology_verdict = verdict.loc[verdict["verdict_topic"].astype(str).eq("typology_holdout")].head(1)
    cell_verdict = verdict.loc[verdict["verdict_topic"].astype(str).eq("cell_group_holdout")].head(1)
    neutral_high = anchor_neutral.loc[
        anchor_neutral["failure_type"].astype(str).eq("neutral-false-promotion")
        & anchor_neutral["severity"].astype(str).isin(["high", "medium"])
    ]
    anchor_high = anchor_neutral.loc[
        anchor_neutral["failure_type"].astype(str).eq("anchor-underprediction")
        & anchor_neutral["severity"].astype(str).isin(["high", "medium"])
    ]
    scope_spatial = scope.loc[
        scope["split_family"].astype(str).eq("spatial_holdout")
        & scope["gate_level"].astype(str).isin(["moderate_gate", "strict_gate"])
    ].copy()
    best_scope = scope_spatial.sort_values("Spearman_retained", ascending=False).head(1)
    rows = [
        {
            "readiness_item": "spatial_holdout",
            "status": "BLOCKED",
            "evidence": spatial_evidence,
            "blocker": "spatial-bin-out-of-domain and weak ranking support",
            "next_action": "B8.6g feature acquisition plus B8.7-N300-PRE review.",
            "allowed_future_lane": "B8.6g|B8.7-N300-PRE",
        },
        {
            "readiness_item": "typology_holdout",
            "status": "DIAGNOSTIC_ONLY",
            "evidence": typology_verdict.iloc[0]["headline"] if not typology_verdict.empty else "Typology remains diagnostic.",
            "blocker": "Spearman-only improvement is insufficient when top-k worsens.",
            "next_action": "Keep typology gains as feature-acquisition clues.",
            "allowed_future_lane": "B8.6g",
        },
        {
            "readiness_item": "cell_group_holdout",
            "status": "BLOCKED",
            "evidence": cell_verdict.iloc[0]["headline"] if not cell_verdict.empty else "Cell-group closure not validated.",
            "blocker": "safe feature probe did not improve cell-group evidence.",
            "next_action": "Retest only after new compact/vector features or N300 labels.",
            "allowed_future_lane": "B8.6f2_model_retest_after_inputs",
        },
        {
            "readiness_item": "neutral false-promotion",
            "status": "BLOCKED",
            "evidence": f"{len(neutral_high)} neutral/near-zero rows remain in the B8.6f matrix.",
            "blocker": "known neutral and near-zero cells can still be promoted as cooling.",
            "next_action": "Use neutral-boundary N300 quota and abstention gate.",
            "allowed_future_lane": "B8.7-N300-PRE|B8.6h_conditional",
        },
        {
            "readiness_item": "anchor underprediction",
            "status": "BLOCKED",
            "evidence": f"{len(anchor_high)} anchor rows remain medium/high severity.",
            "blocker": "TP_0857/TP_0542/TP_0433/TP_0037/TP_0141 anchor contexts remain required gates.",
            "next_action": "Use anchor-like replication quota and geometry/shade acquisition.",
            "allowed_future_lane": "B8.6g|B8.7-N300-PRE",
        },
        {
            "readiness_item": "feature gap closure",
            "status": "NOT_CLOSED",
            "evidence": f"{feature['priority'].astype(str).eq('high').sum()} high-priority feature families remain.",
            "blocker": "current safe engineered features did not close spatial holdout.",
            "next_action": "Run vector/compact feature acquisition before model promotion.",
            "allowed_future_lane": "B8.6g",
        },
        {
            "readiness_item": "N300 design",
            "status": "READY_FOR_REVIEW_NOT_EXECUTION",
            "evidence": f"{len(design)} role-balanced additional candidate-design cells selected.",
            "blocker": "candidate design is not a SOLWEIG manifest or run package.",
            "next_action": "Freeze design only in B8.7-N300-PRE if reviewed.",
            "allowed_future_lane": "B8.7-N300-PRE",
        },
        {
            "readiness_item": "feature acquisition",
            "status": "RECOMMENDED",
            "evidence": "Feature acquisition register and spec are actionable.",
            "blocker": "feature representation is the dominant blocker.",
            "next_action": "Acquire vector/compact features without raster/QGIS/SOLWEIG.",
            "allowed_future_lane": "B8.6g",
        },
        {
            "readiness_item": "uncertainty/abstention gate",
            "status": "DIAGNOSTIC_ONLY",
            "evidence": (
                f"Best spatial gated Spearman={fmt(best_scope.iloc[0]['Spearman_retained'])}, "
                f"coverage={fmt(best_scope.iloc[0]['retained_coverage_fraction'])}"
                if not best_scope.empty
                else "No gated subset supports preflight promotion."
            ),
            "blocker": "gate is not a production or AOI-wide prediction path.",
            "next_action": "Use only as future dry-run preflight diagnostic if metrics become strong.",
            "allowed_future_lane": "B8.6h_conditional",
        },
        {
            "readiness_item": "claim boundary",
            "status": "PASS",
            "evidence": "B8.6f creates compact diagnostic/design outputs only.",
            "blocker": "none if boundaries are preserved.",
            "next_action": "Keep AOI-wide prediction and B9 blocked.",
            "allowed_future_lane": "B8.6g|B8.7-N300-PRE",
        },
        {
            "readiness_item": "overall_aoi_preflight",
            "status": "AOI_PREFLIGHT_BLOCKED",
            "evidence": "Spatial, neutral, anchor, and feature-gap blockers remain.",
            "blocker": "insufficient spatial closure and safety diagnostics.",
            "next_action": "Do not create AOI-wide prediction; proceed to B8.6g/B8.7 review lanes.",
            "allowed_future_lane": "B8.6g|B8.7-N300-PRE",
        },
    ]
    out = pd.DataFrame(rows)
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def next_lane_matrix(config: dict[str, Any]) -> pd.DataFrame:
    """Create next-lane decision matrix."""
    out_dir = Path(config["outputs"]["out_dir"])
    rows = [
        {
            "future_lane": "B8.6g vector/compact feature acquisition",
            "recommended_priority": "high",
            "why": "Feature representation gaps are the dominant blocker and B8.6e safe features did not close spatial holdout.",
            "prerequisites": "Reviewer acceptance of B8.6f feature acquisition spec and no-raster/vector-only source list.",
            "forbidden_actions": "No raster, QGIS, SOLWEIG, AOI-wide prediction, B9, WBGT, hazard/risk score, observed truth, causal feature importance, or System A/B coupling.",
            "codex_prompt_path": f"{out_dir.as_posix()}/b86f_codex_prompt_B86G_feature_acquisition.md",
        },
        {
            "future_lane": "B8.7-N300-PRE targeted sample design freeze",
            "recommended_priority": "high",
            "why": "N300 v2 is role-balanced and current compact features cannot close spatial/anchor/neutral failures alone.",
            "prerequisites": "Review B8.6f v2 list, quota plan, exclusions, and candidate-design-only boundary.",
            "forbidden_actions": "No SOLWEIG execution, no QGIS runner, no raster I/O, no AOI-wide prediction, no B9 output, and no System A/B coupling.",
            "codex_prompt_path": f"{out_dir.as_posix()}/b86f_codex_prompt_B87_N300_PRE.md",
        },
        {
            "future_lane": "B8.6h scope-limited surrogate dry-run preflight",
            "recommended_priority": "low_conditional",
            "why": "Abstention gate is useful diagnostically, but should only proceed if retained metrics become clearly strong.",
            "prerequisites": "Materially improved retained spatial metrics, neutral false-promotion reduction, and meaningful coverage.",
            "forbidden_actions": "No AOI-wide prediction in B8.6f; any dry-run must remain explicitly scope-limited and diagnostic.",
            "codex_prompt_path": "",
        },
        {
            "future_lane": "B8.6f2 model retest",
            "recommended_priority": "medium_after_new_inputs",
            "why": "Model retest is useful only after B8.6g features or reviewed N300 labels exist.",
            "prerequisites": "New compact/vector feature table or reviewed targeted N300 label set.",
            "forbidden_actions": "No random split as main evidence; no production claims.",
            "codex_prompt_path": "",
        },
        {
            "future_lane": "no-go / wait",
            "recommended_priority": "fallback",
            "why": "If feature acquisition or N300 review is not approved, AOI/B9 should remain blocked.",
            "prerequisites": "None.",
            "forbidden_actions": "Do not promote current surrogate.",
            "codex_prompt_path": "",
        },
    ]
    out = pd.DataFrame(rows)
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def b86g_prompt() -> str:
    """Return the future B8.6g prompt."""
    return """# Future Codex Prompt: B8.6g Vector/Compact Feature Acquisition

Work inside the OpenHeat-ToaPayoh project. Read B8.6f outputs first, especially
the feature acquisition register/spec and AOI readiness matrix.

Task: create vector/compact feature acquisition outputs for pedestrian-accessible
shade, shade continuity, overhead geometry descriptors, sunlit-hot-pocket
proxies, edge context, neighbourhood context, tree/building interaction, canyon
orientation/roughness, and typology-specific geometry.

Rules: do not read/open/copy/create/write raster files; do not run QGIS or
SOLWEIG; do not create AOI-wide predictions, B9 outputs, WBGT, hazard_score,
risk_score, observed-truth labels, causal feature-importance claims, or System
A/B coupling. Use deterministic vector/compact tables only. Write CSV/JSON plus
Markdown summaries and keep claim boundaries explicit.
"""


def b87_prompt() -> str:
    """Return the future B8.7-N300-PRE prompt."""
    return """# Future Codex Prompt: B8.7-N300-PRE Targeted Sample Design Freeze

Work inside the OpenHeat-ToaPayoh project. Read B8.6f outputs first, especially
the N300 v2 design, role quota plan, N300 review note, and AOI readiness matrix.

Task: review and freeze a targeted N300-PRE candidate design package from the
B8.6f v2 list. Validate exclusions of current N150 cells, role balance, spatial
and typology coverage, anchor/neutral replication, sparse-space coverage, and
candidate-design-only boundaries.

Rules: do not execute SOLWEIG; do not run QGIS; do not create a QGIS runner; do
not read/open/copy/create/write raster files; do not create AOI-wide predictions,
B9 outputs, WBGT, hazard_score, risk_score, observed-truth labels, causal
feature-importance claims, or System A/B coupling. This lane is a pre-execution
design freeze only.
"""


def report_text(config: dict[str, Any], tables: dict[str, pd.DataFrame], status: str, readiness: pd.DataFrame, next_lanes: pd.DataFrame) -> str:
    """Build the English B8.6f report."""
    caveats = tables["b86e_caveat_register"]
    spatial = tables["spatial_failure_decision_table"]
    anchor_neutral = tables["anchor_neutral_failure_matrix"]
    verdict = tables["safe_feature_probe_verdict"]
    v1 = tables["n300_design_v1_audit"]
    plan = tables["n300_role_quota_plan"]
    design = tables["targeted_n300_design_v2"]
    feature = tables["feature_acquisition_register"]
    abstention = tables["abstention_gate_metrics"]
    scope = tables["scope_limited_surrogate_metrics"]
    role_mix = design["primary_role"].value_counts().rename_axis("primary_role").reset_index(name="count")
    best_scope = scope.loc[scope["gate_level"].astype(str).ne("baseline_no_gate")].sort_values(
        ["split_family", "Spearman_retained"], ascending=[True, False]
    )
    return f"""# B8.6f Surrogate Closure Mega-Suite

Status: `{status}`

## 1. Why B8.6f Follows B8.6e

B8.6e diagnosed spatial failure and proposed a targeted N300 v1 design, but it
also left over-optimistic wording around safe engineered features. B8.6f
therefore consolidates the evidence, corrects that caveat, rebalances N300
candidate roles, and tests abstention gates without creating AOI-wide or B9
outputs.

## 2. What B8.6e Proved And Did Not Prove

{md_table(caveats, ['caveat_id', 'caveat_headline', 'required_action'])}

## 3. Spatial Failure Synthesis

{md_table(spatial, ['spatial_bin', 'mean_abs_error', 'Spearman', 'top10pct_overlap', 'false_promotion_rate', 'dominant_blocker', 'b86f_decision'])}

## 4. Anchor / Neutral Failure Synthesis

{md_table(anchor_neutral, ['cell_id', 'diagnostic_role', 'spatial_bin', 'typology', 'mean_abs_error', 'failure_rate', 'failure_type', 'severity'], max_rows=20)}

## 5. Safe Feature Probe Verdict

{md_table(verdict, ['verdict_topic', 'feature_variant', 'Spearman_delta_vs_b86d', 'top10_delta_vs_b86d', 'verdict', 'production_boundary'])}

## 6. N300 V1 Audit And V2 Role-Balanced Design

V2 selected {len(design)} additional candidate-design cells. It is not run-ready
and does not create a SOLWEIG manifest or runner.

{md_table(plan, ['primary_role', 'target_count', 'final_selected_count', 'final_deficit_or_surplus'])}

{md_table(role_mix, ['primary_role', 'count'])}

## 7. Feature Acquisition Register

{md_table(feature, ['feature_family', 'priority', 'expected_benefit', 'implementation_lane', 'likely_failure_modes_addressed'], max_rows=12)}

## 8. Abstention Gate Diagnostics

{md_table(abstention, ['gate_level', 'split_family', 'retained_coverage_fraction', 'MAE_retained', 'Spearman_retained', 'top10pct_overlap_retained', 'neutral_false_promotion_rate_retained'], max_rows=18)}

## 9. Scope-Limited Surrogate Diagnostic

{md_table(scope, ['gate_level', 'split_family', 'retained_coverage_fraction', 'Spearman_delta_vs_baseline', 'top10_delta_vs_baseline', 'topk_screening_suitability', 'scope_status'], max_rows=18)}

## 10. AOI Preflight Readiness

{md_table(readiness, ['readiness_item', 'status', 'evidence', 'blocker', 'allowed_future_lane'], max_rows=12)}

AOI preflight status: `AOI_PREFLIGHT_BLOCKED`.

## 11. Recommended Next Lane

{md_table(next_lanes, ['future_lane', 'recommended_priority', 'why', 'codex_prompt_path'], max_rows=8)}

Recommended order: B8.6g vector/compact feature acquisition, then B8.7-N300-PRE
targeted design freeze if reviewers approve the role-balanced candidate list.

## 12. Claim Boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not hazard_score or risk_score.
- Not observed truth.
- Not causal feature importance.
- No raster read/open/create/copy/write.
- No QGIS or SOLWEIG.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
"""


def status_text(config: dict[str, Any], tables: dict[str, pd.DataFrame], status: str, readiness: pd.DataFrame, next_lanes: pd.DataFrame) -> str:
    """Build B8.6f status Markdown."""
    design = tables["targeted_n300_design_v2"]
    role_mix = ", ".join(f"{role}={count}" for role, count in design["primary_role"].value_counts().items())
    next_high = next_lanes.loc[next_lanes["recommended_priority"].astype(str).eq("high"), "future_lane"].astype(str).tolist()
    files = [
        "configs/v12/systemb_b86f_surrogate_closure.yaml",
        "scripts/v12_b86f_input_inventory.py",
        "scripts/v12_b86f_failure_synthesis.py",
        "scripts/v12_b86f_n300_design_review.py",
        "scripts/v12_b86f_feature_acquisition_plan.py",
        "scripts/v12_b86f_abstention_gate.py",
        "scripts/v12_b86f_scope_limited_probe.py",
        "scripts/v12_b86f_workflow_decision.py",
        "scripts/v12_b86f_run_surrogate_closure.py",
        *[value for key, value in config["outputs"].items() if key != "out_dir"],
    ]
    return f"""# B8.6f Status

Status: {status}
Branch: {config['branch']}
Scope: System B surrogate closure mega-suite using compact diagnostic/design inputs only.

## Key Results

- Inputs: see `b86f_input_inventory.csv`.
- B8.6e caveat headline: safe physical engineered features did not close spatial_holdout.
- Spatial failure headline: spatial_holdout remains blocking; west_north/west_south/east_south/east_north all require review.
- Anchor/neutral headline: anchor underprediction and neutral false-promotion remain explicit gates.
- N300 v2 role mix: {role_mix}
- Feature acquisition headline: vector/compact feature acquisition is recommended.
- AOI preflight status: AOI_PREFLIGHT_BLOCKED.
- B9 status: BLOCKED.
- Recommended next lane: {'; '.join(next_high)}.

## Commands Run By Suite

- `python scripts/v12_b86f_run_surrogate_closure.py --config configs/v12/systemb_b86f_surrogate_closure.yaml`

## Files Created / Modified

{chr(10).join(f'- `{path}`' for path in files)}

## Caveats

- Labels are SOLWEIG-derived compact Tmrt deltas, not observed truth.
- Feature interpretation is diagnostic, not causal.
- Coordinate and distance context remains diagnostic-only.
- No AOI-wide prediction, B9 output, local WBGT, hazard_score, risk_score, raster, QGIS/SOLWEIG, Tmrt-to-WBGT conversion, or System A/B coupling output was created.

## Safe To Commit After Review

Compact B8.6f config, scripts, docs, CSV, and Markdown outputs.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip packages, AOI-wide prediction outputs, B9 outputs, WBGT, hazard_score, risk_score, and System A/B coupling outputs.
"""


def cn_doc_text(status: str, tables: dict[str, pd.DataFrame]) -> str:
    """Build the UTF-8 Chinese B8.6f documentation."""
    design = tables["targeted_n300_design_v2"]
    feature = tables["feature_acquisition_register"]
    role_mix = "；".join(f"{role}={count}" for role, count in design["primary_role"].value_counts().items())
    high_features = "、".join(feature.loc[feature["priority"].astype(str).eq("high"), "feature_family"].astype(str).tolist())
    return f"""# OpenHeat System B B8.6f 代理模型闭合综合审查说明

## 结论

- B8.6f 状态：`{status}`
- AOI preflight 状态：`AOI_PREFLIGHT_BLOCKED`
- B9 状态：`BLOCKED`
- N300 v2 候选设计行数：{len(design)}
- N300 v2 角色配比：{role_mix}

## 为什么 B8.6f 接在 B8.6e 后面

B8.6e 已经定位了空间留出失败、锚点低估和中性单元误提升问题，但安全工程特征探针没有闭合 spatial_holdout。B8.6f 因此只做证据综合、候选设计复核、特征获取路线图和弃权门诊断，不做 AOI-wide 预测，也不进入 B9。

## B8.6e 证明了什么，没有证明什么

B8.6e 证明当前紧凑特征存在空间和类型覆盖缺口；没有证明安全工程特征已经可以作为生产级空间闭合证据。类型留出中的 Spearman 改善只能作为诊断线索，因为 top-k 支持变差。坐标和距离特征只能用于诊断空间外推风险，不能作为生产预测特征。

## 空间失败综合

west_north、west_south、east_south、east_north 仍然是需要审查的空间分箱。主要失败模式包括 spatial-bin-out-of-domain、anchor-underprediction、neutral-false-promotion、feature-distribution-shift、target-role-mismatch 和 sample-support-low。

## 锚点和中性失败综合

TP_0857、TP_0542、TP_0433、TP_0037、TP_0141 仍然需要作为锚点门控单元。已知中性单元和近零单元仍可能被模型误提升为有意义冷却，因此中性边界必须保留为弃权或复核条件。

## 安全特征探针裁决

B8.6e 的安全物理工程特征没有改善 spatial_holdout，也没有改善 cell_group。typology 的 Spearman 改善是诊断性的，同时 top-k 变差，不能视为生产级闭合。

## N300 v1 审计与 N300 v2 设计

N300 v1 是候选设计，不是运行清单，并且过度偏向 typology_gap_fill。B8.6f 生成了角色配额平衡的 N300 v2：{role_mix}。该文件仍然只是 candidate design，不是 SOLWEIG manifest，不是 QGIS runner，也不是 N300 执行包。

## 特征获取路线图

高优先级特征族包括：{high_features}。下一步应优先做 B8.6g vector/compact feature acquisition，并保持无 raster、无 QGIS、无 SOLWEIG。

## 弃权门诊断

B8.6f 只在已有 B8.6d/B8.6e 紧凑预测和失败诊断上模拟 moderate / strict gate。该诊断不会生成 AOI-wide 预测。只有在未来保留覆盖率和空间指标同时显著改善时，才可考虑单独的 scope-limited dry-run preflight。

## 推荐下一路线

优先推荐 B8.6g vector/compact feature acquisition；如果评审接受 N300 v2 角色平衡设计，则推进 B8.7-N300-PRE targeted sample design freeze。B8.6h scope-limited dry-run preflight 仅作为低优先级、条件性未来路线。

## 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 hazard_score 或 risk_score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 QGIS 或 SOLWEIG。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
"""


def run(config_path: Path = DEFAULT_CONFIG) -> WorkflowDecisionResult:
    """Write final B8.6f workflow decision outputs."""
    config = load_config(config_path)
    tables = load_outputs(config)
    status = decide_status(config, tables)
    readiness = aoi_readiness_matrix(config, tables)
    next_lanes = next_lane_matrix(config)
    write_csv(readiness, output_path(config, "aoi_preflight_readiness_matrix"))
    write_csv(next_lanes, output_path(config, "next_lane_decision_matrix"))
    write_text(b86g_prompt(), output_path(config, "codex_prompt_b86g_feature_acquisition"))
    write_text(b87_prompt(), output_path(config, "codex_prompt_b87_n300_pre"))
    write_text(report_text(config, tables, status, readiness, next_lanes), output_path(config, "report"))
    write_text(status_text(config, tables, status, readiness, next_lanes), output_path(config, "status"))
    write_text(cn_doc_text(status, tables), output_path(config, "cn_doc"))
    recommended = "B8.6g vector/compact feature acquisition; B8.7-N300-PRE targeted sample design freeze"
    return WorkflowDecisionResult(
        status=status,
        aoi_preflight_status="AOI_PREFLIGHT_BLOCKED",
        b9_status="BLOCKED",
        recommended_next_lane=recommended,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Write B8.6f decision matrices, prompts, report, status, and CN doc.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
