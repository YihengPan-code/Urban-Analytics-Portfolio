# v10-delta overhead cell QA report

Rows: **986**

## Overhead flag counts

```text
                flag  n_cells
      clean_or_minor      716
moderate_confounding      159
   major_confounding      111
```

## Overhead interpretation counts

```text
                         interpretation  n_cells
                          minor_or_none      726
              transport_deck_or_viaduct      126
               pedestrian_shelter_shade       90
mixed_pedestrian_and_transport_overhead       44
```

## Summary statistics

```text
       overhead_fraction_total  overhead_shade_proxy  pedestrian_shelter_fraction  transport_deck_fraction  n_overhead_features
count               986.000000            986.000000                   986.000000               986.000000           986.000000
mean                  0.046232              0.038409                     0.009063                 0.039008             1.733266
std                   0.139607              0.122837                     0.034084                 0.137814             3.841115
min                   0.000000              0.000000                     0.000000                 0.000000             0.000000
25%                   0.000000              0.000000                     0.000000                 0.000000             0.000000
50%                   0.000000              0.000000                     0.000000                 0.000000             0.000000
75%                   0.024800              0.021039                     0.005982                 0.000000             2.000000
max                   1.000000              1.000000                     0.714019                 1.000000            43.000000
```

## Top overhead cells

```text
cell_id  overhead_fraction_total  overhead_shade_proxy  pedestrian_shelter_fraction  transport_deck_fraction  n_overhead_features overhead_confounding_flag                 overhead_interpretation
TP_0887                 1.000000              1.000000                     0.423706                 1.000000                 35.0         major_confounding mixed_pedestrian_and_transport_overhead
TP_0803                 1.000000              0.872564                     0.000000                 1.000000                 25.0         major_confounding               transport_deck_or_viaduct
TP_0888                 1.000000              1.000000                     0.175555                 1.000000                 23.0         major_confounding mixed_pedestrian_and_transport_overhead
TP_0859                 1.000000              1.000000                     0.714019                 1.000000                 23.0         major_confounding mixed_pedestrian_and_transport_overhead
TP_0944                 1.000000              0.866772                     0.000000                 1.000000                 20.0         major_confounding               transport_deck_or_viaduct
TP_0717                 1.000000              1.000000                     0.000000                 1.000000                 21.0         major_confounding               transport_deck_or_viaduct
TP_0916                 1.000000              1.000000                     0.000000                 1.000000                 31.0         major_confounding               transport_deck_or_viaduct
TP_0860                 1.000000              0.900275                     0.132634                 0.976130                 21.0         major_confounding mixed_pedestrian_and_transport_overhead
TP_0746                 1.000000              1.000000                     0.000000                 1.000000                 24.0         major_confounding               transport_deck_or_viaduct
TP_0831                 1.000000              1.000000                     0.392077                 1.000000                 43.0         major_confounding mixed_pedestrian_and_transport_overhead
TP_0915                 0.949624              0.759699                     0.000000                 0.949624                 24.0         major_confounding               transport_deck_or_viaduct
TP_0973                 0.863881              0.691104                     0.000000                 0.863881                 29.0         major_confounding               transport_deck_or_viaduct
TP_0972                 0.837961              0.670369                     0.000000                 0.837961                 14.0         major_confounding               transport_deck_or_viaduct
TP_0974                 0.742172              0.593738                     0.000000                 0.742172                 11.0         major_confounding               transport_deck_or_viaduct
TP_0945                 0.738418              0.590735                     0.000000                 0.738418                 14.0         major_confounding               transport_deck_or_viaduct
TP_0088                 0.732482              0.549361                     0.000000                 0.732482                  7.0         major_confounding               transport_deck_or_viaduct
TP_0774                 0.691200              0.552960                     0.000000                 0.691200                 13.0         major_confounding               transport_deck_or_viaduct
TP_0802                 0.618789              0.495031                     0.000000                 0.618789                 16.0         major_confounding               transport_deck_or_viaduct
TP_0431                 0.592219              0.446653                     0.017217                 0.575001                  9.0         major_confounding               transport_deck_or_viaduct
TP_0946                 0.568704              0.454963                     0.000000                 0.568704                  8.0         major_confounding               transport_deck_or_viaduct
TP_0832                 0.561928              0.449542                     0.000000                 0.561928                 16.0         major_confounding               transport_deck_or_viaduct
TP_0943                 0.541659              0.433327                     0.000000                 0.541659                 10.0         major_confounding               transport_deck_or_viaduct
TP_0830                 0.507130              0.414924                     0.092205                 0.414925                 11.0         major_confounding mixed_pedestrian_and_transport_overhead
TP_0571                 0.450632              0.341359                     0.067706                 0.382926                 11.0         major_confounding mixed_pedestrian_and_transport_overhead
TP_0575                 0.435459              0.326594                     0.000000                 0.435459                  5.0         major_confounding               transport_deck_or_viaduct
TP_0851                 0.411399              0.328939                     0.032731                 0.378668                  7.0         major_confounding mixed_pedestrian_and_transport_overhead
TP_0969                 0.393235              0.313370                     0.018039                 0.375196                  6.0         major_confounding               transport_deck_or_viaduct
TP_0858                 0.390499              0.318592                     0.061924                 0.328575                 12.0         major_confounding mixed_pedestrian_and_transport_overhead
TP_0538                 0.387284              0.291397                     0.018673                 0.368612                  8.0         major_confounding               transport_deck_or_viaduct
TP_0632                 0.381144              0.287599                     0.000000                 0.381144                  6.0         major_confounding               transport_deck_or_viaduct
```

## Interpretation
- These metrics flag overhead infrastructure separately from ground-up buildings.
- Elevated transport deck cells should not automatically be treated as pedestrian heat-risk cells.
- Covered walkway/station canopy cells may represent pedestrian adaptation infrastructure.
