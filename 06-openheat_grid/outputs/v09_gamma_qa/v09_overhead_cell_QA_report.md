# v0.9-gamma overhead cell QA report

Grid cells: **986**

Overhead source: `outputs\v09_gamma_qa\v09_overhead_structures.geojson`

## Cell-level confounding flags

```text
overhead_confounding_flag
clean_or_minor          749
moderate_confounding    141
major_confounding        96
```

## Type-specific intersection counts

```text
covered_walkway      683
pedestrian_bridge    132
elevated_rail        577
elevated_road        138
viaduct               63
other_overhead         0
```

## Interpretation

- `overhead_fraction_cell` is an approximate footprint fraction based on buffered OSM/Overpass features.
- This is a QA/sensitivity layer, not an engineering-grade transport DSM.
- Cells flagged `major_confounding` should not be used as clean SOLWEIG reference/hazard tiles without manual inspection.
