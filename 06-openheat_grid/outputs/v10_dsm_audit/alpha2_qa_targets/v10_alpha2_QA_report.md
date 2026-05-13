# v1.0-alpha.2 manual QA target report

This report prioritises manual QA targets before v10 morphology/ranking rerun.

## Inputs
- `canonical_buildings_height`: `data/features_3d/v10/height_imputed/canonical_buildings_v10_height.geojson`
- `canonical_conflicts`: `data/features_3d/v10/canonical/canonical_buildings_v10_conflicts.geojson`
- `grid_geojson`: `data/grid/toa_payoh_grid_v07_features.geojson`
- `v09_tiles_buffered`: `data/solweig/v09_tiles_overhead_aware/v09_solweig_tiles_overhead_aware_buffered.geojson`
- `v08_risk_scenario_geojson`: `outputs/v08_umep_with_veg_forecast_live/risk_scenarios/v08_risk_scenario_rankings.geojson`
- `per_cell_completeness`: `outputs/v10_dsm_audit/v10_building_completeness_per_cell.csv`
- `per_tile_completeness`: `outputs/v10_dsm_audit/v10_building_completeness_per_tile.csv`
- `negative_gain_cells`: `outputs/v10_dsm_audit/v10_negative_gain_cells.csv`

## Target counts
- Building QA targets: **250**
- Conflict QA targets: **64**
- Cell QA targets: **44**

## Building target categories
```text
qa_category
critical_tile_building_review;transport_shelter_overhead_candidate                                                                     191
transport_shelter_overhead_candidate                                                                                                    14
large_low_confidence_building;transport_shelter_overhead_candidate                                                                      12
transport_shelter_overhead_candidate;very_large_default_height_building                                                                 10
large_low_confidence_building;transport_shelter_overhead_candidate;very_large_default_height_building                                    5
critical_tile_building_review;large_low_confidence_building;transport_shelter_overhead_candidate                                         5
critical_tile_building_review;very_large_default_height_building                                                                         3
critical_tile_building_review;transport_shelter_overhead_candidate;very_large_default_height_building                                    3
critical_tile_building_review;large_low_confidence_building;transport_shelter_overhead_candidate;very_large_default_height_building      2
critical_tile_building_review;large_low_confidence_building;very_large_default_height_building                                           2
very_large_default_height_building                                                                                                       2
critical_tile_building_review;large_low_confidence_building                                                                              1
```

