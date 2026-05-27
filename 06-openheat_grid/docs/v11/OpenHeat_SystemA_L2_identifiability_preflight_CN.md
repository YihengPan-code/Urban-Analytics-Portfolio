# OpenHeat System A A-L2.0 站点上下文残差可识别性预检

本文档说明 A-L2.0 的用途、输入、方法、输出和声明边界。A-L2.0 是进入站点上下文残差工作的前置检查，不是 A-L2 模型训练任务。

## 目的

System A Level 1 现在以 `WBGT_A/model_score` 作为回顾性时间强度诊断，并以 `P_ge31` 作为诊断伴随量。A-L1H.3 又给出了一个 recall-first challenger：`cost_sensitive_logistic_score_weather`。该 challenger 只能作为诊断证据，不能替代当前 canonical companion。

A-L2.0 只回答一个问题：在控制 Level 1 分数/概率、天气分型、小时和事件支撑度以后，站点层面的残差或概率误差是否仍然稳定、足够大，并且有可用的站点上下文特征，足以支持后续小范围 A-L2.1 预检模型设计。

## 不是 Level 1 高尾校准的替代品

A-L2.0 不修正 Level 1，也不重新训练 canonical `P_ge31`。如果高尾漏报来自 Level 1 分数压缩或概率校准问题，应先在 Level 1 轨道内处理。A-L2 只能在残差结构经过这些诊断后仍然稳定时，才作为独立的站点上下文问题继续。

## 比较对象

预检同时比较三种概率/阈值语境：

- 当前 canonical diagnostic companion：`M4_inertia_ridge + isotonic_score_only`，best-F1 / selected policy 阈值约为 0.309。
- A-L1H.3 recall-first challenger：`cost_sensitive_logistic_score_weather` 的 selected policy / best-F1。
- 当前 companion 的 recall90 操作点，用于诊断高召回阈值下的站点误差变化。

## 方法

- 残差定义：`score_residual_c = official_wbgt_c - model_score`。
- 概率误差定义：`probability_error = obs_ge31 - p_ge31`。
- 高尾残差：仅在 `obs_ge31` 行上计算 `score_residual_c`。
- 分组单位：站点。
- 稳定性：在每个站点内按日期/小时行进行确定性 bootstrap，输出均值、95% 区间和稳定性标签。
- 语境控制：报告天气分型和小时语境去均值后的残差/概率误差。
- 低支撑警告：ge31 事件数不足的站点不用于强结论。

## 特征边界

脚本只盘点站点上下文特征，不训练完整残差 ML 模型。允许盘点：

- 站点元数据，例如站点名称、经纬度；
- forcing pairing metadata，例如 station-to-grid 或 Open-Meteo pairing 信息；
- 有显式 station-to-cell mapping 时的 morphology proxy。

禁止使用：

- `station_id` 作为预测特征；
- `official_wbgt_c`、`obs_ge31`、`obs_ge33`、残差、目标派生字段；
- System B、SOLWEIG、Tmrt 字段；
- 没有显式站点映射的 100m 网格形态来推断站点 WBGT。

## 输出

输出目录：

`outputs/v11_systema_l2_residual/identifiability_preflight/`

主要文件：

- `station_context_input_inventory.csv`
- `station_level_residual_summary.csv`
- `station_level_probability_error_summary.csv`
- `station_residual_stability_bootstrap.csv`
- `station_context_feature_schema.csv`
- `station_context_identifiability_matrix.csv`
- `station_context_preflight_report.md`
- `A_L2_0_STATUS.md`

## 运行命令

```powershell
python scripts/v11_l2_run_identifiability_preflight.py --config configs/v11/systema_l2_identifiability_preflight.yaml
```

如果系统 `python` 不在 PATH 中，可使用 Codex bundled runtime 的 `python.exe` 执行同一命令。

## 决策解释

可能的决策状态：

- `A_L2_READY_FOR_SCOPED_PREFLIGHT_MODEL`：站点残差结构稳定，且站点上下文特征可用；只允许进入小范围 A-L2.1 预检模型设计。
- `A_L2_DATA_LIMITED`：存在残差信号，但特征或事件支撑较弱；不应训练最终残差模型。
- `A_L2_NOT_IDENTIFIABLE`：信号不稳定或低支撑，A-L2 不可识别。
- `BLOCKED`：无法构建站点层面数据。

## 声明边界

- 不声明本地 100m WBGT。
- 不声明站点上下文因果校正。
- 不声明 operational warning probability。
- 不把 challenger 提升为 canonical replacement。
- 不训练最终 A-L2 残差 ML 模型。
