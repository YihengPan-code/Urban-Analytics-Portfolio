"""Write B8.6g decision matrices, prompts, report, status, and CN doc.

Inputs:
    B8.6g inventories, feature schema, family feature tables, feature datasets,
    readiness/coverage/quality matrices, and failure-context join.
Outputs:
    b86g_feature_gap_closure_matrix.csv, b86g_retest_readiness_matrix.csv,
    b86g_aoi_preflight_boundary_matrix.csv, b86g_next_lane_decision_matrix.csv,
    future Codex prompts, b86g_report.md, B8_6G_STATUS.md, and
    docs/v12/OpenHeat_SystemB_B8_6g_feature_acquisition_CN.md.
Saved metrics:
    Feature-gap closure status, retest readiness, AOI/B9 boundary status,
    next-lane recommendation, source/coverage headlines, and explicit claim
    boundaries. This script does not train a surrogate, create AOI-wide
    predictions, create B9 outputs, run QGIS/SOLWEIG, read/write rasters,
    produce local WBGT, hazard/risk score, observed-truth claims, causal
    feature-importance claims, Tmrt-to-WBGT conversion, or System A/B coupling.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86g_feature_readiness import HIGH_PRIORITY_FAMILIES
from v12_b86g_source_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, load_config, output_path, read_csv, write_csv, write_text


@dataclass(frozen=True)
class WorkflowDecisionResult:
    """B8.6g workflow decision result."""

    status: str
    retest_readiness_status: str
    aoi_b9_status: str
    recommended_next_lane: str


def md_table(frame: pd.DataFrame, columns: list[str] | None = None, max_rows: int = 20) -> str:
    """Render a compact Markdown table without optional dependencies."""
    if frame.empty:
        return "_No rows._"
    view = frame.copy()
    if columns:
        view = view[[column for column in columns if column in view.columns]]
    view = view.head(max_rows)
    headers = [str(column) for column in view.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in view.iterrows():
        values = [str(row[column]).replace("\n", " ") for column in view.columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def decide_status(inputs: pd.DataFrame, quality: pd.DataFrame, readiness: pd.DataFrame) -> str:
    """Decide B8.6g final feature acquisition status."""
    if inputs.empty or (~inputs["exists"].astype(bool)).any() or inputs["missing_required_columns"].fillna("").astype(str).str.len().gt(0).any():
        return "B86G_BLOCKED_INPUT"
    high = readiness.loc[readiness["feature_family"].isin(HIGH_PRIORITY_FAMILIES)]
    usable_high = high.loc[(high["n150_coverage_fraction"] >= 0.8) & (high["n_non_null_features"] > 0)]
    vector_high = usable_high.loc[usable_high["proxy_status"].astype(str).isin(["VECTOR_DERIVED_COMPACT", "STRONG_COMPACT_VECTOR_PROXY"])]
    if not quality.empty and quality["status"].astype(str).eq("FAIL").any():
        return "FAILED"
    if not usable_high.empty and not vector_high.empty:
        return "B86G_FEATURE_ACQUISITION_PASS"
    if not usable_high.empty:
        return "B86G_PARTIAL_PROXY_FEATURES"
    return "B86G_NOT_READY_NEEDS_VECTOR_SOURCES"


def feature_gap_closure_matrix(config: dict[str, Any], readiness: pd.DataFrame) -> pd.DataFrame:
    """Build B8.6f feature-gap closure matrix."""
    register = read_csv(config["b86f_feature_acquisition_register_path"])
    rows: list[dict[str, Any]] = []
    readiness_map = {row["feature_family"]: row for _, row in readiness.iterrows()}
    for _, register_row in register.iterrows():
        family = str(register_row["feature_family"])
        ready = readiness_map.get(family)
        if ready is None:
            source_found = False
            computed = False
            proxy_only = False
            n150 = 0.0
            n300 = 0.0
            closure = "NOT_AVAILABLE_REQUIRES_SOURCE"
            next_lane = "acquire source"
        else:
            source_text = str(ready["source_status"])
            source_found = "NOT_AVAILABLE" not in source_text and "REQUIRES_" not in source_text
            computed = float(ready["n_non_null_features"]) > 0
            proxy_only = "PROXY" in str(ready["proxy_status"])
            n150 = float(ready["n150_coverage_fraction"])
            n300 = float(ready["n300_coverage_fraction"])
            if not computed and "GEOMETRY" in str(ready["blocked_reason"]):
                closure = "BLOCKED_GEOMETRY"
            elif not computed:
                closure = "NOT_AVAILABLE_REQUIRES_SOURCE"
            elif str(ready["proxy_status"]) == "VECTOR_DERIVED_COMPACT":
                closure = "CLOSED_WITH_VECTOR_FEATURE"
            elif proxy_only or str(ready["proxy_status"]) in {"STRONG_COMPACT_VECTOR_PROXY", "PROXY_ONLY"}:
                closure = "PARTIAL_PROXY_ONLY"
            else:
                closure = "DIAGNOSTIC_ONLY"
            next_lane = "B8.6g2/B8.6f2 feature-upgraded compact retest" if computed else "B8.7-N300-PRE or acquire missing vector source"
        rows.append(
            {
                "gap_family": family,
                "B8.6f_priority": register_row.get("priority", ""),
                "B8.6g_source_found": source_found,
                "feature_computed": computed,
                "proxy_only": proxy_only,
                "n150_coverage": n150,
                "n300_coverage": n300,
                "addresses_failure_modes": register_row.get("likely_failure_modes_addressed", ""),
                "closure_status": closure,
                "recommended_next_lane": next_lane,
            }
        )
    return pd.DataFrame(rows)


def retest_readiness_matrix(readiness: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Build retest readiness matrix and overall status."""
    high = readiness.loc[readiness["feature_family"].isin(HIGH_PRIORITY_FAMILIES)].copy()
    high["coverage_ready"] = high["n150_coverage_fraction"] >= 0.8
    high["strong_enough_for_retest"] = high["coverage_ready"] & high["proxy_status"].astype(str).isin(
        ["VECTOR_DERIVED_COMPACT", "STRONG_COMPACT_VECTOR_PROXY", "DIRECT_OR_COMPACT"]
    )
    strong_count = int(high["strong_enough_for_retest"].sum())
    proxy_count = int((high["coverage_ready"] & high["proxy_status"].astype(str).str.contains("PROXY", na=False)).sum())
    if strong_count >= 3:
        status = "READY_FOR_FEATURE_UPGRADED_RETEST"
    elif int(high["coverage_ready"].sum()) > 0:
        status = "PARTIAL_RETEST_ONLY"
    else:
        status = "NOT_READY_NEEDS_VECTOR_SOURCES"
    if strong_count < 3:
        n300_status = "TARGETED_N300_PRE_STILL_RECOMMENDED"
    else:
        n300_status = "TARGETED_N300_PRE_REVIEW_STILL_USEFUL"
    rows = [
        {
            "readiness_item": "high_priority_feature_coverage",
            "status": status,
            "evidence": f"strong_or_non_proxy_high_priority_families={strong_count}; coverage_ready_high_priority={int(high['coverage_ready'].sum())}; proxy_ready={proxy_count}",
            "allowed_action": "B8.6g2/B8.6f2 compact feature-upgraded retest only; no AOI prediction.",
        },
        {
            "readiness_item": "targeted_n300_pre",
            "status": n300_status,
            "evidence": "B8.6g does not create new SOLWEIG labels and shade-corridor/network sources remain unavailable.",
            "allowed_action": "B8.7-N300-PRE design freeze only; no SOLWEIG execution.",
        },
        {
            "readiness_item": "aoi_or_b9",
            "status": "NOT_READY",
            "evidence": "B8.6g only acquires features and does not run validation retest or AOI preflight.",
            "allowed_action": "keep AOI/B9 blocked.",
        },
    ]
    return pd.DataFrame(rows), status


