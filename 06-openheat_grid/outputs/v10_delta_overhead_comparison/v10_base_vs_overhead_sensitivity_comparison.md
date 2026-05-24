# v10-delta base vs overhead-shade sensitivity comparison

Metric: `hazard_score`

Merged cells: **986**

Clean compared cells: **986**

Spearman rank correlation: **0.9327**

Top 20 overlap: **8 / 20**

## Entering overhead-sensitivity top set

TP_0030, TP_0060, TP_0116, TP_0136, TP_0144, TP_0366, TP_0452, TP_0527, TP_0639, TP_0641, TP_0984, TP_0985

## Leaving base v10 top set

TP_0088, TP_0089, TP_0315, TP_0344, TP_0373, TP_0460, TP_0564, TP_0572, TP_0575, TP_0888, TP_0916, TP_0973

## Largest rank drops under overhead sensitivity

```text
cell_id  hazard_score_base_v10  rank_base_v10_hazard_score  hazard_score_overhead_sens  rank_overhead_sens_hazard_score  rank_change_base_minus_overhead  overhead_fraction_total  overhead_shade_proxy overhead_confounding_flag                 overhead_interpretation
TP_0916               0.715338                        20.0                    0.083271                            939.0                           -919.0                 1.000000              1.000000         major_confounding               transport_deck_or_viaduct
TP_0746               0.705626                        31.0                    0.085001                            937.0                           -906.0                 1.000000              1.000000         major_confounding               transport_deck_or_viaduct
TP_0831               0.683553                        59.0                    0.058976                            962.0                           -903.0                 1.000000              1.000000         major_confounding mixed_pedestrian_and_transport_overhead
TP_0888               0.720679                        17.0                    0.096970                            918.0                           -901.0                 1.000000              1.000000         major_confounding mixed_pedestrian_and_transport_overhead
TP_0803               0.685471                        54.0                    0.067896                            953.0                           -899.0                 1.000000              0.872564         major_confounding               transport_deck_or_viaduct
TP_0860               0.672987                        80.0                    0.086599                            933.0                           -853.0                 1.000000              0.900275         major_confounding mixed_pedestrian_and_transport_overhead
TP_0859               0.637220                       124.0                    0.056912                            967.0                           -843.0                 1.000000              1.000000         major_confounding mixed_pedestrian_and_transport_overhead
TP_0887               0.631493                       137.0                    0.056230                            969.0                           -832.0                 1.000000              1.000000         major_confounding mixed_pedestrian_and_transport_overhead
TP_0717               0.711285                        27.0                    0.160298                            832.0                           -805.0                 1.000000              1.000000         major_confounding               transport_deck_or_viaduct
TP_0944               0.710993                        28.0                    0.171564                            815.0                           -787.0                 1.000000              0.866772         major_confounding               transport_deck_or_viaduct
TP_0973               0.725356                        11.0                    0.187953                            792.0                           -781.0                 0.863881              0.691104         major_confounding               transport_deck_or_viaduct
TP_0972               0.575498                       220.0                    0.143615                            861.0                           -641.0                 0.837961              0.670369         major_confounding               transport_deck_or_viaduct
TP_0915               0.458792                       395.0                    0.089103                            931.0                           -536.0                 0.949624              0.759699         major_confounding               transport_deck_or_viaduct
TP_0832               0.648790                       108.0                    0.351001                            532.0                           -424.0                 0.561928              0.449542         major_confounding               transport_deck_or_viaduct
TP_0774               0.459004                       394.0                    0.172340                            813.0                           -419.0                 0.691200              0.552960         major_confounding               transport_deck_or_viaduct
TP_0802               0.434200                       430.0                    0.181257                            802.0                           -372.0                 0.618789              0.495031         major_confounding               transport_deck_or_viaduct
TP_0943               0.468113                       379.0                    0.228905                            731.0                           -352.0                 0.541659              0.433327         major_confounding               transport_deck_or_viaduct
TP_0974               0.496157                       346.0                    0.255842                            687.0                           -341.0                 0.742172              0.593738         major_confounding               transport_deck_or_viaduct
TP_0830               0.428007                       443.0                    0.213525                            752.0                           -309.0                 0.507130              0.414924         major_confounding mixed_pedestrian_and_transport_overhead
TP_0431               0.650541                       106.0                    0.440677                            399.0                           -293.0                 0.592219              0.446653         major_confounding               transport_deck_or_viaduct
TP_0088               0.754081                         1.0                    0.559243                            224.0                           -223.0                 0.732482              0.549361         major_confounding               transport_deck_or_viaduct
TP_0946               0.304538                       618.0                    0.161652                            831.0                           -213.0                 0.568704              0.454963         major_confounding               transport_deck_or_viaduct
TP_0822               0.643180                       118.0                    0.488002                            329.0                           -211.0                 0.330874              0.262954         major_confounding mixed_pedestrian_and_transport_overhead
TP_0571               0.624934                       151.0                    0.471871                            351.0                           -200.0                 0.450632              0.341359         major_confounding mixed_pedestrian_and_transport_overhead
TP_0745               0.363131                       527.0                    0.252162                            697.0                           -170.0                 0.321014              0.256811         major_confounding               transport_deck_or_viaduct
```

