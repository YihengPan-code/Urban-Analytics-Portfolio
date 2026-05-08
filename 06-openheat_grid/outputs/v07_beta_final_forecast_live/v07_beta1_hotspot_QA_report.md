# OpenHeat-ToaPayoh v0.7-beta.1 Hotspot QA Report

This report is generated from the v0.7-beta real-grid forecast outputs. It is a QA and interpretation aid, not a validation report.

## Input files

- `ranking`: `outputs\v07_beta_final_forecast_live\v06_live_hotspot_ranking.csv`
- `grid_csv`: `data\grid\toa_payoh_grid_v07_features_beta_final.csv`
- `event_windows`: `outputs\v07_beta_final_forecast_live\v06_live_event_windows.csv`
- `grid_geojson`: `data\grid\toa_payoh_grid_v07_features.geojson`

## Key diagnostics

```json
{
  "n_cells": 986,
  "svf_ge_0_98_count": 119,
  "svf_ge_0_98_share": 0.1206896551724138,
  "svf_ge_0_95_count": 267,
  "svf_ge_0_95_share": 0.27079107505070993,
  "svf_min": 0.3998163559515927,
  "svf_mean": 0.8621122774942264,
  "svf_median": 0.9145255263555581,
  "svf_max": 0.98,
  "shade_min": 0.04,
  "shade_mean": 0.25041362773331827,
  "shade_median": 0.23635849117364371,
  "shade_max": 0.6367218903462821,
  "shade_floorish_count": 11,
  "shade_floorish_share": 0.011156186612576065,
  "tree_canopy_zero_count": 817,
  "tree_canopy_zero_share": 0.8286004056795132,
  "impervious_mean": 0.4968321013646348,
  "impervious_median": 0.5312901334404415,
  "impervious_ge_0_95_share": 0.0030425963488843813,
  "impervious_old_mean": 0.8411047470236253,
  "impervious_old_median": 0.9446716919682039,
  "impervious_old_ge_0_95_share": 0.44523326572008115
}
```


## Event-window summary

```json
{
  "event_file_found": true,
  "n_event_hours": 96,
  "wbgt_alert_counts": {
    "low": 96
  },
  "utci_alert_counts": {
    "moderate": 49,
    "strong": 44,
    "very_strong": 3
  },
  "combined_alert_counts": {
    "watch": 49,
    "elevated": 44,
    "high": 3
  },
  "neighbourhood_alert_counts": {
    "watch": 49,
    "elevated": 44,
    "high": 3
  },
  "max_wbgt_proxy_c_max": 29.799700209407696,
  "p90_wbgt_proxy_c_max": 29.06388708665603,
  "max_utci_c_max": 39.6,
  "p90_utci_c_max": 38.1,
  "peak_utci_time": "2026-05-09 14:00:00+08:00",
  "peak_utci_value": 39.6,
  "peak_wbgt_time": "2026-05-09 14:00:00+08:00",
  "peak_wbgt_value": 29.799700209407696
}
```


## Hazard vs risk metrics

```json
{
  "spearman_rank_vs_hazard_rank": 0.9213637085866224,
  "top20_risk_hazard_overlap": 4
}
```


## Top 20 vs all cells

```
                           all_mean   top20_mean   all_median  top20_median
max_utci_c                37.179310    38.425000    37.100000     38.300000
mean_utci_c               31.002555    31.575885    30.998958     31.415104
max_wbgt_proxy_c          28.698445    29.218639    28.665013     29.101909
mean_wbgt_proxy_c         26.118422    26.454947    26.113227     26.351965
hazard_score               0.411329     0.662473     0.403812      0.652692
risk_priority_score        0.445216     0.672854     0.444766      0.668620
vulnerability_score        0.500507     0.662830     0.737830      0.737830
exposure_score             0.500507     0.731136     0.500507      0.699290
gvi_percent               10.132285     5.897309     8.516137      5.024511
svf                        0.862112     0.948295     0.914526      0.980000
shade_fraction             0.250414     0.126971     0.236358      0.126434
mean_building_height_m    17.303592    11.798323    17.770020     11.076480
max_building_height_m     15.474019    13.706978    13.200000     13.200000
tree_canopy_fraction       0.045834     0.011352     0.000000      0.000000
grass_fraction             0.013527     0.000000     0.000000      0.000000
ndvi_mean                  0.320857     0.239926     0.306094      0.231656
impervious_fraction        0.496832     0.710640     0.531290      0.675015
building_density           0.065906     0.021601     0.000000      0.000000
road_fraction              0.196654     0.523080     0.153869      0.444343
park_distance_m          410.579987   396.106037   360.736455    317.498414
large_park_distance_m   1601.160746  1361.499514  1536.020130   1473.815433
water_distance_m         339.160983   454.104455   298.133367    396.082758
```

## Interpretive flags

- **OK**: Top hotspots have higher peak UTCI than the grid average. (`all_mean=37.179`, `top20_mean=38.425`).
- **OK**: Top hotspots have higher peak WBGT proxy than the grid average. (`all_mean=28.698`, `top20_mean=29.219`).
- **OK**: Top hotspots have higher hazard score than the grid average. (`all_mean=0.411`, `top20_mean=0.662`).
- **OK**: Top hotspots have lower greenery proxy than the grid average. (`all_mean=10.132`, `top20_mean=5.897`).
- **OK**: Top hotspots have lower shade fraction than the grid average. (`all_mean=0.250`, `top20_mean=0.127`).
- **OK**: Top hotspots have higher SVF / sky exposure than the grid average. (`all_mean=0.862`, `top20_mean=0.948`).
- **OK**: Top hotspots have higher road fraction than the grid average. (`all_mean=0.197`, `top20_mean=0.523`).
- **OK**: Top hotspots have lower tree canopy fraction than the grid average. (`all_mean=0.046`, `top20_mean=0.011`).
- **OK**: Top hotspots have lower NDVI than the grid average. (`all_mean=0.321`, `top20_mean=0.240`).
- **OK**: SVF upper-end saturation is not severe (`svf>=0.98` share 12.1%).
- **OK**: Impervious fraction was revised from old beta mean `0.841` to `0.497`; keep the revised file as the beta-final grid if ranking remains stable.

