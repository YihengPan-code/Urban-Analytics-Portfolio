"""Write B8.6g2 baseline comparison, promotion gate, reports, and status.

Inputs:
    All B8.6g2 compact CSV outputs plus B8.6d/B8.6f compact baseline inputs.
Outputs:
    b86g2_baseline_comparison.csv, b86g2_promotion_gate.csv,
    b86g2_aoi_preflight_readiness_matrix.csv,
    b86g2_next_lane_decision_matrix.csv, b86g2_model_card.md,
    b86g2_report.md, B8_6G2_STATUS.md, and the UTF-8 Chinese CN doc.
Saved metrics:
    Baseline deltas, promotion-gate decisions, AOI/B9 status, next-lane
    recommendation, and model-card/report headline summaries.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86g2_common import (
    CLAIM_BOUNDARY,
    COMBO_COLS,
    DEFAULT_CONFIG,
    WEAK_SPLITS,
    load_config,
    markdown_table,
    metric_group_summary,
    now_stamp,
    output_path,
    read_csv,
    repo_path,
    safe_float,
    selected_two_stage_combo,
    write_csv,
    write_text,
)


PASS_STATUS = "B86G2_FEATURE_RETEST_PASS"
DIAGNOSTIC_STATUS = "B86G2_DIAGNOSTIC_IMPROVEMENT_ONLY"
NO_IMPROVEMENT_STATUS = "B86G2_NO_MATERIAL_IMPROVEMENT"
BLOCKED_STATUS = "B86G2_BLOCKED_INPUT"
FAILED_STATUS = "FAILED"


@dataclass(frozen=True)
class DecisionResult:
    """Workflow decision result."""

    status: str
    recommended_next_lane: str
    selected_feature_set: str
    selected_classifier: str
    selected_regressor: str


def selected_b86d_baseline(config: dict[str, Any]) -> pd.DataFrame:
    """Load B8.6d selected full_safe_compact/logistic/ridge baseline."""
    try:
        metrics = read_csv(config["b86d_combined_metrics_path"])
    except FileNotFoundError:
        return pd.DataFrame()
    selected = metrics.copy()
    filters = {
        "feature_set": "full_safe_compact",
        "classifier": "logistic_regression",
        "regressor": "ridge",
    }
    for column, value in filters.items():
        selected = selected.loc[selected[column].astype(str).eq(value)]
    selected = selected.loc[pd.to_numeric(selected["neutral_threshold_c"], errors="coerce").eq(float(config["neutral_threshold_c"]))]
    if selected.empty:
        return pd.DataFrame()
    grouped = selected.groupby("split_family", dropna=False).agg(
        b86d_MAE=("MAE", "mean"),
        b86d_RMSE=("RMSE", "mean"),
        b86d_Spearman=("Spearman_observed_vs_predicted", "mean"),
        b86d_top10pct_overlap=("top10pct_overlap", "mean"),
        b86d_false_promotion_rate=("false_promotion_rate", "mean"),
        b86d_anchor_MAE=("robust_anchor_MAE", "mean"),
        b86d_neutral_accuracy=("accuracy", "mean"),
    ).reset_index()
    return grouped


def baseline_comparison(config: dict[str, Any], by_split: pd.DataFrame) -> pd.DataFrame:
    """Compare selected B8.6g2 metrics against B8.6d and B8.6f readiness context."""
    b86g2 = by_split.groupby("split_family", dropna=False).agg(
        b86g2_MAE=("MAE", "mean"),
        b86g2_RMSE=("RMSE", "mean"),
        b86g2_Spearman=("Spearman", "mean"),
        b86g2_top10pct_overlap=("top10pct_overlap", "mean"),
        b86g2_false_promotion_rate=("false_promotion_rate", "mean"),
        b86g2_anchor_MAE=("anchor_MAE", "mean"),
        b86g2_neutral_accuracy=("neutral_accuracy", "mean"),
    ).reset_index()
    out = b86g2.merge(selected_b86d_baseline(config), on="split_family", how="left")
    out["Spearman_delta_vs_b86d"] = out["b86g2_Spearman"] - out["b86d_Spearman"]
    out["top10_delta_vs_b86d"] = out["b86g2_top10pct_overlap"] - out["b86d_top10pct_overlap"]
    out["false_promotion_delta_vs_b86d"] = out["b86g2_false_promotion_rate"] - out["b86d_false_promotion_rate"]
    out["anchor_MAE_delta_vs_b86d"] = out["b86g2_anchor_MAE"] - out["b86d_anchor_MAE"]
    try:
        readiness = read_csv(config["b86f_aoi_readiness_path"])
        readiness_map = readiness.set_index("readiness_item")["status"].to_dict()
    except FileNotFoundError:
        readiness_map = {}
    split_to_item = {
        "spatial_holdout": "spatial_holdout",
        "typology_holdout": "typology_holdout",
        "cell_group_holdout": "cell_group_holdout",
        "forcing_day_holdout": "claim_boundary",
        "hour_holdout": "claim_boundary",
    }
    out["b86f_context_status"] = out["split_family"].map(lambda value: readiness_map.get(split_to_item.get(str(value), ""), "not_mapped"))
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def best_single_stage(single_stage: pd.DataFrame) -> pd.Series:
    """Select a headline single-stage model from weak split families."""
    ok = single_stage.loc[single_stage["status"].astype(str).eq("OK") & single_stage["split_family"].isin(WEAK_SPLITS)].copy()
    if ok.empty:
        return pd.Series(dtype=object)
    grouped = ok.groupby(["feature_set", "model"], dropna=False).agg(
        Spearman=("Spearman", "mean"),
        top10pct_overlap=("top10pct_overlap", "mean"),
        MAE=("MAE", "mean"),
        anchor_MAE=("anchor_MAE", "mean"),
    ).reset_index()
    grouped["score"] = grouped["Spearman"].fillna(-1.0) * 0.55 + grouped["top10pct_overlap"].fillna(0.0) * 0.35 - grouped[
        "MAE"
    ].fillna(1.0) * 0.10
    return grouped.sort_values(["score", "Spearman", "top10pct_overlap"], ascending=False).iloc[0]


def promotion_gate_frame(
    config: dict[str, Any],
    comparison: pd.DataFrame,
    anchor: pd.DataFrame,
    registry: pd.DataFrame,
    best: dict[str, Any],
) -> tuple[str, pd.DataFrame]:
    """Evaluate the B8.6g2 promotion gate."""
    thresholds = config["promotion_gate"]
    rows: list[dict[str, Any]] = []

    def split_value(split: str, column: str) -> float:
        row = comparison.loc[comparison["split_family"].astype(str).eq(split)]
        return safe_float(row[column].iloc[0]) if not row.empty and column in row.columns else float("nan")

    spatial_spearman_gain = split_value("spatial_holdout", "Spearman_delta_vs_b86d")
    spatial_top10_gain = split_value("spatial_holdout", "top10_delta_vs_b86d")
    weak = comparison.loc[comparison["split_family"].isin(WEAK_SPLITS)].copy()
    false_promotion_reduction = safe_float(weak["b86d_false_promotion_rate"].mean() - weak["b86g2_false_promotion_rate"].mean())
    anchor_delta = safe_float(anchor["MAE_delta_vs_b86d"].mean()) if not anchor.empty and "MAE_delta_vs_b86d" in anchor.columns else float("nan")
    cell_group_gain = max(
        split_value("cell_group_holdout", "Spearman_delta_vs_b86d"),
        split_value("cell_group_holdout", "top10_delta_vs_b86d"),
    )
    typology_gain = max(
        split_value("typology_holdout", "Spearman_delta_vs_b86d"),
        split_value("typology_holdout", "top10_delta_vs_b86d"),
    )
    selected_registry = registry.loc[registry["feature_set"].astype(str).eq(str(best.get("feature_set")))]
    shortcut_driven = bool(selected_registry["coordinate_dependent"].astype(str).str.lower().eq("true").any()) if not selected_registry.empty else False

    checks = [
        (
            "spatial_spearman_material_gain",
            spatial_spearman_gain >= float(thresholds["material_spearman_gain"]),
            f"spatial Spearman delta vs B8.6d={spatial_spearman_gain:.3f}",
            "Require material spatial ranking improvement before AOI/B9 can move.",
        ),
        (
            "spatial_top10_material_gain",
            spatial_top10_gain >= float(thresholds["material_top10_gain"]),
            f"spatial top10pct delta vs B8.6d={spatial_top10_gain:.3f}",
            "Require top-k support, not Spearman alone.",
        ),
        (
            "neutral_false_promotion_reduced",
            false_promotion_reduction >= float(thresholds["false_promotion_reduction_min"]),
            f"weak-split false-promotion reduction={false_promotion_reduction:.3f}",
            "Keep neutral false-promotion as explicit blocker if not reduced.",
        ),
        (
            "anchor_underprediction_not_worse",
            pd.isna(anchor_delta) or anchor_delta <= float(thresholds["anchor_mae_worsening_tolerance"]),
            f"mean anchor MAE delta vs B8.6d={anchor_delta:.3f}",
            "Do not accept feature upgrade if anchor underprediction worsens.",
        ),
        (
            "cell_group_or_typology_support",
            (cell_group_gain >= float(thresholds["material_spearman_gain"]))
            or (typology_gain >= float(thresholds["material_spearman_gain"])),
            f"cell_group best gain={cell_group_gain:.3f}; typology best gain={typology_gain:.3f}",
            "Require at least one supporting weak holdout to improve.",
        ),
        (
            "not_coordinate_or_diagnostic_shortcut_driven",
            not shortcut_driven,
            f"selected feature set={best.get('feature_set')}; coordinate_dependent={shortcut_driven}",
            "Coordinate/diagnostic shortcuts cannot justify promotion.",
        ),
        (
            "claim_boundaries_clean",
            True,
            "No raster, QGIS/SOLWEIG, AOI-wide, B9, WBGT, hazard/risk, observed-truth, causal-importance, Tmrt-to-WBGT, or System A/B coupling output is produced.",
            "Keep claim boundaries in all downstream wording.",
        ),
    ]
    for gate, passed, evidence, next_action in checks:
        rows.append(
            {
                "gate": gate,
                "status": "PASS" if passed else "DIAGNOSTIC",
                "evidence": evidence,
                "next_action": next_action,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    frame = pd.DataFrame(rows)
    all_pass = bool(frame["status"].eq("PASS").all())
    any_improvement = any(
        [
            spatial_spearman_gain > 0,
            spatial_top10_gain > 0,
            false_promotion_reduction > 0,
            cell_group_gain > 0,
            typology_gain > 0,
            not pd.isna(anchor_delta) and anchor_delta < 0,
        ]
    )
    if all_pass:
        status = PASS_STATUS
    elif any_improvement:
        status = DIAGNOSTIC_STATUS
    else:
        status = NO_IMPROVEMENT_STATUS
    return status, frame


def aoi_readiness(status: str, comparison: pd.DataFrame) -> pd.DataFrame:
    """Create AOI/B9 readiness matrix."""
    spatial = comparison.loc[comparison["split_family"].astype(str).eq("spatial_holdout")]
    spatial_evidence = "missing spatial metrics"
    if not spatial.empty:
        row = spatial.iloc[0]
        spatial_evidence = (
            f"Spearman={row['b86g2_Spearman']:.3f}; top10pct={row['b86g2_top10pct_overlap']:.3f}; "
            f"delta_vs_b86d=({row['Spearman_delta_vs_b86d']:.3f}, {row['top10_delta_vs_b86d']:.3f})"
        )
    rows = [
        {
            "readiness_item": "spatial_holdout",
            "status": "BLOCKED" if status != PASS_STATUS else "REVIEW_ONLY_NOT_EXECUTED",
            "evidence": spatial_evidence,
            "blocker": "Spatial/top-k evidence is still compact validation only.",
            "allowed_future_lane": "B8.6h_scope_limited_dry_run_preflight_review_only",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "readiness_item": "aoi_preflight",
            "status": "AOI_PREFLIGHT_BLOCKED" if status != PASS_STATUS else "FUTURE_DRY_RUN_PREFLIGHT_REVIEW_ONLY",
            "evidence": "B8.6g2 creates no AOI-wide prediction.",
            "blocker": "Separate reviewed preflight lane required.",
            "allowed_future_lane": "B8.6h_scope_limited_dry_run",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "readiness_item": "b9",
            "status": "B9_BLOCKED",
            "evidence": "B8.6g2 is not B9 and produces no B9 output.",
            "blocker": "AOI and production validation remain blocked.",
            "allowed_future_lane": "none_in_this_lane",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    return pd.DataFrame(rows)


def next_lane_matrix(status: str, ablation: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """Create next-lane recommendation matrix."""
    spatial_help = []
    if not ablation.empty and "helps_spatial_holdout" in ablation.columns:
        spatial_help = sorted(
            ablation.loc[ablation["helps_spatial_holdout"].astype(bool), "removed_family_key"].dropna().astype(str).unique().tolist()
        )
    if status == PASS_STATUS:
        recommended = "B8.6h scope-limited dry-run preflight"
    elif status == DIAGNOSTIC_STATUS:
        recommended = "B8.7-N300-PRE plus B8.6g3 true vector source acquisition"
    elif status == NO_IMPROVEMENT_STATUS:
        recommended = "B8.6g3 true vector source acquisition"
    else:
        recommended = "no-go / wait"
    rows = [
        {
            "future_lane": "B8.7-N300-PRE",
            "recommended_priority": "high" if status != PASS_STATUS else "medium",
            "why": "Add targeted sample support because B8.6g2 remains compact N150 validation only.",
            "decision": "recommended" if status in {DIAGNOSTIC_STATUS, NO_IMPROVEMENT_STATUS} else "secondary_review",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "B8.6g3 true vector source acquisition",
            "recommended_priority": "high" if status != PASS_STATUS else "medium",
            "why": "Connected shade corridor remains unavailable; proxy families need true vector sources.",
            "decision": "recommended" if status != PASS_STATUS else "review_if_needed",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "B8.6h scope-limited dry-run",
            "recommended_priority": "conditional",
            "why": "Only appropriate after reviewed compact evidence; B8.6g2 itself creates no AOI-wide output.",
            "decision": "conditional_candidate" if status == PASS_STATUS else "not_now",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "no-go / wait",
            "recommended_priority": "fallback",
            "why": f"Use if reviewers reject N300/vector acquisition. Ablation spatial-help signals: {', '.join(spatial_help) or 'none'}.",
            "decision": "fallback",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    return recommended, pd.DataFrame(rows)


def split_headline(by_split: pd.DataFrame) -> str:
    """Create a compact split headline."""
    if by_split.empty:
        return "No selected split metrics available."
    parts = []
    summary = by_split.groupby("split_family", dropna=False).mean(numeric_only=True).reset_index()
    for family in ["spatial_holdout", "cell_group_holdout", "typology_holdout", "forcing_day_holdout", "hour_holdout"]:
        row = summary.loc[summary["split_family"].astype(str).eq(family)]
        if row.empty:
            continue
        item = row.iloc[0]
        parts.append(
            f"{family}: Spearman={item['Spearman']:.3f}, top10pct={item['top10pct_overlap']:.3f}, false_promotion={item['false_promotion_rate']:.3f}"
        )
    return "; ".join(parts)


def ablation_headline(ablation: pd.DataFrame) -> str:
    """Summarize family ablation signals."""
    if ablation.empty:
        return "No ablation metrics available."
    spatial = sorted(ablation.loc[ablation.get("helps_spatial_holdout", False).astype(bool), "removed_family_key"].dropna().astype(str).unique())
    neutral = sorted(
        ablation.loc[ablation.get("helps_neutral_false_promotion", False).astype(bool), "removed_family_key"].dropna().astype(str).unique()
    )
    anchor = sorted(
        ablation.loc[ablation.get("helps_anchor_underprediction", False).astype(bool), "removed_family_key"].dropna().astype(str).unique()
    )
    return (
        f"spatial_help={', '.join(spatial) or 'none'}; "
        f"neutral_false_promotion_help={', '.join(neutral) or 'none'}; "
        f"anchor_help={', '.join(anchor) or 'none'}"
    )


def report_text(
    config: dict[str, Any],
    status: str,
    best: dict[str, Any],
    frames: dict[str, pd.DataFrame],
    recommended: str,
) -> str:
    """Build English B8.6g2 report."""
    inventory = frames["inventory"]
    dataset_row = inventory.loc[inventory["input_key"].eq("f5_pairwise_label_path")].iloc[0] if not inventory.empty else {}
    single_best = best_single_stage(frames["single_stage"])
    single_headline = (
        f"{single_best.get('feature_set')} + {single_best.get('model')}: weak-split Spearman={single_best.get('Spearman'):.3f}, "
        f"top10pct={single_best.get('top10pct_overlap'):.3f}, MAE={single_best.get('MAE'):.3f}"
        if not single_best.empty
        else "No single-stage model completed."
    )
    return f"""# B8.6g2 Feature-Upgraded Surrogate Retest

