"""Write B8.6e decision matrix, recommendation, report, status, and CN doc.

Inputs:
    All B8.6e compact audit/probe/sampling outputs and the B8.6e config.
Outputs:
    b86e_decision_matrix.csv, b86e_b86f_recommendation.md,
    b86e_aoi_preflight_prerequisites.md, b86e_report.md, B8_6E_STATUS.md,
    and docs/v12/OpenHeat_SystemB_B8_6e_spatial_feature_closure_CN.md.
Saved metrics:
    Final B8.6e status, spatial failure headline, typology-spatial headline,
    anchor and neutral confusion headlines, feature-gap summary, engineered
    probe decision, targeted N300 candidate-design status, and explicit claim
    boundaries.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86e_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    input_path,
    load_config,
    output_path,
    read_csv,
    write_csv,
    write_text,
)


@dataclass(frozen=True)
class DecisionResult:
    """Workflow decision result."""

    status: str
    dataset_rows: int
    dataset_cells: int
    targeted_candidates: int


def fmt(value: Any, digits: int = 3) -> str:
    """Format values for compact Markdown."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric != numeric:
        return "NA"
    return f"{numeric:.{digits}f}"


def md_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 8) -> str:
    """Create a small Markdown table without external dependencies."""
    if frame.empty:
        return "_No rows._"
    view = frame.loc[:, [column for column in columns if column in frame.columns]].head(max_rows).copy()
    for column in view.columns:
        if pd.api.types.is_numeric_dtype(view[column]):
            view[column] = view[column].map(lambda item: "" if pd.isna(item) else fmt(item, 3))
    header = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = ["| " + " | ".join(str(item) for item in row) + " |" for row in view.to_numpy()]
    return "\n".join([header, sep, *rows])


