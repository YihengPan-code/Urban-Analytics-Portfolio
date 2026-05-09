# Uploaded v0.8-beta UMEP with vegetation morphology initial QA

Rows: **986**
Columns: **29**
Duplicate `cell_id`: **0**

## Critical columns
- `svf_umep_mean_open_with_veg`: missing=0, min=0.0242, mean=0.4906, median=0.4778, p75=0.7127, max=0.9978
- `shade_fraction_umep_10_16_open_with_veg`: missing=0, min=0.0000, mean=0.4225, median=0.3988, p75=0.6352, max=0.9712
- `shade_fraction_umep_13_15_open_with_veg`: missing=0, min=0.0000, mean=0.3987, median=0.3676, p75=0.6041, max=0.9700
- `open_pixel_fraction`: missing=0, min=0.0936, mean=0.9254, median=1.0000, p75=1.0000, max=1.0000
- `building_pixel_fraction`: missing=0, min=0.0000, mean=0.0746, median=0.0000, p75=0.1187, max=0.9064

## Building-only vs building+canopy delta
- `svf_umep_mean_open_with_veg` minus `svf_umep_mean_open`: mean=-0.3728, median=-0.3381, p25=-0.5526, p75=-0.1548, min=-0.9700, max=-0.0000, correlation=0.3820
- `shade_fraction_umep_10_16_open_with_veg` minus `shade_fraction_umep_10_16_open`: mean=0.3732, median=0.3304, p25=0.1449, p75=0.5719, min=0.0000, max=0.9700, correlation=0.1646
- `shade_fraction_umep_13_15_open_with_veg` minus `shade_fraction_umep_13_15_open`: mean=0.3743, median=0.3343, p25=0.1424, p75=0.5795, min=0.0000, max=0.9700, correlation=0.0662

## Interpretation
- Building+canopy UMEP sharply lowers open-pixel SVF and sharply increases shade fraction relative to building-only UMEP.
- The values are plausible for a vegetation-inclusive equatorial morphology layer, but they must be interpreted as canopy-aware morphology rather than full Tmrt simulation.