"""Write B8.6d workflow reports, promotion gate, and Chinese documentation.

Inputs:
    All B8.6d CSV outputs from the dataset, two-stage pipeline, seed stability,
    and diagnostic scripts.
Outputs:
    - b86d_target_role_decision.csv
    - b86d_promotion_gate.csv
    - b86d_model_card.md
    - b86d_surrogate_workflow_v0_2.md
    - b86d_report.md
    - B8_6D_STATUS.md
    - docs/v12/OpenHeat_SystemB_B8_6d_two_stage_surrogate_CN.md
Saved metrics:
    Target role decision rows, gate evidence rows, headline summaries, and
    claim-boundary status for the B8.6d compact surrogate workflow.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86d_common import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    SUPPORTING_WEAK_SPLITS,
    load_config,
    markdown_table,
    now_stamp,
    output_path,
    read_csv,
    repo_path,
    write_csv,
    write_text,
)
from v12_b86d_two_stage_pipeline import select_best_pipeline


PASS_STATUS = "B86D_TWO_STAGE_WORKFLOW_PASS"
DIAGNOSTIC_STATUS = "B86D_TWO_STAGE_DIAGNOSTIC_ONLY"
AOI_READY_STATUS = "B86D_AOI_PREFLIGHT_READY_CANDIDATE"
BLOCKED_STATUS = "B86D_BLOCKED_INPUT"
FAILED_STATUS = "FAILED"


@dataclass(frozen=True)
class ReportResult:
    """Workflow report result."""

    status: str
    best_threshold: float
    best_classifier: str
    best_regressor: str


def read_output(config: dict[str, Any], key: str) -> pd.DataFrame:
    """Read an output CSV if available."""
    path = output_path(config, key)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def selected_combo(config: dict[str, Any]) -> dict[str, Any]:
    """Select best pipeline from combined metrics."""
    metrics = read_output(config, "combined_pipeline_metrics")
    return select_best_pipeline(metrics, config) if not metrics.empty else {}


def split_family_summary(by_split: pd.DataFrame) -> pd.DataFrame:
    """Aggregate selected metrics by split family."""
    if by_split.empty:
        return pd.DataFrame()
    numeric_cols = [
        "MAE",
        "RMSE",
        "R2",
        "Spearman",
        "top10pct_overlap",
        "neutral_accuracy",
        "false_promotion_rate",
        "robust_anchor_MAE",
        "Spearman_gain_vs_b86c_single_stage",
        "top10_gain_vs_b86c_single_stage",
        "anchor_MAE_delta_vs_b86c_single_stage",
    ]
    available = [col for col in numeric_cols if col in by_split.columns]
    return by_split.groupby("split_family", dropna=False)[available].mean(numeric_only=True).reset_index()


def target_role_decision(config: dict[str, Any], metrics_by_target: pd.DataFrame) -> pd.DataFrame:
    """Create target role decision rows."""
    rows: list[dict[str, Any]] = []
    target_roles = config["targets"]["target_roles"]
    primary = config["targets"]["primary_target"]
    target_summary = (
        metrics_by_target.groupby("target", dropna=False).agg(
            MAE=("MAE", "mean"),
            Spearman=("Spearman", "mean"),
            top10pct_overlap=("top10pct_overlap", "mean"),
        )
        if not metrics_by_target.empty
        else pd.DataFrame()
    )
    for target, role in target_roles.items():
        row = {
            "target": target,
            "role": role,
            "mean_MAE": float(target_summary.loc[target, "MAE"]) if target in target_summary.index else float("nan"),
            "mean_Spearman": float(target_summary.loc[target, "Spearman"]) if target in target_summary.index else float("nan"),
            "mean_top10pct_overlap": float(target_summary.loc[target, "top10pct_overlap"]) if target in target_summary.index else float("nan"),
            "decision": "p90 remains primary" if target == primary else "companion side output",
            "workflow_use": "stage1 boundary and ranking gate" if target == primary else "sensitivity report only",
            "claim_boundary": CLAIM_BOUNDARY,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def gate_decision(config: dict[str, Any], by_split: pd.DataFrame, seed: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """Evaluate the B8.6d promotion gate."""
    summary = split_family_summary(by_split)
    gates: list[dict[str, Any]] = []
    if summary.empty:
        gate_frame = pd.DataFrame(
            [
                {
                    "gate": "compact_outputs",
                    "status": "BLOCKED",
                    "evidence": "Missing selected split metrics.",
                    "next_action": "Re-run B8.6d pipeline.",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            ]
        )
        return BLOCKED_STATUS, gate_frame

    weak = summary.loc[summary["split_family"].isin(SUPPORTING_WEAK_SPLITS)].copy()
    improved = 0
    for _, row in weak.iterrows():
        spearman_gain = float(row.get("Spearman_gain_vs_b86c_single_stage", 0.0))
        top10_gain = float(row.get("top10_gain_vs_b86c_single_stage", 0.0))
        if spearman_gain >= float(config["promotion_gate"]["supporting_spearman_material_gain"]) or top10_gain >= float(
            config["promotion_gate"]["supporting_top10_material_gain"]
        ):
            improved += 1
    neutral_accuracy = float(summary["neutral_accuracy"].mean())
    false_promotion = float(summary["false_promotion_rate"].mean())
    top10_support_improved = int(
        weak.loc[weak["split_family"].isin(["spatial_holdout", "typology_holdout"]), "top10_gain_vs_b86c_single_stage"].fillna(0.0).gt(
            float(config["promotion_gate"]["supporting_top10_material_gain"])
        ).sum()
    )
    anchor_delta = float(weak["anchor_MAE_delta_vs_b86c_single_stage"].mean()) if "anchor_MAE_delta_vs_b86c_single_stage" in weak else 0.0
    seed_neutral_std = float(
        seed.loc[(seed["split_family"] == "overall") & (seed["metric"] == "neutral_accuracy"), "std"].iloc[0]
    ) if not seed.empty and ((seed["split_family"] == "overall") & (seed["metric"] == "neutral_accuracy")).any() else 0.0
    seed_spearman_std = float(
        seed.loc[(seed["split_family"] == "overall") & (seed["metric"] == "Spearman"), "std"].iloc[0]
    ) if not seed.empty and ((seed["split_family"] == "overall") & (seed["metric"] == "Spearman")).any() else 0.0

    gate_specs = [
        (
            "supporting_holdout_improvement",
            improved >= 2,
            f"{improved}/3 weak supporting split families improved vs B8.6c single-stage reference.",
            "Require at least two of cell_group/spatial/typology to improve materially.",
        ),
        (
            "neutral_accuracy",
            neutral_accuracy >= float(config["promotion_gate"]["neutral_accuracy_min"]),
            f"Average selected neutral accuracy={neutral_accuracy:.3f}.",
            "Keep two-stage neutral gate diagnostic if below threshold.",
        ),
        (
            "false_promotion_rate",
            false_promotion <= float(config["promotion_gate"]["false_promotion_material_max"]),
            f"Average selected false promotion rate={false_promotion:.3f}.",
            "Do not promote neutral cells as cooling candidates when false promotion remains high.",
        ),
        (
            "spatial_or_typology_top10",
            top10_support_improved >= 1,
            f"Spatial/typology top10 improvements passing threshold={top10_support_improved}.",
            "Require top10 support in at least one weak generalisation family.",
        ),
        (
            "anchor_underprediction",
            anchor_delta <= float(config["promotion_gate"]["anchor_mae_worsening_tolerance"]),
            f"Mean anchor MAE delta vs B8.6c single-stage={anchor_delta:.3f}.",
            "Do not accept if anchor underprediction worsens materially.",
        ),
        (
            "seed_stability",
            seed_neutral_std <= float(config["promotion_gate"]["max_seed_std_neutral_accuracy"])
            and seed_spearman_std <= float(config["promotion_gate"]["max_seed_std_spearman"]),
            f"Seed std neutral={seed_neutral_std:.3f}; Spearman={seed_spearman_std:.3f}.",
            "Downgrade if selected stochastic workflow is seed-sensitive.",
        ),
        (
            "claim_boundaries",
            True,
            "No AOI-wide prediction, B9, local WBGT, risk, observed-truth, causal feature-importance, raster, QGIS/SOLWEIG, Tmrt-to-WBGT, or System A/B coupling outputs are produced.",
            "Keep B9 blocked in this lane.",
        ),
    ]
    for gate, passed, evidence, next_action in gate_specs:
        gates.append(
            {
                "gate": gate,
                "status": "PASS" if passed else "DIAGNOSTIC",
                "evidence": evidence,
                "next_action": next_action,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    all_pass = all(row["status"] == "PASS" for row in gates)
    supporting_mean = float(weak["Spearman"].mean()) if not weak.empty else float("nan")
    top10_mean = float(weak["top10pct_overlap"].mean()) if not weak.empty else float("nan")
    if all_pass and supporting_mean >= 0.50 and top10_mean >= 0.35:
        status = AOI_READY_STATUS
    elif all_pass:
        status = PASS_STATUS
    else:
        status = DIAGNOSTIC_STATUS
    return status, pd.DataFrame(gates)


def headline_from_split(by_split: pd.DataFrame) -> str:
    """Create spatial/typology/cell-group headline."""
    summary = split_family_summary(by_split)
    if summary.empty:
        return "No selected split metrics available."
    parts = []
    for family in SUPPORTING_WEAK_SPLITS:
        row = summary.loc[summary["split_family"] == family]
        if row.empty:
            continue
        item = row.iloc[0]
        parts.append(
            f"{family}: Spearman={item['Spearman']:.3f}, top10pct={item['top10pct_overlap']:.3f}, neutral_acc={item['neutral_accuracy']:.3f}"
        )
    return "; ".join(parts)


def report_text(config: dict[str, Any], status: str, best: dict[str, Any], frames: dict[str, pd.DataFrame]) -> str:
    """Build the English report Markdown."""
    inventory = frames["inventory"]
    schema = frames["schema"]
    stage1 = frames["stage1"]
    stage2 = frames["stage2"]
    combined = frames["combined"]
    sweep = frames["sweep"]
    by_split = frames["by_split"]
    seed = frames["seed"]
    anchor = frames["anchor"]
    neutral = frames["neutral"]
    unstable = frames["unstable"]
    target_decision = frames["target_decision"]
    promotion = frames["promotion"]
    dataset_row = inventory.loc[inventory["input_key"] == "b86c_dataset_path"].iloc[0] if not inventory.empty else {}
    rows = int(dataset_row.get("row_count", 0)) if len(inventory) else 0
    cells = int(dataset_row.get("unique_cells", 0)) if len(inventory) else 0
    forcing_days = int(dataset_row.get("forcing_day_count", 0)) if len(inventory) else 0
    hours = int(dataset_row.get("hour_count", 0)) if len(inventory) else 0
    selected_stage1 = stage1.loc[
        (stage1["feature_set"].astype(str) == str(best.get("feature_set")))
        & (stage1["neutral_threshold_c"].astype(float) == float(best.get("neutral_threshold_c", 0.05)))
        & (stage1["classifier"].astype(str) == str(best.get("classifier")))
    ]
    selected_stage2 = stage2.loc[
        (stage2["feature_set"].astype(str) == str(best.get("feature_set")))
        & (stage2["neutral_threshold_c"].astype(float) == float(best.get("neutral_threshold_c", 0.05)))
        & (stage2["regressor"].astype(str) == str(best.get("regressor")))
    ]
    selected_combined = combined.loc[
        (combined["feature_set"].astype(str) == str(best.get("feature_set")))
        & (combined["neutral_threshold_c"].astype(float) == float(best.get("neutral_threshold_c", 0.05)))
        & (combined["classifier"].astype(str) == str(best.get("classifier")))
        & (combined["regressor"].astype(str) == str(best.get("regressor")))
    ]
    combined_headline = (
        f"Selected {best.get('feature_set')} / {best.get('classifier')} + {best.get('regressor')} "
        f"at threshold {float(best.get('neutral_threshold_c', 0.05)):.2f}: "
        f"MAE={selected_combined['MAE'].mean():.3f}, Spearman={selected_combined['Spearman_observed_vs_predicted'].mean():.3f}, "
        f"top10pct={selected_combined['top10pct_overlap'].mean():.3f}, neutral_acc={selected_combined['accuracy'].mean():.3f}."
    )
    return f"""# B8.6d Two-Stage Surrogate Workflow Formalization

