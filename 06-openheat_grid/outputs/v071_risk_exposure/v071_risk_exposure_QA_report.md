# OpenHeat v0.7.1 risk/exposure QA report

Grid cells: **986**
Cleaned nodes: **8360**

## Node counts
- bus_stop: 5166
- preschool: 2290
- mrt_exit: 597
- eldercare: 133
- hawker_centre: 129
- sport_facility: 45

## Feature summaries
- `elderly_pct_65plus`: missing=0, min=0.1265, mean=0.1961, median=0.1953, max=0.2626
- `children_pct_under5`: missing=0, min=0.0196, mean=0.0342, median=0.0341, max=0.0508
- `demographic_vulnerability_score`: missing=0, min=0.0000, mean=0.4883, median=0.4645, max=1.0000
- `node_vulnerability_score`: missing=0, min=0.0000, mean=0.3411, median=0.2486, max=1.0000
- `vulnerability_score_v071`: missing=0, min=0.0000, mean=0.4442, median=0.4344, max=1.0000
- `outdoor_exposure_score_v071`: missing=0, min=0.0000, mean=0.3886, median=0.3450, max=1.0000

## Dominant subzones in AOI
- BISHAN EAST: 162
- MARYMOUNT: 114
- TOA PAYOH CENTRAL: 106
- BALESTIER: 98
- LORONG CHUAN: 88
- TOA PAYOH WEST: 75
- LORONG 8 TOA PAYOH: 46
- BRADDELL: 43
- BOON TECK: 43
- KIM KEAT: 39
- PEI CHUN: 38
- POTONG PASIR: 35
- WOODLEIGH: 33
- BENDEMEER: 22
- SERANGOON GARDEN: 19
- SERANGOON CENTRAL: 8
- UPPER THOMSON: 7
- MALCOLM: 7
- MOUNT PLEASANT: 2
- CHONG BOON: 1

## Interpretation / limitations
- v0.7.1 uses static open-data proxies. It estimates potential vulnerability/exposure, not real-time people counts or activity-space exposure.
- Outdoor exposure nodes are static and not time-of-day weighted in v0.7.1. Peak heat exposure around 13:00-16:00 may not match node activity peaks.
- Subzone demographic vulnerability is an area-based residential proxy and may not represent where residents spend time during the day.
- Hawker centres, eldercare services and preschools are treated as vulnerable-congregation nodes, not direct outdoor-exposure nodes.
- Bus stops, MRT exits and SportSG facilities are treated as public outdoor exposure potential, not observed pedestrian counts.
