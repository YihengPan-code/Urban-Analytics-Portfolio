# v10-gamma v08-v10 forecast ranking comparison

Metric: `hazard_score`

Merged cells: **986**

Clean compared cells: **986**

Spearman rank correlation: **0.9705**

Top 20 overlap: **10 / 20**

False-positive diagnostic: `old_top20_false_positive_candidates=12; leaving_top20_false_positive_candidates=9`

## Entering v10 top set

TP_0120, TP_0171, TP_0315, TP_0344, TP_0373, TP_0572, TP_0766, TP_0888, TP_0916, TP_0973

## Leaving v08 top set

TP_0027, TP_0060, TP_0116, TP_0638, TP_0820, TP_0849, TP_0876, TP_0923, TP_0984, TP_0985

## Largest rank changes toward v10 top

```text
cell_id  hazard_score_v08  rank_v08_hazard_score  hazard_score_v10  rank_v10_hazard_score  rank_change_v08_minus_v10  is_old_dsm_gap_false_positive_candidate
TP_0463          0.123402                  880.0          0.463880                  383.0                      497.0                                    False
TP_0218          0.384650                  498.0          0.628487                  142.0                      356.0                                    False
TP_0343          0.414893                  449.0          0.626717                  145.0                      304.0                                    False
TP_0828          0.080274                  932.0          0.280377                  663.0                      269.0                                    False
TP_0857          0.065366                  949.0          0.256370                  699.0                      250.0                                    False
TP_0257          0.178611                  805.0          0.338603                  569.0                      236.0                                    False
TP_0827          0.233864                  722.0          0.386487                  506.0                      216.0                                    False
TP_0217          0.325735                  583.0          0.476728                  370.0                      213.0                                    False
TP_0212          0.537897                  260.0          0.687418                   48.0                      212.0                                    False
TP_0074          0.292287                  637.0          0.438875                  426.0                      211.0                                    False
TP_0408          0.112684                  895.0          0.253381                  705.0                      190.0                                    False
TP_0254          0.135921                  863.0          0.266159                  689.0                      174.0                                    False
TP_0310          0.571036                  220.0          0.687051                   49.0                      171.0                                    False
TP_0438          0.133036                  865.0          0.258317                  698.0                      167.0                                    False
TP_0223          0.346367                  551.0          0.462998                  384.0                      167.0                                    False
TP_0406          0.162086                  823.0          0.283256                  658.0                      165.0                                    False
TP_0189          0.508428                  302.0          0.614665                  162.0                      140.0                                    False
TP_0599          0.269818                  676.0          0.359460                  537.0                      139.0                                    False
TP_0286          0.488030                  343.0          0.586554                  204.0                      139.0                                    False
TP_0213          0.593347                  187.0          0.686868                   51.0                      136.0                                    False
TP_0600          0.427064                  431.0          0.521853                  300.0                      131.0                                    False
TP_0383          0.259789                  689.0          0.345253                  562.0                      127.0                                    False
TP_0227          0.197054                  778.0          0.285257                  655.0                      123.0                                    False
TP_0962          0.587046                  197.0          0.674248                   75.0                      122.0                                    False
TP_0420          0.534780                  266.0          0.625903                  149.0                      117.0                                    False
```

## Largest rank drops under v10

```text
cell_id  hazard_score_v08  rank_v08_hazard_score  hazard_score_v10  rank_v10_hazard_score  rank_change_v08_minus_v10  is_old_dsm_gap_false_positive_candidate
TP_0945          0.686649                   48.0          0.000000                  986.0                     -938.0                                    False
TP_0068          0.348167                  547.0          0.194952                  790.0                     -243.0                                    False
TP_0855          0.415134                  448.0          0.271404                  679.0                     -231.0                                    False
TP_0057          0.502723                  315.0          0.353845                  545.0                     -230.0                                    False
TP_0377          0.393170                  484.0          0.265365                  691.0                     -207.0                                    False
TP_0176          0.338316                  566.0          0.218127                  754.0                     -188.0                                    False
TP_0013          0.497556                  326.0          0.377988                  513.0                     -187.0                                    False
TP_0070          0.391810                  489.0          0.274991                  674.0                     -185.0                                    False
TP_0040          0.612362                  162.0          0.497238                  341.0                     -179.0                                    False
TP_0789          0.369016                  517.0          0.264634                  693.0                     -176.0                                    False
TP_0878          0.686045                   50.0          0.573091                  223.0                     -173.0                                     True
TP_0696          0.645843                  117.0          0.528176                  289.0                     -172.0                                    False
TP_0069          0.336345                  568.0          0.233773                  731.0                     -163.0                                    False
TP_0955          0.692969                   44.0          0.587908                  203.0                     -159.0                                     True
TP_0956          0.654876                   99.0          0.551167                  257.0                     -158.0                                    False
TP_0723          0.543353                  254.0          0.449059                  410.0                     -156.0                                    False
TP_0854          0.390787                  493.0          0.289438                  647.0                     -154.0                                    False
TP_0877          0.638813                  125.0          0.535808                  278.0                     -153.0                                    False
TP_0663          0.467505                  372.0          0.371675                  520.0                     -148.0                                    False
TP_0907          0.515257                  296.0          0.427030                  444.0                     -148.0                                    False
TP_0650          0.576192                  210.0          0.486346                  357.0                     -147.0                                    False
TP_0720          0.650310                  109.0          0.553065                  255.0                     -146.0                                    False
TP_0760          0.701994                   29.0          0.604341                  174.0                     -145.0                                     True
TP_0810          0.494505                  331.0          0.406422                  476.0                     -145.0                                    False
TP_0724          0.574904                  212.0          0.486510                  356.0                     -144.0                                    False
```

## Interpretation note

- This is the first reviewed-DSM forecast/ranking comparison using v10 UMEP morphology.

- If many old false-positive candidates leave the top set, this supports the v0.9 audit finding that old hazard ranking was affected by building-DSM coverage gaps.