## Largest rank gains under overhead sensitivity

```text
cell_id  hazard_score_base_v10  rank_base_v10_hazard_score  hazard_score_overhead_sens  rank_overhead_sens_hazard_score  rank_change_base_minus_overhead  overhead_fraction_total  overhead_shade_proxy overhead_confounding_flag overhead_interpretation
TP_0383               0.345253                       562.0                    0.360008                            515.0                             47.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0038               0.288350                       650.0                    0.306077                            603.0                             47.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0805               0.498325                       337.0                    0.512125                            291.0                             46.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0039               0.417787                       459.0                    0.429518                            414.0                             45.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0297               0.515148                       312.0                    0.530051                            268.0                             44.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0828               0.280377                       663.0                    0.296730                            619.0                             44.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0337               0.277965                       669.0                    0.293031                            626.0                             43.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0617               0.277362                       670.0                    0.292278                            627.0                             43.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0008               0.496261                       345.0                    0.507782                            302.0                             43.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0328               0.500825                       331.0                    0.514588                            288.0                             43.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0372               0.401512                       482.0                    0.415812                            439.0                             43.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0424               0.294733                       639.0                    0.309806                            596.0                             43.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0499               0.273056                       676.0                    0.288457                            634.0                             42.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0303               0.407962                       474.0                    0.420059                            432.0                             42.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0016               0.556457                       250.0                    0.569628                            208.0                             42.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0364               0.292729                       642.0                    0.308295                            600.0                             42.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0371               0.325635                       590.0                    0.343418                            548.0                             42.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0356               0.446305                       414.0                    0.457164                            372.0                             42.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0453               0.294830                       638.0                    0.309289                            597.0                             41.0                 0.001785              0.001606            clean_or_minor           minor_or_none
TP_0314               0.556011                       251.0                    0.569048                            210.0                             41.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0010               0.431501                       436.0                    0.441945                            395.0                             41.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0193               0.497092                       342.0                    0.508240                            301.0                             41.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0015               0.557557                       248.0                    0.570373                            207.0                             41.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0759               0.496545                       344.0                    0.507676                            303.0                             41.0                 0.000000              0.000000            clean_or_minor           minor_or_none
TP_0384               0.511620                       316.0                    0.522205                            275.0                             41.0                 0.000000              0.000000            clean_or_minor           minor_or_none
```

## Interpretation note
- This comparison tests a ground-level overhead-shade sensitivity, not a final overhead-aware physical model.
- Cells dominated by elevated transport decks should be flagged separately from pedestrian exposure cells.
- Large rank drops in major overhead cells indicate locations where the v10 base hazard may overstate ground-level radiant exposure.
