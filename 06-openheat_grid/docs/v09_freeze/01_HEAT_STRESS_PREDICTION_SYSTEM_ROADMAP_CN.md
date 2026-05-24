# OpenHeat-ToaPayoh 未来版本路线图：从作品集原型到 heat-stress prediction system

## 0. 项目重新定位

你现在真正要做的不是 Plymouth GEMA 的延伸分析，而是一个 **heat stress forecasting and hotspot-prioritisation system**：

> 输入未来天气预报、城市形态、绿量/遮阴、暴露与脆弱性，输出未来 24–96 小时 neighbourhood 内哪些 grid/POI 会出现最高 UTCI/WBGT heat stress。

Plymouth dissertation 已经证明你具备 mobile monitoring + GEMA + PET/GVI 的实测研究能力。这个系统应该把它作为背景资产，而不是继续重复 wellbeing 分析。

---

## 1. 预测目标应该是什么？

### 主目标

每个 grid cell / POI / route segment 在未来每小时的：

- `UTCI_c`
- `WBGT_proxy_c` 或 calibrated `WBGT_c`
- heat-stress category
- high-risk hours
- maximum heat-stress time window
- hotspot rank

### 不建议第一版就预测

- 真实健康结局，如中暑人数；
- 官方级 WBGT；
- 每条街 CFD 风场；
- 全新加坡 10 m 级 UTCI。

### 推荐第一版表述

> This prototype predicts relative neighbourhood-scale heat-stress hotspots and event timing for decision support. It requires further calibration before operational public-health use.

---

## 2. 最稳技术架构

### A. Forecast layer

- Open-Meteo / ECMWF / GFS / ICON 等背景预报；
- hourly temperature, RH, wind, radiation, cloud cover；
- 未来 24–96 小时。

### B. Urban downscaling layer

对每个 grid 加城市形态修正：

- building density;
- building height / HDB max floor;
- SVF;
- shade fraction / solar exposure;
- GVI / NDVI / tree canopy;
- road/impervious fraction;
- park/water distance.

### C. Thermal-index layer

- UTCI：用于空间连续 heat stress map；
- WBGT：用于对齐 Singapore official heat stress advisory；
- PET：作为学术补充，不作为预警主指标。

### D. Hotspot layer

每个 grid 计算：

```text
hazard_score = intensity + duration + threshold exceedance
risk_priority = hazard_score + vulnerability + outdoor exposure
```

输出 top hotspots。

---

## 3. 版本路线

### v0.5 — Heat forecast engine skeleton

目标：用 sample forecast + sample Toa Payoh grid 跑通预测链。

交付：

- hourly grid heat-stress forecast;
- hotspot ranking;
- event window table;
- README + model limitation。

### v0.6 — Live data ingestion

接入：

- Open-Meteo live forecast；
- data.gov.sg NEA realtime weather readings；
- data.gov.sg official WBGT observations。

验证：

- forecast vs observed T/RH/wind；
- WBGT proxy vs official WBGT；
- bias correction。

### v0.7 — Real Toa Payoh spatial features

加入真实数据：

- URA building footprints；
- HDB property information / max floor level；
- NParks parks；
- OSM/OneMap roads and POIs；
- GVI or street-view greenery sample。

输出 50–100 m grid features。

### v0.8 — Hindcast and spatial ML

训练目标：

```text
local_heat_stress = background_forecast + urban_morphology_offset
```

推荐模型：

- GAM baseline;
- Random Forest / XGBoost;
- spatial block CV;
- temporal event split CV;
- SHAP / permutation importance。

### v0.9 — SOLWEIG/UMEP nested microclimate module

只对 top hotspot neighbourhood 做 10–20 m 级 Tmrt / shade simulation。

目标：

- baseline vs tree/shade/cool-roof scenarios；
- strongest UTCI reduction area；
- design intervention priority。

### v1.0 — Portfolio-ready dashboard

Streamlit dashboard：

- forecast map；
- event timeline；
- top hotspots；
- vulnerable POIs；
- scenario comparison；
- validation panel；
- uncertainty panel。

---

## 4. 核心验证策略

### 不能用 Plymouth 验证 Singapore 绝对热风险

Plymouth 是 temperate winter walking context，不是 tropical heatwave context。

### 应该这样用

- Plymouth：证明你会做 pedestrian-scale field measurement and sensor-to-index workflow；
- Singapore official WBGT：用于目标城市校准；
- NEA station data：用于 forecast nowcast validation；
- satellite LST / LCZ：用于 hotspot spatial plausibility check；
- future field campaign：用于 Toa Payoh local validation。

---

## 5. 作品集主标题

**OpenHeat-ToaPayoh: An open-data heat-stress forecast and hotspot-prioritisation prototype for a high-density tropical neighbourhood**

副标题：

**From mobile monitoring experience to operational-style UTCI/WBGT decision support**