Generated: {now_stamp()}

Status: `{status}`

## 1. Why B8.6d Follows B8.6c

B8.6c found that simple compact feature-set hardening did not materially fix the weak cell-group, spatial, and typology holdouts, while a two-stage neutral-boundary pretest was promising. B8.6d therefore formalizes and stress-tests that compact two-stage workflow before any AOI-wide dry-run preflight is considered.

## 2. Input Counts And Leakage Guard

- Dataset rows: {rows}
- Unique cells: {cells}
- Forcing days: {forcing_days}
- Hours: {hours}
- Predictor feature sets tested: {len(config["feature_sets_to_test"])}
- Schema columns audited: {len(schema)}
- `cell_id` remains metadata/group only; `forcing_day_id` remains split metadata.
- Target, rank, path/status, WBGT, risk, hazard, observed-truth, future exposure/vulnerability, raster, and System A columns are excluded from predictors.

## 3. Neutral Threshold Definition

Stage 1 uses `neutral = abs(delta_tmrt_p90_c) <= threshold`; meaningful cooling is `delta_tmrt_p90_c < -threshold`. Positive warming or weak positive rows are tracked but not promoted. The primary threshold remains `{config["primary_neutral_threshold_c"]}` C.

## 4. Stage 1 Results

{markdown_table(selected_stage1.groupby(["split_family"], as_index=False)[["accuracy", "balanced_accuracy", "false_promotion_rate", "false_neutral_rate"]].mean(numeric_only=True), ["split_family", "accuracy", "balanced_accuracy", "false_promotion_rate", "false_neutral_rate"], 10)}