## Top building targets
```text
    building_id                                                                                                                         qa_category  qa_priority_score source_name geometry_source      area_m2  height_m                   height_source height_confidence                          height_warning              lu_desc_v10                                         v09_tile_types
v10_bldg_000690                               large_low_confidence_building;transport_shelter_overhead_candidate;very_large_default_height_building             25.000         osm             osm 19921.192687       4.0            type_default_shelter        medium_low possible_shelter_not_ground_up_building     TRANSPORT FACILITIES                                                       
v10_bldg_000746 critical_tile_building_review;large_low_confidence_building;transport_shelter_overhead_candidate;very_large_default_height_building             23.285         osm             osm  3284.928265      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                        social_risk_top
v10_bldg_000754 critical_tile_building_review;large_low_confidence_building;transport_shelter_overhead_candidate;very_large_default_height_building             23.020         osm             osm  3019.680779      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                        overhead_confounded_hazard_case
v10_bldg_000764                                    critical_tile_building_review;large_low_confidence_building;transport_shelter_overhead_candidate             22.807         osm             osm  2806.829500      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                        overhead_confounded_hazard_case
v10_bldg_000775                                    critical_tile_building_review;large_low_confidence_building;transport_shelter_overhead_candidate             22.624         osm             osm  2623.729075      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                  conservative_risk_top
v10_bldg_000786                                    critical_tile_building_review;large_low_confidence_building;transport_shelter_overhead_candidate             22.503         osm             osm  2502.981552      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                        overhead_confounded_hazard_case
v10_bldg_000814                                    critical_tile_building_review;large_low_confidence_building;transport_shelter_overhead_candidate             22.100         osm             osm  2100.478100      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                        overhead_confounded_hazard_case
v10_bldg_000695                                                                  critical_tile_building_review;transport_shelter_overhead_candidate             22.000         osm             osm 12508.786350       9.0 osm_levels_x_3m:levels_original       medium_high                                         COMMERCIAL & RESIDENTIAL                                       clean_hazard_top
v10_bldg_000838                                    critical_tile_building_review;large_low_confidence_building;transport_shelter_overhead_candidate             21.857         osm             osm  1857.440954      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                        overhead_confounded_hazard_case
v10_bldg_000701                                                                  critical_tile_building_review;transport_shelter_overhead_candidate             20.794         osm             osm  8794.443540      18.0 osm_levels_x_3m:levels_original       medium_high                                                       BUSINESS 1                                  conservative_risk_top
v10_bldg_000714                               large_low_confidence_building;transport_shelter_overhead_candidate;very_large_default_height_building             20.484         osm             osm  5484.180893      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
v10_bldg_000732                               large_low_confidence_building;transport_shelter_overhead_candidate;very_large_default_height_building             18.977         osm             osm  3977.432409      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
v10_bldg_000712                                      critical_tile_building_review;large_low_confidence_building;very_large_default_height_building             18.750         osm             osm  5750.200944      12.0      area_default:unknown_large               low      manual_review_large_unknown_height             RESERVE SITE clean_shaded_reference;overhead_confounded_hazard_case
v10_bldg_000748                               large_low_confidence_building;transport_shelter_overhead_candidate;very_large_default_height_building             18.270         osm             osm  3269.865110      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
v10_bldg_000749                               large_low_confidence_building;transport_shelter_overhead_candidate;very_large_default_height_building             18.262         osm             osm  3262.140992      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
v10_bldg_000769                                                                  large_low_confidence_building;transport_shelter_overhead_candidate             17.700         osm             osm  2699.611360      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
v10_bldg_000782                                                                  large_low_confidence_building;transport_shelter_overhead_candidate             17.565         osm             osm  2564.739007      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
v10_bldg_000819                                                                  large_low_confidence_building;transport_shelter_overhead_candidate             17.043         osm             osm  2043.144634      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
v10_bldg_000691                                                             transport_shelter_overhead_candidate;very_large_default_height_building             17.000         osm             osm 16318.415378      20.0           lu_default:COMMERCIAL            medium                                                       BUSINESS 1                                                       
v10_bldg_000697                                                             transport_shelter_overhead_candidate;very_large_default_height_building             17.000         osm             osm 10929.073179       8.0            lu_default:TRANSPORT            medium                                             TRANSPORT FACILITIES                                                       
v10_bldg_000001                                                                                                transport_shelter_overhead_candidate             17.000       hdb3d           hdb3d 10357.772791      85.3                        height_m              high                                                       BUSINESS 1                                                       
v10_bldg_000694                                                             transport_shelter_overhead_candidate;very_large_default_height_building             17.000         osm             osm 12644.952532      20.0           lu_default:COMMERCIAL            medium                                                       BUSINESS 1                                                       
v10_bldg_000693                                                             transport_shelter_overhead_candidate;very_large_default_height_building             17.000         osm             osm 14810.611461      15.0          lu_default:RESIDENTIAL            medium                                                      RESIDENTIAL                                                       
v10_bldg_000731                                      critical_tile_building_review;large_low_confidence_building;very_large_default_height_building             16.981         osm             osm  3981.459609      12.0      area_default:unknown_large               low      manual_review_large_unknown_height             RESERVE SITE                                 clean_shaded_reference
v10_bldg_000837                                                                  large_low_confidence_building;transport_shelter_overhead_candidate             16.875         osm             osm  1875.196694      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
v10_bldg_000849                                                                  large_low_confidence_building;transport_shelter_overhead_candidate             16.788         osm             osm  1787.949047      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
v10_bldg_000872                                                                  large_low_confidence_building;transport_shelter_overhead_candidate             16.608         osm             osm  1608.156181      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
v10_bldg_000877                                                                  large_low_confidence_building;transport_shelter_overhead_candidate             16.561         osm             osm  1561.039020      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
v10_bldg_000885                                                                  large_low_confidence_building;transport_shelter_overhead_candidate             16.523         osm             osm  1523.360348      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
v10_bldg_000935                                                                  large_low_confidence_building;transport_shelter_overhead_candidate             16.255         osm             osm  1255.339716      12.0      area_default:unknown_large               low      manual_review_large_unknown_height               BUSINESS 1                                                       
```

