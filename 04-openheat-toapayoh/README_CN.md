# OpenHeat-ToaPayoh v0.6.1 — feedback-optimised live forecast + NEA/WBGT calibration prototype

v0.6.1 是根据 `V0.6优化意见.pdf` 做的稳定性与科学定位修订版。核心变化不是多加一个模型，而是把 API、时区、归档、校准对象和方法限制写清楚，避免 v0.6 最容易踩的隐性 bug。

## v0.6.1 更新重点

1. **Open-Meteo 不需要 API key**：直接 GET；默认 `timezone=Asia/Singapore`。
2. **data.gov.sg / NEA 读接口默认不需要 API key**：`DATA_GOV_SG_API_KEY` 只是 optional future-proof header。
3. **NEA 默认改用 legacy v1 endpoints**：`https://api.data.gov.sg/v1/environment/...`，同时保留 v2 parser。
4. **所有时间统一为 tz-aware Asia/Singapore**：避免 Open-Meteo 与 NEA 配对时偏 8 小时。
5. **官方 WBGT 只作为 calibration target**：不要把官方 WBGT 再塞回 proxy 公式。
6. **nearest WBGT station 增加 representativeness flag**：避免把 nearby station calibration 误写成 Toa Payoh street-level validation。
7. **归档脚本更稳**：支持 null value、station list 变化、fetch timestamp、空响应 heartbeat。
8. **新增 GitHub Actions 归档模板**：可每 15 分钟拉取 NEA observations。

## 系统逻辑

```text
Open-Meteo background forecast
    ↓
Toa Payoh grid-feature downscaling / local modification
    ↓
UTCI / WBGT proxy hotspot ranking
    ↓
NEA official WBGT + station observations
    ↓
future: multi-day bias correction / hindcast calibration
```

重要定位：Open-Meteo 在 Toa Payoh 尺度提供的是背景气象，不是街区内 50–100 m 的空间差异。v0.7 的 building density、SVF、GVI、shade、road fraction 等 grid features 才是 intra-neighbourhood spatial downscaling 的核心。

## 快速运行：离线复现实验

```bash
cd openheat_toapayoh_v0_6_1_feedback_optimised
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/run_live_forecast_v06.py --mode sample
python scripts/run_nea_api_schema_check.py --mode fixture
pytest -q
```

会生成：

```text
outputs/v06_offline_hourly_grid_heatstress_forecast.csv
outputs/v06_offline_hotspot_ranking.csv
outputs/v06_offline_event_windows.csv
outputs/v06_1_nea_station_observations_schema_check.csv
outputs/v06_1_grid_nearest_wbgt_station.csv
outputs/v06_offline_hotspot_preview.png
```

## 运行 live forecast

有网络时：

```bash
python scripts/run_live_forecast_v06.py --mode live
```

输出：

```text
outputs/v06_live_openmeteo_forecast_raw.csv
outputs/v06_live_hourly_grid_heatstress_forecast.csv
outputs/v06_live_hotspot_ranking.csv
outputs/v06_live_event_windows.csv
```

## 检查 NEA / data.gov.sg API schema

默认 v1：

```bash
python scripts/run_nea_api_schema_check.py --mode live --api-version v1
```

可选 v2：

```bash
python scripts/run_nea_api_schema_check.py --mode live --api-version v2
```

## 开始归档 NEA observations

```bash
python scripts/archive_nea_observations.py --mode live --api-version v1
```

归档到：

```text
data/archive/nea_realtime_observations.csv
```

也可以启用：

```text
.github/workflows/archive_nea_observations.yml
```

让 GitHub Actions 每 15 分钟执行一次归档。详见：

```text
docs/07_GITHUB_ACTIONS_ARCHIVING_CN.md
```

## 不需要 API key

v0.6.1 默认不需要 API key。

如果未来 data.gov.sg 改策略，或者你注册了 higher-rate-limit key，可以设置：

```bash
export DATA_GOV_SG_API_KEY="your_optional_key_here"
```

Windows PowerShell：

```powershell
$env:DATA_GOV_SG_API_KEY="your_optional_key_here"
```

## v0.6.1 已完成

- Open-Meteo live forecast fetcher；
- data.gov.sg v1 / v2 realtime weather / WBGT fetcher；
- v1/v2 schema-tolerant station parser；
- SGT timezone utilities；
- wind speed knots → m/s conversion；
- nearest-station matching + representativeness flag；
- station skill metrics；
- WBGT proxy → official WBGT calibration skeleton；
- data archiving with heartbeat rows；
- GitHub Actions 15-min archive template；
- feedback-specific tests。

## v0.6.1 不能替你完成的部分

1. **正式 WBGT calibration**：需要你持续归档多日 observations，最好跨 sunny / overcast / pre-thundershower regimes，并包含 WBGT ≥31°C，理想情况下包含 ≥33°C。
2. **真实 Toa Payoh grid features**：当前 grid 仍是 sample；v0.7 要换成真实建筑、道路、GVI、SVF、shade、绿地和脆弱性特征。
3. **正式 Tmrt 模拟**：当前 Tmrt 是 screening proxy；SOLWEIG/UMEP 应放到 v0.8/v0.9。
4. **官方公共健康预警**：当前系统是 decision-support / hotspot prioritisation prototype，不是 NEA/MSS operational warning。

详细操作见：

```text
docs/06_V06_1_FEEDBACK_OPTIMISATION_CN.md
docs/07_GITHUB_ACTIONS_ARCHIVING_CN.md
docs/08_V06_1_TO_V07_PRIORITY_CN.md
```