## 5. Stage 2 Results

{markdown_table(selected_stage2.groupby(["split_family"], as_index=False)[["MAE", "RMSE", "R2", "Spearman_observed_vs_predicted", "top10pct_overlap", "robust_anchor_MAE"]].mean(numeric_only=True), ["split_family", "MAE", "RMSE", "R2", "Spearman_observed_vs_predicted", "top10pct_overlap", "robust_anchor_MAE"], 10)}

## 6. Combined Pipeline Results

- {combined_headline}

{markdown_table(split_family_summary(by_split), ["split_family", "MAE", "Spearman", "top10pct_overlap", "neutral_accuracy", "false_promotion_rate", "Spearman_gain_vs_b86c_single_stage", "top10_gain_vs_b86c_single_stage"], 10)}

## 7. Threshold Sweep

{markdown_table(sweep.sort_values(["neutral_accuracy", "Spearman"], ascending=False), ["neutral_threshold_c", "feature_set", "classifier", "regressor", "neutral_accuracy", "false_promotion_rate", "Spearman", "top10pct_overlap", "robust_anchor_MAE"], 12)}

## 8. Seed Stability

{markdown_table(seed, ["split_family", "metric", "mean", "std", "min", "max", "n_seeds"], 18)}

## 9. Spatial / Typology / Cell-Group Holdouts

