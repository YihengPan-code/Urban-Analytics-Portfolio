# OpenHeat System A L1H formula/proxy audit 说明

## 对应任务

本文档对应 A-L1H.1: formula-v2 / physical proxy audit。

本任务回答一个诊断问题:

> 在 A-L1H.0 已发现 high-tail compression 和 station bias, A-L1H.0c 已发现 ge31 misses 集中出现在 radiation-hot regimes 之后, 透明的 WBGT proxy / physical formula candidates 是否能相对当前 v09 proxy 与 M4/M7 OOF score baselines 减轻 ge31 high-tail compression?

## Claim boundary

本任务只做 retrospective diagnostic audit。

允许表述:

- calibrated hourly WBGT temporal baseline;
- simulation-informed local radiative modifier;
- WBGT-gated local radiative hazard score;
- first-order local heat hazard prioritisation;
- future risk overlay after exposure and vulnerability are explicit.

禁止表述:

- validated local WBGT prediction;
- real-time heat risk forecast;
- SOLWEIG Tmrt equals WBGT;
- ML surrogate calibrates observed local WBGT;
- hazard map equals risk map;
- feature importance proves real-world causal heat-risk drivers.

A-L1H.0c 只支持优先开展 formula/proxy audit, 不证明 v09 formula 导致 high-tail compression。

## 输入

主输入:

- `outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/residual_weather_merge_full_period.csv`
- `outputs/v11_systema_l1_high_tail/residual_decomposition/residual_analysis_input.csv`
- `outputs/v11_beta_calibration/hourly_max/v11_beta_oof_predictions.csv`

配置文件:

- `configs/v11/systema_l1h_formula_proxy_audit.yaml`

脚本:

- `scripts/v11_l1h_formula_proxy_audit.py`
- `scripts/v11_l1h_run_formula_proxy_audit.py`

## 候选项

必须包含:

- M4_inertia_ridge OOF score comparator;
- M7_compact_weather_ridge OOF score comparator;
- existing `wbgt_proxy_v09_c` if found, otherwise labelled v09-style reconstruction;
- Stull wet-bulb plus simplified globe proxy candidates.

Stull simple-globe 定义:

```text
wetbulb = Stull(T, RH)
globe_simple = T + k * radiation / sqrt(wind_speed_10m + wind_floor)
WBGT_proxy = 0.7 * wetbulb + 0.2 * globe_simple + 0.1 * T
```

配置扫描:

- `k = [0.002, 0.003, 0.0045, 0.006, 0.008, 0.010, 0.012]`
- `wind_floor = [0.25, 0.5, 1.0]`
- radiation input: `shortwave_radiation`, `shortwave_3h_mean`, `direct_radiation + diffuse_radiation`

Advanced packages such as `pythermalcomfort`, `psychrolib`, and `pywbgt` are detected only if already installed. The audit does not run `pip install` and does not fake a Liljegren-style formula.

## 行单位

M4/M7 comparator scores keep the row unit of `residual_weather_merge_full_period`, including LOSO and blocked-time OOF rows.

Formula/proxy candidates are computed on deduplicated unique station-hour targets to avoid duplicating the same physical formula prediction for duplicate M4/M7 residual rows.

## 输出

输出目录:

- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/`

核心输出:

- `formula_input_inventory.csv`
- `formula_candidate_registry.csv`
- `formula_candidate_predictions.csv.gz`
- `formula_component_diagnostics.csv`
- `formula_overall_metrics.csv`
- `formula_threshold_metrics_31_33.csv`
- `formula_residual_by_observed_bin.csv`
- `formula_residual_by_radiation_regime.csv`
- `formula_ge31_miss_by_regime.csv`
- `formula_physics_audit_report.md`
- `A_L1H_1_STATUS.md`

## 判读规则

`PROMISING_DIAGNOSTIC`:

候选 formula materially reduces observed-ge31 high-tail residual, best-F1 threshold moves closer to 31 C, and this does not come with severe false alarms or large overall degradation.

`WEAK_OR_NEGATIVE`:

Formula candidates do not improve high-tail compression enough, or fixed_31 crossing remains absent or unstable.

`BLOCKED`:

Required weather inputs are missing.

`PARTIAL`:

Candidate looks promising but depends on package/physics implementation validation.

## 下一步门控

推荐动作只能在 report 中诊断性提出。A-L1H.1 不执行:

- probability / threshold calibration;
- high-tail regression;
- A-L2;
- System B coupling;
- SOLWEIG output changes;
- archive collector changes.