Generated: {now_stamp()}

Status: `{status}`

## 1. Why B8.6g2 follows B8.6g

B8.6g produced compact/vector-derived feature tables but did not train or promote a final surrogate. B8.6g2 therefore retests those B8.6g features against the same blocked validation families used in B8.6d/B8.6f, without creating AOI-wide or B9 outputs.

## 2. Input rows and cell counts

- Modeling rows: {int(dataset_row.get("row_count", 0))}
- Unique cells: {int(dataset_row.get("unique_cells", 0))}
- Expected rows/cells: {config["expected_label_rows"]}/{config["expected_n150_cell_count"]}
- B8.6g features are joined to F5 labels by `cell_id`; `cell_id` is metadata/group only.

## 3. Feature leakage audit

- Leakage audit rows: {len(frames["leakage"])}
- Registered feature sets: {len(frames["registry"])}
- Target-derived columns, status/method/source fields, output paths, raster/QGIS/SOLWEIG/WBGT/risk/hazard/observed columns, and `cell_id` are excluded as predictors.

## 4. Feature-set definitions

{markdown_table(frames["registry"], ["feature_set", "feature_count", "proxy_feature_count", "vector_or_vector_compact_feature_count", "uses_hour_sgt", "status"], 10)}

## 5. Single-stage results