def aoi_preflight_boundary_matrix() -> pd.DataFrame:
    """Keep AOI/B9 boundaries blocked after B8.6g."""
    return pd.DataFrame(
        [
            {
                "boundary_item": "overall_aoi_preflight",
                "status": "AOI_PREFLIGHT_BLOCKED",
                "evidence": "B8.6g created feature tables only; feature-upgraded retest has not been run.",
                "blocker": "requires formal retest and review before any AOI preflight.",
                "allowed_future_lane": "B8.6g2/B8.6f2|B8.7-N300-PRE",
                "claim_boundary": CLAIM_BOUNDARY,
            },
            {
                "boundary_item": "B9",
                "status": "BLOCKED",
                "evidence": "No AOI-wide prediction, no production surrogate promotion, and no new N300 labels.",
                "blocker": "spatial closure and sample support remain unresolved.",
                "allowed_future_lane": "not B9",
                "claim_boundary": CLAIM_BOUNDARY,
            },
        ]
    )


def next_lane_decision_matrix(status: str, retest_status: str) -> tuple[pd.DataFrame, str]:
    """Create next-lane recommendations."""
    if retest_status == "READY_FOR_FEATURE_UPGRADED_RETEST":
        recommended = "B8.6g2/B8.6f2 feature-upgraded compact surrogate retest"
    elif retest_status == "PARTIAL_RETEST_ONLY":
        recommended = "B8.6g2 partial feature-upgraded retest plus B8.7-N300-PRE design freeze"
    else:
        recommended = "B8.7-N300-PRE design freeze and source acquisition before retest"
    rows = [
        {
            "future_lane": "B8.6g2/B8.6f2 feature-upgraded surrogate retest",
            "recommended_priority": "high" if retest_status != "NOT_READY_NEEDS_VECTOR_SOURCES" else "medium_after_sources",
            "why": "B8.6g produced new compact/vector-derived feature tables, but no validation retest has been run.",
            "allowed_scope": "compact feature-upgraded surrogate retest only",
            "forbidden_actions": "no AOI-wide prediction, no B9, no WBGT, no hazard/risk score, no raster/QGIS/SOLWEIG.",
        },
        {
            "future_lane": "B8.7-N300-PRE targeted sample design freeze",
            "recommended_priority": "high",
            "why": "B8.6f N300 v2 remains role-balanced candidate design and shade-corridor/source gaps remain.",
            "allowed_scope": "freeze targeted N300 design only",
            "forbidden_actions": "no SOLWEIG execution, no manifest/run package, no QGIS runner.",
        },
        {
            "future_lane": "B8.6h scope-limited dry-run preflight",
            "recommended_priority": "low_conditional",
            "why": "Only after a retest shows materially stronger retained spatial/neutral metrics.",
            "allowed_scope": "diagnostic dry-run only",
            "forbidden_actions": "no AOI-wide/public-health output or B9.",
        },
        {
            "future_lane": "AOI/B9",
            "recommended_priority": "blocked",
            "why": "B8.6g is feature acquisition, not surrogate closure validation or production promotion.",
            "allowed_scope": "none",
            "forbidden_actions": "keep blocked.",
        },
    ]
    matrix = pd.DataFrame(rows)
    matrix["b86g_status"] = status
    matrix["claim_boundary"] = CLAIM_BOUNDARY
    return matrix, recommended


