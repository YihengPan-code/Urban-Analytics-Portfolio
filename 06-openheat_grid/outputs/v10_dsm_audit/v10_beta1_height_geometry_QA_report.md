# v10-beta.1 height / geometry correction QA report

Input canonical buildings: **5319**
Output height-QA canonical buildings: **5321**
Applied corrections: **2**
Null heights after correction: **0**

## Correction decisions applied

```text
      target_id manual_decision  old_height_m   new_height_m                status                                                                                                                                                   notes  n_split_polygons
v10_bldg_000001   height_adjust          85.3           30.0 applied_height_adjust Google Street View visual QA: adjacent high-rise labelled around 71m; this building appears less than half that height. Original 85.3m likely too high.               NaN
v10_bldg_000002   split_complex          93.7 split_geometry applied_split_complex           Block complex contains two high-rise towers and a low/mid-rise podium. Replace original uniform 93.7m footprint with manual split geometries.               3.0
```

## Height source counts after beta1 correction

```text
height_source
lu_default:RESIDENTIAL             2921
osm_levels_x_3m:levels_original    1266
height_m                            597
manual_missing_height                74
lu_default:COMMERCIAL                67
lu_default:EDUCATIONAL               66
lu_default:INDUSTRIAL                45
lu_default:PLACE OF WORSHIP          45
lu_default:CIVIC                     39
lu_default:TRANSPORT                 33
area_default:unknown_large           28
explicit:height_m_original           23
type_default_shelter                 23
manual_default_unknown_10m           20
area_default:unknown_normal          20
lu_default:UTILITY                   14
lu_default:PARK                      12
lu_default:SPORTS                     8
lu_default:HEALTH                     7
lu_default:HOTEL                      5
manual_split_height_beta1             3
area_default:unknown_small            3
manual_height_adjust_beta1            1
lu_default:HOSPITAL                   1
```

## Height statistics after beta1 correction

```text
count    5321.000000
mean       17.079628
std        15.890278
min         3.000000
25%        12.000000
50%        15.000000
75%        15.000000
max       133.000000
```

## Outputs

- height-QA canonical: `data\features_3d\v10\height_imputed\canonical_buildings_v10_height_reviewed_heightqa.geojson`
- split replaced originals: `data\features_3d\v10\manual_qa\split_replaced_originals_v10.geojson`
- applied corrections CSV: `outputs\v10_dsm_audit\v10_beta1_applied_height_geometry_corrections.csv`