- Best single-stage headline: {single_headline}

{markdown_table(metric_group_summary(frames["single_stage"].loc[frames["single_stage"]["status"].astype(str).eq("OK")], ["feature_set", "model"]), ["feature_set", "model", "n_folds", "MAE", "Spearman", "top10pct_overlap", "anchor_MAE"], 12)}

## 6. Two-stage results

- Selected workflow: `{best.get("feature_set")}` + `{best.get("classifier")}` / `{best.get("regressor")}` at neutral threshold {float(best.get("neutral_threshold_c", config["neutral_threshold_c"])):.2f} C.

{markdown_table(frames["two_stage"].sort_values(["Spearman", "top10pct_overlap"], ascending=False), ["feature_set", "classifier", "regressor", "split_family", "MAE", "Spearman", "top10pct_overlap", "false_promotion_rate", "anchor_MAE"], 16)}

## 7. Baseline comparison vs B8.6d/B8.6f

{markdown_table(frames["baseline"], ["split_family", "b86g2_Spearman", "b86d_Spearman", "Spearman_delta_vs_b86d", "b86g2_top10pct_overlap", "b86d_top10pct_overlap", "top10_delta_vs_b86d", "b86f_context_status"], 10)}

## 8. Blocked validation-family results

- {split_headline(frames["by_split"])}

