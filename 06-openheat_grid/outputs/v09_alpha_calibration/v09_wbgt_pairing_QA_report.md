# OpenHeat v0.9-alpha WBGT station-pairing QA report

Pairs CSV: `data\calibration\v09_wbgt_station_pairs.csv`
Rows: **2564**
Stations: **27**
Dates: **2026-05-07 → 2026-05-08**

## Raw physics WBGT proxy baseline
   n  bias_pred_minus_obs      mae     rmse  p90_abs_error
2564             -1.14036 1.324787 1.949099       3.588358

## Morphology representativeness
morphology_representativeness
regional_distance_not_representative    22
nearby_grid_proxy                        3
local_grid_proxy                         2

## Best/worst station metrics preview
station_id            station_name  n      mae     rmse  bias_pred_minus_obs  official_wbgt_max  moderate_obs  high_obs  nearest_grid_distance_m        morphology_representativeness
      S148          Pasir Ris Walk 95 0.774654 1.295742            -0.589111               31.1             1         0             11139.912859 regional_distance_not_representative
      S124 Upper Changi Road North 95 0.805540 1.206101            -0.573258               30.4             0         0             13078.252030 regional_distance_not_representative
      S149           Tampines Walk 95 1.004191 1.569444            -0.721742               31.6             6         0              8182.296726 regional_distance_not_representative
      S140   Choa Chu Kang Stadium 95 1.030138 1.464530            -0.700878               31.0             2         0             10762.214795 regional_distance_not_representative
      S145    MacRitchie Reservoir 95 1.072756 1.624998            -0.999955               31.7             9         0               684.708689                     local_grid_proxy
      S150              Evans Road 95 1.099286 1.564954            -0.745034               30.9             0         0              2322.116185                    nearby_grid_proxy
      S180     Taman Jurong Greens 95 1.193190 1.780718            -1.031405               31.6             8         0             13537.003252 regional_distance_not_representative
      S146             Jalan Bahar 95 1.198310 1.559257            -0.625669               31.2             1         0             16451.394926 regional_distance_not_representative
      S153   Bukit Batok Street 22 95 1.262562 1.756939            -1.210352               31.5             5         0             10113.869961 regional_distance_not_representative
      S184    Sengkang East Avenue 95 1.277272 1.820759            -1.263828               32.5             8         0              4745.580002 regional_distance_not_representative

## Interpretation notes
- This paired dataset is a v0.9-alpha pilot calibration table, not a final ML training set.
- `wbgt_proxy_physics` is a screening-level weather-only WBGT proxy; official WBGT residuals are suitable for baseline calibration diagnostics.
- Station morphology joined from the Toa Payoh v0.8 grid is only meaningful for nearby stations; distant stations are flagged as `regional_distance_not_representative`.