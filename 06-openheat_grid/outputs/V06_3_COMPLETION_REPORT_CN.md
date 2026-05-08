# v0.6.3 完成报告：WBGT v2 parser 修复

已基于用户上传的 `debug_wbgt_raw.json` 修复 data.gov.sg v2 WBGT schema 解析问题。

## 关键发现

- API 成功返回 `code = 0`。
- 当前 endpoint 为 `https://api-open.data.gov.sg/v2/real-time/api/weather?api=wbgt`。
- WBGT 读数位于 `data.records[].item.readings[]`。
- 每条 reading 包含：
  - `station.id`
  - `station.name`
  - `station.townCenter`
  - sibling `location.latitude/location.longitude`
  - `wbgt`
  - `heatStress`
- 本次 debug 文件中共有 27 个 WBGT station readings。
- S128 Bishan Street / Bishan Stadium 的坐标为 `1.354825, 103.852219`，WBGT 为 `30.6`，heat stress 为 `Low`。

## 修复内容

- 支持 `data.records[].item.readings[]`。
- 支持 sibling `location` 坐标。
- 输出 `station_town_center`、`heat_stress_category` 和 `record_updated_timestamp`。
- 新增当前 schema fixture 与测试。

## 测试

```text
11 passed
```

## 下一步

运行：

```bash
python scripts/run_nea_api_schema_check.py --mode live --api-version v2
python scripts/archive_nea_observations.py --mode live --api-version v2
```

然后检查：

```text
outputs/v06_1_nea_station_observations_schema_check.csv
outputs/v06_1_grid_nearest_wbgt_station.csv
data/archive/nea_realtime_observations.csv
```
