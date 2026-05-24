# v10-gamma forecast finalisation QA report

Ranking rows: **986**

Output rows: **986**

CSV: `outputs\v10_gamma_forecast_live\v10_gamma_hotspot_ranking_with_grid_features.csv`

GeoJSON: `outputs\v10_gamma_forecast_live\v10_gamma_hotspot_ranking_with_grid_features.geojson`

## Missing expected explanatory columns from grid

```text
None
```

## GeoJSON diagnostics

```text
missing_geometry_rows: 0
```

## Feature summaries

```text
       max_utci_c  max_wbgt_proxy_c  hazard_score  risk_priority_score         svf  shade_fraction  building_density
count  985.000000        985.000000    986.000000           986.000000  985.000000      986.000000        986.000000
mean    36.037413         28.491193      0.391340             0.432823    0.380031        0.465755          0.214805
std      2.558402          0.516604      0.193729             0.134825    0.215978        0.245803          0.156040
min     30.530669         26.701330      0.000000             0.096915    0.010397        0.000000          0.000000
25%     34.131714         28.157565      0.229025             0.334098    0.222008        0.264048          0.088000
50%     35.686764         28.491213      0.393857             0.437345    0.363252        0.464767          0.204400
75%     37.935802         28.874268      0.557564             0.536184    0.530007        0.643978          0.316300
max     42.945945         29.908888      0.754081             0.704399    0.948570        0.978518          1.000000
```
