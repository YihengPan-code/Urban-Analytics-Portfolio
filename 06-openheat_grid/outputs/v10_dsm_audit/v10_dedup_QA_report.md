# v1.0-alpha.1 footprint deduplication QA

Input candidates: **6492**
Canonical buildings: **5226**
Conflict review candidates: **77**
Canonical buildings with promoted height/level/type fields: **468**

## Dedup status counts
```text
    dedup_status    n
    accepted_new 5226
 conflict_review   77
merged_duplicate 1189
```

## Canonical geometry source counts
```text
geometry_source    n
            osm 4536
          hdb3d  599
            ura   91
```

## Hotfix notes
- Duplicate candidates now promote useful OSM height / level / building-type fields into canonical records when the existing canonical record lacks them.
- Conflict-review candidates are still excluded from canonical output to avoid double-counting.
- This implementation is conservative and prioritizes provenance clarity over maximal footprint union.