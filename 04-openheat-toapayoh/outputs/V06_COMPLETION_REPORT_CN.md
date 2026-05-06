# OpenHeat-ToaPayoh v0.6 completion report

## 已完成

- Open-Meteo forecast fetcher: `src/openheat_forecast/live_api.py`
- data.gov.sg / NEA realtime weather + WBGT fetcher
- NEA station response normaliser
- wind speed knots to m/s conversion
- nearest-station matching
- station skill metrics
- WBGT proxy linear calibration skeleton
- offline fixtures for API schema tests
- scripts for sample/live forecast and NEA schema checks
- observation archive script for future calibration
- notebook: `notebooks/04_live_forecast_and_calibration_v06.ipynb`
- tests: 5 passed

## 仍需用户本地完成

1. 在联网环境运行 live mode。
2. 连续归档 NEA official WBGT observations。
3. 构建 forecast issue archive。
4. 将 sample Toa Payoh grid 替换成真实 spatial features。
5. 收集足够 paired observations 后再发布 calibration metrics。

## 当前最重要输出

```text
outputs/v06_offline_hotspot_ranking.csv
outputs/v06_fixture_station_observations.csv
outputs/v06_sample_calibration_model.json
```
