# v10-gamma UMEP zonal morphology QA report

Rows: **986**

## Parsed shadow hours

```text
800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900
```

## Feature summaries

```text
       svf_umep_mean_open_v10  shade_fraction_umep_10_16_open_v10  shade_fraction_umep_13_15_open_v10  building_pixel_fraction_v10  open_pixel_fraction_v10  dsm_building_height_mean_m_v10  dsm_building_height_max_m_v10
count              985.000000                          986.000000                          986.000000                   986.000000               986.000000                      898.000000                     898.000000
mean                 0.380031                            0.465755                            0.424577                     0.202752                 0.797248                       24.197920                      37.435524
std                  0.215978                            0.245803                            0.258342                     0.147006                 0.147006                       18.920347                      31.710367
min                  0.010397                            0.000000                            0.000000                     0.000000                 0.038831                        3.000000                       3.000000
25%                  0.222008                            0.264048                            0.210599                     0.081765                 0.701720                       12.000000                      15.000000
50%                  0.363252                            0.464767                            0.404399                     0.193756                 0.806244                       15.617712                      25.250000
75%                  0.530007                            0.643978                            0.607581                     0.298280                 0.918235                       29.977569                      54.000000
max                  0.948570                            0.978518                            0.977359                     0.961169                 1.000000                      127.233083                     133.000000
```

## Notes

- This is v10 reviewed-building-DSM + vegetation UMEP morphology, not final SOLWEIG/Tmrt.

- Final hazard reranking should use this table merged into the forecast grid, then rerun the forecast/hazard engine.
