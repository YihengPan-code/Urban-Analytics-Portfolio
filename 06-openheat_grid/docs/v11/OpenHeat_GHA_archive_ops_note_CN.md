# OpenHeat v1.1 GHA Archive Operations Note

**Track:** `v1.1-ops-gha-migration`  
**Purpose:** cloud archive continuity while Singapore local Windows runner is not reliable for 24/7 collection  
**Compute split:** GHA = archive lane; domestic PC = research compute lane

## 1. Role split

```text
GitHub Actions:
    best-effort scheduled archive collection;
    compact live chunks;
    run manifests;
    health summaries;
    commit guard.

Domestic PC:
    formal pass;
    formula audit;
    QGIS / UMEP / SOLWEIG;
    surrogate experiments;
    figures and reports.
```

GHA is not intended to run SOLWEIG, QGIS, or heavy raster work.

## 2. Schedule

Recommended cron:

```text
7,22,37,52 * * * *
```

Reason: avoid exact hour boundaries and approximate 15-minute attempts.

Cadence caveat:

```text
GitHub Actions scheduled workflows are best-effort. Runs can be delayed under platform load and should not be described as exact 15-minute wall-clock sensor cadence.
```

## 3. Safety design

Required workflow properties:

```text
permissions: contents: write
concurrency group: openheat-v11-archive
timeout-minutes < schedule interval
workflow_dispatch trigger for manual tests
no `git add -A`
commit only controlled archive / ops paths
run commit guard before push
```

Implemented workflow lane:

```text
.github/workflows/v11_archive_collector.yml
configs/v11/v11_archive_gha_config.example.json
scripts/v11_archive_gha_collect_once.py
scripts/v11_archive_health_summary.py
scripts/v11_archive_commit_guard.py
```

The wrapper runs the existing v11 collector in a temporary work area, disables
raw JSON and daily raw partitions for GHA, and emits only compact paired chunks
plus run manifests into controlled paths. It does not replace the collector hot
path.

Controlled paths:

```text
data/calibration/v11/live_chunks/
outputs/v11_archive_ops/
```

Run manifest fields:

```text
scheduled_at_utc
started_at_utc
completed_at_utc
source = gha
exit_code
rows_fetched
rows_added
stations_seen
warnings
api_status
commit_sha
```

Forbidden paths:

```text
*.tif
*.tiff
data/solweig/
data/rasters/
data/archive/
outputs/*forecast_live/*hourly_grid_heatstress_forecast*.csv
```

## 4. Test plan

### Stage A — local dry run

```bat
conda activate openheat
python scripts\v11_archive_commit_guard.py --repo-root . --max-mb 25
python scripts\v11_archive_health_summary.py --help
python scripts\v11_archive_commit_guard.py --help
```

### Stage B — workflow_dispatch smoke test

On GitHub:

```text
Actions → OpenHeat v1.1 archive collector → Run workflow
```

Check:

```text
- collector exits 0;
- health summary generated;
- only controlled paths committed;
- no rasters / raw archive / large CSV committed.
- run manifest written under outputs/v11_archive_ops/;
```

### Stage C — local + GHA parallel ≥3 days

Compare:

```text
rows/day
stations/day
valid timestamps
ge31/ge33 event counts
latest health summaries
```

If GHA misses runs but hourly aggregation remains healthy, document cadence caveat and continue.

### Stage D — local loop shutdown

Only stop local Windows loop after:

```text
- GHA has succeeded for ≥3 days;
- all 27 stations appear;
- commit guard passes;
- no duplicate explosion;
- domestic PC can pull and run diagnostics.
```

## 5. Troubleshooting

| Symptom | Likely cause | Response |
|---|---|---|
| Workflow delayed | GHA schedule latency | accept if health remains hourly-complete; document |
| Collector exits nonzero | API or CLI mismatch | run workflow_dispatch; inspect logs; adapt wrapper |
| Push rejected | branch protection / token permissions | enable workflow write permissions or use PR workflow |
| Large file guard fails | dangerous output path | do not override; fix `.gitignore` / staging |
| Duplicate rows | dedup key mismatch | dedup by station_id + valid timestamp, not fetch time |
| Missing stations | API or station parser issue | compare with local loop; do not stop local runner |

## 6. Required disclosure in formal docs

```text
GHA migration protects archive continuity but changes scheduling semantics from local near-15-minute loop cadence to best-effort scheduled cloud cadence. Formal v1.1 results use the frozen local-loop snapshot; later GHA archive diagnostics must disclose effective cadence.
```

## 7. GitHub setup still required

```text
- Enable Actions for the repository.
- Set workflow permissions to allow contents: write, or the commit-back step will fail.
- Optional: add DATA_GOV_SG_API_KEY if the public API starts requiring it.
- Optional: add NEA_API_KEY only if a future endpoint requires it.
- Keep the local Singapore loop running until GHA has passed the parallel convergence check.
```