def load_outputs(config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Load B8.6e output tables for decision reporting."""
    keys = [
        "input_inventory",
        "failure_joined_dataset",
        "spatial_holdout_failure_summary",
        "typology_spatial_cross_failure",
        "worst_cell_error_context",
        "anchor_underprediction_context",
        "neutral_false_promotion_context",
        "feature_distribution_shift",
        "feature_coverage_matrix",
        "feature_gap_register",
        "domain_distance_metrics",
        "safe_engineered_feature_catalog",
        "spatial_closure_probe_metrics",
        "targeted_n300_candidate_design",
    ]
    return {key: read_csv(output_path(config, key)) for key in keys if output_path(config, key).exists()}


def decide_status(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> str:
    """Assign final B8.6e decision status."""
    inventory = tables["input_inventory"]
    missing_schema = inventory["missing_required_columns"].fillna("").astype(str).str.strip()
    if (~inventory["exists"].astype(bool)).any() or missing_schema.ne("").any():
        return "B86E_BLOCKED_INPUT"
    probe = tables["spatial_closure_probe_metrics"]
    design = tables["targeted_n300_candidate_design"]
    if probe["variant_decision"].astype(str).eq("FEATURE_UPGRADE_PROMISING").any():
        return "B86E_SPATIAL_FEATURE_CLOSURE_PASS"
    if not design.empty:
        return "B86E_TARGETED_N300_RECOMMENDED"
    return "B86E_DIAGNOSTIC_ONLY"


def decision_matrix(config: dict[str, Any], tables: dict[str, pd.DataFrame], status: str) -> pd.DataFrame:
    """Build final decision matrix."""
    spatial = tables["spatial_holdout_failure_summary"]
    gaps = tables["feature_gap_register"]
    probe = tables["spatial_closure_probe_metrics"]
    design = tables["targeted_n300_candidate_design"]
    rows = [
        {
            "gate": "compact_inputs",
            "status": "PASS",
            "evidence": "All required compact CSV inputs exist and schema checks passed.",
            "next_action": "Keep B8.6e compact-only; no raster/QGIS/SOLWEIG.",
        },
        {
            "gate": "spatial_failure_diagnosis",
            "status": "PASS" if not spatial.empty else "BLOCKED",
            "evidence": f"{len(spatial)} spatial bins diagnosed; worst={spatial.iloc[0]['spatial_bin'] if not spatial.empty else 'NA'}.",
            "next_action": "Use weak spatial bins as B8.6f/N300 targeting evidence.",
        },
        {
            "gate": "feature_gap_register",
            "status": "PASS" if len(gaps) >= 10 else "DIAGNOSTIC",
            "evidence": f"{len(gaps)} feature families classified.",
            "next_action": "Prioritize shade continuity, hot-pocket fraction, and geometry interaction features.",
        },
        {
            "gate": "safe_engineered_probe",
            "status": "PROMISING" if probe["variant_decision"].astype(str).eq("FEATURE_UPGRADE_PROMISING").any() else "DIAGNOSTIC",
            "evidence": "Safe non-coordinate engineered features tested on spatial/typology/cell-group holdouts.",
            "next_action": "Only promote in B8.6f if non-coordinate gains replicate.",
        },
        {
            "gate": "targeted_n300_candidate_design",
            "status": "READY" if not design.empty else "NOT_SUPPORTED",
            "evidence": f"{len(design)} candidate-design cells selected; not run-ready.",
            "next_action": "Review candidate list before any separate targeted N300 lane.",
        },
        {
            "gate": "aoi_b9_boundary",
            "status": "PASS",
            "evidence": "No AOI-wide predictions, B9 outputs, WBGT, hazard, risk, raster, QGIS/SOLWEIG, or System A/B coupling created.",
            "next_action": "Keep AOI-wide/B9 blocked pending future preflight prerequisites.",
        },
        {
            "gate": "final_status",
            "status": status,
            "evidence": "B8.6e compact spatial failure / feature-gap closure package completed.",
            "next_action": "Follow B8.6f recommendation and targeted sampling review.",
        },
    ]
    out = pd.DataFrame(rows)
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def report_text(config: dict[str, Any], tables: dict[str, pd.DataFrame], status: str) -> str:
    """Build the English B8.6e report."""
    joined = tables["failure_joined_dataset"]
    spatial = tables["spatial_holdout_failure_summary"]
    cross = tables["typology_spatial_cross_failure"]
    anchor = tables["anchor_underprediction_context"]
    neutral = tables["neutral_false_promotion_context"]
    shift = tables["feature_distribution_shift"]
    gaps = tables["feature_gap_register"]
    distances = tables["domain_distance_metrics"]
    engineered = tables["safe_engineered_feature_catalog"]
    probe = tables["spatial_closure_probe_metrics"]
    design = tables["targeted_n300_candidate_design"]
    worst_spatial = spatial.head(3)
    worst_cross = cross.sort_values(["failure_label", "mean_abs_error"], ascending=[True, False]).head(5)
    anchor_spatial = anchor.loc[anchor["split_family"].astype(str).eq("spatial_holdout")].sort_values("mean_abs_error", ascending=False)
    neutral_bad = neutral.sort_values(["false_promotion_rate", "mean_abs_error"], ascending=False).head(8)
    probe_spatial = probe.loc[probe["split_family"].astype(str).eq("spatial_holdout")]
    safe_probe = probe.loc[probe["feature_variant"].astype(str).eq("safe_physical_engineered")]
    targeted_headline = (
        f"{len(design)} targeted candidate-design cells selected; first roles: "
        + ", ".join(design["expected_role"].head(5).astype(str).tolist())
        if not design.empty
        else "Candidate universe did not support targeted expansion."
    )
    return f"""# B8.6e Spatial Failure and Feature-Gap Closure Package

Status: `{status}`

## 1. Why B8.6e Follows B8.6d

B8.6d kept the two-stage System B surrogate diagnostic-only because spatial holdout remained the main blocker. B8.6e therefore does not train a broader model zoo and does not create AOI-wide predictions. It diagnoses the spatial failure, audits missing feature families, tests only safe compact engineered features, and prepares a review-only targeted N300 candidate design.

Dataset rows/cells/features: {len(joined)} joined diagnostic rows, {joined['cell_id'].nunique()} cells, {len(engineered)} engineered diagnostic features.

## 2. Spatial Failure Headline

{md_table(worst_spatial, ['spatial_bin', 'n_rows', 'n_cells', 'mean_abs_error', 'Spearman', 'top10pct_overlap', 'neutral_accuracy', 'false_promotion_rate', 'suspected_failure_type'])}

## 3. Typology x Spatial Failure Headline

{md_table(worst_cross, ['typology', 'spatial_bin', 'n_cells', 'meaningful_cooling_support', 'neutral_support', 'median_true_delta_tmrt_p90_c', 'median_predicted_delta_tmrt_p90_c', 'false_promotion_rate', 'failure_label'])}

## 4. Anchor Underprediction Context

{md_table(anchor_spatial, ['cell_id', 'spatial_bin', 'typology', 'mean_true_delta_tmrt_p90_c', 'mean_predicted_delta_tmrt_p90_c', 'mean_abs_error', 'underprediction_rate_for_cooling', 'false_neutral_rate'])}

## 5. Neutral False-Promotion Context

{md_table(neutral_bad, ['cell_id', 'split_family', 'spatial_bin', 'typology', 'known_neutral_flag', 'false_promotion_rate', 'mean_predicted_delta_tmrt_p90_c', 'mean_abs_error'])}

## 6. Feature Distribution Shift

{md_table(shift, ['distribution_axis', 'group_value', 'feature', 'standardized_difference_vs_rest', 'missing_fraction', 'out_of_domain_flag'])}

## 7. Domain Distance / OOD Diagnostics

Domain-distance rows written: {len(distances)}. These distances are diagnostic only and are not production predictors.

{md_table(distances, ['scope', 'cell_id', 'nearest_cell_id', 'feature_space_distance', 'distance_percentile', 'sparse_feature_space_flag'])}

## 8. Feature Gap Register

{md_table(gaps, ['feature_family', 'currently_available', 'computable_from_existing_compact_tables', 'requires_new_data_or_processing', 'expected_benefit', 'recommended_lane'], max_rows=12)}

## 9. Safe Engineered Feature Probe

{md_table(probe_spatial, ['feature_variant', 'MAE', 'Spearman', 'top10pct_overlap', 'neutral_accuracy', 'false_promotion_rate', 'anchor_MAE', 'Spearman_delta_vs_b86d', 'variant_decision'])}

Safe physical feature probe summary:

{md_table(safe_probe, ['split_family', 'Spearman_delta_vs_b86d', 'top10_delta_vs_b86d', 'variant_decision'])}

## 10. Targeted N300 Design

{targeted_headline}

This is candidate design only. It is not a SOLWEIG manifest, QGIS runner, N300 execution package, AOI-wide prediction, or B9 output.

## 11. Recommendation

- B8.6f: run a narrow improved-workflow lane only if reviewers accept the safe non-coordinate engineered features and require the same spatial/typology/cell-group holdouts.
- Targeted N300: recommended if reviewers agree current compact features cannot close spatial failure; use the candidate design as a review list only.
- External feature acquisition: prioritize connected shade continuity, pedestrian-accessible shade, hot-pocket/open-sun fraction, and canyon orientation or roughness.
- AOI preflight: no-go until spatial holdout and neutral false-promotion are materially improved.

## 12. Claim Boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not hazard_score or risk_score.
- Not observed truth.
- Not causal feature importance.
- No raster read/open/create/copy/write.
- No SOLWEIG or QGIS.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
"""


def recommendation_text(status: str) -> str:
    """Build the B8.6f recommendation Markdown."""
    return f"""# B8.6e B8.6f Recommendation

Status: `{status}`

Recommended next action: review a narrow B8.6f improved-workflow lane only after the B8.6e outputs are reviewed. B8.6f should test safe non-coordinate compact feature upgrades first, retain spatial/typology/cell-group holdouts, and keep coordinate/distance features diagnostic-only unless explicitly scoped otherwise.

If safe compact features do not materially improve spatial holdout, prioritize targeted N300 sampling design review and external compact feature acquisition for shade continuity, pedestrian-accessible shade, hot-pocket/open-sun fraction, and canyon orientation/roughness.

AOI-wide prediction and B9 remain blocked.
"""


def aoi_prerequisites_text() -> str:
    """Build AOI preflight prerequisite Markdown."""
    return """# B8.6e AOI-Wide Preflight Prerequisites

AOI-wide preflight is not ready from B8.6e.

Prerequisites before any separate future AOI preflight:

- spatial holdout Spearman and top10 overlap must materially improve under non-coordinate evidence;
- neutral false-promotion must be reduced and audited for known neutral cells;
- anchor underprediction must not worsen for TP_0857, TP_0542, TP_0141, TP_0433, and TP_0037;
- feature gaps must be closed or explicitly accepted as limitations;
- targeted N300, if pursued, must be reviewed as a separate sampling lane before execution.

Still forbidden here: AOI-wide prediction, B9, local WBGT, hazard_score, risk_score, raster, QGIS/SOLWEIG, Tmrt-to-WBGT conversion, observed-truth claims, causal feature-importance claims, and System A/B coupling.
"""


def cn_doc_text(config: dict[str, Any], tables: dict[str, pd.DataFrame], status: str) -> str:
    """Build the UTF-8 Chinese B8.6e documentation."""
    spatial = tables["spatial_holdout_failure_summary"]
    cross = tables["typology_spatial_cross_failure"]
    probe = tables["spatial_closure_probe_metrics"]
    design = tables["targeted_n300_candidate_design"]
    worst_bin = spatial.iloc[0]["spatial_bin"] if not spatial.empty else "NA"
    worst_cross = (
        f"{cross.iloc[0]['typology']} @ {cross.iloc[0]['spatial_bin']}"
        if not cross.empty
        else "NA"
    )
    safe_promising = "是" if probe["variant_decision"].astype(str).eq("FEATURE_UPGRADE_PROMISING").any() else "否"
    return f"""# OpenHeat System B B8.6e 空间失败与特征缺口闭合说明

生成范围：System B 代理模型的空间失败诊断、特征缺口审计、紧凑安全特征探针，以及 targeted N300 候选设计。

## 结论

- B8.6e 状态：`{status}`
- 最弱空间分箱：`{worst_bin}`
- 最弱 typology × spatial 组合：`{worst_cross}`
- 安全非坐标工程特征是否已证明可升级：{safe_promising}
- targeted N300 候选数：{len(design)}

## 为什么接在 B8.6d 后面

B8.6d 的两阶段工作流仍然是诊断用途，主要阻碍是 spatial_holdout。B8.6e 因此不继续盲目扩展模型族，而是解释空间失败、审计缺失特征，并判断 B8.6f 或 targeted N300 是否有必要。

## 主要发现

1. spatial_holdout 的排序与 top-k 支持仍然不足，弱分箱需要被视为特征空间覆盖问题，而不是已验证的局地 WBGT 预测问题。
2. 锚点低估仍然集中在少数强冷却参考单元，尤其需要检查 TP_0857 等锚点相似邻域。
3. 中性单元误提升仍需控制；中性边界单元不能因为模型输出被提升为冷却候选。
4. 当前紧凑特征对连续遮阴廊道、可步行遮阴、热口袋开敞曝晒比例、峡谷方向与粗糙度等表达仍不足。

## 建议

- B8.6f 只能作为窄范围改进工作流：优先复测安全、非坐标、可解释的紧凑工程特征。
- 如果当前紧凑特征无法闭合空间失败，应审阅 targeted N300 候选设计；它不是运行清单。
- AOI-wide preflight 和 B9 仍然不应启动。

## 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 hazard_score 或 risk_score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 SOLWEIG 或 QGIS。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
"""


def status_text(config: dict[str, Any], tables: dict[str, pd.DataFrame], status: str) -> str:
    """Build B8.6e status Markdown."""
    joined = tables["failure_joined_dataset"]
    design = tables["targeted_n300_candidate_design"]
    return f"""# B8.6e Status

Status: {status}
Branch: {config['branch']}
Scope: System B spatial failure / feature-gap closure using compact CSV inputs only.

## Key Results

- Joined diagnostic rows/cells: {len(joined)}/{joined['cell_id'].nunique()}
- Targeted candidate-design rows: {len(design)}
- AOI-wide/B9 status: BLOCKED; no AOI-wide prediction and no B9 output created.

## Caveats

- Labels are SOLWEIG-derived Tmrt deltas, not observed truth.
- Feature interpretation is diagnostic, not causal.
- Coordinate and distance features are diagnostic-only.
- No raster, QGIS, SOLWEIG, WBGT, hazard, risk, AOI-wide prediction, B9, or System A/B coupling output was created.

## Safe to Commit After Review

Compact B8.6e config, scripts, docs, CSV, and Markdown outputs.

## Not Safe to Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip packages, AOI-wide prediction outputs, and B9 outputs.
"""


def run(config_path: Path = DEFAULT_CONFIG) -> DecisionResult:
    """Write final decision outputs."""
    config = load_config(config_path)
    tables = load_outputs(config)
    status = decide_status(config, tables)
    matrix = decision_matrix(config, tables, status)
    write_csv(matrix, output_path(config, "decision_matrix"))
    write_text(recommendation_text(status), output_path(config, "b86f_recommendation"))
    write_text(aoi_prerequisites_text(), output_path(config, "aoi_preflight_prerequisites"))
    write_text(report_text(config, tables, status), output_path(config, "report"))
    write_text(status_text(config, tables, status), output_path(config, "status"))
    write_text(cn_doc_text(config, tables, status), output_path(config, "cn_doc"))
    joined = tables["failure_joined_dataset"]
    design = tables["targeted_n300_candidate_design"]
    return DecisionResult(
        status=status,
        dataset_rows=len(joined),
        dataset_cells=int(joined["cell_id"].nunique()),
        targeted_candidates=len(design),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Write B8.6e decision matrix, reports, status, and UTF-8 CN doc.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