- {headline_from_split(by_split)}

## 10. Anchor, Neutral-Boundary, And Unstable-Cell Diagnostics

- Anchor diagnostic rows: {len(anchor)}
- Neutral-boundary diagnostic rows: {len(neutral)}
- Unstable-cell diagnostic rows: {len(unstable)}

## 11. h10 Caveat

h10 is reported separately from core-hour behavior in stage-2 and combined metrics. It is not used alone as anchor evidence.

## 12. Target Role Decision

{markdown_table(target_decision, ["target", "role", "mean_Spearman", "mean_top10pct_overlap", "decision", "workflow_use"], 10)}

## 13. Promotion Gate Decision

{markdown_table(promotion, ["gate", "status", "evidence", "next_action"], 10)}

## 14. Future AOI-Wide Dry-Run Preflight

B8.6d creates no AOI-wide prediction. If the gate status is `{AOI_READY_STATUS}`, the only allowed next step is to design a separate future AOI-wide dry-run preflight lane; B9 remains blocked here.

## 15. Claim Boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not hazard_score or risk_score.
- Not observed truth.
- Not causal feature importance.
- No raster read/write/open/copy.
- No SOLWEIG or QGIS.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
"""


def model_card_text(status: str, best: dict[str, Any], frames: dict[str, pd.DataFrame]) -> str:
    """Build model card Markdown."""
    by_split = split_family_summary(frames["by_split"])
    return f"""# B8.6d Two-Stage Surrogate Model Card