def prompt_b86g2() -> str:
    """Return future B8.6g2/B8.6f2 prompt."""
    return """# Future Codex prompt: B8.6g2 / B8.6f2 feature-upgraded surrogate retest

Work inside the OpenHeat-ToaPayoh project subdirectory.

Lane: B8.6g2/B8.6f2 compact feature-upgraded surrogate retest.

Use these B8.6g inputs:
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_n150_feature_dataset.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_feature_schema.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_feature_coverage_matrix.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_feature_quality_checks.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_failure_context_feature_join.csv
- outputs/v12_surrogate/b8_6d_two_stage_surrogate/b86d_oof_predictions.csv

Task:
Run only a compact feature-upgraded surrogate retest against the existing N150 labelled cells. Compare against B8.6d/B8.6f diagnostics using blocked spatial, typology, cell-group, forcing-day, and hour holdouts. Do not use target-derived columns as predictors. Treat proxy/status/method columns as diagnostic metadata unless explicitly registered as predictors in the B8.6g schema.

Forbidden:
No AOI-wide prediction, no B9, no QGIS, no SOLWEIG, no raster read/write/open/copy, no local WBGT, no hazard_score, no risk_score, no observed-truth claim, no causal feature-importance claim, no Tmrt-to-WBGT conversion, and no System A/B coupling.

Required outputs:
CSV metrics by split, anchor/neutral diagnostics for TP_0857/TP_0542/TP_0433/TP_0037/TP_0141 and known neutral/near-zero cells, feature inclusion audit, leakage audit, Markdown report, and next-lane decision. Keep AOI/B9 blocked unless a later reviewed lane explicitly changes that boundary.
"""


