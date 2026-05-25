# OpenHeat System A Level 1 Interim Model Card

## 0. Document metadata

- Project: OpenHeat-ToaPayoh
- Date: 2026-05-25
- Repo: `Urban-Analytics-Portfolio/06-openheat_grid`
- Branch: `dev/systema-level1-audit`
- Model card status: interim / retrospective / not operational
- Covered sprints: Sprint 1, Sprint 1b/1c, Sprint 2A, Sprint 2B, Sprint 2C, Sprint 3A, Sprint 3B, Sprint 4A packaging

## 1. Intended use

Allowed:

- 回顾性 `WBGT_A` 分数分析。
- 站点网络 / AOI 背景热应激严重度描述。
- `p_ge31_diagnostic` 诊断概率伴随输出。
- System B 的 temporal severity input。
- 研究、报告、质量说明和后续评估设计。

Not intended:

- 100m 本地 WBGT。
- 公共运营预警。
- 健康风险 forecast。
- 前瞻 forecast skill claim。
- station context 或 station residual 的因果解释。

## 2. System A Level 1 architecture

System A Level 1 当前是一个站点网络背景层。输入来自冻结/既有的站点官方 WBGT 目标、Open-Meteo 动态 forcing、v09 proxy 与滞后/辐射/时间特征。输出分两层：

1. `wbgt_a_score_c`: `M4_like_inertia_ridge` 的 WBGT-like 回归分数。
2. `p_ge31_diagnostic`: 基于 `M4_like_inertia_ridge` 分数、`logistic_score_calibration`、`blocked_date_calibration` 的 ge31 回顾性诊断概率。

不包含：Level 2、System B、SOLWEIG、Tmrt、rasters、QGIS、risk map、local WBGT、exposure、vulnerability 或 formula-v2 部署。

## 3. Data and validation context

- Formal-hourly OOF-derived diagnostics: `hourly_max` / `hourly_mean`，station count 27，M4 `hourly_max` n=10473。
- Targets: `official_wbgt_c_max` and `official_wbgt_c_mean` in hourly formal diagnostics; ge31 event target is official WBGT >=31 C.
- Validation schemes: LOSO, formal-hourly OOF-derived diagnostics, blocked-date CV, future-block diagnostic, station-grouped / blocked-date probability calibration。
- Nature: 全部为 retrospective diagnostics；不是 prospective operational validation。

Evidence gaps recorded in the ledger:

- Missing: `docs/v11/SystemA_Level1_Level2_architecture_discussion_record_CN.md`
- Missing: `docs/v11/OpenHeat_SystemA_next_development_plan_GPT_Codex_CN.md`

## 4. Model components

### 4.1 WBGT_A regression score

Default model: `M4_like_inertia_ridge`。

Selected because it is the current conservative Level 1 default with strong retrospective LOSO/formal-hourly regression performance and a clear evidence chain through Sprint 1/1c/2A/2B. It should be described as a WBGT-like background heat-stress score, not as calibrated fixed-threshold crossing.

Sensitivity candidates:

- `M7_like_compact_weather_ridge`
- `L1_full_dynamic`
- `L1_proxy_radiation`

Limitations: high-tail underprediction remains, station-level bias remains, and blocked-date diagnostics are weaker than LOSO.

### 4.2 P_ge31 diagnostic companion

Default: `M4_like_inertia_ridge + logistic_score_calibration + blocked_date_calibration`，output name `p_ge31_diagnostic`。

Selected because Sprint 3B identified it as the conservative diagnostic companion: it preserves the M4_like score source, uses a simple logistic calibration layer, and uses blocked-date validation context. It estimates retrospective diagnostic probability that official WBGT >=31 C.

Limitations: not official warning probability, not prospective forecast, residual station bias remains.

### 4.3 ge33 exploratory

`ge33` remains exploratory only. The event count is sparse, fixed nominal ge33 prediction is weak/zero in several diagnostics, and threshold behavior is unstable. Do not promote ge33 to operational output.

## 5. Evidence summary by sprint

| Sprint | Purpose | Key outputs | Main finding | Impact on next step |
|---|---|---|---|---|
| Sprint 1 | M2 recovery, station pairing, M3/M4/M7 reproduction | recovery/pairing/reproduction reports and metrics | Core Level 1 evidence chain passed; no fallback in canonical reproduction | Enabled formal-hourly reference |
| Sprint 1b/1c | Formal-hourly OOF-derived reference | formal_hourly_oof_derived_metrics.csv | M4 formal-hourly metrics available without retraining | Anchored model-card regression numbers |
| Sprint 2A | Dynamic feature ablation | ablation metrics, deltas, station/high-tail diagnostics | M4_like remains conservative default; high-tail compression persists | Required event/probability companion |
| Sprint 2B | Blocked-time and high-tail diagnostics | blocked-date/future-holdout metrics | Temporal diagnostics are weaker and retrospective | Prospective evaluation remains needed |
| Sprint 2C | Event calibration | operating points, threshold stability, score bins | ge31 best-F1 requires threshold below nominal 31; ge33 weak | Motivated probability companion |
| Sprint 3A | Formula-v2 proxy benchmark | formula registry/comparison/feasibility | simple formula/k-sweep/affine candidates do not solve high-tail compression | Keep formula-v2 separate |
| Sprint 3B | P_ge31 probability calibration | model selection, metrics, reliability, predictions | selected `p_ge31_diagnostic` conservative default | Sprint 4A output contract and sample |