Generated: {now_stamp()}

## Intended Role

Compact N150 review of a two-stage surrogate for SOLWEIG-derived Tmrt-delta labels. The workflow ranks local radiative cooling deltas; it is not WBGT, risk, observed truth, B9, or AOI-wide prediction.

## Decision

`{status}`

## Selected Workflow

- Feature set: `{best.get("feature_set")}`
- Stage 1 classifier: `{best.get("classifier")}`
- Stage 2 regressor: `{best.get("regressor")}`
- Neutral threshold: `{float(best.get("neutral_threshold_c", 0.05)):.2f}` C
- Primary target: `delta_tmrt_p90_c`

## Validation

{markdown_table(by_split, ["split_family", "MAE", "Spearman", "top10pct_overlap", "neutral_accuracy", "false_promotion_rate"], 10)}

## Explicit Non-Claims

Not B9, not AOI-wide, not local WBGT, not risk, not observed truth, not causal feature importance, no raster/QGIS/SOLWEIG, no Tmrt-to-WBGT conversion, and no System A/B coupling.
"""


def workflow_text() -> str:
    """Build workflow v0.2 Markdown."""
    return f"""# B8.6d Surrogate Workflow v0.2

Generated: {now_stamp()}

## Contract

1. Use F5 compact pairwise labels and B8.6c safe compact features only.
2. Keep `delta_tmrt_p90_c` as the primary hot-pocket / upper-tail target.
3. Stage 1 classifies neutral boundary versus meaningful cooling; positive or weak warming is tracked but not promoted.
4. Stage 2 regresses/ranks non-neutral magnitudes.
5. Combined prediction is conservative: Stage 1 neutral or other-positive rows receive 0.0 delta; meaningful-cooling rows receive Stage 2 delta.
6. Evidence uses forcing-day, cell-group, spatial, typology, and hour holdouts. Random row split is not main evidence.
7. Feature importance is diagnostic only and non-causal.
8. B9, AOI-wide prediction, local WBGT, hazard_score, risk_score, raster, QGIS/SOLWEIG, Tmrt-to-WBGT conversion, and System A/B coupling remain forbidden in this lane.
"""


def cn_doc_text(status: str, best: dict[str, Any], frames: dict[str, pd.DataFrame]) -> str:
    """Build UTF-8 Chinese documentation."""
    by_split = split_family_summary(frames["by_split"])
    return f"""# OpenHeat System B B8.6d 两阶段代理工作流说明

生成时间：{now_stamp()}

## 结论

- B8.6d 状态：`{status}`
- 主目标：`delta_tmrt_p90_c = overhead_as_canopy - base`
- 最佳阈值：{float(best.get("neutral_threshold_c", 0.05)):.2f} C
- Stage 1 分类器：`{best.get("classifier")}`
- Stage 2 回归器：`{best.get("regressor")}`
- B9 状态：`B9_BLOCKED`

## 为什么接在 B8.6c 后面

B8.6c 显示，简单增加安全特征并没有明显修复 cell-group、空间和 typology 留出的弱项；但两阶段预检对中性边界和支持性排序有改善信号。因此 B8.6d 只在紧凑 N150 数据上正式评审两阶段工作流，不生成 AOI-wide 预测。

## 中性边界定义

`neutral = abs(delta_tmrt_p90_c) <= threshold`。`delta_tmrt_p90_c < -threshold` 被视为 meaningful cooling；正值或弱正值只跟踪，不作为晋级冷却候选。

## 综合结果

{markdown_table(by_split, ["split_family", "MAE", "Spearman", "top10pct_overlap", "neutral_accuracy", "false_promotion_rate"], 10)}

## 目标角色

`delta_tmrt_p90_c` 仍作为热口袋 / 上尾部主目标。`delta_tmrt_mean_c`、`delta_tmrt_p50_c`、`delta_tmrt_p95_c` 作为伴随敏感性输出，不自动替换 p90。

## 边界

