# A-L1H.7 Snapshot Command Template

Decision status: `A_L1H7_WAITING_FOR_FORMAL_INPUT`
Current freeze mode: `dry_run`

## Dry Run

The default lane mode is dry-run. It writes inventories, schema checks,
manifests, validation rows, and reports, but it does not write a formal snapshot
data table.

```bash
python scripts/v11_l1h7_run_formal_snapshot_freezer.py --config configs/v11/systema_l1h7_formal_snapshot_freezer.yaml
```

## Write Snapshot

Only after review, set `freeze_mode: write_snapshot` in
`configs/v11/systema_l1h7_formal_snapshot_freezer.yaml` and rerun the same command. The freezer will write a compact
CSV.GZ under `outputs/v11_systema_l1_high_tail/formal_snapshot/` only if a real
candidate passes required schema, forbidden-column, numeric, metadata, quality,
prospective-row, and ge31 support checks.

```bash
python scripts/v11_l1h7_run_formal_snapshot_freezer.py --config configs/v11/systema_l1h7_formal_snapshot_freezer.yaml
```

## Standalone Validation

After a snapshot is written, validate the frozen table explicitly:

```bash
python scripts/v11_l1h7_validate_frozen_snapshot.py --config configs/v11/systema_l1h7_formal_snapshot_freezer.yaml --snapshot outputs/v11_systema_l1_high_tail/formal_snapshot/<snapshot_id>.csv.gz
```

No command in this template trains a model, modifies the archive collector, or
creates station-adjusted WBGT, local 100 m WBGT, official warning probability,
risk/hazard score, System A/B coupling output, fake rows, or fake metrics.
