# v1.0-alpha.3 manual QA application report

Reviewed canonical buildings: **5319**
Overhead candidates: **1**
Applied decisions: **95**
Manual missing buildings appended: **74**
Conflict candidates merged: **20**

## Height source counts
```text
height_source
lu_default:RESIDENTIAL             2921
osm_levels_x_3m:levels_original    1266
height_m                            599
manual_missing_height                74
lu_default:COMMERCIAL                67
lu_default:EDUCATIONAL               66
lu_default:PLACE OF WORSHIP          45
lu_default:INDUSTRIAL                45
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
area_default:unknown_small            3
lu_default:HOSPITAL                   1
```

## Height confidence counts
```text
height_confidence
medium         3269
medium_high    1289
high            599
low              87
medium_low       75
```

## Notes
- `v10_bldg_000690` is moved to overhead candidates by default.
- Top conflict targets can be merged automatically only because the user manually confirmed they are real buildings.
- Manual missing buildings are appended as medium/low-confidence manual-digitised buildings.
- This reviewed layer is the recommended input for v10-beta basic morphology recomputation.