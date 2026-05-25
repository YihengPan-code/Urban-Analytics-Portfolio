# OpenHeat v1.2-beta pre-scale development plan

**Document date:** 2026-05-25
**Stage:** post Core-8 v10-epsilon-forcing pilot checkpoint -> pre scale-design gate
**Scope:** development steps before `v1.2-beta-scale` sampling design
**Status:** implementation plan and gate checklist

## 0. Current state

Current status after checkpoint:

```text
v1.2-beta Core-8 SOLWEIG typology pilot checkpoint complete.
Wave 0 / Wave 1 / Core 8 base / Core 8 overhead_as_canopy / TP0542 h15 diagnostic passed.
```

Current outputs support:

```text
SOLWEIG-derived 100m mixed-cell Tmrt summaries
local radiative modifier evidence
tmrt_p90_c / delta_tmrt_p90_c / m_rad_pct target sanity
```

They do not support:

```text
local WBGT
validated 100m WBGT
hazard map
risk map
surrogate / ML result
observed truth
```

## 1. Development objective before scale design

The objective is not to add more cells immediately. The objective is to turn the Core-8 pilot into a defensible pre-scale evidence package.

Recommended sequence:

```text
v1.2-beta.2  pilot closeout + docs/index alignment
v1.2-beta.3  formal-hot-day QA plan + manifest generation
v1.2-beta.4  20-run formal-hot-day smoke, local QGIS/SOLWEIG execution
v1.2-beta.5  formal-hot-day smoke review + scale-readiness decision note
```

Only after those gates pass should `v1.2-beta-scale` sampling design begin.

## 2. Why formal-hot-day QA comes before scale design

Current Core-8 evidence is useful but forcing-limited:

```text
current forcing = v10-epsilon forcing
not formal-hot-day forcing
```

Adding more cells under the same forcing would increase sample width but would not test the most important robustness question:

```text
Does the accepted target / typology interpretation remain coherent under formal-hot-day forcing?
```

Therefore:

```text
formal-hot-day QA tests evidence robustness;
optional diagnostics only add case diversity.
```

## 3. Pre-scale gates

### Gate A - pilot closeout

Required files:

```text
docs/v12/OpenHeat_v12_SOLWEIG_typology_pilot_closeout_CN.md
docs/v12/OpenHeat_v12_formal_hotday_SOLWEIG_QA_plan_CN.md
docs/v12/OpenHeat_v12_formal_hotday_SOLWEIG_QA_runbook_CN.md
```

Acceptance criteria:

```text
- claim boundary is explicit;
- v10-epsilon forcing limitation is explicit;
- tmrt_p90_c remains accepted as primary mixed-cell upper-tail target;
- m_rad_pct remains batch-relative;
- no surrogate / hazard / risk claim is introduced.
```

### Gate B - formal-hot-day forcing provenance

Before running smoke QA, the formal-hot-day forcing files must exist and be documented.

Expected paths:

```text
data/solweig/v12_formal_hotday_forcing/v12_formal_hotday_S128_h10.txt
data/solweig/v12_formal_hotday_forcing/v12_formal_hotday_S128_h12.txt
data/solweig/v12_formal_hotday_forcing/v12_formal_hotday_S128_h13.txt
data/solweig/v12_formal_hotday_forcing/v12_formal_hotday_S128_h15.txt
data/solweig/v12_formal_hotday_forcing/v12_formal_hotday_S128_h16.txt
```

Do not commit those forcing files unless they are intentionally size-controlled and reviewed. They are local runtime inputs by default.

### Gate C - 20-run formal-hot-day smoke

Smoke matrix:

```text
5 cells x 2 hours x 2 scenarios = 20 SOLWEIG runs
```

Cells:

```text
TP_0986  high-exposure null-control
TP_0565  road-edge hot anchor
TP_0542  mapped pedestrian-overhead shade case
TP_0059  hardscape mean-vs-p90 diagnostic
TP_0835  wooded low-radiative lower anchor
```

Hours:

```text
h13, h15
```

Scenarios:

```text
base
overhead_as_canopy
```

Acceptance criteria:

```text
TP_0986: remains high; overhead p90 delta near zero.
TP_0565: remains high; overhead p90 delta near zero.
TP_0542: overhead response remains directionally interpretable.
TP_0059: mean-vs-p90 distinction remains diagnostic.
TP_0835: remains low-radiative lower anchor.
```

### Gate D - scale-readiness decision

After the smoke run:

```text
PASS:
  proceed to write scale sampling design.

CONDITIONAL:
  run optional Core-8 formal-hot-day full matrix before scale design.

FAIL:
  audit forcing, geometry, masks, SVF, scenario inputs, and aggregation.
  do not scale.
```

## 4. What Codex should do vs what local PC should do

Codex-suitable:

```text
- add docs and runbooks;
- add plan CSVs;
- add manifest-builder script;
- add comparison diagnostic script;
- run static checks / --help / manifest generation with --allow-missing-forcing;
- update docs index if present.
```

Local PC only:

```text
- generate / verify formal-hot-day forcing files;
- run QGIS preprocessing;
- run SOLWEIG through QGIS Python Console;
- aggregate real Tmrt outputs;
- review maps/rasters if diagnostics fail.
```

## 5. Do-not-commit rules

Do not commit:

```text
*.tif
*.tiff
wall_height.tif
wall_aspect.tif
svfs.zip
Tmrt_average.tif
data/solweig/
data/rasters/
raw archive
large hourly forecast CSV
patch zip packages
```

Allowed after review:

```text
docs/v12/*.md
docs/codex/*.md
configs/v12/*plan*.csv
configs/v12/*manifest*.csv
configs/v12/*config.example.json
scripts/v12_*.py
small summary CSV/MD reports
```

## 6. Recommended version labels

```text
v1.2-beta.1  Core-8 v10-epsilon-forcing pilot checkpoint, completed
v1.2-beta.2  pilot closeout + formal-hot-day QA plan
v1.2-beta.3  formal-hot-day smoke manifest + local run prep
v1.2-beta.4  formal-hot-day smoke results and review
v1.2-beta-scale-alpha  scale sampling design, only after smoke gate
```