## Top conflict-review targets
```text
source_name source_building_id  qa_priority_score     area_m2  height_m_original  levels_original building_type_original
        ura            ura_619              8.626 2626.088627                NaN              NaN                   None
        ura             ura_98              8.381 2381.048766                NaN              NaN                   None
        osm      osm_271792805              8.371 2371.469591                NaN             12.0            residential
        osm      osm_724661186              8.020 2019.710284                NaN              NaN                 school
        osm      osm_103290607              7.802 1801.770361                NaN              9.0            residential
        osm      osm_320899805              7.709 1709.038345                0.0              NaN                 office
        ura            ura_417              7.708 1707.887562                NaN              NaN                   None
        osm      osm_169227975              7.663 1663.232476                NaN             12.0            residential
        ura            ura_187              7.653 1652.888504                NaN              NaN                   None
        osm     osm_1025757368              7.644 1644.280823                NaN              3.0                parking
        osm      osm_818020477              7.589 1588.862822                NaN              NaN                    yes
        osm      osm_818020475              7.578 1578.068288                NaN              NaN                    yes
        osm      osm_320899575              7.524 1523.980372                0.0              NaN                 office
        ura            ura_161              7.502 1501.677551                NaN              NaN                   None
        ura            ura_236              7.491 1490.650258                NaN              NaN                   None
        osm      osm_170067545              7.445 1444.673453                NaN              NaN            residential
        ura            ura_309              7.438 1437.786385                NaN              NaN                   None
        osm      osm_724661187              7.434 1434.024809                NaN              NaN                 school
        osm      osm_103406723              7.376 1375.625094                0.0              NaN            residential
        osm      osm_103406722              7.358 1358.258766                0.0              NaN            residential
        osm      osm_552957497              7.305 1305.216830                NaN             18.0            residential
        ura            ura_243              7.181 1181.074622                NaN              NaN                   None
        ura            ura_250              7.181 1181.130894                NaN              NaN                   None
        osm      osm_169844044              7.169 1168.675044                NaN             25.0            residential
        osm      osm_169844050              7.169 1168.656995                NaN             25.0            residential
        osm      osm_103018886              7.132 1132.467093                NaN              4.0            residential
        osm      osm_170089756              7.097 1096.595448                NaN             18.0            residential
        osm      osm_170089580              7.072 1072.293654                NaN             11.0            residential
        osm      osm_170066220              7.019 1019.081664                NaN              NaN            residential
        ura            ura_401              7.012 1012.355144                NaN              NaN                   None
```

## Cell target categories
```text
qa_category
old_top_hazard_cell;low_old_completeness;high_coverage_gain    37
negative_gain_cell                                              5
old_top_hazard_cell;high_coverage_gain                          1
old_top_hazard_cell;low_old_completeness                        1
```