## Top 20 ranking table

```
    rank  cell_id  max_utci_c  max_wbgt_proxy_c  hazard_score  risk_priority_score  gvi_percent       svf  shade_fraction  mean_building_height_m  tree_canopy_fraction  ndvi_mean  impervious_fraction  building_density  road_fraction  park_distance_m land_use_hint
0      1  TP_0581        39.1         29.477119      0.707233             0.714981    13.622622  0.980000        0.045650                4.048391              0.227044   0.266283             0.671122          0.000000       0.796332       328.878896   residential
1      2  TP_0448        38.5         29.290944      0.684935             0.701004     6.044066  0.967265        0.145095               17.558604              0.000000   0.254313             0.726297          0.000000       0.553328       963.855295   residential
2      3  TP_0726        38.3         29.175427      0.670313             0.688743     0.448997  0.956543        0.137789               16.910247              0.000000   0.129978             0.704436          0.000000       0.416354       333.467957   residential
3      4  TP_0633        38.3         29.122179      0.656254             0.682765    13.029490  0.980000        0.126997                9.916504              0.000000   0.409544             0.647114          0.000000       0.511387       335.388135   residential
4      5  TP_0030        38.4         29.159818      0.667086             0.682026     3.041938  0.980000        0.113469               10.529288              0.000000   0.187599             0.651020          0.000000       0.352739       373.558722   residential
5      6  TP_0662        38.4         29.125061      0.660412             0.678954     5.300976  0.980000        0.108280                8.711604              0.000000   0.237799             0.512497          0.000000       0.365258       306.036353   residential
6      7  TP_0410        38.1         29.130994      0.656656             0.678602     8.281244  0.883430        0.152181                7.366407              0.000000   0.304028             0.662401          0.079335       0.383488       823.706658   residential
7      8  TP_0923        38.3         29.081638      0.649130             0.676674     4.414123  0.980000        0.104539               10.122155              0.000000   0.218092             0.678909          0.000000       0.431386       112.797568   residential
8      9  TP_0827        38.2         29.065839      0.642262             0.672112     2.759162  0.960106        0.142027               16.303660              0.000000   0.181315             0.688992          0.000000       0.423970       171.163856   residential
9     10  TP_0849        38.3         29.061516      0.643401             0.670841     6.627702  0.980000        0.115868                9.424704              0.000000   0.267282             0.637169          0.000000       0.384800       204.535824   residential
10    11  TP_0353        37.7         29.068576      0.630593             0.666399    11.712641  0.820259        0.219265               13.735559              0.000000   0.380281             0.707271          0.122538       0.487214       702.854105   residential
11    12  TP_0732        38.2         29.028677      0.632974             0.666201     6.176399  0.980000        0.125872               11.880751              0.000000   0.257253             0.658625          0.000000       0.420190       130.108090   residential
12    13  TP_0468        38.0         29.051267      0.629639             0.665351    12.893457  0.963491        0.179175               16.292476              0.000000   0.406521             0.621204          0.000000       0.457300       712.100877   residential
13    14  TP_0778        38.0         29.027155      0.624774             0.662486     4.748045  0.954938        0.158300               18.259366              0.000000   0.225512             0.691428          0.000000       0.461991       152.356514   residential
14    15  TP_0638        38.2         29.057118      0.639389             0.661355     4.374992  0.974408        0.128012               11.097286              0.000000   0.217222             0.623202          0.000000       0.319320       290.789939   residential
15    16  TP_0088        39.6         29.799700      0.734748             0.658571     0.000000  0.980000        0.040000               11.055674              0.000000   0.053939             0.940093          0.000000       0.903503       500.319697     transport
16    17  TP_0454        37.4         29.040812      0.616736             0.658112     9.506857  0.705460        0.313614               20.444470              0.000000   0.331263             0.788172          0.230156       0.504635       789.608497   residential
17    18  TP_0171        39.6         29.783035      0.731060             0.657730     3.166758  0.980000        0.040000                0.042853              0.000000   0.190372             0.973610          0.000000       1.000000       306.117931     transport
18    19  TP_0575        39.6         29.775225      0.730493             0.657378     0.775425  0.980000        0.040000               13.368258              0.000000   0.137232             0.993538          0.000000       1.000000       221.899980     transport
19    20  TP_0986        38.3         29.050673      0.641364             0.656799     1.021276  0.980000        0.103281                8.898206              0.000000   0.142695             0.635695          0.000000       0.288411       162.575854   residential
```

## Recommended interpretation

- Treat this output as a **screening-level hotspot prioritisation** based on forecast meteorology and real 100 m grid features.
- Use `hazard_score` to discuss physically hotter cells; use `risk_priority_score` only with caution until v0.7.1 adds stronger elderly/exposure proxies.
- If top hotspots are high-SVF, low-shade, low-greenery and road-dominated, the ranking is directionally plausible.
- If top hotspots fall in water bodies or dense green interiors during map QA, revisit water/greenery/shade feature scaling.
- Replace proxy SVF/shade with UMEP-derived values in v0.8/v0.9.
