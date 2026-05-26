# OpenHeat System A L1H full-period weather merge 说明

## A-L1H.0c interpretation / provenance hygiene patch

Status remains `PASS_FULL_PERIOD` only because retention is 6696 / 6696 and all observed ge31 rows are matched.

Weather-regime diagnostic coverage: `PASS_FULL_PERIOD`. Radiation-hot regimes contain nearly all observed ge31 events and misses, but conditional miss-rate enrichment beyond the observed-ge31 base rate is mixed. This supports full-period weather-regime diagnostic evidence, not causal proof. The dominant issue remains global high-tail score compression, with station-specific bias and weather-regime structure as interacting diagnostics.

Allowed claim boundary wording is limited to retrospective System A WBGT_A temporal severity diagnostics, full-period weather-regime residual diagnostics, and evidence to inform later WBGT-gated radiative priority only after System B coupling.

Disallowed wording includes validated local WBGT prediction, real-time heat risk forecast, standalone local hazard prioritisation from System A alone, and official warning probability claims.

## 目的

本文档对应 A-L1H.0c。任务目标是把
`outputs/v11_systema_l1_high_tail/residual_decomposition/residual_analysis_input.csv`
和 A-L1H.0b 之后恢复出的 compact weather feature source 合并，判断天气情景残差分解是否已经具备 full-period 证据。

本任务只做 merge hardening 和诊断汇总：

- 不训练模型；
- 不实现 formula-v2；
- 不做 probability / threshold calibration；
- 不做 high-tail regression；
- 不启动 A-L2；
- 不触碰 System B、SOLWEIG、raster、raw archive 或大型 hourly forecast CSV。

## 首选天气源

首选输入是：

- `outputs/v11_systema_l1_high_tail/weather_regime_merge_inputs/best_weather_feature_source.csv.gz`

该 compact source 保留原始来源 provenance：

- base: `orig`
- relative path: `outputs/v11_beta_formal/diagnostics_inputs/v11_pairs_14d_formal_20260524_40419_v091_diag.csv`

运行 A-L1H.0c 时不需要复制或提交原始 diagnostics input；脚本直接使用 compact recovered source，并把 provenance 写入 inventory 和 decision report。

## 合并规则

- residual 侧与 weather 侧均规范化为 SGT hourly timestamp；
- 只用 `station_id + SGT hourly timestamp` 作为 merge key；
- 目标 WBGT 值不参与匹配；
- merged output 保留所有 residual rows；
- 未匹配 residual rows 标记为 `has_weather_match = False`；
- weather-regime summary 只使用 matched rows。

## 输出

输出目录：

- `outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/`

核心输出：

- `full_period_weather_source_inventory.csv`
- `residual_weather_merge_full_period.csv`
- `residual_by_weather_regime_full_period.csv`
- `ge31_miss_by_weather_regime_full_period.csv`
- `weather_regime_full_period_decision_report.md`
- `A_L1H_0C_STATUS.md`

## 判读规则

- retention rate >= 0.80 且 observed ge31 event coverage 足够时，status 为 `PASS_FULL_PERIOD`；
- 0.40 <= retention rate < 0.80 时，status 为 `PARTIAL_DIAGNOSTIC`；
- retention rate < 0.40 时，status 为 `BLOCKED_FOR_FULL_PERIOD`。

即使 status 为 `PASS_FULL_PERIOD`，结论也只限于 retrospective OOF diagnostic evidence；不得升级为 validated local WBGT prediction、real-time heat risk forecast、official warning probability、formula-v2 结果或 high-tail regression 结果。
