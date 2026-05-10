# v1.0-alpha.1 building completeness gain report

## Interpretation note
- Completeness is calculated relative to OSM-mapped building footprint area, not absolute real-world completeness.
- Ratios can exceed 1.0 because OSM is a reference layer, not ground truth. HDB3D/URA/canonical footprints may include buildings missing from OSM, and small OSM denominators can inflate cell-level ratios.
- Use manual QA for final interpretation, especially for transport facilities, shelters, roofs, and overhead structures.

## Per-cell completeness
Rows: **986**
Old DSM area sum: **735820.0 m²**
New DSM area sum: **1957024.0 m²**
OSM area sum: **1896357.9 m²**
Old vs OSM completeness: **0.388**
New vs OSM completeness: **1.032**

Completeness distribution:
```text
       old_vs_osm_completeness  new_vs_osm_completeness  coverage_gain_vs_osm  new_minus_old_dsm_area_m2
count               871.000000               871.000000            871.000000                 986.000000
mean                  0.477142                 1.108168              0.631026                1238.543611
std                   1.693017                 1.593500              0.453290                1500.511487
min                   0.000000                 0.000000             -0.604609               -1196.000000
25%                   0.000000                 0.993540              0.034396                   0.000000
50%                   0.000000                 1.001154              0.988280                 520.000000
75%                   0.936983                 1.032381              1.000471                2255.000000
max                  46.183379                46.183379              1.118747                7268.000000
```

## Per-tile completeness
Rows: **6**
Old DSM area sum: **110936.0 m²**
New DSM area sum: **418740.0 m²**
OSM area sum: **421247.6 m²**
Old vs OSM completeness: **0.263**
New vs OSM completeness: **0.994**

Completeness distribution:
```text
       old_vs_osm_completeness  new_vs_osm_completeness  coverage_gain_vs_osm  new_minus_old_dsm_area_m2
count                 6.000000                 6.000000              6.000000                   6.000000
mean                  0.241496                 0.994583              0.753087               51300.666667
std                   0.246045                 0.034895              0.232690               16312.465597
min                   0.000000                 0.928096              0.359252               30204.000000
25%                   0.097151                 0.995732              0.658897               38114.000000
50%                   0.151255                 0.999293              0.848354               54264.000000
75%                   0.340127                 1.016890              0.863043               65287.000000
max                   0.664266                 1.023518              0.998879               67380.000000
```

## Critical v0.9 tile recovery
```text
                            tile_id                       tile_type cell_id  old_dsm_area_m2  new_dsm_area_m2  osm_area_m2  old_vs_osm_completeness  new_vs_osm_completeness  coverage_gain_vs_osm
               T01_clean_hazard_top                clean_hazard_top TP_0116           6676.0          72872.0 78517.761027                 0.085025                 0.928096              0.843070
          T02_conservative_risk_top           conservative_risk_top TP_0378           5472.0          40968.0 40980.017963                 0.133528                 0.999707              0.866178
                T03_social_risk_top                 social_risk_top TP_0452          55848.0          86052.0 84074.739520                 0.664266                 1.023518              0.359252
             T04_open_paved_hotspot              open_paved_hotspot TP_0120          30556.0          76524.0 76933.085255                 0.397176                 0.994683              0.597506
         T05_clean_shaded_reference          clean_shaded_reference TP_0433          12384.0          74944.0 73286.448318                 0.168981                 1.022617              0.853637
T06_overhead_confounded_hazard_case overhead_confounded_hazard_case TP_0575              0.0          67380.0 67455.593306                 0.000000                 0.998879              0.998879
```

## Negative-gain cell QA
Cells with new_minus_old_dsm_area_m2 < -100: **5**
CSV: `outputs\v10_dsm_audit\v10_negative_gain_cells.csv`

## Notes
- The v10-alpha.1 DSM should have no nodata metadata; 0.0 is valid ground/no-building height.
- Do not use this audit alone to decide final hazard ranking; it is a morphology data-integrity check before v10 morphology/ranking rerun.