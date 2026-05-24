# v10-delta opacity sensitivity sweep report

This sweep tests robustness of the v10-delta overhead shade sensitivity to the prior `type_opacity` values.

## Scenarios

### `low_opacity`

```text
covered_walkway          0.70
pedestrian_bridge        0.60
station_canopy           0.75
elevated_rail            0.60
elevated_road            0.55
viaduct                  0.55
unknown_overhead         0.40
```

### `default`

```text
covered_walkway          0.90
pedestrian_bridge        0.80
station_canopy           0.95
elevated_rail            0.80
elevated_road            0.75
viaduct                  0.75
unknown_overhead         0.60
```

### `high_opacity`

```text
covered_walkway          0.98
pedestrian_bridge        0.95
station_canopy           1.00
elevated_rail            0.95
elevated_road            0.90
viaduct                  0.90
unknown_overhead         0.80
```

### `pedestrian_strong`

```text
covered_walkway          0.98
pedestrian_bridge        0.95
station_canopy           1.00
elevated_rail            0.65
elevated_road            0.60
viaduct                  0.60
unknown_overhead         0.60
```

### `transport_strong`

```text
covered_walkway          0.65
pedestrian_bridge        0.55
station_canopy           0.70
elevated_rail            0.95
elevated_road            0.95
viaduct                  0.95
unknown_overhead         0.60
```

## Per-scenario aggregate stats

```text
         scenario  shade_new_mean  shade_new_std  delta_mean  delta_std  delta_max  delta_p95  n_cells_with_delta_gt_0p05  n_cells_with_delta_gt_0p10
      low_opacity        0.490949       0.242401    0.025194   0.108452        1.0   0.096981                          82                          48
          default        0.495922       0.242693    0.030167   0.117127        1.0   0.131326                         100                          64
     high_opacity        0.499080       0.243028    0.033325   0.122282        1.0   0.155281                         109                          69
pedestrian_strong        0.493475       0.242306    0.027719   0.111715        1.0   0.109109                          95                          51
 transport_strong        0.497982       0.243347    0.032227   0.122470        1.0   0.151911                         102                          70
```

## Focus cells across scenarios

Tracking 14 cells (of 14 requested):

```text
cell_id  shade_base  open_pixel_fraction_v10  shade_new__low_opacity  delta__low_opacity  shade_new__default  delta__default  shade_new__high_opacity  delta__high_opacity  shade_new__pedestrian_strong  delta__pedestrian_strong  shade_new__transport_strong  delta__transport_strong  shade_new_range
TP_0120    0.058669                 0.856594                0.058669        2.775558e-17            0.058669    2.775558e-17                 0.058669         2.775558e-17                      0.058669              2.775558e-17                     0.058669             2.775558e-17         0.000000
TP_0171    0.097824                 1.000000                0.165270        6.744588e-02            0.189795    9.197166e-02                 0.208190         1.103660e-01                      0.171401              7.357733e-02                     0.214321             1.164974e-01         0.049052
TP_0315    0.035861                 0.734540                0.113889        7.802816e-02            0.142263    1.064020e-01                 0.163543         1.276824e-01                      0.120983              8.512163e-02                     0.170637             1.347759e-01         0.056748
TP_0344    0.034412                 0.579186                0.162837        1.284247e-01            0.209537    1.751246e-01                 0.244562         2.101495e-01                      0.174512              1.400997e-01                     0.256237             2.218245e-01         0.093400
TP_0373    0.062175                 0.659393                0.171718        1.095433e-01            0.211552    1.493772e-01                 0.241427         1.792527e-01                      0.181676              1.195018e-01                     0.251386             1.892112e-01         0.079668
TP_0564    0.046361                 0.699704                0.196325        1.499647e-01            0.249114    2.027533e-01                 0.288005         2.416448e-01                      0.231597              1.852364e-01                     0.267741             2.213801e-01         0.091680
TP_0565    0.072720                 0.680769                0.072720       -2.775558e-17            0.072720   -2.775558e-17                 0.072720        -2.775558e-17                      0.072720             -2.775558e-17                     0.072720            -2.775558e-17         0.000000
TP_0572    0.068435                 0.982353                0.179332        1.108979e-01            0.218150    1.497152e-01                 0.245973         1.775383e-01                      0.201594              1.331597e-01                     0.236196             1.677615e-01         0.066640
TP_0766    0.083877                 0.685897                0.090442        6.565198e-03            0.092318    8.440969e-03                 0.093068         9.191277e-03                      0.093068              9.191277e-03                     0.089973             6.096255e-03         0.003095
TP_0888    0.039691                 0.690828                1.000000        9.603090e-01            1.000000    9.603090e-01                 1.000000         9.603090e-01                      1.000000              9.603090e-01                     1.000000             9.603090e-01         0.000000
TP_0916    0.027683                 0.742022                1.000000        9.723168e-01            1.000000    9.723168e-01                 1.000000         9.723168e-01                      1.000000              9.723168e-01                     1.000000             9.723168e-01         0.000000
TP_0945    0.000000                 0.038831                1.000000        1.000000e+00            1.000000    1.000000e+00                 1.000000         1.000000e+00                      1.000000              1.000000e+00                     1.000000             1.000000e+00         0.000000
TP_0973    0.084597                 0.397189                1.000000        9.154030e-01            1.000000    9.154030e-01                 1.000000         9.154030e-01                      1.000000              9.154030e-01                     1.000000             9.154030e-01         0.000000
TP_0986    0.080620                 0.588846                0.080620        0.000000e+00            0.080620    0.000000e+00                 0.080620         0.000000e+00                      0.080620              0.000000e+00                     0.080620             0.000000e+00         0.000000
```

## How to read this

- If `shade_new` for a focus cell varies by < 0.05 across all five scenarios, the sensitivity result for that cell is robust to opacity prior.
- If `shade_new_range` > 0.15 for a cell, the prior is a critical assumption for that cell — call this out as a limitation in dissertation.
- If `n_cells_with_delta_gt_0p10` differs by an order of magnitude between `low_opacity` and `high_opacity`, the overall fraction-affected claim is opacity-dependent.
- The `pedestrian_strong` vs `transport_strong` contrast tells you whether the v10-gamma stubborn cells move based on pedestrian or transport overhead — useful for the dual-interpretation framing.
