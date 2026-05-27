# OpenHeat System A A-L2.1a-S1 站点缓冲区空间源获取说明

生成日期：2026-05-27
决策状态：`PASS_FEATURE_TABLE`

## 1. 为什么上一轮 A-L2.1a 被阻塞

上一轮 A-L2.1a 的结论是 `BLOCKED_MISSING_SOURCES`。原因是当时可用的数据主要是 Toa Payoh AOI 或网格代理数据，不能代表全部 27 个 NEA WBGT 站点的站点本地缓冲区环境。因此这些 Toa Payoh-only 特征只能盘点，不能进入 27 站特征表。

## 2. 本轮使用的本地来源

- `osm_station_context_buildings`：buildings，7557 行，路径 `C:/OpenHeat-local/station_context_sources/raw/osm/osm_station_context_buildings.gpkg`
- `osm_station_context_green`：green，385 行，路径 `C:/OpenHeat-local/station_context_sources/raw/osm/osm_station_context_green.gpkg`
- `osm_station_context_landuse`：landuse，2349 行，路径 `C:/OpenHeat-local/station_context_sources/raw/osm/osm_station_context_landuse.gpkg`
- `osm_station_context_roads`：roads，20485 行，路径 `C:/OpenHeat-local/station_context_sources/raw/osm/osm_station_context_roads.gpkg`
- `osm_station_context_water`：water，270 行，路径 `C:/OpenHeat-local/station_context_sources/raw/osm/osm_station_context_water.gpkg`

## 3. 已形成全 27 站覆盖的特征组

buildings;green;landuse;roads;water

## 4. 仍不可用的特征组

无

## 5. CRS 与几何处理

站点坐标按 EPSG:4326 读取，并在计算缓冲区、长度和距离之前投影到 Singapore SVY21 EPSG:3414。本轮只写出紧凑的 CSV/Markdown 汇总，不把原始 OSM、data.gov.sg 或 OneMap 空间图层复制进仓库。

## 6. 关键假设

- CRS read from source metadata.
- Area fractions use deterministic grid sampling of source polygons within EPSG:3414 circular buffers; no clipped raw geometries are written.
- Road lengths use exact line-circle segment clipping in EPSG:3414.
- OSM landuse polygons are treated as partial context where polygons exist, not as a complete LCZ product.

## 7. 边界声明

- 本轮没有训练残差机器学习模型。
- 本轮没有提出站点上下文因果校正。
- 本轮没有生成站点校正 WBGT。
- 本轮没有生成本地 100 m WBGT。
- 本轮没有使用 official_wbgt_c、residual、obs_ge31、obs_ge33、System B 或 SOLWEIG 输出作为特征。
- `station_id` 只作为行键和元数据，不作为预测特征。

站点数量：27。
