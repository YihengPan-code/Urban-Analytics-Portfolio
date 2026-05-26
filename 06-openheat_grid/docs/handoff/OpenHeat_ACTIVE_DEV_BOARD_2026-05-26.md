# OpenHeat Active Development Board

## Current canonical branch

dev/systema-level1-audit

## Latest stable checkpoint

B7 N150 SOLWEIG label set complete:

- 150 cells
- 1500 merged SOLWEIG label rows
- target_version = systemb_target_family_v0_1_b5
- reference_domain_version = n150_training_future
- no local WBGT / risk / hazard_score

Known B7 facts:

- B6 N150 = 24 retained N24 + 126 new cells
- B6 full matrix rows = 1500
- B6 new-run-only matrix rows = 1260
- B7 new-run-only SOLWEIG = 1260/1260 success
- n150_focus_tmrt_summary_merged.csv = 1500 rows
- n150_base_vs_overhead_delta_merged.csv = 750 rows
- n150_modifier_targets_b5.csv = 1500 rows
- n150_merge_validation.md = 21 checks, 0 failed

## Active lanes

### Lane B8 — System B surrogate

Status: planned  
Branch: codex/b8-surrogate-dataset-protocol  
Output dir: outputs/v12_surrogate/  
Scope: B8.0 dataset audit + B8.1 validation split protocol; B8.2 baseline benchmark only after review.  
Forbidden: local WBGT, risk, hazard_score, System A/B coupling, random row split as main evidence.

### Lane A-L1H — System A high-tail

Status: planned  
Branch: codex/systema-l1h-residual-decomposition  
Output dir: outputs/v11_systema_l1_high_tail/  
Scope: A-L1H.0 residual decomposition and ge31 miss inventory; no new model search before review.  
Forbidden: archive collector changes, System B changes, claiming P_ge31 as official warning probability.

### Lane A-L2 — Station-context residual

Status: planned / waiting  
Branch: codex/systema-l2-station-context-preflight  
Output dir: outputs/v11_systema_l2_residual/  
Scope: 27-station context feature builder and residual preflight.  
Gate: start only after A-L1H.0 shows stable station-specific residual structure.

## Global forbidden paths / files

Never stage or commit:

- data/solweig/
- data/rasters/
- data/archive raw
- *.tif
- *.tiff
- svfs.zip
- large hourly forecast CSV
- outputs/*forecast_live/*hourly_grid_heatstress_forecast*.csv
- patch zip packages

## Claim boundaries

Allowed:

- System A provides retrospective calibrated WBGT_A temporal severity.
- P_ge31 may be a diagnostic companion, not official warning probability.
- System B provides SOLWEIG-derived local radiative modifier labels.
- Surrogate/emulator may approximate SOLWEIG-derived delta_tmrt_p90_c / M_rad.
- N150 labels support surrogate training / validation under current single-forcing setup.
- Full risk requires exposure + vulnerability.

Forbidden:

- validated 100m local WBGT
- Tmrt equals WBGT
- delta_tmrt_p90_c equals delta WBGT
- m_rad_pct01 as full risk
- surrogate as observed WBGT calibration
- B7 N150 labels as final AOI-wide map
- hazard_score / risk_score already completed
- feature importance as causal truth

## Latest decisions

- B8 starts with B8.0/B8.1: surrogate dataset audit + validation protocol.
- B8.2 model benchmark waits for B8.0/B8.1 review.
- A-L1H starts with A-L1H.0 residual decomposition.
- A-L1H formula/probability/model benchmarks wait for residual decomposition review.
- A-L2 waits for A-L1H.0 residual findings.
- No System A/B coupling, hazard map, risk map, exposure/vulnerability, or full AOI inference in the current sprint.

## Required lane status format

Each lane must produce a lane status file:

- outputs/v12_surrogate/B8_LANE_STATUS.md
- outputs/v11_systema_l1_high_tail/A_L1H_LANE_STATUS.md

Each status file must include:

- Status: RUNNING / PASS / BLOCKED / FAILED
- Branch
- Scope
- Commands run
- Files created / modified
- Key results
- Caveats
- Safe to commit
- Not safe to commit
- Next recommended action
