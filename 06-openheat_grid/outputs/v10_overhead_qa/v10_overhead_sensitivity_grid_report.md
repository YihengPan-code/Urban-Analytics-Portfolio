# v10-delta overhead shade sensitivity grid report

Input grid: `data\grid\v10\toa_payoh_grid_v10_features_umep_with_veg.csv`

Output sensitivity grid: `data\grid\v10\toa_payoh_grid_v10_features_overhead_sensitivity.csv`

## Scope alignment

- overhead proxy rescaled from cell-area scope to open-pixel scope using `open_pixel_fraction_v10`.
- Method: `open_pixel_scope`

## Shade sensitivity summary

```text
       shade_fraction  shade_fraction_base_v10  shade_fraction_overhead_sens  overhead_shade_proxy_cell_scope  overhead_shade_proxy_open_scope  delta_shade_overhead_sens_minus_base  overhead_fraction_total
count      986.000000               986.000000                    986.000000                       986.000000                       986.000000                          9.860000e+02               986.000000
mean         0.495922                 0.465755                      0.495922                         0.038409                         0.043748                          3.016707e-02                 0.046232
std          0.242693                 0.245803                      0.242693                         0.122837                         0.135973                          1.171267e-01                 0.139607
min          0.011139                 0.000000                      0.011139                         0.000000                         0.000000                         -5.551115e-17                 0.000000
25%          0.301728                 0.264048                      0.301728                         0.000000                         0.000000                          0.000000e+00                 0.000000
50%          0.496380                 0.464767                      0.496380                         0.000000                         0.000000                          2.775558e-17                 0.000000
75%          0.669048                 0.643978                      0.669048                         0.021039                         0.027665                          1.142882e-02                 0.024800
max          1.000000                 0.978518                      1.000000                         1.000000                         1.000000                          1.000000e+00                 1.000000
```

## Top cells by overhead shade increment

```text
cell_id  shade_fraction_base_v10  shade_fraction_overhead_sens  delta_shade_overhead_sens_minus_base  overhead_fraction_total  overhead_shade_proxy_cell_scope  overhead_shade_proxy_open_scope overhead_confounding_flag                 overhead_interpretation
TP_0945                 0.000000                      1.000000                              1.000000                 0.738418                         0.590735                         1.000000         major_confounding               transport_deck_or_viaduct
TP_0831                 0.010117                      1.000000                              0.989883                 1.000000                         1.000000                         1.000000         major_confounding mixed_pedestrian_and_transport_overhead
TP_0916                 0.027683                      1.000000                              0.972317                 1.000000                         1.000000                         1.000000         major_confounding               transport_deck_or_viaduct
TP_0803                 0.034356                      0.997311                              0.962955                 1.000000                         0.872564                         0.997215         major_confounding               transport_deck_or_viaduct
TP_0888                 0.039691                      1.000000                              0.960309                 1.000000                         1.000000                         1.000000         major_confounding mixed_pedestrian_and_transport_overhead
TP_0746                 0.052097                      1.000000                              0.947903                 1.000000                         1.000000                         1.000000         major_confounding               transport_deck_or_viaduct
TP_0887                 0.055156                      1.000000                              0.944844                 1.000000                         1.000000                         1.000000         major_confounding mixed_pedestrian_and_transport_overhead
TP_0859                 0.057780                      1.000000                              0.942220                 1.000000                         1.000000                         1.000000         major_confounding mixed_pedestrian_and_transport_overhead
TP_0973                 0.084597                      1.000000                              0.915403                 0.863881                         0.691104                         1.000000         major_confounding               transport_deck_or_viaduct
TP_0860                 0.095767                      1.000000                              0.904233                 1.000000                         0.900275                         1.000000         major_confounding mixed_pedestrian_and_transport_overhead
TP_0717                 0.106826                      1.000000                              0.893174                 1.000000                         1.000000                         1.000000         major_confounding               transport_deck_or_viaduct
TP_0944                 0.108351                      1.000000                              0.891649                 1.000000                         0.866772                         1.000000         major_confounding               transport_deck_or_viaduct
TP_0915                 0.238648                      0.852704                              0.614056                 0.949624                         0.759699                         0.806534         major_confounding               transport_deck_or_viaduct
TP_0972                 0.136315                      0.742503                              0.606189                 0.837961                         0.670369                         0.701863         major_confounding               transport_deck_or_viaduct
TP_0088                 0.016589                      0.556837                              0.540248                 0.732482                         0.549361                         0.549361         major_confounding               transport_deck_or_viaduct
TP_0974                 0.500502                      1.000000                              0.499498                 0.742172                         0.593738                         1.000000         major_confounding               transport_deck_or_viaduct
TP_0832                 0.086967                      0.528730                              0.441764                 0.561928                         0.449542                         0.483842         major_confounding               transport_deck_or_viaduct
TP_0774                 0.245759                      0.666873                              0.421114                 0.691200                         0.552960                         0.558328         major_confounding               transport_deck_or_viaduct
TP_0802                 0.244829                      0.618662                              0.373834                 0.618789                         0.495031                         0.495031         major_confounding               transport_deck_or_viaduct
TP_0431                 0.210218                      0.562976                              0.352759                 0.592219                         0.446653                         0.446653         major_confounding               transport_deck_or_viaduct
TP_0943                 0.209795                      0.552212                              0.342417                 0.541659                         0.433327                         0.433327         major_confounding               transport_deck_or_viaduct
TP_0830                 0.253411                      0.567416                              0.314005                 0.507130                         0.414924                         0.420586         major_confounding mixed_pedestrian_and_transport_overhead
TP_0946                 0.601687                      0.910152                              0.308465                 0.568704                         0.454963                         0.774430         major_confounding               transport_deck_or_viaduct
TP_0575                 0.081150                      0.381241                              0.300091                 0.435459                         0.326594                         0.326594         major_confounding               transport_deck_or_viaduct
TP_0822                 0.146092                      0.410513                              0.264421                 0.330874                         0.262954                         0.309660         major_confounding mixed_pedestrian_and_transport_overhead
TP_0089                 0.103921                      0.365529                              0.261608                 0.376595                         0.282446                         0.291948         major_confounding               transport_deck_or_viaduct
TP_0571                 0.248297                      0.508365                              0.260068                 0.450632                         0.341359                         0.345972         major_confounding mixed_pedestrian_and_transport_overhead
TP_0037                 0.411348                      0.669097                              0.257749                 0.217888                         0.196099                         0.437863         major_confounding                pedestrian_shelter_shade
TP_0460                 0.059373                      0.300006                              0.240633                 0.341096                         0.255822                         0.255822         major_confounding               transport_deck_or_viaduct
TP_0917                 0.072266                      0.310238                              0.237972                 0.192216                         0.153773                         0.256509         major_confounding               transport_deck_or_viaduct
```

## Interpretation
- This grid is an overhead-shade sensitivity scenario, not a final overhead-aware physical model.
- Use it to test whether ground-level overhead shading materially changes hotspot ranking.
- Transport deck heat is not represented; elevated expressway/rail cells should be flagged separately.
- The overhead proxy is rescaled to open-pixel scope to match the scope of the UMEP shade fraction it modifies.
