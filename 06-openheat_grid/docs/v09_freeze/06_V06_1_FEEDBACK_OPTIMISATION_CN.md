# OpenHeat-ToaPayoh v0.6.1：基于 V0.6 优化意见的修订说明

本版本吸收 `V0.6优化意见.pdf` 中对 API、时区、校准与科学定位的建议。v0.6.1 不是新加花哨功能，而是把 v0.6 的 live-calibration 层做得更可靠、更可解释、更不容易踩科学性地雷。

## 1. API 运行逻辑修订

### 1.1 Open-Meteo 不再暗示需要 key

Open-Meteo 在非商业使用场景下无需 API key。v0.6.1 保留直接 GET 调用方式，并在文档中明确：

```bash
python scripts/run_live_forecast_v06.py --mode live
```

即可请求 Open-Meteo。没有任何 Open-Meteo key 前置条件。

### 1.2 data.gov.sg / NEA 读接口默认不需要 key

v0.6 原先写了 `DATA_GOV_SG_API_KEY`，容易让使用者误以为它是必填。v0.6.1 改成：

- 默认不需要 API key；
- 如果本地设置了 `DATA_GOV_SG_API_KEY`，代码会作为 optional header 加上；
- 这个 key 仅作为 future-proof / higher-rate-limit 预留，不是运行前置条件。

### 1.3 默认改用 legacy v1 environment endpoints

v0.6.1 默认使用：

```text
https://api.data.gov.sg/v1/environment/wbgt
https://api.data.gov.sg/v1/environment/air-temperature
https://api.data.gov.sg/v1/environment/relative-humidity
https://api.data.gov.sg/v1/environment/wind-speed
https://api.data.gov.sg/v1/environment/wind-direction
https://api.data.gov.sg/v1/environment/rainfall
```

代码位置：

```text
src/openheat_forecast/live_api.py
```

同时仍然支持新版 v2 API：

```python
fetch_official_wbgt(api_version="v2")
```

这样做的原因：v1 shape 更直接，`metadata + items + readings` 结构容易归一化，也方便 `?date=` / `?date_time=` 历史快照查询。

## 2. 时区 bug 修复

v0.6.1 新增：

```text
src/openheat_forecast/time_utils.py
```

所有 Open-Meteo forecast time 和 NEA observation timestamp 都会被转换为 timezone-aware `Asia/Singapore` 时间。

为什么这重要：

- Open-Meteo 如果不传 `timezone=Asia/Singapore`，默认容易是 UTC；
- NEA timestamp 通常带 `+08:00`；
- 如果一个 naive、一个 aware，或者一个 UTC、一个 SGT，calibration 会 silently 偏 8 小时。

v0.6.1 在 `make_paired_wbgt_table()` 中也强制二次转换，避免后续 notebook 中再次出现配对错误。

## 3. Open-Meteo 空间分辨率限制写入方法论

v0.6.1 把一个关键事实写进了输出 metadata 和文档：

> Open-Meteo 在 Toa Payoh 尺度提供的是 neighbourhood/background meteorology，而不是街区内 50–100 m 的空间差异。

因此，OpenHeat 的空间差异不是由 forecast grid 本身产生，而是由以下 grid features 进行 statistical downscaling / local modification：

```text
building_density
road_fraction
gvi_percent
svf
shade_fraction
park_distance_m
elderly_proxy
outdoor_exposure_proxy
```

这对 v0.7 很关键。v0.7 的 grid features 不是“锦上添花”，而是系统解释 intra-Toa Payoh heat-stress difference 的核心。

## 4. WBGT calibration 定位收窄

v0.6.1 明确：

```text
WBGT_proxy = f(Open-Meteo T, RH, wind, radiation + local features)
Official NEA WBGT = calibration target
```

也就是说，官方 WBGT 只作为校准/验证目标，不作为输入变量再计算一遍 WBGT。

新加坡官方 WBGT station 数量有限，Toa Payoh 本身不一定有站点。因此 v0.6.1 在 nearest station 输出中新增：

```text
nearest_station_distance_m
station_representativeness
```

`station_representativeness` 分为：

```text
local             <= 1 km
nearby_proxy      1–3 km
regional_proxy    > 3 km
```

这可以防止错误表述：不能把 Bishan / nearby station 的 WBGT calibration 说成 Toa Payoh 每个 HDB cell 的直接实测验证。

## 5. 数据缺口与 station-list 变化处理

v0.6.1 的 parser 支持：

- value = null；
- station 临时下线；
- station list 改变；
- v1 / v2 schema 差异；
- fetch timestamp 归档；
- endpoint URL 归档。

归一化后的 observation 表新增字段：

```text
timestamp
station_id
station_name
station_lat
station_lon
value_missing
api_name
api_version
endpoint_url
fetch_timestamp_utc
```

归档脚本也会在空响应时写入 heartbeat row，方便确认定时任务不是“静默断掉”。

## 6. 长期归档方案

新增 GitHub Actions 模板：

```text
.github/workflows/archive_nea_observations.yml
```

它可以每 15 分钟运行一次：

```bash
python scripts/archive_nea_observations.py --mode live --api-version v1
```

注意：这只是 prototype 方案。如果长期运行，最好把 archive 写入 object storage / database，而不是长期每 15 分钟 commit CSV 到 GitHub，否则 repo 会膨胀。

## 7. 新增测试

新增测试文件：

```text
tests/test_v06_1_feedback_optimisations.py
```

覆盖：

- v1 NEA schema parser；
- null value handling；
- SGT timezone pairing；
- nearest station representativeness flag；
- calibration readiness 对 event diversity 的要求。

## 8. v0.6.1 的科学定位

现在最严谨的表述是：

> OpenHeat-ToaPayoh v0.6.1 is a live-data and calibration-ready prototype. It uses Open-Meteo as background meteorology, NEA observations as official calibration targets, and local grid features as the basis for statistical downscaling of intra-neighbourhood heat-stress differences.

不要写：

> It accurately predicts official WBGT at every Toa Payoh street cell.

可以写：

> It produces decision-support hotspot rankings and is ready for multi-day calibration against official WBGT observations.
