# v10-delta overhead layer QA report

This layer is for overhead-infrastructure sensitivity. It is **not** merged into the ground-up building DSM.

Output layer: `data\features_3d\v10\overhead\overhead_structures_v10.geojson`

Features (after dedup): **952**
Total footprint area: **672186.3 m²**

## Dedup statistics

```text
input candidates:        1769
kept canonical features: 952
dropped as duplicate:    817
IoU threshold:           0.5
multi-source canonical:  789
```

## Loaded sources

```text
v09_overhead_footprints: 884 features from outputs\v09_gamma_qa\v09_overhead_structures_footprints.geojson
v09_overhead_structures: 884 features from outputs\v09_gamma_qa\v09_overhead_structures.geojson
v10_manual_overhead_candidates: 1 features from data\features_3d\v10\manual_qa\overhead_candidates_v10.geojson
```

## Overhead type counts (after dedup)

```text
    overhead_type   n
  covered_walkway 538
    elevated_rail 166
    elevated_road 127
pedestrian_bridge  83
          viaduct  38
```

## Source counts (kept canonical only)

```text
                  source_layer   n
       v09_overhead_footprints 871
       v09_overhead_structures  80
v10_manual_overhead_candidates   1
```

## Interpretation
- Elevated roads/rail/canopies are represented as separate overhead footprints.
- Each canonical feature carries `dup_sources` and `n_source_candidates` for provenance auditing.
- IoU-based dedup ensures `overhead_fraction_total` per cell is not double-counted across overlapping source layers.
- The next step is cell-level overhead metrics and shade-sensitivity analysis.
