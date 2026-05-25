# v12 formal-hot-day SOLWEIG forcing QA

This summary documents meteorological forcing only. It does not validate local WBGT, run SOLWEIG, generate rasters, create hazard/risk maps, convert Tmrt to WBGT, or train a surrogate model.

- Input CSV: `data\calibration\v11\snapshots\v11_pairs_14d_formal_20260524_40419_v091.csv`
- Time column: `timestamp_sgt`
- Station: `S128`
- Selected date: `2026-05-10`
- Selection mode: `max_shortwave_then_wbgt`
- QA CSV: `outputs\v12_solweig_typology_pilot\formal_hotday_forcing\formal_hotday_forcing_QA.csv`

## Warnings
- None.

## Selected Hours

| hour_sgt | temperature_2m | relative_humidity_2m | wind_speed_10m | shortwave_radiation | Kdiff_written | Kdir_written | forcing_file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 13 | 32.1 | 63.0 | 7.4 | 900.0 | 139.0 | 761.0 | data\solweig\v12_formal_hotday_forcing\v12_formal_hotday_S128_h13.txt |
| 15 | 32.2 | 57.0 | 9.3 | 784.0 | 184.0 | 600.0 | data\solweig\v12_formal_hotday_forcing\v12_formal_hotday_S128_h15.txt |
