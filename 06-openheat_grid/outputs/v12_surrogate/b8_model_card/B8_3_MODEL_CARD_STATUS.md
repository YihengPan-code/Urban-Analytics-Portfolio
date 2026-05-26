# B8.3 Model Card Status

Status: PASS
Branch: codex/b8-surrogate-dataset-protocol
Scope: B8.3 System B surrogate model card and promotion gate for SOLWEIG-derived System B targets.

## Commands run

- `C:/Users/CloudStar/anaconda3/envs/openheat/python.exe scripts/v12_b8_run_model_card.py --config configs/v12/systemb_surrogate_b8_model_card.yaml`

## Files created / modified

- `configs/v12/systemb_surrogate_b8_model_card.yaml`
- `scripts/v12_b8_make_model_card.py`
- `scripts/v12_b8_run_model_card.py`
- `docs/v12/OpenHeat_SystemB_surrogate_model_card_CN.md`
- `outputs/v12_surrogate/b8_model_card/model_card_metrics_summary.csv`
- `outputs/v12_surrogate/b8_model_card/promotion_gate_checklist.csv`
- `outputs/v12_surrogate/b8_model_card/split_family_decision_matrix.csv`
- `outputs/v12_surrogate/b8_model_card/feature_contract_summary.csv`
- `outputs/v12_surrogate/b8_model_card/model_card_decision_report.md`
- `outputs/v12_surrogate/b8_model_card/B8_3_MODEL_CARD_STATUS.md`

## Key results

- Candidate model: `extra_trees`.
- Primary evidence: extra_trees best by MAE on required cell/spatial splits; mean cell/spatial Spearman=0.726, mean cell top-10 overlap=0.444.
- Candidate for internal model-card review: yes.
- Approved for final AOI-wide inference: no.
- Recommended next gate: B8.5-F0 N24 x 2-3 forcing days.

## Blockers

- multi_forcing_stability NOT_TESTED
- feature_bin_typology_extrapolation PARTIAL
- topk_prioritisation_signal PARTIAL
- full_aoi_inference_readiness FAIL

## Caveats

- B8.3 reads B8.2 metrics only; it does not train or rerun benchmark models.
- N150 only.
- Single forcing setup.
- SOLWEIG-derived labels only.
- No local WBGT.
- No risk map.
- No causal feature-importance claim.
- No final AOI-wide prediction map.

## Safe to commit

- Compact B8.3 config, scripts, docs, and model-card outputs after review.

## Not safe to commit

- `data/solweig/`, `data/rasters/`, raw archive files, `.tif`, `.tiff`, `svfs.zip`, patch zip packages, large hourly forecast CSVs, AOI-wide prediction maps, local WBGT, hazard_score, risk_score, or System A/B coupling outputs.

## Next recommended action

- B8.5-F0 N24 x 2-3 forcing days before B9 full AOI inference.
