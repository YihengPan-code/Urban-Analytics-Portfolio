# v10-epsilon SOLWEIG base vs overhead scenario comparison

This is a selected-cell physical sensitivity check, not a full overhead-aware operational model.

## Focus-cell comparison
```text
                                   tile_id cell_id                           role  tmrt_time_label  tmrt_hour_sgt      base  overhead  delta_overhead_minus_base_c        delta_class
        E01_confident_hot_anchor_1_TP_0565 TP_0565         confident_hot_anchor_1             1000             10 43.720139 43.711323                    -0.008816      little_change
        E01_confident_hot_anchor_1_TP_0565 TP_0565         confident_hot_anchor_1             1200             12 60.030983 60.023449                    -0.007534      little_change
        E01_confident_hot_anchor_1_TP_0565 TP_0565         confident_hot_anchor_1             1300             13 60.055317 60.045807                    -0.009510      little_change
        E01_confident_hot_anchor_1_TP_0565 TP_0565         confident_hot_anchor_1             1500             15 57.522087 57.510502                    -0.011585      little_change
        E01_confident_hot_anchor_1_TP_0565 TP_0565         confident_hot_anchor_1             1600             16 48.525780 48.514706                    -0.011074      little_change
        E02_confident_hot_anchor_2_TP_0986 TP_0986         confident_hot_anchor_2             1000             10 43.921703 43.921703                     0.000000      little_change
        E02_confident_hot_anchor_2_TP_0986 TP_0986         confident_hot_anchor_2             1200             12 60.958656 60.958656                     0.000000      little_change
        E02_confident_hot_anchor_2_TP_0986 TP_0986         confident_hot_anchor_2             1300             13 60.673000 60.673000                     0.000000      little_change
        E02_confident_hot_anchor_2_TP_0986 TP_0986         confident_hot_anchor_2             1500             15 57.422287 57.422287                     0.000000      little_change
        E02_confident_hot_anchor_2_TP_0986 TP_0986         confident_hot_anchor_2             1600             16 48.352276 48.352276                     0.000000      little_change
E03_overhead_confounded_rank1_case_TP_0088 TP_0088 overhead_confounded_rank1_case             1000             10 45.493149 36.659515                    -8.833633 moderate_reduction
E03_overhead_confounded_rank1_case_TP_0088 TP_0088 overhead_confounded_rank1_case             1200             12 61.694836 45.462746                   -16.232090    large_reduction
E03_overhead_confounded_rank1_case_TP_0088 TP_0088 overhead_confounded_rank1_case             1300             13 61.739075 44.980919                   -16.758156    large_reduction
E03_overhead_confounded_rank1_case_TP_0088 TP_0088 overhead_confounded_rank1_case             1500             15 59.777481 42.776337                   -17.001144    large_reduction
E03_overhead_confounded_rank1_case_TP_0088 TP_0088 overhead_confounded_rank1_case             1600             16 50.706322 38.742023                   -11.964298 moderate_reduction
       E04_saturated_overhead_case_TP_0916 TP_0916        saturated_overhead_case             1000             10 44.708523 33.649845                   -11.058678 moderate_reduction
       E04_saturated_overhead_case_TP_0916 TP_0916        saturated_overhead_case             1200             12 60.949413 38.486156                   -22.463257    large_reduction
       E04_saturated_overhead_case_TP_0916 TP_0916        saturated_overhead_case             1300             13 61.149025 38.999508                   -22.149517    large_reduction
       E04_saturated_overhead_case_TP_0916 TP_0916        saturated_overhead_case             1500             15 59.428688 37.911655                   -21.517033    large_reduction
       E04_saturated_overhead_case_TP_0916 TP_0916        saturated_overhead_case             1600             16 50.327488 35.562042                   -14.765446 moderate_reduction
        E05_clean_shaded_reference_TP_0433 TP_0433         clean_shaded_reference             1000             10 32.891094 32.891003                    -0.000092      little_change
        E05_clean_shaded_reference_TP_0433 TP_0433         clean_shaded_reference             1200             12 36.001133 36.000683                    -0.000450      little_change
        E05_clean_shaded_reference_TP_0433 TP_0433         clean_shaded_reference             1300             13 36.091625 36.091061                    -0.000565      little_change
        E05_clean_shaded_reference_TP_0433 TP_0433         clean_shaded_reference             1500             15 35.887836 35.887661                    -0.000175      little_change
        E05_clean_shaded_reference_TP_0433 TP_0433         clean_shaded_reference             1600             16 34.476162 34.476086                    -0.000076      little_change
```

## Mean delta by role
```text
                          role  n  mean_delta  min_delta  max_delta
        clean_shaded_reference  5   -0.000272  -0.000565  -0.000076
        confident_hot_anchor_1  5   -0.009704  -0.011585  -0.007534
        confident_hot_anchor_2  5    0.000000   0.000000   0.000000
overhead_confounded_rank1_case  5  -14.157864 -17.001144  -8.833633
       saturated_overhead_case  5  -18.390786 -22.463257 -11.058678
```

## Interpretation
- TP_0565 / TP_0986 should show little change if they are true low-overhead hot anchors.
- TP_0088 / TP_0916 should show meaningful Tmrt reduction if v10-delta overhead sensitivity is directionally supported.
- If saturated overhead cells only show small SOLWEIG reductions, the v10-delta algebraic shade sensitivity is too aggressive for exact magnitude, though still useful as a confounding flag.