def prompt_b87() -> str:
    """Return future B8.7-N300-PRE prompt."""
    return """# Future Codex prompt: B8.7-N300-PRE updated feature-schema design freeze

Work inside the OpenHeat-ToaPayoh project subdirectory.

Lane: B8.7-N300-PRE targeted sample design freeze.

Use these inputs:
- outputs/v12_surrogate/b8_6f_surrogate_closure/b86f_targeted_n300_design_v2.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_n300_candidate_feature_dataset.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_feature_schema.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_feature_gap_closure_matrix.csv
- outputs/v12_surrogate/b8_6g_feature_acquisition/b86g_failure_context_feature_join.csv

Task:
Freeze an updated targeted N300 candidate design package and feature-schema review only. Use B8.6g feature coverage to flag candidates needing source review, anchor-like replication, neutral-boundary replication, shade-corridor/source acquisition, and typology/spatial support. This is not a SOLWEIG execution package.

Forbidden:
No SOLWEIG execution, no QGIS runner, no N300 SOLWEIG manifest, no raster read/write/open/copy, no AOI-wide prediction, no B9, no local WBGT, no hazard_score, no risk_score, no observed-truth claim, no causal feature-importance claim, no Tmrt-to-WBGT conversion, and no System A/B coupling.

Required outputs:
Updated N300-PRE design freeze CSV, schema coverage audit, exclusion/review register, Markdown report, and explicit keep-blocked AOI/B9 decision.
"""


