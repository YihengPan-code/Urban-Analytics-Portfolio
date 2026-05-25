# System A 本地 prospective metadata dry smoke 运行手册

## 这是什么

Sprint 4B.2 是 System A Level 1 元数据基础设施的本地干跑检查。它只生成合成 prospective metadata 形状的行，并检查 issue/model time、valid time、retrieval time、lead time、issue-valid pair id 和 quality flag 是否能按预期工作。

本 dry smoke 不联网，不调用 Open-Meteo，不调用 NEA/WBGT，不修改 collector runtime，不修改历史 archive，不训练模型，不评估模型。

## 为什么必须离线和合成

当前项目证据只支持 retrospective valid-time calibration。要进入真正 prospective forecast evaluation，必须先证明未来 collector 行所需的 metadata schema、fail-closed 规则和 manifest 结构可以在本地稳定产生。合成 dry smoke 可以先检查这些机制，而不会误把历史回填或实时抓取说成 forecast skill。

## 与 24h live smoke 的区别

本 dry smoke：

- 使用 synthetic rows only；
- output 只写入 `outputs/v11_level1/prospective_eval/local_dry_smoke/`；
- 不产生 provider run metadata 证据；
- 不测量官方 WBGT 发布延迟；
- 不比较 forecast 与未来 official observation；
- 不建立 prospective forecast skill。

24h live smoke 只有在用户明确批准 API calls 和输出路径后才能做。它会涉及真实 collection timing、provider metadata 可用性、official retrieval delay 和本地/GHA 连续性检查。

## 它证明什么

- helper/schema 可以产生 future prospective metadata-shaped rows；
- `issue_valid_pair_id` 可以非空且唯一；
- 有 `model_run_time_utc` 时可以正确计算 `forecast_lead_time_hours`；
- 缺少 `model_run_time_utc` 和 `forecast_issue_time_utc` 时会 fail closed；
- `missing_model_run_time`、`missing_forecast_issue_time`、`missing_lead_time` 等 quality flags 会出现；
- manifest 和 validation 输出结构可供审阅。

## 它不证明什么

This dry smoke does not establish prospective forecast skill.

它也不证明：

- live collection 已经运行；
- Open-Meteo provider run metadata 已经可用；
- NEA/WBGT retrieval delay 已经被真实测量；
- GHA/local parity 已经通过；
- operational forecast 或 public warning 能力已经建立；
- System B、v12、SOLWEIG、rasters、risk maps 或 local WBGT 已经被触碰或验证。

## 如何运行

在 repo 根目录运行：

```powershell
C:\Users\CloudStar\anaconda3\Scripts\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\v11_l1_prospective_metadata_local_dry_smoke.py
```

不要直接调用 env 内的 `python.exe`。不要使用 fallback solver。

## 需要检查的输出

- `outputs/v11_level1/prospective_eval/local_dry_smoke/synthetic_prospective_rows.csv`
- `outputs/v11_level1/prospective_eval/local_dry_smoke/legacy_compatibility_rows.csv`，如果生成
- `outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_manifest.json`
- `outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_manifest.md`
- `outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.csv`
- `outputs/v11_level1/prospective_eval/local_dry_smoke/local_dry_smoke_validation.md`
- `outputs/v11_level1/prospective_eval/local_dry_smoke/sprint4b2_local_dry_smoke_report.md`

## Stop conditions

停止并审查，如果出现任一情况：

- 脚本试图联网或调用 API；
- 输出路径不在 `outputs/v11_level1/prospective_eval/local_dry_smoke/`；
- 历史 archive 文件被修改；
- collector runtime 被修改；
- fail-closed rows 仍有非空 lead time；
- 缺失 issue/model time 的行没有 `missing_lead_time`；
- 输出包含 `local_wbgt_c`、`risk_score`、`cell_id` 等越界字段；
- 报告或 manifest 声称 forecast skill 或 prospective skill。

## 如何准备 Sprint 4B.3

通过本 dry smoke 后，下一步应先审阅 helper/schema 和输出 manifest。只有在用户明确批准 API calls、输出路径和 live smoke 范围后，才能进入 Sprint 4B.3 的 one-run live local prospective metadata smoke。
