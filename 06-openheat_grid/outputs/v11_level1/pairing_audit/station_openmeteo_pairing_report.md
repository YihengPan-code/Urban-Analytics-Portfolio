# Station x Open-Meteo Pairing Audit

Generated: 2026-05-25

## Inputs

- Primary paired input: `outputs/v11_beta_formal/diagnostics_inputs/v11_pairs_14d_formal_20260524_40419_v091_diag.csv`
- Hourly aggregation input: `data/calibration/v11/v11_station_weather_pairs_hourly.csv`

## Coverage

- Stations in mapping: 27
- Rows in primary input: 40419
- Stations sharing an Open-Meteo coordinate with another station: 0
- All stations accidentally share identical forcing at every multi-station timestamp: no

## Time Alignment And Aggregation

input_label,input_file,n_rows,n_stations,timestamp_sgt_nonnull,timestamp_sgt_min_sgt,timestamp_sgt_max_sgt,timestamp_sgt_n_unique,timestamp_utc_nonnull,timestamp_utc_min_sgt,timestamp_utc_max_sgt,timestamp_utc_n_unique,valid_time_sgt_nonnull,valid_time_sgt_min_sgt,valid_time_sgt_max_sgt,valid_time_sgt_n_unique,valid_time_sgt_hour_nonnull,valid_time_sgt_hour_min_sgt,valid_time_sgt_hour_max_sgt,valid_time_sgt_hour_n_unique,timestamp_sgt_vs_utc_abs_delta_min_median,timestamp_sgt_vs_utc_abs_delta_min_max,timestamp_sgt_vs_utc_aligned_zero_delta_rows,unique_hours,unique_station_hours,duplicate_station_hour_rows,hour_only_grouping_suspect,station_hour_grouping_expected_rows_if_hourly,hour_bucket_nonnull,hour_bucket_min_sgt,hour_bucket_max_sgt,hour_bucket_n_unique
primary,outputs/v11_beta_formal/diagnostics_inputs/v11_pairs_14d_formal_20260524_40419_v091_diag.csv,40419,27,40419,2026-05-07 02:00:00+08:00,2026-05-24 20:40:03+08:00,1497,40419.0,2026-05-07 02:00:00+08:00,2026-05-24 20:40:03+08:00,1497.0,40419.0,2026-05-07 02:00:00+08:00,2026-05-24 20:00:00+08:00,388.0,40419.0,2026-05-07 02:00:00+08:00,2026-05-24 20:00:00+08:00,388.0,0.0,0.0,40419.0,388,10476,29943,False,10476,,,,
hourly,data/calibration/v11/v11_station_weather_pairs_hourly.csv,1674,27,1674,2026-05-07 02:00:00+08:00,2026-05-11 04:00:00+08:00,62,,,,,,,,,,,,,,,,62,1674,0,False,1674,1674.0,2026-05-07 02:00:00+08:00,2026-05-11 04:00:00+08:00,62.0


## Same-Timestamp Spatial Variation Preview

timestamp_key,n_stations,forcing_cluster_count,largest_forcing_cluster_station_count,temperature_2m_n_unique,relative_humidity_2m_n_unique,wind_speed_10m_n_unique,shortwave_radiation_n_unique,wbgt_proxy_v09_c_n_unique,all_available_forcing_identical
2026-05-07 02:00:00+0800,27,13,20,11,8,7,1,13,False
2026-05-07 03:00:00+0800,27,12,20,11,7,9,1,12,False
2026-05-07 04:00:00+0800,27,13,16,11,8,9,1,13,False
2026-05-07 05:00:00+0800,27,11,20,9,6,10,1,10,False
2026-05-07 06:00:00+0800,27,12,20,11,6,10,1,12,False
2026-05-07 07:00:00+0800,27,11,20,10,7,11,1,11,False
2026-05-07 08:00:00+0800,27,12,20,10,8,9,6,12,False
2026-05-07 09:00:00+0800,27,11,20,8,9,11,10,11,False
2026-05-07 10:00:00+0800,27,13,20,6,6,10,11,13,False
2026-05-07 11:00:00+0800,27,12,20,7,5,9,10,12,False
2026-05-07 12:00:00+0800,27,13,20,10,7,10,10,13,False
2026-05-07 13:00:00+0800,27,13,20,12,8,10,10,13,False
2026-05-07 14:00:00+0800,27,12,20,7,6,10,11,12,False
2026-05-07 15:00:00+0800,27,13,20,10,8,10,11,13,False
2026-05-07 16:00:00+0800,27,13,20,9,7,10,10,13,False
2026-05-07 17:00:00+0800,27,13,20,8,6,9,11,13,False
2026-05-07 18:00:00+0800,27,11,20,6,5,9,10,11,False
2026-05-07 19:00:00+0800,27,11,20,7,7,10,9,11,False
2026-05-07 20:00:00+0800,27,12,20,10,8,9,1,12,False
2026-05-07 21:00:00+0800,27,12,15,11,8,10,1,12,False


## Blocker Status

- No hard blocker found for proceeding to Level 1 reproduction.

## Caveats

- This audit checks station-context forcing pairing and temporal grouping only; it does not validate local WBGT prediction.
- Duplicate forcing clusters are expected when Open-Meteo returns the same rounded values for nearby stations or low-variation hours; they are flagged for review rather than treated as automatic failure.
