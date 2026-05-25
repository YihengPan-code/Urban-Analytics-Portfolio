# System A 前瞻性元数据 Schema 说明

状态：Sprint 4B.1 元数据准备说明。本文不报告预测技巧，不训练模型，不修改历史 archive。

## 为什么需要这些字段

当前 System A Level 1 证据主要支持 retrospective valid-time calibration：把天气强迫与官方 WBGT 按有效时间对齐，然后做回顾性诊断。这不能自动变成前瞻性 forecast skill。

前瞻性评估需要回答更严格的问题：在某个预报发布或获取时间点，当时已经可用的预报信息，对后续有效时间的官方观测表现如何。因此 future rows 必须保存 issue/model time、valid time、retrieval time、source lane、产品身份、lead time 和 row-level quality flag。

## 时间字段定义

| 字段 | 含义 | 可否替代 issue/model time |
|---|---|---:|
| `valid_time_utc` | 预报或观测描述的有效时间 | 否 |
| `valid_time_sgt` | 同一有效时间的新加坡时间显示 | 否 |
| `forecast_issue_time_utc` | 预报产品语义上发布或可用的时间 | 可作为 fallback，但必须语义可靠 |
| `model_run_time_utc` | provider 模型循环或运行时间 | 首选 lead-time 参考 |
| `forecast_requested_at_utc` | collector 发出 Open-Meteo 请求的时间 | 否 |
| `forecast_retrieved_at_utc` | collector 收到 Open-Meteo 响应的时间 | 否 |
| `official_observed_at_utc` | 官方 WBGT/观测对应的观测时间 | 否 |
| `official_retrieved_at_utc` | collector 获取官方观测的时间 | 否 |

## 为什么 retrieval time 不是 issue time

Retrieval time 只说明 collector 什么时候拿到数据，不说明 provider 什么时候生成或发布预报。把 `forecast_retrieved_at_utc` 当成 `forecast_issue_time_utc` 会把事后获取、延迟获取、重试获取、GHA 排队延迟等操作细节误写成预报产品本身的发布时间。

因此本 schema 明确要求：`forecast_lead_time_hours` 只能由 `valid_time_utc - model_run_time_utc` 计算；若没有 model run time，只有在 `forecast_issue_time_utc` 语义可靠时才可 fallback。不能用 retrieval time 计算 lead time。

## Lead Time 必须 fail closed

如果 `model_run_time_utc` 缺失，且 `forecast_issue_time_utc` 也不可靠或缺失，则 `forecast_lead_time_hours = null`，并设置质量标记：

- `missing_model_run_time`
- `missing_forecast_issue_time`
- `missing_lead_time`

这种行可以保留作 archive metadata，但不能进入 lead-time-specific forecast skill 评估。

## Legacy Rows 的处理

历史 archive 和已冻结 snapshot 不应被重写。Legacy rows 可以在读取或派生视图中被识别为缺少前瞻性元数据，并标记：

- `legacy_missing_prospective_metadata`
- 以及相应的缺失项，例如 `missing_forecast_retrieved_at`、`missing_official_retrieved_at`、`missing_lead_time`

这不是坏数据，只是说明这些行属于 retrospective calibration evidence，而不是 live prospective evaluation evidence。

## Future Prospective Rows 如何评估

未来可评估行至少需要：

- `issue_valid_pair_id`
- `station_id`
- `valid_time_utc`
- `forecast_provider`
- `forecast_api_product`
- `forecast_retrieved_at_utc`
- `official_observed_at_utc`
- `official_retrieved_at_utc`
- `forecast_lead_time_hours`
- `collector_run_id`
- `source_lane`
- `quality_flag`

只有 `quality_flag` 包含 `ok_prospective_metadata`，且不包含 blocking 缺失项时，才可进入前瞻性 lead-time 评估。评估仍然只限 System A Level 1 station-network 背景时间严重度，不代表 local WBGT、official warning、risk forecast、System B 或 v12/SOLWEIG 结果。

## Hindcast Mode B 与 Live Mode C

Hindcast Mode B：以后可能使用 Open-Meteo Historical Forecast、Previous Runs 或 Single Runs 产品重建过去某个 issue/model time 当时可用的预报。它需要产品能可靠表达 issue/model run、valid time、endpoint/product 和检索假设。

Live Mode C：collector 现在或未来实时保存预报和官方观测元数据。预报必须在目标有效时间之前或按定义可用；官方观测稍后到达后再评分。Live Mode C 需要记录 GHA/local source lane、run manifest、retrieval latency、official observation delay 和 issue-valid pair key。

## Claim Boundary

在完成有效前瞻性 archive smoke 与评估前，OpenHeat 仍只能声称：

- calibrated hourly WBGT temporal baseline；
- simulation-informed local radiative modifier；
- WBGT-gated local radiative hazard score；
- first-order local heat hazard prioritisation。

不得声称 prospective forecast skill、real-time warning、validated local WBGT prediction、hazard map equals risk map，或 System B/v12/SOLWEIG 已经在本 sprint 中被修改或验证。
