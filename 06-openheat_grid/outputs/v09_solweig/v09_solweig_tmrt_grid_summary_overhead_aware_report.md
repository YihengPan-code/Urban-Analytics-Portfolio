# v0.9-gamma overhead-aware SOLWEIG Tmrt aggregation report

Rows: **2478**

Tmrt time labels: `['1000', '1200', '1300', '1500', '1600', 'unknown']`

## Tmrt summary by time

                  count       mean       std        min        25%        50%        75%        max
tmrt_time_label                                                                                    
1000              245.0  38.809143  4.028551  32.617687  35.376118  38.244625  41.915226  46.518459
1200              245.0  49.763485  7.694454  35.418755  44.504639  49.960823  56.131378  62.273537
1300              245.0  49.815003  7.695377  35.561058  44.327499  50.001877  56.302307  62.526764
1500              245.0  48.074673  7.344089  35.478802  42.640469  48.103554  54.230972  60.751823
1600              245.0  42.194485  5.127995  34.255814  38.116615  41.939152  46.323166  51.760277
unknown          1253.0  45.847579  7.891148  32.617687  39.056786  45.056660  51.827583  62.526764

## Notes

- Aggregation uses open pixels based on `dsm_buildings_tile_masked.tif` and `dsm <= 0.5`.
- Tmrt time labels are parsed from HHMM near the end of filenames, avoiding confusion with year strings.
