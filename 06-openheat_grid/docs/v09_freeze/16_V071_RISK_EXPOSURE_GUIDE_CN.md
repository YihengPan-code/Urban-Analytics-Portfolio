# OpenHeat-ToaPayoh v0.7.1 风险/暴露层指南

## 版本目标

v0.7-beta 已经回答了：

> 哪些 100 m grid cell 的 screening-level UTCI/WBGT heat hazard 更高？

v0.7.1 要回答的是：

> 哪些 heat-hazard cells 同时叠加了更高的居民脆弱性和公共户外暴露潜力，因此更值得优先干预？

因此 v0.7.1 不修改 UTCI/WBGT forecast engine，也不试图做真实人流模型。它新增一层静态 open-data risk/exposure proxy。

## 新增文件

```text
configs/v071_risk_exposure_config.example.json
scripts/v071_download_risk_exposure_data.py
scripts/v071_build_risk_exposure_features.py
scripts/v071_apply_risk_to_forecast.py
scripts/v071_run_full_pipeline.py
docs/16_V071_RISK_EXPOSURE_GUIDE_CN.md
```

## 数据源

v0.7.1 主模型使用这些开放数据：

| 维度 | 数据 | 用途 |
|---|---|---|
| Demographic vulnerability | SingStat Census 2020 subzone age-sex population | elderly_pct_65plus, children_pct_under5 |
| Boundary | URA MP19 Subzone Boundary No Sea | 面积加权把 subzone demographic 分配到 100 m grid |
| Outdoor exposure | LTA Bus Stops | 公交等候/换乘暴露潜力 |
| Outdoor exposure | LTA MRT Station Exits | 站口行人暴露潜力 |
| Outdoor exposure | SportSG Sport Facilities | 户外/运动活动暴露潜力 |
| Node vulnerability | NEA Hawker Centres | 老年人/居民聚集节点 proxy |
| Node vulnerability | MOH Eldercare Services | 高脆弱群体服务节点 proxy |
| Node vulnerability | ECDA Pre-Schools | 儿童脆弱性节点 proxy |

Hawker/eldercare/preschool 不被当作 direct outdoor exposure，而是 vulnerable-congregation nodes。

## 安装依赖

你已经为 v0.7 安装了 geospatial 依赖，一般不用新增。如果缺包：

```bat
conda install -c conda-forge geopandas shapely pyproj pyogrio pandas numpy requests tabulate
```

`tabulate` 用于生成 markdown 表格；如果没有，`pandas.to_markdown()` 会报错。

## 运行步骤

### 1. 确认 beta-final grid 和 forecast 存在

需要已有：

```text
data/grid/toa_payoh_grid_v07_features_beta_final.csv
data/grid/toa_payoh_grid_v07_features.geojson
outputs/v07_beta_final_forecast_live/v06_live_hotspot_ranking.csv
```

如果还没有 forecast，先运行：

```bat
python scripts\run_live_forecast_v06.py --mode live --grid data\grid\toa_payoh_grid_v07_features_beta_final.csv --out-dir outputs\v07_beta_final_forecast_live
```

### 2. 下载 v0.7.1 数据

```bat
python scripts\v071_download_risk_exposure_data.py
```

如果 MOH eldercare 自动下载失败，手动从 data.gov.sg 的 Eldercare Services 页面下载 GEOJSON，保存为：

```text
data/raw/poi/moh_eldercare_services.geojson
```

Eldercare 是 v0.7.1-alpha 的可选增强项；没有它也能跑。

### 3. 构建 risk/exposure grid features

```bat
python scripts\v071_build_risk_exposure_features.py --config configs\v071_risk_exposure_config.example.json
```

输出：

```text
data/grid/toa_payoh_grid_v07_features_beta_final_v071_risk.csv
data/features/v071/v071_subzone_demographic_vulnerability.csv
data/features/v071/v071_node_scores_raw.csv
data/features/v071/v071_risk_exposure_features.csv
data/features/v071/v071_public_nodes_clean.geojson
outputs/v071_risk_exposure/v071_grid_risk_exposure_features.geojson
outputs/v071_risk_exposure/v071_risk_exposure_QA_report.md
```

### 4. 把 risk/exposure features 应用到 hotspot ranking

```bat
python scripts\v071_apply_risk_to_forecast.py --config configs\v071_risk_exposure_config.example.json --forecast-dir outputs\v07_beta_final_forecast_live
```

输出：