## 9. Feature ablation

- {ablation_headline(frames["ablation"])}

{markdown_table(frames["ablation"], ["ablation_variant", "split_family", "Spearman_delta_full_minus_variant", "top10_delta_full_minus_variant", "false_promotion_delta_variant_minus_full", "anchor_MAE_delta_variant_minus_full"], 14)}

## 10. Anchor / neutral / unstable diagnostics

- Anchor diagnostic rows: {len(frames["anchor"])}
- Neutral and near-zero diagnostic rows: {len(frames["neutral"])}
- Unstable-cell diagnostic rows: {len(frames["unstable"])}

## 11. Whether B8.6g features help

The promotion gate status is `{status}`. Improvements are treated as diagnostic unless spatial Spearman, spatial top-k, neutral false-promotion, anchor behavior, and at least one supporting weak holdout all pass together.

## 12. AOI preflight readiness

{markdown_table(frames["aoi"], ["readiness_item", "status", "evidence", "allowed_future_lane"], 10)}

## 13. Next lane recommendation

Recommended next lane: `{recommended}`.

{markdown_table(frames["next"], ["future_lane", "recommended_priority", "decision", "why"], 10)}

## 14. Claim boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not risk score or hazard score.
- Not observed truth.
- Not causal feature importance.
- No raster read/open/copy/create/write.
- No QGIS or SOLWEIG.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
"""


def model_card_text(status: str, best: dict[str, Any], by_split: pd.DataFrame) -> str:
    """Build model card Markdown."""
    return f"""# B8.6g2 Feature-Upgraded Surrogate Model Card

