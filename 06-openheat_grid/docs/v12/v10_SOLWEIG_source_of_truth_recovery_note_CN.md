# v10 SOLWEIG source-of-truth recovery note for v1.2

## Confirmed source of truth

The v1.2 Wave 0 technical smoke test should reuse the v10-epsilon source-of-truth:

```text
building DSM:
  data/rasters/v10/dsm_buildings_2m_augmented_reviewed_heightqa.tif

vegetation DSM:
  data/rasters/v08/dsm_vegetation_2m_toapayoh.tif

overhead layer:
  data/features_3d/v10/overhead/overhead_structures_v10.geojson

forcing:
  data/solweig/v09_met_forcing_2026_05_07_S128_h{10,12,13,15,16}.txt

SOLWEIG execution:
  QGIS Python Console
  processing.run("umep:Outdoor Thermal Comfort: SOLWEIG", params)

critical parameter:
  INPUTMET, not INPUT_MET
```

## Why Wave 0 reuses v10 E02

`TP_0986` / `E02_confident_hot_anchor_2_TP_0986` is the clean null-control from v10-epsilon.
It has existing Wall H/A and SVF outputs, so it is the lowest-risk way to verify that QGIS/UMEP/SOLWEIG still runs.

Wave 0 writes new v12 outputs and does not overwrite v10-epsilon outputs.

## What remains outside Git

Rasters, SOLWEIG outputs, SVF folders, and raw `.tif` files remain local artifacts.
