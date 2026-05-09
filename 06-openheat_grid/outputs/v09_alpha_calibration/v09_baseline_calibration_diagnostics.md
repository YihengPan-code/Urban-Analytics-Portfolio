# OpenHeat v0.9-alpha baseline WBGT calibration diagnostics

## Overall raw physics proxy metrics
   n  bias_pred_minus_obs      mae     rmse  p90_abs_error
2564             -1.14036 1.324787 1.949099       3.588358

## Event detection
threshold  tp  fp  fn   tn  precision  recall  f1
 WBGT>=31   0   0 268 2296        NaN     0.0 NaN
 WBGT>=33   0   0  10 2554        NaN     0.0 NaN

## Station metrics preview
 n  bias_pred_minus_obs      mae     rmse  p90_abs_error station_id                        station_name  obs_max  obs_mean
95            -0.589111 0.774654 1.295742       2.479136       S148                      Pasir Ris Walk     31.1 27.157895
95            -0.573258 0.805540 1.206101       2.235260       S124             Upper Changi Road North     30.4 27.106316
95            -0.721742 1.004191 1.569444       3.085080       S149                       Tampines Walk     31.6 27.290526
95            -0.700878 1.030138 1.464530       2.530816       S140               Choa Chu Kang Stadium     31.0 26.775789
95            -0.999955 1.072756 1.624998       3.175865       S145                MacRitchie Reservoir     31.7 26.918947
95            -0.745034 1.099286 1.564954       2.666479       S150                          Evans Road     30.9 27.018947
95            -1.031405 1.193190 1.780718       3.191065       S180                 Taman Jurong Greens     31.6 27.106316
95            -0.625669 1.198310 1.559257       2.734969       S146                         Jalan Bahar     31.2 26.763158
95            -1.210352 1.262562 1.756939       3.174414       S153               Bukit Batok Street 22     31.5 27.285263
95            -1.263828 1.277272 1.820759       3.317169       S184                Sengkang East Avenue     32.5 27.442105
95            -1.167419 1.278416 2.125119       4.420270       S151 Outward Bound Singapore(Pulau ubin)     32.2 27.461053
95            -1.255857 1.292323 1.778894       3.151858       S143                       Punggol North     32.5 27.273684

## Residual by hour preview
 hour_sgt  n  residual_mean  residual_median  residual_p90_abs  official_wbgt_mean  proxy_wbgt_mean
     0.00 27       0.217123         0.241024          0.845246           26.100000        25.882877
     0.25 27       0.203723         0.263144          0.814404           26.062963        25.859240
     0.50 27       0.197756         0.138384          0.840154           26.033333        25.835577
     0.75 27       0.169592         0.089480          0.765929           25.981481        25.811889
     1.00 27       0.167380         0.138943          0.731728           25.955556        25.788175
     1.25 27       0.173466         0.184828          0.698914           25.922222        25.748756
     1.50 27       0.190653         0.161004          0.746020           25.900000        25.709347
     1.75 27       0.222643         0.183523          0.734622           25.892593        25.669950
     2.00 54       0.201613         0.246928          0.759948           25.559259        25.357647
     2.25 27       0.116491         0.252551          0.687242           25.185185        25.068694
     2.50 27       0.099223         0.183104          0.660789           25.151852        25.052629
     2.75 27       0.093094         0.155455          0.642592           25.129630        25.036535
     3.00 27       0.079587         0.135543          0.686462           25.100000        25.020413
     3.25 27       0.093461         0.135543          0.661966           25.077778        24.984317
     3.50 27       0.129603         0.135543          0.670644           25.077778        24.948174
     3.75 27       0.176902         0.211991          0.750347           25.088889        24.911987
     4.00 27       0.198319         0.263791          0.738047           25.074074        24.875755
     4.25 27       0.160975         0.263791          0.661757           25.033333        24.872359
     4.50 27       0.097711         0.263791          0.665806           24.966667        24.868956
     4.75 27       0.071491         0.063791          0.653986           24.937037        24.865546

## Notes
- These metrics evaluate the raw screening-level physics proxy against official WBGT.
- This is a v0.9-alpha diagnostic, not final calibration or ML validation.
- Use this report to decide whether v0.9-beta linear calibration and v0.9-ML residual learning are justified.