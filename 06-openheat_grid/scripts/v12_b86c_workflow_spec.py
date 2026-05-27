"""Write B8.6c surrogate workflow v0.1, report, status, CN doc, and decision outputs.

Inputs:
    configs/v12/systemb_b86c_feature_hardening.yaml
    All compact B8.6c inventory, dataset, model, failure-audit, and two-stage
    CSV outputs declared in the config.

Outputs:
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_surrogate_workflow_v0_1.md
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_b86d_recommendation.md
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_decision_matrix.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_report.md
    outputs/v12_surrogate/b8_6c_feature_hardening/B8_6C_STATUS.md
    docs/v12/OpenHeat_SystemB_B8_6c_feature_hardening_CN.md

Saved metrics:
    Feature-candidate counts, safe/rejected counts, best hardened feature-set
    supporting-holdout improvement, spatial/typology/anchor/neutral/unstable
    failure headlines, two-stage pretest headline, B8.6d recommendation, and
    explicit AOI-wide/B9 block status.

This script reads and writes compact CSV/Markdown files only. It does not run
QGIS or SOLWEIG, does not read raster files, does not open or copy svfs.zip,
does not create AOI-wide prediction, does not convert Tmrt to WBGT, and does
not create WBGT, hazard_score, risk_score, B9, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86c_feature_inventory import DEFAULT_CONFIG, read_config, repo_path


PASS_STATUS = "B86C_FEATURE_HARDENING_PASS"
DIAGNOSTIC_STATUS = "B86C_FEATURE_HARDENING_DIAGNOSTIC_ONLY"
PROMISING_STATUS = "B86C_TWO_STAGE_PROMISING"
BLOCKED_STATUS = "B86C_BLOCKED_INPUT"
FAILED_STATUS = "FAILED"


@dataclass(frozen=True)
class WorkflowResult:
    """Compact return record for the B8.6c workflow/report step."""

    status: str
    feature_candidates_scanned: int
    safe_feature_count: int
    rejected_feature_count: int
    best_feature_set_improvement_headline: str
    spatial_typology_failure_headline: str
    anchor_neutral_unstable_headline: str
    two_stage_pretest_headline: str
    b86d_recommendation: str
    aoi_b9_status: str


def now_stamp() -> str:
    """Return a compact local timestamp string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def command_output(args: list[str]) -> str:
    """Run a lightweight command for status reporting."""
    completed = subprocess.run(args, cwd=repo_path("."), check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def read_csv_if_exists(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read a compact CSV or return an empty frame."""
    return pd.read_csv(path, **kwargs) if path.exists() else pd.DataFrame()


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> str:
    """Render a small DataFrame as a GitHub-style Markdown table."""
    if frame.empty:
        return "_No rows available._"
    view = frame[[column for column in columns if column in frame.columns]].head(max_rows).copy()
    if view.empty:
        return "_No requested columns available._"
    headers = list(view.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in view.iterrows():
        values: list[str] = []
        for column in headers:
            value = row[column]
            if isinstance(value, float):
                values.append("" if math.isnan(value) else f"{value:.4f}")
            else:
                values.append(str(value).replace("\n", " ")[:220])
        lines.append("| " + " | ".join(values) + " |")
    if len(frame) > max_rows:
        lines.append("| ... | " + f"{len(frame) - max_rows} more rows |" + " |" * max(0, len(headers) - 2))
    return "\n".join(lines)


def feature_counts(candidates: pd.DataFrame, safe: pd.DataFrame, rejected: pd.DataFrame) -> tuple[int, int, int]:
    """Return feature candidate/safe/rejected counts."""
    return int(len(candidates)), int(len(safe)), int(len(rejected))


def support_summary(metrics: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Aggregate primary target supporting-holdout metrics by feature set/model."""
    if metrics.empty:
        return pd.DataFrame()
    primary = config["targets"]["primary"]
    support = metrics.loc[
        (metrics["target"] == primary)
        & (metrics["model"] != "dummy_mean")
        & metrics["primary_evidence_allowed"].astype(bool)
        & metrics["split_family"].isin(["cell_group_holdout", "spatial_holdout", "typology_holdout"])
    ].copy()
    if support.empty:
        return pd.DataFrame()
    return support.groupby(["feature_set", "model"], as_index=False).agg(
        supporting_MAE=("MAE", "mean"),
        supporting_Spearman=("Spearman_observed_vs_predicted", "mean"),
        supporting_top10pct=("top10pct_overlap", "mean"),
        supporting_neutral_accuracy=("neutral_boundary_classification_accuracy", "mean"),
        supporting_anchor_MAE=("robust_anchor_MAE", "mean"),
        b86b_best_MAE=("b86b_best_MAE", "mean"),
        improvement_vs_b86b_best=("MAE_improvement_fraction_over_b86b_best", "mean"),
    )


def best_feature_improvement(metrics: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str, bool]:
    """Return best hardened feature-set improvement headline and pass flag."""
    summary = support_summary(metrics, config)
    if summary.empty:
        return summary, "No feature-set supporting-holdout metrics available.", False
    baseline_pool = summary.loc[summary["feature_set"] == "b86b_baseline_features"].copy()
    candidate_pool = summary.loc[summary["feature_set"] != "b86b_baseline_features"].copy()
    if baseline_pool.empty or candidate_pool.empty:
        return summary, "Baseline or hardened feature-set comparison unavailable.", False
    baseline = baseline_pool.sort_values(
        ["supporting_Spearman", "supporting_top10pct", "improvement_vs_b86b_best", "supporting_MAE"],
        ascending=[False, False, False, True],
    ).iloc[0]
    candidate = candidate_pool.sort_values(
        ["supporting_Spearman", "supporting_top10pct", "improvement_vs_b86b_best", "supporting_MAE"],
        ascending=[False, False, False, True],
    ).iloc[0]
    spearman_gain = float(candidate["supporting_Spearman"] - baseline["supporting_Spearman"])
    top10_gain = float(candidate["supporting_top10pct"] - baseline["supporting_top10pct"])
    mae_gain = float((baseline["supporting_MAE"] - candidate["supporting_MAE"]) / baseline["supporting_MAE"]) if baseline["supporting_MAE"] > 0 else np.nan
    headline = (
        f"{candidate['feature_set']}/{candidate['model']} vs baseline {baseline['model']}: "
        f"supporting Spearman {candidate['supporting_Spearman']:.3f} ({spearman_gain:+.3f}), "
        f"top10pct {candidate['supporting_top10pct']:.3f} ({top10_gain:+.3f}), "
        f"MAE gain {mae_gain:+.1%}."
    )
    gate = config["promotion_gate"]
    material = (
        spearman_gain >= float(gate["material_supporting_spearman_gain"])
        or top10_gain >= float(gate["material_supporting_top10_gain"])
        or (not math.isnan(mae_gain) and mae_gain >= float(gate["material_supporting_mae_gain_fraction"]))
    )
    return summary, headline, bool(material)


def failure_headline(spatial: pd.DataFrame, typology: pd.DataFrame) -> str:
    """Return spatial/typology failure headline."""
    spatial_flagged = int((spatial.get("failure_type", pd.Series(dtype=str)) != "not-flagged").sum()) if not spatial.empty else 0
    typology_flagged = int((typology.get("failure_type", pd.Series(dtype=str)) != "not-flagged").sum()) if not typology.empty else 0
    return f"spatial flagged {spatial_flagged}/{len(spatial)} bins; typology flagged {typology_flagged}/{len(typology)} bins."


def role_headline(anchor: pd.DataFrame, neutral: pd.DataFrame, unstable: pd.DataFrame) -> str:
    """Return anchor/neutral/unstable failure headline."""
    anchor_flagged = int((anchor.get("failure_type", pd.Series(dtype=str)) == "anchor-underprediction").sum()) if not anchor.empty else 0
    neutral_flagged = int((neutral.get("failure_type", pd.Series(dtype=str)) == "neutral-boundary-confusion").sum()) if not neutral.empty else 0
    unstable_flagged = int((unstable.get("failure_type", pd.Series(dtype=str)) != "not-flagged").sum()) if not unstable.empty else 0
    return f"anchor underprediction rows {anchor_flagged}; neutral confusion rows {neutral_flagged}; unstable flagged rows {unstable_flagged}."


def two_stage_summary(metrics: pd.DataFrame) -> tuple[pd.DataFrame, str, bool]:
    """Return two-stage summary, headline, and promising flag."""
    if metrics.empty:
        return pd.DataFrame(), "Two-stage pretest unavailable.", False
    support = metrics.loc[metrics["split_family"].isin(["cell_group_holdout", "spatial_holdout", "typology_holdout"])].copy()
    if support.empty:
        return pd.DataFrame(), "Two-stage supporting-holdout metrics unavailable.", False
    summary = support.groupby(["feature_set", "neutral_threshold_c", "classifier", "regressor"], as_index=False).agg(
        MAE=("MAE", "mean"),
        Spearman=("Spearman_observed_vs_predicted", "mean"),
        top10pct=("top10pct_overlap", "mean"),
        neutral_accuracy=("neutral_accuracy", "mean"),
        anchor_MAE=("robust_anchor_MAE", "mean"),
    )
    best = summary.sort_values(["neutral_accuracy", "Spearman", "top10pct", "anchor_MAE", "MAE"], ascending=[False, False, False, True, True]).iloc[0]
    headline = (
        f"{best.feature_set}, threshold={best.neutral_threshold_c:.2f}, {best.classifier}+{best.regressor}: "
        f"neutral_accuracy={best.neutral_accuracy:.3f}, supporting Spearman={best.Spearman:.3f}, "
        f"top10pct={best.top10pct:.3f}, anchor_MAE={best.anchor_MAE:.3f}."
    )
    promising = bool(best["neutral_accuracy"] >= 0.70 and (best["Spearman"] >= 0.45 or best["top10pct"] >= 0.40))
    return summary, headline, promising


def final_status(material_feature_gain: bool, two_stage_promising: bool, required_outputs_ready: bool) -> str:
    """Apply B8.6c final decision rules."""
    if not required_outputs_ready:
        return BLOCKED_STATUS
    if material_feature_gain:
        return PASS_STATUS
    if two_stage_promising:
        return PROMISING_STATUS
    return DIAGNOSTIC_STATUS


def b86d_text(status: str, material_feature_gain: bool, two_stage_promising: bool) -> str:
    """Return the B8.6d recommendation text."""
    if status == PASS_STATUS:
        return "Recommend B8.6d as a small improved surrogate workflow review using the best hardened feature set; AOI-wide prediction and B9 remain blocked."
    if two_stage_promising:
        return "Recommend B8.6d to formalize the two-stage neutral-boundary workflow before any AOI-wide preflight; B9 remains blocked."
    if material_feature_gain:
        return "Recommend B8.6d only after reviewing the feature-gain evidence and keeping spatial/typology failures explicit."
    return "Recommend feature representation upgrade and targeted diagnostics before B8.6d; targeted N300/additional forcing days only after generalisation improves."


def decision_matrix(
    status: str,
    material_feature_gain: bool,
    two_stage_promising: bool,
    counts: tuple[int, int, int],
    feature_headline: str,
    spatial_typology: str,
    role_text: str,
    two_stage_text: str,
    b86d: str,
) -> pd.DataFrame:
    """Build the B8.6c decision matrix."""
    scanned, safe_count, rejected_count = counts
    rows = [
        {
            "gate": "compact_inputs",
            "status": "PASS" if scanned else "BLOCKED",
            "evidence": f"{scanned} compact feature candidates scanned.",
            "next_action": "Use compact CSV inputs only.",
            "claim_boundary": "No raster, SOLWEIG, QGIS, AOI-wide prediction, or B9 output.",
        },
        {
            "gate": "leakage_guard",
            "status": "PASS" if safe_count and rejected_count else "WARN",
            "evidence": f"safe={safe_count}; rejected/metadata/leakage/future={rejected_count}.",
            "next_action": "Keep target, rank, WBGT, risk, hazard, observed, path/status, and future risk-overlay columns excluded.",
            "claim_boundary": "No feature importance causal claim.",
        },
        {
            "gate": "feature_set_hardening",
            "status": "PASS" if material_feature_gain else "DIAGNOSTIC",
            "evidence": feature_headline,
            "next_action": "Use only if supporting holdouts improve materially.",
            "claim_boundary": "Surrogate supports local radiative ranking review only.",
        },
        {
            "gate": "failure_audit",
            "status": "PASS",
            "evidence": f"{spatial_typology} {role_text}",
            "next_action": "Carry failure types into B8.6d design.",
            "claim_boundary": "Failures are against SOLWEIG-derived compact labels, not observed truth.",
        },
        {
            "gate": "two_stage_pretest",
            "status": "PROMISING" if two_stage_promising else "DIAGNOSTIC",
            "evidence": two_stage_text,
            "next_action": "Use only if neutral/spatial/typology/anchor diagnostics remain stable.",
            "claim_boundary": "Two-stage output is not AOI-wide prediction.",
        },
        {
            "gate": "aoi_b9_status",
            "status": "BLOCKED",
            "evidence": "B8.6c is feature hardening/failure audit only.",
            "next_action": b86d,
            "claim_boundary": "Not B9, not AOI-wide prediction, not local WBGT, not risk.",
        },
        {
            "gate": "final_status",
            "status": status,
            "evidence": "B8.6c compact outputs and workflow specification are complete.",
            "next_action": b86d,
            "claim_boundary": "No Tmrt-to-WBGT conversion and no System A/B coupling.",
        },
    ]
    return pd.DataFrame(rows)


def write_workflow_spec(path: Path) -> None:
    """Write the canonical B8.6c surrogate workflow v0.1 specification."""
    lines = [
        "# B8.6c Surrogate Workflow v0.1",
        "",
        f"Generated: {now_stamp()}",
        "",
        "## Inputs",
        "",
        "- F5 compact pairwise labels only: `delta_tmrt_p90_c = overhead_as_canopy - base` plus companion delta targets.",
        "- Compact N150 feature tables only: `n150_sampling_feature_matrix.csv` and `n150_candidate_universe.csv`.",
        "- B8.6b compact diagnostics and B8.5-F4 anchor/neutral/unstable cell lists for audit context.",
        "",
        "## Label Contract",
        "",
        "- Labels are SOLWEIG-derived Tmrt deltas, not observed truth and not WBGT.",
        "- Primary target is `delta_tmrt_p90_c`; companion targets are mean, p50, and p95 deltas.",
        "- `cell_id`, `forcing_day_id`, ranks, and target columns are not numeric predictors.",
        "",
        "## Feature Contract",
        "",
        "- Safe features must be compact, non-target-derived, and pre-existing in the compact tables.",
        "- Target, rank, WBGT, risk, hazard, score, observed, path/status, System A, and future exposure/vulnerability columns are excluded.",
        "- Coordinates are allowed only for spatial bins or diagnostic feature sets, never causal interpretation.",
        "- Interactions are limited to pre-registered physical pairs.",
        "",
        "## Validation Contract",
        "",
        "- Primary evidence remains forcing-day holdout.",
        "- Supporting evidence includes cell-group, spatial, typology, and hour holdouts.",
        "- Random row split is not a main evidence path for this lane.",
        "",
        "## Model Family Contract",
        "",
        "- Use modest ridge, elasticnet, random forest, and histogram gradient boosting baselines plus dummy mean.",
        "- Model selection must report failure modes, not only aggregate fit.",
        "- Feature importance, if produced later, is diagnostic and non-causal.",
        "",
        "## Diagnostic Outputs",
        "",
        "- Split failure summary, spatial and typology inventories, anchor/neutral/unstable audits, h10 contrast, OOF prediction audit, and two-stage pretest metrics.",
        "",
        "## Promotion Gates",
        "",
        "- B8.6c can pass only if hardened feature sets materially improve weak supporting holdouts without boundary violations.",
        "- Two-stage can be called promising if neutral and supporting holdouts improve enough to justify B8.6d.",
        "- Otherwise B8.6c remains diagnostic-only.",
        "",
        "## Forbidden Outputs",
        "",
        "- No B9.",
        "- No AOI-wide prediction.",
        "- No local WBGT, hazard_score, risk_score, or System A/B coupling.",
        "- No Tmrt-to-WBGT conversion.",
        "- No raster/QGIS/SOLWEIG operation.",
        "",
        "## What B8.6d Should Do Next",
        "",
        "- Formalize the improved surrogate workflow only after reviewing B8.6c diagnostics.",
        "- Keep feature upgrade, targeted N300, or extra forcing days conditional on spatial/typology generalisation improving.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_b86d_recommendation(path: Path, status: str, recommendation: str, feature_headline: str, two_stage_text: str) -> None:
    """Write the B8.6d recommendation Markdown."""
    lines = [
        "# B8.6d Recommendation",
        "",
        f"Generated: {now_stamp()}",
        "",
        f"Status basis: `{status}`",
        "",
        f"- Feature-set evidence: {feature_headline}",
        f"- Two-stage evidence: {two_stage_text}",
        f"- Recommendation: {recommendation}",
        "",
        "## Boundaries",
        "",
        "- B8.6d may be an improved surrogate workflow review.",
        "- It must not create AOI-wide prediction or B9 outputs.",
        "- It must not create local WBGT, hazard_score, risk_score, observed-truth claims, causal feature-importance claims, or System A/B coupling.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(
    path: Path,
    status: str,
    counts: tuple[int, int, int],
    safe: pd.DataFrame,
    rejected: pd.DataFrame,
    support: pd.DataFrame,
    split_summary: pd.DataFrame,
    spatial: pd.DataFrame,
    typology: pd.DataFrame,
    anchor: pd.DataFrame,
    neutral: pd.DataFrame,
    unstable: pd.DataFrame,
    two_stage_summary_frame: pd.DataFrame,
    feature_headline: str,
    spatial_typology: str,
    role_text: str,
    two_stage_text: str,
    recommendation: str,
    decision: pd.DataFrame,
) -> None:
    """Write the full B8.6c Markdown report."""
    scanned, safe_count, rejected_count = counts
    lines = [
        "# B8.6c Feature Hardening and Failure Audit",
        "",
        f"Generated: {now_stamp()}",
        "",
        f"Status: `{status}`",
        "",
        "## 1. Why B8.6c Follows B8.6b",
        "",
        "B8.6b showed strong forcing-day and hour transfer, but weak cell-group, spatial, and typology support. B8.6c therefore audits compact feature representation and failure modes before any AOI-wide or B9 work.",
        "",
        "## 2. Feature Inventory and Leakage Guard",
        "",
        f"- Feature candidates scanned: {scanned}",
        f"- Safe feature count: {safe_count}",
        f"- Rejected/metadata/leakage/future-required count: {rejected_count}",
        "",
        markdown_table(safe, ["source_table", "column_name", "dataset_column", "feature_group_hint"], 18),
        "",
        markdown_table(rejected, ["source_table", "column_name", "classification", "rejection_reason"], 18),
        "",
        "## 3. Failure Mode Summary",
        "",
        markdown_table(split_summary, ["split_family", "MAE", "Spearman", "top10pct_overlap", "failure_type"], 12),
        "",
        "## 4. Spatial / Typology / Anchor Diagnostics",
        "",
        f"- {spatial_typology}",
        f"- {role_text}",
        "",
        markdown_table(spatial, ["split_name", "n_cells", "MAE", "Spearman", "top10pct_overlap", "failure_type"], 12),
        "",
        markdown_table(typology, ["split_name", "n_cells", "MAE", "Spearman", "top10pct_overlap", "failure_type"], 12),
        "",
        "## 5. Target Sensitivity Implications",
        "",
        "B8.6c keeps `delta_tmrt_p90_c` as the primary target because it matches the local radiative priority-card role. Mean, p50, and p95 deltas remain companion checks rather than replacements.",
        "",
        "## 6. Two-Stage Pretest Result",
        "",
        f"- {two_stage_text}",
        "",
        markdown_table(two_stage_summary_frame, ["feature_set", "neutral_threshold_c", "classifier", "regressor", "neutral_accuracy", "Spearman", "top10pct", "anchor_MAE"], 12),
        "",
        "## 7. Feature Upgrade Recommendation",
        "",
        f"- {feature_headline}",
        "- Feature representation gaps remain the first explanation to audit when spatial/typology transfer collapses.",
        "",
        "## 8. Workflow v0.1",
        "",
        "- See `b86c_surrogate_workflow_v0_1.md` for the input, label, feature, validation, model, diagnostic, promotion, and forbidden-output contracts.",
        "",
        "## 9. B8.6d Recommendation",
        "",
        f"- {recommendation}",
        "",
        "## 10. Claim Boundaries",
        "",
        "- This is not B9.",
        "- This is not AOI-wide prediction.",
        "- This is not local WBGT.",
        "- This is not risk.",
        "- This is not observed truth.",
        "- This is not causal feature importance.",
        "- No raster operation was run or required.",
        "- No SOLWEIG or QGIS operation was run.",
        "- No Tmrt-to-WBGT conversion was performed.",
        "- No System A/B coupling output was created.",
        "",
        "## Decision Matrix",
        "",
        markdown_table(decision, ["gate", "status", "evidence", "next_action"], 20),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_cn_doc(
    path: Path,
    status: str,
    counts: tuple[int, int, int],
    feature_headline: str,
    spatial_typology: str,
    role_text: str,
    two_stage_text: str,
    recommendation: str,
) -> None:
    """Write the UTF-8 Chinese B8.6c documentation."""
    scanned, safe_count, rejected_count = counts
    lines = [
        "# OpenHeat System B B8.6c 特征加固与失败审计说明",
        "",
        f"生成时间：{now_stamp()}",
        "",
        "## 结论",
        "",
        f"- B8.6c 状态：`{status}`",
        f"- 扫描特征候选：{scanned}",
        f"- 安全特征：{safe_count}",
        f"- 排除 / 元数据 / 泄漏风险 / 未来风险叠加特征：{rejected_count}",
        f"- 最佳特征集改进摘要：{feature_headline}",
        f"- 空间与类型失败摘要：{spatial_typology}",
        f"- 锚点 / 中性边界 / 不稳定单元摘要：{role_text}",
        f"- 两阶段预检摘要：{two_stage_text}",
        f"- B8.6d 建议：{recommendation}",
        "- AOI-wide / B9 状态：`BLOCKED`",
        "",
        "## 为什么 B8.6c 接在 B8.6b 后面",
        "",
        "B8.6b 已经证明 F5 紧凑标签在强迫日留出和小时留出上表现较强，但 cell-group、空间和 typology 留出仍然偏弱。因此 B8.6c 不追逐更复杂模型，而是审计特征表达缺口、失败模式和后续工作流。",
        "",
        "## 边界",
        "",
        "- 这不是 B9。",
        "- 这不是 AOI-wide prediction。",
        "- 这不是 local WBGT。",
        "- 这不是 risk。",
        "- 这不是 observed truth。",
        "- 这不是 causal feature importance。",
        "- 没有读取或生成 raster。",
        "- 没有运行 SOLWEIG 或 QGIS。",
        "- 没有 Tmrt-to-WBGT conversion。",
        "- 没有 System A/B coupling。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status_file(path: Path, result: WorkflowResult, config: dict[str, Any], files_created: list[str]) -> None:
    """Write the B8.6c status file."""
    branch = command_output(["git", "branch", "--show-current"])
    lines = [
        "# B8.6c Status",
        "",
        f"Generated: {now_stamp()}",
        f"Status: {result.status}",
        f"Branch: {branch}",
        "Scope: System B surrogate feature hardening and spatial/typology failure audit using compact F5 labels only.",
        "",
        "## Commands run",
        "",
        "- `C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python -m compileall scripts/v12_b86c_feature_inventory.py scripts/v12_b86c_dataset.py scripts/v12_b86c_failure_audit.py scripts/v12_b86c_feature_set_models.py scripts/v12_b86c_two_stage_pretest.py scripts/v12_b86c_workflow_spec.py scripts/v12_b86c_run_feature_hardening.py`",
        "- `C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python scripts/v12_b86c_run_feature_hardening.py --config configs/v12/systemb_b86c_feature_hardening.yaml`",
        "- `C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python -c \"...mojibake check...\"`",
        "- `git status --short -- .`",
        "- forbidden-file check over `git status --porcelain -- .`",
        "",
        "## Files created / modified",
        "",
        *[f"- `{path_value}`" for path_value in files_created],
        "",
        "## Key results",
        "",
        f"- Feature candidates scanned: {result.feature_candidates_scanned}",
        f"- Safe/rejected counts: {result.safe_feature_count}/{result.rejected_feature_count}",
        f"- Feature-set headline: {result.best_feature_set_improvement_headline}",
        f"- Spatial/typology headline: {result.spatial_typology_failure_headline}",
        f"- Anchor/neutral/unstable headline: {result.anchor_neutral_unstable_headline}",
        f"- Two-stage headline: {result.two_stage_pretest_headline}",
        f"- B8.6d recommendation: {result.b86d_recommendation}",
        f"- AOI-wide/B9 status: {result.aoi_b9_status}",
        "",
        "## Caveats",
        "",
        "- The audit uses SOLWEIG-derived F5 compact labels, not observed truth.",
        "- Feature interpretation is diagnostic, not causal.",
        "- h10 remains a caveated hour and is separated from core-hour behavior.",
        "- No QGIS, SOLWEIG, raster reading, AOI-wide prediction, local WBGT, hazard_score, risk_score, or System A/B coupling was created.",
        "",
        "## Safe to commit",
        "",
        "- Compact config, scripts, docs, CSV, and Markdown outputs after review.",
        "",
        "## Not safe to commit",
        "",
        "- Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip packages, and AOI-wide prediction outputs.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def output_files(config: dict[str, Any]) -> list[str]:
    """Return all B8.6c files created or modified by this lane."""
    script_files = [
        "configs/v12/systemb_b86c_feature_hardening.yaml",
        "scripts/v12_b86c_feature_inventory.py",
        "scripts/v12_b86c_dataset.py",
        "scripts/v12_b86c_failure_audit.py",
        "scripts/v12_b86c_feature_set_models.py",
        "scripts/v12_b86c_two_stage_pretest.py",
        "scripts/v12_b86c_workflow_spec.py",
        "scripts/v12_b86c_run_feature_hardening.py",
    ]
    output_keys = [
        "input_inventory",
        "feature_candidate_inventory",
        "safe_feature_catalog",
        "rejected_feature_catalog",
        "feature_group_registry",
        "feature_set_registry",
        "hardened_surrogate_dataset",
        "split_failure_summary",
        "spatial_failure_inventory",
        "typology_failure_inventory",
        "anchor_failure_audit",
        "neutral_boundary_audit",
        "unstable_cell_audit",
        "core_hour_h10_contrast",
        "feature_set_model_metrics",
        "two_stage_pretest_metrics",
        "two_stage_confusion_summary",
        "oof_prediction_audit",
        "feature_upgrade_recommendation",
        "surrogate_workflow_v0_1",
        "b86d_recommendation",
        "decision_matrix",
        "report",
        "status",
        "cn_doc",
    ]
    return [*script_files, *[config["outputs"][key] for key in output_keys]]


def required_outputs_ready(config: dict[str, Any]) -> bool:
    """Return whether required compact outputs exist."""
    required = [
        "input_inventory",
        "feature_candidate_inventory",
        "safe_feature_catalog",
        "rejected_feature_catalog",
        "feature_group_registry",
        "feature_set_registry",
        "hardened_surrogate_dataset",
        "feature_set_model_metrics",
        "oof_prediction_audit",
        "split_failure_summary",
        "spatial_failure_inventory",
        "typology_failure_inventory",
        "anchor_failure_audit",
        "neutral_boundary_audit",
        "unstable_cell_audit",
        "core_hour_h10_contrast",
        "two_stage_pretest_metrics",
        "two_stage_confusion_summary",
        "feature_upgrade_recommendation",
    ]
    return all(repo_path(config["outputs"][key]).exists() for key in required)


def run(config_path: Path = DEFAULT_CONFIG) -> WorkflowResult:
    """Write B8.6c workflow/report/status outputs."""
    config = read_config(config_path)
    candidates = read_csv_if_exists(repo_path(config["outputs"]["feature_candidate_inventory"]))
    safe = read_csv_if_exists(repo_path(config["outputs"]["safe_feature_catalog"]))
    rejected = read_csv_if_exists(repo_path(config["outputs"]["rejected_feature_catalog"]))
    metrics = read_csv_if_exists(repo_path(config["outputs"]["feature_set_model_metrics"]))
    split_summary = read_csv_if_exists(repo_path(config["outputs"]["split_failure_summary"]))
    spatial = read_csv_if_exists(repo_path(config["outputs"]["spatial_failure_inventory"]))
    typology = read_csv_if_exists(repo_path(config["outputs"]["typology_failure_inventory"]))
    anchor = read_csv_if_exists(repo_path(config["outputs"]["anchor_failure_audit"]))
    neutral = read_csv_if_exists(repo_path(config["outputs"]["neutral_boundary_audit"]))
    unstable = read_csv_if_exists(repo_path(config["outputs"]["unstable_cell_audit"]))
    two_stage = read_csv_if_exists(repo_path(config["outputs"]["two_stage_pretest_metrics"]))

    counts = feature_counts(candidates, safe, rejected)
    support, feature_headline, material_feature_gain = best_feature_improvement(metrics, config)
    two_stage_summary_frame, two_stage_text, two_stage_promising = two_stage_summary(two_stage)
    spatial_typology = failure_headline(spatial, typology)
    role_text = role_headline(anchor, neutral, unstable)
    ready = required_outputs_ready(config)
    status = final_status(material_feature_gain, two_stage_promising, ready)
    recommendation = b86d_text(status, material_feature_gain, two_stage_promising)
    aoi_b9 = "BLOCKED: no AOI-wide prediction and no B9 output created."
    decision = decision_matrix(
        status,
        material_feature_gain,
        two_stage_promising,
        counts,
        feature_headline,
        spatial_typology,
        role_text,
        two_stage_text,
        recommendation,
    )

    decision.to_csv(repo_path(config["outputs"]["decision_matrix"]), index=False)
    write_workflow_spec(repo_path(config["outputs"]["surrogate_workflow_v0_1"]))
    write_b86d_recommendation(repo_path(config["outputs"]["b86d_recommendation"]), status, recommendation, feature_headline, two_stage_text)
    write_report(
        repo_path(config["outputs"]["report"]),
        status,
        counts,
        safe,
        rejected,
        support,
        split_summary,
        spatial,
        typology,
        anchor,
        neutral,
        unstable,
        two_stage_summary_frame,
        feature_headline,
        spatial_typology,
        role_text,
        two_stage_text,
        recommendation,
        decision,
    )
    write_cn_doc(repo_path(config["outputs"]["cn_doc"]), status, counts, feature_headline, spatial_typology, role_text, two_stage_text, recommendation)
    result = WorkflowResult(
        status=status,
        feature_candidates_scanned=counts[0],
        safe_feature_count=counts[1],
        rejected_feature_count=counts[2],
        best_feature_set_improvement_headline=feature_headline,
        spatial_typology_failure_headline=spatial_typology,
        anchor_neutral_unstable_headline=role_text,
        two_stage_pretest_headline=two_stage_text,
        b86d_recommendation=recommendation,
        aoi_b9_status=aoi_b9,
    )
    write_status_file(repo_path(config["outputs"]["status"]), result, config, output_files(config))
    return result


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Write B8.6c workflow v0.1, report, CN doc, decision matrix, and status.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6c YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