## 6. Key quantitative findings

- M4 formal-hourly `hourly_max`: n=10473, MAE=0.937, RMSE=1.273, R2=0.699, fixed ge31 F1=0.433。
- M4 formal-hourly `hourly_mean`: MAE=0.878, RMSE=1.197, R2=0.672。
- M4_like Sprint 2A `hourly_max`: MAE=0.937, RMSE=1.273, R2=0.699; official ge31 high-tail MAE=1.571, bias=-1.525。
- Sensitivity candidates, `hourly_max` LOSO MAE: M7_like=0.954, L1_full_dynamic=0.950。
- Blocked-date M4_like `hourly_max`: MAE=1.116, RMSE=1.575, R2=0.538。
- Future-holdout M4_like `hourly_max`: MAE=0.937, RMSE=1.236, R2=0.725。
- M4_like ge31 best-F1 分数阈值在不同验证语境下均低于名义 31°C：LOSO 约 29.5°C，blocked-date 约 30.2°C，future-block 约 30.0°C，对应偏移大约为 -1.5°C 到 -0.8°C。
- Formula-v2 benchmark: best raw formula ge31 best-F1 threshold=27.6 C with high-tail bias=-4.022; best simple affine threshold=29.2 C with high-tail bias=-2.253。These candidates did not solve high-tail compression.
- Probability default `M4_like + logistic + blocked-date`: Brier=0.064, ECE_10=0.013, ROC_AUC=0.931, average precision=0.601, mean p=0.113, observed event rate=0.114。
- Probability threshold diagnostic for the default: precision=0.479, recall=0.671, F1=0.559。
- Station probability bias examples: S142 event rate=0.216, mean p=0.108, bias=-0.108; S139 event rate=0.021, mean p=0.106, bias=0.086。

## 7. Recommended output contract

Use `configs/v11/system_a_level1_output_contract.yaml` as the machine-readable contract and `outputs/v11_level1/model_card/system_a_level1_output_contract.md` as the Chinese interpretation guide.

Required conceptual outputs:

- `wbgt_a_score_c`
- `wbgt_a_score_model_id`
- `p_ge31_diagnostic`
- `p_ge31_calibrator_id`
- `p_ge31_validation_context`
- `is_retrospective`
- `quality_flag`

Forbidden conceptual outputs:

- `cell_id`, `local_wbgt_c`, `wbgt_cell_c`, `delta_wbgt_cell`, `risk_score`, `m_rad`, `tmrt`, `solweig`, `exposure`, `vulnerability`。

## 8. Known limitations

- Retrospective, not prospective。
- Station-network limited。
- High-tail compression remains。
- Nominal threshold crossing is not calibrated。
- ge33 is exploratory。
- Station-level bias remains。
- No Level 2 yet。
- No local WBGT。
- No System B integration yet。

## 9. Safety / claim boundary

Allowed claims:

- calibrated hourly WBGT temporal baseline。
- WBGT-like background heat-stress score。
- retrospective `p_ge31_diagnostic` companion。
- System B temporal severity input, with contract rules。
- first-order local heat hazard prioritisation only after System B keeps hazard-score wording.

Forbidden claims:

- validated local WBGT prediction。
- real-time heat risk forecast。
- official warning probability。
- SOLWEIG Tmrt equals WBGT。
- station residual as cell modifier。
- hazard map equals risk map。
- feature importance proves real-world causal heat-risk drivers。

## 10. Recommended next steps

1. Sprint 4B prospective forecast evaluation design。
2. Sprint 4C P_ge31 export/reliability hardening。
3. Advanced formula implementation as separate track。
4. Level 2 station-context preflight later。
5. Model-family comparison only after output/prospective boundary is clean。

## 11. File inventory

- `docs/v11/SystemA_Level1_Interim_Model_Card_CN.md`
- `configs/v11/system_a_level1_output_contract.yaml`
- `outputs/v11_level1/model_card/system_a_level1_output_contract.md`
- `outputs/v11_level1/model_card/system_a_level1_evidence_ledger.csv`
- `outputs/v11_level1/model_card/system_a_level1_claim_boundary_matrix.csv`
- `outputs/v11_level1/model_card/system_a_level1_current_recommendations.md`
- `outputs/v11_level1/model_card/system_a_level1_current_outputs_sample.csv`
- `outputs/v11_level1/model_card/sprint4a_model_card_integration_report.md`
- `scripts/v11_l1_export_system_a_output_sample.py`

## 12. Short one-paragraph summary

System A Level 1 当前应被视为一个回顾性、站点网络背景热应激评分包：默认回归输出是 `M4_like_inertia_ridge` 的 `wbgt_a_score_c`，默认概率伴随输出是 `M4_like_inertia_ridge + logistic_score_calibration + blocked_date_calibration` 的 `p_ge31_diagnostic`。它可以服务研究、报告和 System B temporal severity 输入，但不能被描述为 100m 本地 WBGT、官方预警概率、实时 forecast skill 或完整风险模型。