def report_markdown(
    status: str,
    retest_status: str,
    recommended_next_lane: str,
    sources: pd.DataFrame,
    readiness: pd.DataFrame,
    coverage: pd.DataFrame,
    failure_join: pd.DataFrame,
    gap: pd.DataFrame,
    n150: pd.DataFrame,
    n300: pd.DataFrame,
) -> str:
    """Create B8.6g Markdown report."""
    usable_sources = int(sources["safety_status"].astype(str).eq("SAFE_TO_INSPECT").sum()) if not sources.empty else 0
    anchor_rows = failure_join.loc[failure_join["diagnostic_role"].astype(str).str.contains("anchor", case=False, na=False)]
    neutral_rows = failure_join.loc[failure_join["diagnostic_role"].astype(str).str.contains("neutral|near_zero", case=False, na=False, regex=True)]
    weak_rows = failure_join.loc[failure_join["row_type"].astype(str).eq("weak_spatial_bin_summary")]
    anchor_headline = f"{len(anchor_rows)} anchor rows joined; mean family coverage={anchor_rows['feature_family_coverage_fraction'].mean():.3f}" if not anchor_rows.empty else "no anchor rows joined"
    neutral_headline = f"{len(neutral_rows)} neutral/near-zero rows joined; mean family coverage={neutral_rows['feature_family_coverage_fraction'].mean():.3f}" if not neutral_rows.empty else "no neutral rows joined"
    weak_headline = f"{len(weak_rows)} weak-bin summaries joined; mean family coverage={weak_rows['feature_family_coverage_fraction'].mean():.3f}" if not weak_rows.empty else "no weak-bin summary rows"
    computed = readiness.loc[readiness["n_non_null_features"].astype(float).gt(0), "feature_family"].tolist()
    blocked = readiness.loc[readiness["n_non_null_features"].astype(float).eq(0), "feature_family"].tolist()
    return f"""# B8.6g Vector/Compact Feature Acquisition

Status: `{status}`

## 1. Why B8.6g follows B8.6f

B8.6f kept AOI preflight and B9 blocked because spatial holdout, anchor underprediction, neutral false-promotion, and feature representation gaps remained unresolved. B8.6g therefore acquires compact/vector-derived cell features only; it does not train a final surrogate or create AOI-wide predictions.

## 2. Source discovery results

- Sources scanned: {len(sources)}
- Usable safe-to-inspect sources: {usable_sources}
- Raster/QGIS/SOLWEIG/raw roots were skipped by guardrail status rather than read.

{md_table(sources[['path', 'extension', 'likely_role', 'read_status', 'safety_status']].head(12))}

## 3. Feature family readiness

{md_table(readiness, ['feature_family', 'priority', 'b86g_computability_status', 'n150_coverage_fraction', 'n300_coverage_fraction', 'source_status', 'proxy_status'])}

## 4. Computed vs blocked features

Computed or partially computed families: {', '.join(computed) if computed else 'none'}.

Blocked families: {', '.join(blocked) if blocked else 'none'}.

## 5. N150 feature coverage

N150 feature dataset shape: {n150.shape}.

{md_table(coverage, ['feature_family', 'n150_coverage_fraction', 'n_non_null_features', 'proxy_status', 'blocked_reason'])}

## 6. N300 candidate feature coverage

N300 candidate feature dataset shape: {n300.shape}.

{md_table(coverage, ['feature_family', 'n300_coverage_fraction', 'n_non_null_features', 'proxy_status', 'recommended_next_action'])}

## 7. Failure-context feature coverage

- Anchors: {anchor_headline}.
- Neutral false-promotion / near-zero cells: {neutral_headline}.
- Weak spatial bins: {weak_headline}.

{md_table(failure_join, ['row_type', 'cell_id', 'diagnostic_role', 'spatial_bin', 'failure_type', 'feature_family_coverage_fraction'], 18)}

## 8. Feature gap closure matrix

{md_table(gap, ['gap_family', 'B8.6f_priority', 'feature_computed', 'proxy_only', 'closure_status', 'recommended_next_lane'])}

## 9. Retest readiness and next lanes

- Retest readiness: `{retest_status}`.
- Recommended next lane: {recommended_next_lane}.
- B8.7-N300-PRE remains useful because connected shade corridor/network sources are still not available and B8.6g created no new SOLWEIG labels.
- B8.6h scope-limited preflight remains low/conditional and cannot bypass a feature-upgraded retest.

## 10. Claim boundaries

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


def cn_doc_text(status: str, retest_status: str, recommended_next_lane: str, readiness: pd.DataFrame) -> str:
    """Create valid UTF-8 Chinese documentation for B8.6g."""
    computed = readiness.loc[readiness["n_non_null_features"].astype(float).gt(0), "feature_family"].tolist()
    blocked = readiness.loc[readiness["n_non_null_features"].astype(float).eq(0), "feature_family"].tolist()
    return f"""# OpenHeat System B B8.6g 矢量/紧凑特征获取说明

## 结论

- B8.6g 状态：`{status}`
- 复测准备：`{retest_status}`
- 推荐下一步：{recommended_next_lane}
- AOI / B9：继续阻断

## 为什么接在 B8.6f 后面

B8.6f 的结论是：AOI preflight 仍然阻断，B9 仍然阻断，主要原因不是再跑一个更复杂模型，而是局地遮阴、架空结构、热口袋、边界环境、树木与建筑相互作用、峡谷高度粗糙度等特征表达不足。B8.6g 因此只做矢量/紧凑来源发现、特征表生成、覆盖率和复测准备判断。

## 已计算的特征族

{', '.join(computed) if computed else '无。'}

## 仍然阻断或缺源的特征族

{', '.join(blocked) if blocked else '无。'}

## 重要解释

本轮生成的 pedestrian shade、sunlit hot pocket、tree/building interaction、canyon roughness 等多项字段是紧凑代理或矢量派生紧凑特征。它们可以进入未来 B8.6g2/B8.6f2 的诊断复测，但不能直接升级为生产级空间闭合证据。connected shade corridor 需要真正的行人遮阴网络或连通性来源，本轮不从质心距离臆造。

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