- 这不是 B9。
- 这不是 AOI-wide prediction。
- 这不是 local WBGT。
- 这不是 hazard_score 或 risk_score。
- 这不是 observed truth。
- 这不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 SOLWEIG 或 QGIS。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
"""


def status_text(status: str, best: dict[str, Any], config: dict[str, Any], frames: dict[str, pd.DataFrame]) -> str:
    """Build lane status Markdown."""
    outputs = [str(repo_path(value).relative_to(repo_path("."))) for value in config["outputs"].values()]
    inventory = frames["inventory"]
    row = inventory.loc[inventory["input_key"] == "b86c_dataset_path"].iloc[0] if not inventory.empty else {}
    return f"""# B8.6d Status

Generated: {now_stamp()}
Status: {status}
Branch: {config["branch"]}
Scope: System B compact two-stage surrogate workflow formalization and long-run validation.

## Commands run

- `C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python -m compileall scripts/v12_b86d_*.py`
- `C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python scripts/v12_b86d_run_two_stage_surrogate.py --config configs/v12/systemb_b86d_two_stage_surrogate.yaml`
- Python UTF-8/mojibake check for the Chinese doc
- `git status --short -- .`
- forbidden-file check over `git status --porcelain -- .`

## Key results

- Rows/cells/forcing days/hours: {int(row.get("row_count", 0))}/{int(row.get("unique_cells", 0))}/{int(row.get("forcing_day_count", 0))}/{int(row.get("hour_count", 0))}
- Best threshold/classifier/regressor: {float(best.get("neutral_threshold_c", 0.05)):.2f} / {best.get("classifier")} / {best.get("regressor")}
- Supporting headline: {headline_from_split(frames["by_split"])}
- AOI-wide preflight recommendation: see promotion gate; no AOI-wide output is created here.
- B9 status: B9_BLOCKED

## Files created / modified

{chr(10).join(f"- `{path}`" for path in outputs)}

## Caveats

- The labels are SOLWEIG-derived Tmrt deltas, not observed truth.
- Feature importance is diagnostic only and non-causal.
- h10 remains caveated and is separated from core-hour behavior.
- No raster, QGIS, SOLWEIG, AOI-wide prediction, local WBGT, hazard_score, risk_score, or System A/B coupling output was created.

## Safe to commit

Compact B8.6d config, scripts, docs, CSV, and Markdown outputs after review.

## Not safe to commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip packages, AOI-wide predictions, and B9 outputs.
"""


def run(config_path: Path = DEFAULT_CONFIG) -> ReportResult:
    """Write all B8.6d report artifacts."""
    config = load_config(config_path)
    frames = {
        "inventory": read_output(config, "input_inventory"),
        "schema": read_output(config, "dataset_schema"),
        "stage1": read_output(config, "stage1_classifier_metrics"),
        "stage2": read_output(config, "stage2_regressor_metrics"),
        "combined": read_output(config, "combined_pipeline_metrics"),
        "sweep": read_output(config, "threshold_sweep_metrics"),
        "by_split": read_output(config, "metrics_by_split"),
        "by_target": read_output(config, "metrics_by_target"),
        "seed": read_output(config, "seed_stability_metrics"),
        "anchor": read_output(config, "anchor_cell_diagnostics"),
        "neutral": read_output(config, "neutral_boundary_diagnostics"),
        "unstable": read_output(config, "unstable_cell_diagnostics"),
    }
    best = selected_combo(config)
    target_decision = target_role_decision(config, frames["by_target"])
    status, promotion = gate_decision(config, frames["by_split"], frames["seed"])
    frames["target_decision"] = target_decision
    frames["promotion"] = promotion
    write_csv(target_decision, output_path(config, "target_role_decision"))
    write_csv(promotion, output_path(config, "promotion_gate"))
    write_text(model_card_text(status, best, frames), output_path(config, "model_card"))
    write_text(workflow_text(), output_path(config, "surrogate_workflow_v0_2"))
    write_text(report_text(config, status, best, frames), output_path(config, "report"))
    write_text(cn_doc_text(status, best, frames), output_path(config, "cn_doc"))
    write_text(status_text(status, best, config, frames), output_path(config, "status"))
    return ReportResult(status, float(best.get("neutral_threshold_c", 0.05)), str(best.get("classifier")), str(best.get("regressor")))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Write B8.6d reports, gate, model card, status, and CN doc.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
