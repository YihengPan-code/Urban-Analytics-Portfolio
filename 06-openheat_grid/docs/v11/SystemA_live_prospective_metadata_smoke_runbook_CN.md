# System A live prospective metadata smoke 运行手册

## 这是什么

Sprint 4B.3 是一次本地、单次、受限的 live metadata smoke。它只检查 System A Level 1 prospective metadata 基础设施能否在真实 API 响应下记录 request/retrieval timing、source lane、provider/product identity、valid time、quality flags 和 manifest。

它不是 collector runtime patch，不写历史 archive，不训练模型，不评估 forecast skill，不产生 operational warning probability，也不产生 local WBGT。

## 会调用哪些 API

本 smoke 最多调用：

- Open-Meteo Forecast API 3 次：每个 selected station 一次；
- data.gov.sg WBGT observations API 1 次，硬上限 2 次。

公开 endpoint 和 query summary 会写入 manifest。没有 secrets。

## 与 dry smoke 的区别

Sprint 4B.2 dry smoke 只用 synthetic rows，证明 helper/schema、fail-closed lead time 和 manifest 结构在离线环境可用。

Sprint 4B.3 live smoke 使用真实 API 响应，但仍然只做 metadata capture。它会记录 `forecast_requested_at_utc`、`forecast_retrieved_at_utc`、官方 WBGT retrieval timing、response status 和 elapsed seconds。

## 为什么仍不证明 forecast skill

Open-Meteo Forecast API 响应如果没有明确 provider `model_run_time_utc` 或可靠 provider issue time，则本项目不能从 retrieval time 推断 lead time。此时必须：

- `model_run_time_utc = null`
- `forecast_issue_time_utc = null`
- `forecast_lead_time_hours = null`
- `quality_flag` 包含 `missing_model_run_time` 和 `missing_lead_time`

因此本 smoke 即使成功，也只证明 live metadata capture 可运行，不证明 prospective forecast skill、lead-time accuracy 或 operational forecast。

## 如何运行

在 repo 根目录运行：

```powershell
C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\v11_l1_prospective_metadata_live_smoke.py
```

不要直接调用 `C:\Users\CloudStar\anaconda3\envs\openheat\python.exe`。

## 如何检查输出

全部输出只应在：

`outputs/v11_level1/prospective_eval/live_smoke/`

重点检查：

- `live_forecast_metadata_rows.csv`
- `live_official_wbgt_metadata_rows.csv`
- `live_issue_valid_pair_candidates.csv`
- `live_smoke_manifest.json`
- `live_smoke_validation.csv`
- `sprint4b3_live_local_smoke_report.md`

检查点：

- API call counts 是否在限制内；
- forecast request/retrieval timestamps 是否存在；
- official retrieval timestamp 是否存在；
- provider model_run_time 缺失时 lead_time 是否为 null；
- quality_flag 是否包含 `live_smoke_not_forecast_skill`；
- pair candidates 是否明确 `is_skill_evaluable = false`。

## Stop conditions

停止并审查，如果出现任一情况：

- Open-Meteo calls 超过 3；
- WBGT calls 超过 2；
- API schema 与预期不符；
- 输出路径不在 live_smoke 目录；
- 脚本写入 `data/archive`、`data/calibration/v11/archive` 或 historical snapshots；
- collector runtime 被修改；
- retrieval time 被当作 issue/model time；
- 缺少 provider model_run_time 时仍计算 lead_time；
- 输出包含 `local_wbgt_c`、`wbgt_cell_c`、`risk_score`、`cell_id`、`m_rad`、`tmrt`、`solweig`；
- 输出或报告声称 forecast skill。

## 如何准备 24h smoke

如果本 one-run live smoke PASS，下一步可以在用户明确批准后进入 Sprint 4B.4 24h local prospective metadata smoke。24h smoke 应继续只写 future-run-only metadata outputs，并重点检查 collection continuity、station coverage、retrieval timing completeness、provider model_run_time availability 和 GHA/local parity 前置条件。
