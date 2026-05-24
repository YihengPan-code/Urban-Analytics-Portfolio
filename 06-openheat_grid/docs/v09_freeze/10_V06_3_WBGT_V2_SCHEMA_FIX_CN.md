# OpenHeat-ToaPayoh v0.6.3 — WBGT v2 schema fix

## 修复原因

用户上传的 `debug_wbgt_raw.json` 显示 data.gov.sg v2 WBGT 当前返回结构为：

```json
{
  "code": 0,
  "data": {
    "records": [
      {
        "datetime": "2026-05-06T09:45:00+08:00",
        "item": {
          "readings": [
            {
              "station": {"id": "S128", "name": "Bishan Street", "townCenter": "Bishan Stadium"},
              "location": {"latitude": "1.354825", "longitude": "103.852219"},
              "wbgt": "30.6",
              "heatStress": "Low"
            }
          ],
          "isStationData": true,
          "type": "observation"
        },
        "updatedTimestamp": "2026-05-06T09:55:03+08:00"
      }
    ]
  }
}
```

v0.6.2 parser 主要兼容 `data.readings[]` 或 `metadata/items` 结构，但当前 WBGT v2 实际是 `data.records[].item.readings[]`。此外，站点坐标不在 `station.location` 里，而是 `readings[].location`，与 `station` 同级。因此 v0.6.2 能访问 API，但无法解析 `station_lat/station_lon`。

## 修复内容

- `normalise_realtime_station_readings()` 现在支持 `data.records[].item.readings[]`。
- `_station_meta_from_any()` 现在可读取 sibling `location.latitude/location.longitude`。
- 保留 `station_town_center`。
- 保留 `heat_stress_category`。
- 保留 `record_updated_timestamp`。
- 新增测试 fixture：`data/fixtures/nea_wbgt_v2_current_schema_sample.json`。
- 新增测试：`tests/test_v06_3_wbgt_v2_schema.py`。

## 验证

本地离线测试：

```bash
pytest -q
```

结果：

```text
11 passed
```

## 使用方式

推荐直接使用 v0.6.3 包；如果只想补丁更新，替换：

```text
src/openheat_forecast/live_api.py
```

然后运行：

```bash
python scripts/run_nea_api_schema_check.py --mode live --api-version v2
python scripts/archive_nea_observations.py --mode live --api-version v2
```

如果成功，应生成：

```text
outputs/v06_1_nea_station_observations_schema_check.csv
outputs/v06_1_grid_nearest_wbgt_station.csv
data/archive/nea_realtime_observations.csv
```

## 科学解释边界

S128 Bishan Stadium 可作为 Toa Payoh 附近官方 WBGT proxy，但不是每个 Toa Payoh HDB cell 的街道级实测 WBGT。v0.7 的真实任务仍是用 building/SVF/GVI/shade/road fraction 等 grid features 做 statistical downscaling。
