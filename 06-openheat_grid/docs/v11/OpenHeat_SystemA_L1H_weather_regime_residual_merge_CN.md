# OpenHeat System A L1H 天气情景残差合并说明

## 目的

本说明对应 A-L1H.0b。它只把既有
`outputs/v11_systema_l1_high_tail/residual_decomposition/residual_analysis_input.csv`
与既有站点小时天气表合并，用于重新检查天气情景下的残差与 `ge31` 漏报集中度。

本任务不训练模型，不实现 formula-v2，不做概率校准，不做 high-tail regression，也不进入 A-L2。

## 输入

核心残差输入：

- `outputs/v11_systema_l1_high_tail/residual_decomposition/residual_analysis_input.csv`

首选 OOF 背景输入：

- `outputs/v11_beta_calibration/hourly_max/v11_beta_oof_predictions.csv`

天气源由配置文件枚举并记录 inventory。脚本会优先寻找 `station_id` 与 SGT 小时时间戳，并只用这些键合并；天气源里的目标 WBGT 列不会参与匹配。

## 输出

所有输出写入：

- `outputs/v11_systema_l1_high_tail/weather_regime_merge/`

核心输出包括：

- `weather_source_inventory.csv`
- `residual_weather_merge_input.csv`
- `residual_by_weather_regime.csv`
- `ge31_miss_by_weather_regime.csv`
- `weather_regime_bias_report.md`
- `A_L1H_0B_STATUS.md`

## 解释边界

这些结果只是 retrospective OOF diagnostic，用于判断天气情景交互是否值得作为后续优先级依据。不得将其表述为 validated local WBGT prediction、real-time forecast、probability calibration 或 high-tail regression 结论。
