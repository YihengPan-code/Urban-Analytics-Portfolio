# v1.0-alpha.1 height imputation QA

Buildings: **5226**
Null heights: **0**

## Height source counts
```text
                  height_source    n
         lu_default:RESIDENTIAL 2921
osm_levels_x_3m:levels_original 1266
                       height_m  599
          lu_default:COMMERCIAL   67
         lu_default:EDUCATIONAL   66
          lu_default:INDUSTRIAL   45
    lu_default:PLACE OF WORSHIP   45
               lu_default:CIVIC   39
           lu_default:TRANSPORT   33
     area_default:unknown_large   28
           type_default_shelter   24
     explicit:height_m_original   23
    area_default:unknown_normal   20
             lu_default:UTILITY   14
                lu_default:PARK   12
              lu_default:SPORTS    8
              lu_default:HEALTH    7
               lu_default:HOTEL    5
     area_default:unknown_small    3
            lu_default:HOSPITAL    1
```

## Height confidence counts
```text
height_confidence    n
           medium 3263
      medium_high 1289
             high  599
              low   51
       medium_low   24
```

## Height statistics
```text
count    5226.000000
mean       17.183065
std        16.001168
min         3.000000
25%        12.000000
50%        15.000000
75%        15.000000
max       133.000000
```

## Large low-confidence buildings
```text
    building_id source_name      area_m2  height_m              height_source          lu_desc_v10                          height_warning
v10_bldg_000690         osm 19921.192687       4.0       type_default_shelter TRANSPORT FACILITIES possible_shelter_not_ground_up_building
v10_bldg_000712         osm  5750.200944      12.0 area_default:unknown_large         RESERVE SITE      manual_review_large_unknown_height
v10_bldg_000714         osm  5484.180893      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000731         osm  3981.459609      12.0 area_default:unknown_large         RESERVE SITE      manual_review_large_unknown_height
v10_bldg_000732         osm  3977.432409      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000746         osm  3284.928265      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000748         osm  3269.865110      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000749         osm  3262.140992      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000754         osm  3019.680779      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000764         osm  2806.829500      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000769         osm  2699.611360      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000775         osm  2623.729075      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000782         osm  2564.739007      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000786         osm  2502.981552      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000814         osm  2100.478100      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000819         osm  2043.144634      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000837         osm  1875.196694      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000838         osm  1857.440954      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000845         osm  1832.206233      12.0 area_default:unknown_large         RESERVE SITE      manual_review_large_unknown_height
v10_bldg_000849         osm  1787.949047      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000872         osm  1608.156181      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000877         osm  1561.039020      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000879         osm  1550.556949      12.0 area_default:unknown_large         RESERVE SITE      manual_review_large_unknown_height
v10_bldg_000885         osm  1523.360348      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000935         osm  1255.339716      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000941         osm  1236.903241      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_000947         osm  1215.690738      12.0 area_default:unknown_large         RESERVE SITE      manual_review_large_unknown_height
v10_bldg_000949         osm  1212.129035      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
v10_bldg_001008         osm  1023.730976      12.0 area_default:unknown_large           BUSINESS 1      manual_review_large_unknown_height
```

## Notes
- Duplicate OSM height / level tags promoted during deduplication can now be used here.
- Large low-confidence buildings should be manually inspected before UMEP/SOLWEIG reruns.