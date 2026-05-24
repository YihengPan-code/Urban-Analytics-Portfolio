# v1.0-alpha.3 reviewed DSM completeness gain report

## Interpretation note
- Completeness is calculated relative to OSM-mapped building footprint area, not absolute real-world completeness.
- Ratios can exceed 1.0 because OSM is a reference layer, not ground truth.
- Reviewed completeness may be slightly lower than alpha.1 if manual QA moved roof/canopy/transport shelter objects out of the ground-up building DSM; this is desirable if those objects belong in a future overhead DSM.

## Per-cell completeness
Rows: **986**
Old DSM area sum: **735820.0 m²**
Reviewed DSM area sum: **2117980.0 m²**
OSM area sum: **1896382.9 m²**
Old vs OSM completeness: **0.388**
Reviewed vs OSM completeness: **1.117**

Completeness distribution:
```text
       old_vs_osm_completeness  reviewed_vs_osm_completeness  coverage_gain_vs_osm  reviewed_minus_old_dsm_area_m2
count               871.000000                    871.000000            871.000000                      986.000000
mean                  0.477138                     12.399943             11.922805                     1401.784990
std                   1.693015                    323.659009            323.671969                     1604.183088
min                   0.000000                      0.000000             -0.201067                     -308.000000
25%                   0.000000                      0.994915              0.061615                        0.000000
50%                   0.000000                      1.003117              0.990780                      744.000000
75%                   0.936983                      1.086317              1.001492                     2527.000000
max                  46.183379                   9552.869760           9552.869760                    10000.000000
```

## Per-tile completeness
Rows: **6**
Old DSM area sum: **110936.0 m²**
Reviewed DSM area sum: **481304.0 m²**
OSM area sum: **421266.8 m²**
Old vs OSM completeness: **0.263**
Reviewed vs OSM completeness: **1.143**

Completeness distribution:
```text
       old_vs_osm_completeness  reviewed_vs_osm_completeness  coverage_gain_vs_osm  reviewed_minus_old_dsm_area_m2
count                 6.000000                      6.000000              6.000000                        6.000000
mean                  0.241475                      1.147566              0.906091                    61728.000000
std                   0.246012                      0.119170              0.293184                    19708.050903
min                   0.000000                      0.981485              0.474761                    39920.000000
25%                   0.097151                      1.131568              0.777541                    45277.000000
50%                   0.151255                      1.136990              0.928946                    63582.000000
75%                   0.340091                      1.143376              0.998850                    70442.000000
max                   0.664189                      1.354669              1.354669                    91380.000000
```

## Critical tile recovery
```text
                            tile_id                       tile_type cell_id  old_dsm_area_m2  new_dsm_area_m2  osm_area_m2  old_vs_osm_completeness  reviewed_vs_osm_completeness  coverage_gain_vs_osm
               T01_clean_hazard_top                clean_hazard_top TP_0116           6676.0          77064.0 78517.761027                 0.085025                      0.981485              0.896460
          T02_conservative_risk_top           conservative_risk_top TP_0378           5472.0          46916.0 40980.017963                 0.133528                      1.144851              1.011322
                T03_social_risk_top                 social_risk_top TP_0452          55848.0          95768.0 84084.441419                 0.664189                      1.138950              0.474761
             T04_open_paved_hotspot              open_paved_hotspot TP_0120          30556.0          87332.0 76942.510663                 0.397128                      1.135029              0.737902
         T05_clean_shaded_reference          clean_shaded_reference TP_0433          12384.0          82844.0 73286.448318                 0.168981                      1.130414              0.961433
T06_overhead_confounded_hazard_case overhead_confounded_hazard_case TP_0575              0.0          91380.0 67455.593306                 0.000000                      1.354669              1.354669
```