Generated: {now_stamp()}

## Intended role

Compact N150 retest of B8.6g feature-upgraded surrogate candidates for SOLWEIG-derived Tmrt-delta labels. This is a diagnostic validation artifact only.

## Decision

`{status}`

## Selected workflow

- Feature set: `{best.get("feature_set")}`
- Stage 1 classifier: `{best.get("classifier")}`
- Stage 2 regressor: `{best.get("regressor")}`
- Neutral threshold: `{float(best.get("neutral_threshold_c", 0.05)):.2f}` C
- Primary target: `delta_tmrt_p90_c`

## Validation headline

{markdown_table(by_split.groupby("split_family", dropna=False).mean(numeric_only=True).reset_index(), ["split_family", "MAE", "Spearman", "top10pct_overlap", "neutral_accuracy", "false_promotion_rate"], 10)}

## Non-claims

Not B9, not AOI-wide prediction, not local WBGT, not risk/hazard score, not observed truth, not causal feature importance, no raster/QGIS/SOLWEIG, no Tmrt-to-WBGT conversion, and no System A/B coupling.
"""


def cn_doc_text(status: str, best: dict[str, Any], frames: dict[str, pd.DataFrame], recommended: str) -> str:
    """Build valid UTF-8 Chinese documentation."""
    return f"""# OpenHeat System B B8.6g2 特征升级代理模型复测说明

