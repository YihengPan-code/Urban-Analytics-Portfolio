# v0.9-gamma overhead-aware tile selection QA report

Selected tiles: **6**

## Selected tile summary

                            tile_id                       tile_type cell_id  hazard_rank_true_v08  risk_rank_v08_conditioned  risk_rank_v08_social_conditioned  overhead_fraction_cell  tile_overhead_fraction selection_status  min_center_distance_to_previous_m  max_iou_with_previous
               T01_clean_hazard_top                clean_hazard_top TP_0116                     2                         13                                27                0.000000                0.000000           strict                                inf           0.000000e+00
          T02_conservative_risk_top           conservative_risk_top TP_0378                    51                          1                                 1                0.037645                0.019571           strict                        2973.213749           0.000000e+00
                T03_social_risk_top                 social_risk_top TP_0452                    59                          3                                 2                0.000000                0.003596           strict                        1612.451550           0.000000e+00
             T04_open_paved_hotspot              open_paved_hotspot TP_0120                    34                         40                                58                0.000000                0.049936           strict                         948.683298           0.000000e+00
         T05_clean_shaded_reference          clean_shaded_reference TP_0433                   974                        974                               974                0.000000                0.048253           strict                        1004.987562           0.000000e+00
T06_overhead_confounded_hazard_case overhead_confounded_hazard_case TP_0575                    20                         84                               155                0.435459                0.087762           strict                         583.095189           2.910383e-14

## Warnings

No major warnings.


## Interpretation

- Clean tiles are selected with overhead and spatial-separation constraints.
- `overhead_confounded_hazard_case`, if present, is diagnostic only and should not be interpreted as a clean radiant-exposure tile.
- Always inspect selected tiles in QGIS before running SOLWEIG.
