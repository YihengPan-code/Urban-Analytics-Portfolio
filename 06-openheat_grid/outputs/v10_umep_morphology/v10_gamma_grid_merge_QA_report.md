# v10-gamma grid merge QA report

Base grid: `data\grid\toa_payoh_grid_v08_features_umep_with_veg.csv`

Morphology CSV: `data\grid\v10\toa_payoh_grid_v10_umep_morphology_with_veg.csv`

Output grid CSV: `data\grid\v10\toa_payoh_grid_v10_features_umep_with_veg.csv`

## Key column summaries

```text
              svf  svf_v08_umep_veg  delta_svf_v10_minus_v08  shade_fraction  shade_fraction_v08_umep_veg  delta_shade_v10_minus_v08  building_density  building_density_v08  v10_building_density  mean_building_height_m  mean_building_height_m_v08
count  985.000000        986.000000               985.000000      986.000000                   986.000000                 986.000000        986.000000            986.000000            986.000000              986.000000                  986.000000
mean     0.380031          0.490616                -0.110082        0.465755                     0.422549                   0.043206          0.214805              0.065906              0.214805               22.334463                   17.303592
std      0.215978          0.274930                 0.129243        0.245803                     0.275761                   0.086305          0.156040              0.112788              0.156040               19.772705                    6.443620
min      0.010397          0.024217                -0.505223        0.000000                     0.000000                  -0.282234          0.000000              0.000000              0.000000                0.000000                    0.042853
25%      0.222008          0.272418                -0.193705        0.264048                     0.192422                  -0.018342          0.088000              0.000000              0.088000               11.568450                   13.233046
50%      0.363252          0.477844                -0.051637        0.464767                     0.398839                   0.011482          0.204400              0.000000              0.204400               15.000000                   17.770020
75%      0.530007          0.712713                -0.005602        0.643978                     0.635208                   0.099229          0.316300              0.104874              0.316300               29.085862                   20.938635
max      0.948570          0.997842                 0.061182        0.978518                     0.971248                   0.337451          1.000000              0.777657              1.000000              127.233083                   41.417447
```

## Missing values

```text
svf                 1
shade_fraction      0
building_density    0
```