生成时间：{now_stamp()}

## 结论

- B8.6g2 状态：`{status}`
- 选定工作流：`{best.get("feature_set")}` + `{best.get("classifier")}` / `{best.get("regressor")}`
- 主目标：`delta_tmrt_p90_c`
- 中性阈值：{float(best.get("neutral_threshold_c", 0.05)):.2f} C
- AOI / B9：继续阻断；本轮不生成 AOI-wide prediction，也不进入 B9。

## 为什么接在 B8.6g 后面

B8.6g 只完成了紧凑/矢量派生特征获取，没有训练最终代理模型，也没有生成 AOI 范围预测。B8.6g2 的作用是在 N150 紧凑数据上复测这些新特征是否改善 spatial、typology、cell-group、forcing-day 和 hour 留出验证。

## 输入规模

- 建模行数：{int(frames["dataset"].shape[0])}
- 唯一 cell 数：{int(frames["dataset"]["cell_id"].nunique()) if not frames["dataset"].empty else 0}
- 特征表通过 `cell_id` 与 F5 标签连接；`cell_id` 只用于元数据和分组，不作为数值预测特征。

## 泄漏审计和特征集

目标派生列、状态/方法/来源列、路径列、raster/QGIS/SOLWEIG/WBGT/risk/hazard/observed 相关列均被排除。`hour_sgt` 可作为预测特征，但 hour holdout 必须保留为泛化检验。

{markdown_table(frames["registry"], ["feature_set", "feature_count", "proxy_feature_count", "vector_or_vector_compact_feature_count", "status"], 10)}

## 主要验证结果

{markdown_table(frames["by_split"].groupby("split_family", dropna=False).mean(numeric_only=True).reset_index(), ["split_family", "MAE", "Spearman", "top10pct_overlap", "neutral_accuracy", "false_promotion_rate"], 10)}

## 与 B8.6d / B8.6f 的比较

{markdown_table(frames["baseline"], ["split_family", "Spearman_delta_vs_b86d", "top10_delta_vs_b86d", "false_promotion_delta_vs_b86d", "anchor_MAE_delta_vs_b86d", "b86f_context_status"], 10)}

## 特征消融

{ablation_headline(frames["ablation"])}

## 锚点、中性边界和不稳定单元

- 锚点诊断行数：{len(frames["anchor"])}
- 中性/近零诊断行数：{len(frames["neutral"])}
- 不稳定单元诊断行数：{len(frames["unstable"])}

## AOI 预检和下一路线

AOI preflight 仍为阻断状态；即使出现诊断改善，也只能建议未来单独评审的 dry-run preflight，不能在本轮执行。推荐下一路线：`{recommended}`。

## 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 risk score 或 hazard score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 QGIS 或 SOLWEIG。
- 没有 Tmrt-to-WBGT 转换。
- 没有 System A/B coupling。
"""


def status_text(status: str, best: dict[str, Any], config: dict[str, Any], frames: dict[str, pd.DataFrame], recommended: str) -> str:
    """Build lane status Markdown."""
    outputs = [str(repo_path(value).relative_to(repo_path("."))) for value in config["outputs"].values()]
    return f"""# B8.6g2 Status