## Top cell targets
```text
cell_id                                                 qa_category  qa_priority_score  old_hazard_rank  old_vs_osm_completeness  new_vs_osm_completeness  coverage_gain_vs_osm  new_minus_old_dsm_area_m2
TP_0985 old_top_hazard_cell;low_old_completeness;high_coverage_gain             25.100                9                      0.0                 1.000012              1.000012                     4248.0
TP_0986 old_top_hazard_cell;low_old_completeness;high_coverage_gain             24.999               10                      0.0                 0.999823              0.999823                     4276.0
TP_0984 old_top_hazard_cell;low_old_completeness;high_coverage_gain             24.794               12                      0.0                 0.998140              0.998140                     4048.0
TP_0027 old_top_hazard_cell;low_old_completeness;high_coverage_gain             24.500               15                      0.0                 1.000083              1.000083                     4104.0
TP_0820 old_top_hazard_cell;low_old_completeness;high_coverage_gain             24.153               19                      0.0                 1.017695              1.017695                     4348.0
TP_0564 old_top_hazard_cell;low_old_completeness;high_coverage_gain             23.789                7                      0.0                 0.997615              0.997615                     3248.0
TP_0012 old_top_hazard_cell;low_old_completeness;high_coverage_gain             23.782               21                      0.0                 1.000759              1.000759                     3940.0
TP_0983 old_top_hazard_cell;low_old_completeness;high_coverage_gain             23.357               24                      0.0                 0.999146              0.999146                     3880.0
TP_0565 old_top_hazard_cell;low_old_completeness;high_coverage_gain             23.341               13                      0.0                 1.000279              1.000279                     3320.0
TP_0876 old_top_hazard_cell;low_old_completeness;high_coverage_gain             23.023               18                      0.0                 0.997134              0.997134                     3416.0
TP_0638 old_top_hazard_cell;low_old_completeness;high_coverage_gain             22.962               14                      0.0                 1.000633              1.000633                     3180.0
TP_0760 old_top_hazard_cell;low_old_completeness;high_coverage_gain             22.951               29                      0.0                 0.998282              0.998282                     3928.0
TP_0902 old_top_hazard_cell;low_old_completeness;high_coverage_gain             22.887               31                      0.0                 0.995508              0.995508                     4420.0
TP_0849 old_top_hazard_cell;low_old_completeness;high_coverage_gain             22.576                8                      0.0                 0.994721              0.994721                     2696.0
TP_0756 old_top_hazard_cell;low_old_completeness;high_coverage_gain             22.496               35                      0.0                 0.998697              0.998697                     4400.0
TP_0028 old_top_hazard_cell;low_old_completeness;high_coverage_gain             22.096               39                      0.0                 0.998709              0.998709                     4308.0
TP_0847 old_top_hazard_cell;low_old_completeness;high_coverage_gain             21.854               30                      0.0                 1.015368              1.015368                     3404.0
TP_0848 old_top_hazard_cell;low_old_completeness;high_coverage_gain             21.849               27                      0.0                 1.004352              1.004352                     3268.0
TP_0727 old_top_hazard_cell;low_old_completeness;high_coverage_gain             21.687               37                      0.0                 1.000980              1.000980                     3692.0
TP_0955 old_top_hazard_cell;low_old_completeness;high_coverage_gain             21.602               44                      0.0                 1.000547              1.000547                     4388.0
TP_0923 old_top_hazard_cell;low_old_completeness;high_coverage_gain             21.556               17                      0.0                 0.997216              0.997216                     2632.0
TP_0315 old_top_hazard_cell;low_old_completeness;high_coverage_gain             21.434               22                      0.0                 1.000515              1.000515                     2816.0
TP_0527 old_top_hazard_cell;low_old_completeness;high_coverage_gain             21.302               42                      0.0                 0.833854              0.833854                     6972.0
TP_0116 old_top_hazard_cell;low_old_completeness;high_coverage_gain             21.299                2                      0.0                 0.995708              0.995708                     1756.0
TP_0786 old_top_hazard_cell;low_old_completeness;high_coverage_gain             21.245               46                      0.0                 0.998978              0.998978                     3924.0
TP_0042 old_top_hazard_cell;low_old_completeness;high_coverage_gain             21.179               23                      0.0                 0.999787              0.999787                     2740.0
TP_0878 old_top_hazard_cell;low_old_completeness;high_coverage_gain             20.955               50                      0.0                 1.006205              1.006205                     3968.0
TP_0030 old_top_hazard_cell;low_old_completeness;high_coverage_gain             20.293               33                      0.0                 0.997505              0.997505                     2800.0
TP_0850 old_top_hazard_cell;low_old_completeness;high_coverage_gain             20.073               45                      0.0                 0.998900              0.998900                     3288.0
TP_0819 old_top_hazard_cell;low_old_completeness;high_coverage_gain             19.724               47                      0.0                 1.026751              1.026751                     3172.0
```

## Recommended manual decisions
- `keep_building_dsm`: valid ground-up building, keep in v10 building DSM.
- `move_to_overhead_dsm`: roof / canopy / elevated structure; remove from building DSM and reserve for overhead DSM.
- `height_adjust`: keep footprint but change `height_m`.
- `remove`: likely false positive / non-building.
- `merge_conflict`: real building excluded by conservative dedup; merge into canonical.
- `no_action`: target checked, no change required.

## Next step
Use QGIS to inspect the GeoJSON layers. Fill `manual_decision`, `manual_height_m`, and `manual_notes` in the review template before modifying the canonical building layer.
