# OpenHeat-ToaPayoh v0.6.4.1：source-review patch

本补丁基于 `src可能的问题.pdf` 的代码审查清单，对 v0.6.4 做了二次修复。v0.6.4 已经修复 archive long format、UTCI/WBGT alert 分离和 hazard score 饱和的主要问题；v0.6.4.1 进一步处理 WBGT v1 默认路径、WBGT-only calibration station matching、以及若干 screening-level 经验系数。

## 逐条判断与处理结果

| 审查点 | 判断 | v0.6.4.1 处理 |
|---|---|---|
| v1 WBGT endpoint 可能不存在 | 属实。v0.6.4 已默认 v2，但显式传 `api_version="v1"` 时仍可能出问题。 | `fetch_official_wbgt()` 现在强制使用 v2；`NEA_V1_API_ENDPOINTS` 中移除 `wbgt`。|
| hazard_score 饱和 | 属实。v0.6.4 已修，但仍可更贴近“percentile + threshold hybrid”。 | 新增/强化 `hazard_wbgt_relative_score`、`hazard_utci_relative_score`、WBGT moderate/high duration 绝对项。|
| 就近站匹配忽略变量网络差异 | 属实，尤其 calibration 时必须只用 WBGT station network。 | 新增 `filter_wbgt_station_observations()`；`attach_nearest_nea_stations_to_grid()` 现在自动筛选 official WBGT rows。|
| wind 上限可超过背景风 | 属实。开阔地加速可解释，但 screening model 中容易过度自信。 | `wind_local_ms` 现在 cap 到 background wind，且保留 0.15 m/s 下限。|
| GVI cap 40% 太低 | 属实。热带/公园边 GVI 高值会被压平。 | `gvi_norm = gvi_percent / 60`，cap 到 1。|
| park cooling 800 m 线性衰减太慢 | 属实。800 m 线性 ramp 对 neighbourhood prototype 偏强。 | 改为 `exp(-distance / 250)`。|
| Tmrt/SVF 方向缺少 canyon longwave | 属实但属于粗模型限制。 | 在 `tmrt_proxy_c` 中新增 `tmrt_wall_longwave_gain_c`。|
| alert 只看 WBGT | v0.6.4 已修。 | 保留 `wbgt_alert`、`utci_alert`、`combined_alert`。|
| cross_join 使用 `_key` | 属低优先级。 | 改为 `merge(how="cross")`，保留旧 pandas fallback。|
| version drift | 属低优先级。 | `__init__.py` 与 `pyproject.toml` 更新至 0.6.4.1；核心 docstring 尽量减少版本号硬编码。|
| `make_paired_wbgt_table` 不适配 long archive | 原审查未作为 critical，但与 v0.6.4 long format 相关。 | 现在可接受 long archive，自动筛选 `variable == official_wbgt_c` 并把 `value` 作为 official WBGT。|

## 主要代码变更

### 1. `live_api.py`

- `fetch_official_wbgt()` 强制走 v2 `weather?api=wbgt`。
- 移除 v1 endpoint 字典中的 `wbgt`，避免误导。
- 保留 v1 给 air temperature / RH / wind / rainfall 等 legacy endpoint 测试。

### 2. `thermal_indices.py`

- `f.merge(g, how="cross")` 替代 `_key` cross join。
- GVI normalization 从 `/40` 改为 `/60`。
- park cooling 从 800 m 线性衰减改为 `exp(-distance / 250)`。
- wind local 不再超过 background wind。
- `tmrt_proxy_c` 增加 low-SVF wall longwave term。
- 输出诊断列：
  - `gvi_norm_for_screening`
  - `park_cooling_exp250`
  - `tmrt_sky_shortwave_gain_c`
  - `tmrt_wall_longwave_gain_c`

### 3. `hotspot_engine.py`

- hazard score 改成 percentile + absolute threshold 混合：
  - `hazard_wbgt_relative_score`
  - `hazard_utci_relative_score`
  - `hazard_utci_intensity_score`
  - `hazard_wbgt_intensity_score`
  - `hazard_utci_duration_score`
  - `hazard_wbgt_moderate_duration_score`
  - `hazard_wbgt_high_duration_score`

### 4. `live_pipeline.py`

- 新增 `filter_wbgt_station_observations()`。
- `attach_nearest_nea_stations_to_grid()` 现在只用 official WBGT rows，避免被更密集的 air-temperature network 误导。

### 5. `calibration.py`

- `make_paired_wbgt_table()` 支持 v0.6.4 long archive。
- 如果 prediction table 里没有 `station_id` 但有 `nearest_station_id`，会自动使用最近 WBGT station id 进行配对。

## 测试

运行：

```bat
pytest -q
```

结果：

```text
18 passed, 1 warning
```

warning 是 pandas 对大写 `H` 时间频率的未来弃用提醒，不影响运行。

## 推荐运行命令

```bat
python scripts\run_live_forecast_v06.py --mode sample
python scripts\archive_nea_observations.py --mode fixture --archive outputs\v06_4_1_fixture_archive_long.csv
pytest -q
```

live 模式：

```bat
python scripts\run_live_forecast_v06.py --mode live
python scripts\run_nea_api_schema_check.py --mode live
python scripts\archive_nea_observations.py --mode live
python scripts\plot_v06_hotspots.py
```

## 仍然保留的科学边界

v0.6.4.1 仍然是 workflow/calibration-ready prototype，不是 operational public-health warning system。关键限制包括：

1. Toa Payoh grid 仍是 sample/synthetic features，不是真实空间降尺度特征；
2. `tmrt_proxy_c` 仍然是简化 proxy，不是 SOLWEIG/UMEP；
3. `wbgt_proxy_c` 仍是 screening proxy，不是官方 WBGT；
4. calibration 需要多日 NEA WBGT archive，并覆盖至少 moderate WBGT regime；
5. 最近官方 WBGT station 只能作为 nearby calibration proxy，不能代表每个 street-level HDB cell。