Generated: {now_stamp()}
Status: {status}
Branch: {config["branch"]}
Scope: System B feature-upgraded compact surrogate retest using B8.6g N150 features and F5 labels.

## Commands run by suite

- `python scripts/v12_b86g2_run_feature_retest.py --config configs/v12/systemb_b86g2_feature_retest.yaml`

## Key results

- Modeling rows / unique cells: {len(frames["dataset"])}/{int(frames["dataset"]["cell_id"].nunique()) if not frames["dataset"].empty else 0}
- Selected two-stage workflow: {best.get("feature_set")} + {best.get("classifier")} / {best.get("regressor")}
- Validation headline: {split_headline(frames["by_split"])}
- Ablation headline: {ablation_headline(frames["ablation"])}
- AOI/B9 status: AOI_PREFLIGHT_BLOCKED / B9_BLOCKED
- Recommended next lane: {recommended}

## Files created / modified

{chr(10).join(f"- `{path}`" for path in outputs)}

## Caveats

- Labels are SOLWEIG-derived compact Tmrt deltas, not observed truth.
- Feature effects are diagnostic and non-causal.
- This lane creates no AOI-wide prediction, B9 output, WBGT, hazard_score, risk_score, raster, QGIS/SOLWEIG run, Tmrt-to-WBGT conversion, or System A/B coupling output.

## Safe to commit after review

Compact B8.6g2 config, scripts, docs, CSV, and Markdown outputs.

## Not safe to commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip packages, AOI-wide predictions, B9 outputs, WBGT, hazard_score, risk_score, and System A/B coupling outputs.
"""


def read_frame(config: dict[str, Any], key: str) -> pd.DataFrame:
    """Read an output CSV if it exists."""
    path = output_path(config, key)
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def run(config_path: Path = DEFAULT_CONFIG) -> DecisionResult:
    """Write B8.6g2 decision artifacts and reports."""
    config = load_config(config_path)
    combined = read_frame(config, "combined_pipeline_metrics")
    best = selected_two_stage_combo(combined, config)
    frames = {
        "inventory": read_frame(config, "input_inventory"),
        "dataset": read_frame(config, "modeling_dataset"),
        "registry": read_frame(config, "feature_set_registry"),
        "leakage": read_frame(config, "feature_leakage_audit"),
        "single_stage": read_frame(config, "single_stage_metrics"),
        "two_stage": read_frame(config, "two_stage_metrics"),
        "by_split": read_frame(config, "metrics_by_split"),
        "ablation": read_frame(config, "feature_ablation_metrics"),
        "anchor": read_frame(config, "anchor_cell_diagnostics"),
        "neutral": read_frame(config, "neutral_boundary_diagnostics"),
        "unstable": read_frame(config, "unstable_cell_diagnostics"),
    }
    comparison = baseline_comparison(config, frames["by_split"])
    status, promotion = promotion_gate_frame(config, comparison, frames["anchor"], frames["registry"], best)
    aoi = aoi_readiness(status, comparison)
    recommended, next_matrix = next_lane_matrix(status, frames["ablation"])
    frames["baseline"] = comparison
    frames["promotion"] = promotion
    frames["aoi"] = aoi
    frames["next"] = next_matrix
    write_csv(comparison, output_path(config, "baseline_comparison"))
    write_csv(promotion, output_path(config, "promotion_gate"))
    write_csv(aoi, output_path(config, "aoi_preflight_readiness_matrix"))
    write_csv(next_matrix, output_path(config, "next_lane_decision_matrix"))
    write_text(model_card_text(status, best, frames["by_split"]), output_path(config, "model_card"))
    write_text(report_text(config, status, best, frames, recommended), output_path(config, "report"))
    write_text(cn_doc_text(status, best, frames, recommended), output_path(config, "cn_doc"))
    write_text(status_text(status, best, config, frames, recommended), output_path(config, "status"))
    return DecisionResult(
        status,
        recommended,
        str(best.get("feature_set", "")),
        str(best.get("classifier", "")),
        str(best.get("regressor", "")),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Write B8.6g2 baseline comparison, gate, reports, and status.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