def status_markdown(status: str, retest_status: str, recommended_next_lane: str, n150: pd.DataFrame, n300: pd.DataFrame, sources: pd.DataFrame, readiness: pd.DataFrame) -> str:
    """Create B8.6g status Markdown."""
    usable_sources = int(sources["safety_status"].astype(str).eq("SAFE_TO_INSPECT").sum()) if not sources.empty else 0
    high_computed = readiness.loc[
        readiness["feature_family"].isin(HIGH_PRIORITY_FAMILIES) & readiness["n_non_null_features"].astype(float).gt(0),
        "feature_family",
    ].tolist()
    return f"""# B8.6g Status

Status: {status}
Branch: codex/b86g-vector-compact-feature-acquisition
Scope: System B vector/compact feature acquisition for surrogate spatial closure.

## Commands Run By Suite

- `python scripts/v12_b86g_run_feature_acquisition.py --config configs/v12/systemb_b86g_feature_acquisition.yaml`

## Key Results

- Sources scanned: {len(sources)}
- Usable sources: {usable_sources}
- High-priority feature families computed: {', '.join(high_computed) if high_computed else 'none'}
- N150 feature dataset shape: {n150.shape}
- N300 candidate feature dataset shape: {n300.shape}
- Retest readiness: {retest_status}
- AOI/B9 status: AOI_PREFLIGHT_BLOCKED / B9_BLOCKED
- Recommended next lane: {recommended_next_lane}

## Caveats

B8.6g creates feature tables, schema, readiness, failure-context joins, and future prompts only. It does not train a final surrogate, create AOI-wide prediction, create B9 output, run QGIS/SOLWEIG, read/write rasters, produce local WBGT, hazard/risk score, observed-truth claims, causal feature-importance claims, Tmrt-to-WBGT conversion, or System A/B coupling.

## Safe To Commit After Review

Controlled B8.6g config, scripts, docs, CSV, and Markdown outputs.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip packages, AOI-wide prediction outputs, B9 outputs, WBGT, hazard_score, risk_score, and System A/B coupling outputs.
"""


def run(config_path: Path = DEFAULT_CONFIG) -> WorkflowDecisionResult:
    """Run B8.6g workflow decisions and documentation."""
    config = load_config(config_path)
    inputs = read_csv(output_path(config, "input_inventory_path"))
    sources = read_csv(output_path(config, "source_inventory_path"))
    readiness = read_csv(output_path(config, "feature_family_readiness_path"))
    coverage = read_csv(output_path(config, "feature_coverage_matrix_path"))
    quality = read_csv(output_path(config, "feature_quality_checks_path"))
    failure_join = read_csv(output_path(config, "failure_context_feature_join_path"))
    n150 = read_csv(output_path(config, "n150_feature_dataset_path"))
    n300 = read_csv(output_path(config, "n300_candidate_feature_dataset_path"))
    status = decide_status(inputs, quality, readiness)
    gap = feature_gap_closure_matrix(config, readiness)
    retest, retest_status = retest_readiness_matrix(readiness)
    aoi = aoi_preflight_boundary_matrix()
    next_lane, recommended = next_lane_decision_matrix(status, retest_status)
    write_csv(gap, output_path(config, "feature_gap_closure_matrix_path"))
    write_csv(retest, output_path(config, "retest_readiness_matrix_path"))
    write_csv(aoi, output_path(config, "aoi_preflight_boundary_matrix_path"))
    write_csv(next_lane, output_path(config, "next_lane_decision_matrix_path"))
    write_text(prompt_b86g2(), output_path(config, "codex_prompt_b86g2_feature_retest_path"))
    write_text(prompt_b87(), output_path(config, "codex_prompt_b87_n300_pre_updated_path"))
    write_text(report_markdown(status, retest_status, recommended, sources, readiness, coverage, failure_join, gap, n150, n300), output_path(config, "report_path"))
    write_text(status_markdown(status, retest_status, recommended, n150, n300, sources, readiness), output_path(config, "status_path"))
    write_text(cn_doc_text(status, retest_status, recommended, readiness), output_path(config, "cn_doc_path"))
    return WorkflowDecisionResult(
        status=status,
        retest_readiness_status=retest_status,
        aoi_b9_status="AOI_PREFLIGHT_BLOCKED / B9_BLOCKED",
        recommended_next_lane=recommended,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Write B8.6g workflow decisions and documentation.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
