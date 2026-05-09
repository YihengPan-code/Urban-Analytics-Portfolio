# OpenHeat v0.9-alpha archive QA report

Archive CSV: `data\archive\nea_realtime_observations.csv`
Rows: **7130**
Archive runs: **96**
Time span SGT: **2026-05-07 02:00:00+08:00 → 2026-05-08 02:03:00+08:00**

## Variable summary
         api_name                  variable  rows  stations  timestamps  missing_value_rows  min_value  mean_value  max_value
  air_temperature         air_temperature_c  1490        16          96                   0  24.700000   28.938389  33.900000
relative_humidity relative_humidity_percent  1490        16          96                   0  55.600000   82.378389 100.000000
             wbgt           official_wbgt_c  2565        27          95                   1  23.500000   27.380343  34.000000
       wind_speed             wind_speed_ms  1585        17          96                   0   0.154333    1.382248   5.813217

## WBGT category counts
category  count
     Low   2296
Moderate    258
    High     10
     NaN      1

## Nearest WBGT stations to Toa Payoh centre
station_id           station_name  distance_to_toapayoh_center_m  wbgt_min  wbgt_mean  wbgt_max  moderate_count  high_count
      S128          Bishan Street                    2403.154131      24.4  27.622105      34.0              20           2
      S145   MacRitchie Reservoir                    2815.201768      24.3  26.918947      31.7               9           0
      S127           Stadium Road                    3860.746423      25.5  28.054737      32.4              17           0
      S150             Evans Road                    4485.957245      24.5  27.018947      30.9               0           0
      S144 Upper Pickering Street                    5474.749574      25.6  27.804211      32.2               8           0
      S141   Yio Chu Kang Stadium                    5557.366048      24.4  27.403158      33.0              11           1
      S147         Marina Barrage                    6144.380512      25.0  27.688421      32.3              19           0
      S187      Bukit Timah(West)                    6421.548072      24.4  27.304211      32.5              15           0

## Focus stations
station_id         station_name  distance_to_toapayoh_center_m  wbgt_min  wbgt_mean  wbgt_max  moderate_count  high_count
      S128        Bishan Street                    2403.154131      24.4  27.622105      34.0              20           2
      S145 MacRitchie Reservoir                    2815.201768      24.3  26.918947      31.7               9           0
      S127         Stadium Road                    3860.746423      25.5  28.054737      32.4              17           0

## Interpretation notes
- This archive is suitable for v0.9-alpha QA and paired-calibration pipeline testing.
- A 24-hour archive is not sufficient for robust ML residual learning; use it as a pilot/smoke test.
- Official WBGT is station-level and should not be interpreted as street-level Toa Payoh validation.