```text
outputs/v071_risk_exposure/v071_risk_hotspot_ranking.csv
outputs/v071_risk_exposure/v071_risk_hotspot_ranking.geojson
outputs/v071_risk_exposure/v071_hazard_vs_risk_comparison.csv
outputs/v071_risk_exposure/v071_hourly_grid_heatstress_forecast_with_risk.csv
outputs/v071_risk_exposure/v071_risk_ranking_QA_report.md
```

### 5. 一键运行

确认数据已下载后：

```bat
python scripts\v071_run_full_pipeline.py --config configs\v071_risk_exposure_config.example.json --forecast-dir outputs\v07_beta_final_forecast_live
```

如果还没下载数据：

```bat
python scripts\v071_run_full_pipeline.py --download --config configs\v071_risk_exposure_config.example.json --forecast-dir outputs\v07_beta_final_forecast_live
```

## 快速检查

### 查看 v0.7.1 risk top 20

```bat
python -c "import pandas as pd; df=pd.read_csv('outputs/v071_risk_exposure/v071_risk_hotspot_ranking.csv'); print(df.sort_values('risk_priority_score_v071', ascending=False)[['risk_rank_v071','cell_id','rank','hazard_score','risk_priority_score_v071','vulnerability_score_v071','outdoor_exposure_score_v071','elderly_pct_65plus','dominant_subzone']].head(20).to_string())"
```

### 比较 hazard top 20 和 risk top 20

```bat
python -c "import pandas as pd; df=pd.read_csv('outputs/v071_risk_exposure/v071_risk_hotspot_ranking.csv'); h=set(df.nsmallest(20,'rank')['cell_id']); r=set(df.nlargest(20,'risk_priority_score_v071')['cell_id']); print('Top20 overlap hazard vs v071 risk:', len(h&r), '/ 20'); print('risk-only cells:', sorted(r-h)[:20]); print('hazard-only cells:', sorted(h-r)[:20])"
```

### QGIS 查看

打开：

```text
outputs/v071_risk_exposure/v071_risk_hotspot_ranking.geojson
```

建议分别按以下字段上色：

```text
rank
risk_rank_v071
hazard_score
vulnerability_score_v071
outdoor_exposure_score_v071
elderly_pct_65plus
```

## 方法说明

### Demographic vulnerability

```text
elderly_pct_65plus = population age 65+ / total resident population
children_pct_under5 = population age 0–4 / total resident population
```

Census 数据是 subzone 粒度。v0.7.1 使用 grid/subzone 面积交叠加权分配到 100 m grid，而不是简单 centroid join。

```text
demographic_vulnerability_raw = 0.75 × elderly_pct_65plus + 0.25 × children_pct_under5
```

随后用 robust min-max scaling 转成 0–1。

### Node vulnerability

使用 distance-decay：

```text
score(cell) = Σ weight × exp(-distance_m / decay_m)
```

默认：

```text
eldercare: 1.5, decay 250 m
hawker: 0.8, decay 250 m
preschool: 0.5, decay 150 m
```

### Outdoor exposure

同样使用 distance-decay：

```text
bus_stop: 1.0, decay 150 m
mrt_exit: 2.0, decay 250 m
sport_facility: 0.7, decay 200 m
```

它代表 static public outdoor exposure potential，不是实际人流量。

### v0.7.1 risk priority

```text
vulnerability_score_v071 =
  0.70 × demographic_vulnerability_score
+ 0.30 × node_vulnerability_score
```

```text
risk_priority_score_v071 =
  0.60 × hazard_score
+ 0.25 × vulnerability_score_v071
+ 0.15 × outdoor_exposure_score_v071
```

同时输出 equity sensitivity score：

```text
risk_priority_score_v071_equity =
  0.50 × hazard_score
+ 0.35 × vulnerability_score_v071
+ 0.15 × outdoor_exposure_score_v071
```

## 解释边界

v0.7.1 可以说：

> This identifies static risk-priority cells where modelled heat hazard overlaps with residential demographic vulnerability and public outdoor exposure potential.

不要说：

> This estimates actual exposed elderly pedestrians during peak heat hours.

原因：

1. subzone elderly 是居住人口 proxy，不是 activity-space exposure；
2. outdoor node score 是公共节点潜力，不是实时人流；
3. v0.7.1 没有 time-of-day weighting；
4. hawker/eldercare/preschool 是 vulnerability nodes，不是直接户外暴露。 

