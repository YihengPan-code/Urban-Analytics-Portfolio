# v0.9-gamma analysis: SOLWEIG Tmrt vs empirical globe-term proxy

Forcing station: **S128** (2026-05-07)

SOLWEIG rows merged: **1225**

## Hourly forcing values (S128, May 7 2026)

```
          temperature_2m  shortwave_radiation  wind_speed_10m  empirical_T_globe_c
hour_sgt                                                                          
10                  28.4                346.0            1.42                29.60
12                  30.1                750.0            1.91                32.40
13                  29.5                753.0            2.25                31.64
15                  29.0                576.0            1.97                30.74
16                  28.9                352.0            1.39                30.14
```

## Focus cell Tmrt (mean over cell pixels) by tile_type x hour

```
tile_type      clean_hazard_top  clean_shaded_reference  conservative_risk_top  open_paved_hotspot  overhead_confounded_hazard_case  social_risk_top
tmrt_hour_sgt                                                                                                                                       
10                         46.3                    32.9                   44.9                41.9                             44.4             42.7
12                         62.1                    36.0                   60.2                57.8                             59.6             59.4
13                         62.3                    36.1                   60.3                57.6                             59.7             58.8
15                         60.5                    35.9                   58.5                55.0                             57.8             55.4
16                         51.5                    34.5                   49.9                46.2                             49.3             46.7
```

## SOLWEIG_Tmrt minus empirical_T_globe (focus cell, per hour)

```
tile_type      clean_hazard_top  clean_shaded_reference  conservative_risk_top  open_paved_hotspot  overhead_confounded_hazard_case  social_risk_top
tmrt_hour_sgt                                                                                                                                       
10                        16.72                    3.32                  15.30               12.31                            14.78            13.07
12                        29.74                    3.63                  27.78               25.39                            27.16            26.97
13                        30.70                    4.48                  28.67               25.94                            28.06            27.11
15                        29.79                    5.18                  27.72               24.26                            27.06            24.69
16                        21.40                    4.36                  19.71               16.04                            19.17            16.55
```

**Reading the delta**: a positive value means SOLWEIG estimates more radiant heat 
than the empirical Stull-style proxy would predict for that hour. Negative 
means SOLWEIG accounts for shading/reflections that lower local Tmrt.

## Vegetation cooling captured by SOLWEIG

`T01_clean_hazard_top - T05_clean_shaded_reference` per hour:

```
tmrt_hour_sgt
10    13.4
12    26.1
13    26.2
15    24.6
16    17.0
```

This contrast cannot be reproduced by an empirical proxy with uniform 
atmospheric forcing per hour - it is a direct fingerprint of vegetation 
morphology being honored by SOLWEIG.

## Overhead infrastructure bias

`T01_clean_hazard_top - T06_overhead_confounded` per hour:

```
tmrt_hour_sgt
10    1.9
12    2.5
13    2.6
15    2.7
16    2.2
```

If this contrast is small, SOLWEIG is unable to distinguish overhead-confounded 
cells from clean cells - confirming the systematic blind spot for transport 
infrastructure documented elsewhere in this work.
