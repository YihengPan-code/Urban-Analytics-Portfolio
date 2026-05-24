# v0.6.1 到 v0.7 的优先级

v0.6.1 已经解决 live API、时区、schema、归档和 calibration framing。v0.7 不应继续堆 API，而应做真实 Toa Payoh spatial downscaling layer。

## v0.7 的第一优先级：真实 grid features

Open-Meteo 对 Toa Payoh 来说是背景气象，不提供街区内空间差异。v0.7 的核心就是构建 50–100 m grid features：

```text
building_density
mean_building_height
max_building_height
road_fraction
impervious_fraction
gvi_percent / ndvi / tree canopy proxy
svf_proxy
shade_fraction
park_distance_m
water_distance_m
elderly_proxy
outdoor_exposure_proxy
```

## 最小可行版本

1. 生成 Toa Payoh boundary。
2. 创建 100 m grid。
3. 接 URA building footprint。
4. 用 HDB max floor level / Open Buildings height proxy 估算高度。
5. 加 NParks parks / water distance。
6. 用 OSM roads 估算 road fraction。
7. 用 GVI 或 tree canopy proxy 加 pedestrian greenery layer。
8. 重新跑 v0.6.1 hotspot engine。

## Plymouth 数据怎么桥接

Plymouth 不做 Singapore calibration。但它可以作为 feature-prior justification：

- 你的 mobile monitoring 证明 GVI、wind exposure、radiant condition 在 walking-route scale 有明显空间梯度；
- 你的 dissertation 使用 120-s POI exposure window 处理 Tair/RH/Tg/wind/GVI，说明你理解 pedestrian-scale exposure 的测量逻辑；
- 因此，v0.7 选 GVI/SVF/shade/wind shelter 作为 downscaling features 是有经验基础的，不是拍脑袋。

## 不要做的事

- 不要直接做全 Toa Payoh 10 m SOLWEIG；
- 不要把 Open-Meteo 当作 50 m forecast；
- 不要把 WBGT proxy 当作 official WBGT；
- 不要在没有 archive/hindcast 的情况下声称 model is calibrated。
