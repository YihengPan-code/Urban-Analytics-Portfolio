"""Package System A Level 1 interim model-card evidence and sample outputs.

Inputs:
    - Prior Sprint 1 to Sprint 3B reports and CSV diagnostics under outputs/v11_level1/.
    - Optional architecture/handoff docs under docs/v11/ and docs/handoff/.
    - Optional p_ge31 diagnostic prediction file:
      outputs/v11_level1/probability_calibration/p_ge31_diagnostic_predictions.csv.

Outputs:
    - docs/v11/SystemA_Level1_Interim_Model_Card_CN.md
    - configs/v11/system_a_level1_output_contract.yaml
    - outputs/v11_level1/model_card/system_a_level1_output_contract.md
    - outputs/v11_level1/model_card/system_a_level1_evidence_ledger.csv
    - outputs/v11_level1/model_card/system_a_level1_claim_boundary_matrix.csv
    - outputs/v11_level1/model_card/system_a_level1_current_recommendations.md
    - outputs/v11_level1/model_card/system_a_level1_current_outputs_sample.csv
    - outputs/v11_level1/model_card/sprint4a_model_card_integration_report.md

Saved metrics:
    - Evidence existence and CSV row counts.
    - Selected prior-sprint quantitative metrics copied from existing CSV outputs.
    - A sample output table with at most 200 rows mapped to the Sprint 4A contract.

This script does not train, fit, recalibrate, or rerun any model. It only packages
existing evidence into documentation, contract files, and a small retrospective sample.
"""

from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GENERATED_DATE = "2026-05-25"
SAMPLE_LIMIT = 200


@dataclass(frozen=True)
class EvidenceSpec:
    sprint_id: str
    artifact_type: str
    artifact_path: str
    key_models: str
    key_targets: str
    validation_schemes: str
    key_findings_short: str
    limitations_short: str
    can_support_model_card_claims: str


CONTRACT_COLUMNS = [
    "timestamp_sgt",
    "timestamp_utc",
    "station_id",
    "dataset_label",
    "wbgt_a_score_c",
    "wbgt_a_score_model_id",
    "wbgt_a_score_version",
    "p_ge31_diagnostic",
    "p_ge31_calibrator_id",
    "p_ge31_validation_context",
    "ge31_screening_flag_best_f1_optional",
    "ge31_screening_flag_high_recall_optional",
    "p_ge33_exploratory_optional",
    "is_retrospective",
    "source_prediction_context",
    "quality_flag",
    "notes",
]


def rel(path: str) -> Path:
    return ROOT / path


def ensure_dirs() -> None:
    rel("docs/v11").mkdir(parents=True, exist_ok=True)
    rel("configs/v11").mkdir(parents=True, exist_ok=True)
    rel("outputs/v11_level1/model_card").mkdir(parents=True, exist_ok=True)


def count_csv_rows(path: Path) -> str:
    if not path.exists() or path.suffix.lower() != ".csv":
        return ""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        row_count = sum(1 for _ in handle)
    return str(max(row_count - 1, 0))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def find_row(rows: list[dict[str, str]], **conditions: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in conditions.items()):
            return row
    return {}


def fmt(value: str | None, digits: int = 3) -> str:
    if value in (None, ""):
        return "unavailable"
    try:
        return f"{float(value):.{digits}f}"
    except ValueError:
        return value


def csv_has_forbidden_path(path: str) -> bool:
    lowered = path.replace("/", "\\").lower()
    forbidden = [
        ".tif",
        ".tiff",
        "data\\solweig",
        "data\\rasters",
        "raw",
        "archive",
        "hourly_grid_heatstress_forecast",
    ]
    return any(token in lowered for token in forbidden)


def get_branch_name() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or "unavailable"
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def evidence_specs() -> list[EvidenceSpec]:
    return [
        EvidenceSpec("Sprint 1", "report", "outputs/v11_level1/m2_recovery/m2_recovery_report.md", "M2 recovery", "official WBGT", "formal snapshot recovery audit", "M2 recovery passed and supports continuity of Level 1 baseline evidence.", "Report only; no new model package selected here.", "yes"),
        EvidenceSpec("Sprint 1", "report", "outputs/v11_level1/pairing_audit/station_openmeteo_pairing_report.md", "station x Open-Meteo pairing", "station forcing alignment", "pairing audit", "Station-weather pairing audit passed for Level 1 forcing context.", "Pairing correctness does not imply local 100m WBGT skill.", "yes"),
        EvidenceSpec("Sprint 1", "report", "outputs/v11_level1/reproduction/reproduction_report.md", "M3/M4/M7 ridge", "official_wbgt_c, hourly max/mean", "LOSO", "Sklearn reproduction passed with no fallback for M3/M4/M7 reference baselines.", "Regression reproduction is retrospective and station-network based.", "yes"),
        EvidenceSpec("Sprint 1", "metrics_csv", "outputs/v11_level1/reproduction/metrics_reproduction_table.csv", "M3_weather_ridge; M4_inertia_ridge; M7_compact_weather_ridge", "official_wbgt_c; official_wbgt_c_max; official_wbgt_c_mean", "LOSO", "M4 improved regression MAE/RMSE over M3/M7 in reproduced formal rows.", "Fixed threshold crossing remains weak, especially ge33.", "yes"),
        EvidenceSpec("Sprint 1b/1c", "report", "outputs/v11_level1/formal_hourly_reproduction/formal_hourly_reproduction_report.md", "M3/M4/M7 formal hourly OOF", "hourly max/mean official WBGT", "LOSO; OOF-derived", "Formal-hourly OOF reference created without retraining in Sprint 1c.", "Derived metrics depend on existing frozen OOF predictions.", "yes"),
        EvidenceSpec("Sprint 1b/1c", "report", "outputs/v11_level1/formal_hourly_reproduction/formal_hourly_oof_derived_metrics_report.md", "M3/M4/M7 formal hourly OOF", "hourly max/mean official WBGT", "LOSO; OOF-derived", "OOF-derived metrics provide the formal-hourly reference for model-card numbers.", "Not a new model run.", "yes"),
        EvidenceSpec("Sprint 1b/1c", "metrics_csv", "outputs/v11_level1/formal_hourly_reproduction/formal_hourly_oof_derived_metrics.csv", "M3/M4/M7 formal hourly OOF", "hourly max/mean official WBGT", "LOSO; OOF-derived", "M4 hourly_max MAE/RMSE/R2 and ge31 fixed-threshold diagnostics available.", "Nominal fixed-threshold crossing under-detects high WBGT.", "yes"),
        EvidenceSpec("Sprint 2A", "report", "outputs/v11_level1/feature_ablation/feature_ablation_report.md", "M4_like; M7_like; L1_full_dynamic; L1_proxy_radiation", "hourly max/mean official WBGT", "LOSO", "Dynamic feature ablation passed; M4_like remains conservative regression default.", "High-tail compression remains across feature sets.", "yes"),
        EvidenceSpec("Sprint 2A", "metrics_csv", "outputs/v11_level1/feature_ablation/feature_ablation_metrics.csv", "M4_like; M7_like; L1_full_dynamic; L1_proxy_radiation", "hourly max/mean official WBGT", "LOSO", "Ablation metrics quantify regression, fixed ge31/ge33, and high-tail residuals.", "Does not validate prospective or local-cell outputs.", "yes"),
        EvidenceSpec("Sprint 2A", "metrics_csv", "outputs/v11_level1/feature_ablation/feature_ablation_delta_vs_proxy.csv", "feature ablation candidates", "hourly max/mean official WBGT", "LOSO", "Feature blocks improve over proxy-only but do not remove tail bias.", "Delta table is diagnostic, not a deployment selector by itself.", "yes"),
        EvidenceSpec("Sprint 2A", "metrics_csv", "outputs/v11_level1/feature_ablation/feature_ablation_high_tail_metrics.csv", "feature ablation candidates", "official WBGT high tail", "LOSO", "High-tail diagnostics document underprediction under hot conditions.", "Supports caveat, not operational high-tail correction.", "yes"),
        EvidenceSpec("Sprint 2A", "metrics_csv", "outputs/v11_level1/feature_ablation/feature_ablation_per_station_metrics.csv", "feature ablation candidates", "station residuals", "LOSO", "Per-station metrics show station bias remains.", "Station residuals must not become cell modifiers.", "yes"),
        EvidenceSpec("Sprint 2B", "report", "outputs/v11_level1/blocked_time_high_tail/sprint2b_blocked_time_high_tail_report.md", "M4_like; M7_like; L1_full_dynamic", "hourly max/mean official WBGT", "blocked-date; future holdout", "Blocked-time and future-block diagnostics passed.", "Temporal robustness is not sufficient for prospective forecast claims.", "yes"),
        EvidenceSpec("Sprint 2B", "metrics_csv", "outputs/v11_level1/blocked_time_high_tail/blocked_time_metrics.csv", "M4_like; M7_like; L1_full_dynamic", "hourly max/mean official WBGT", "blocked-date CV", "Blocked-date performance weaker than LOSO and supports conservative status.", "High-tail compression persists.", "yes"),
        EvidenceSpec("Sprint 2B", "metrics_csv", "outputs/v11_level1/blocked_time_high_tail/future_holdout_metrics.csv", "M4_like; M7_like; L1_full_dynamic", "hourly max/mean official WBGT", "future holdout last block", "Future-block diagnostics are available for stress-testing.", "One historical future block is not a live prospective forecast evaluation.", "yes"),
        EvidenceSpec("Sprint 2B", "metrics_csv", "outputs/v11_level1/blocked_time_high_tail/threshold_scan_metrics.csv", "M4_like; M7_like; L1_full_dynamic", "ge31/ge33 thresholds", "blocked-date threshold scan", "Threshold scan shows fixed nominal threshold is not calibrated for events.", "Threshold offsets are diagnostic, not official advisory rules.", "yes"),
        EvidenceSpec("Sprint 2B", "metrics_csv", "outputs/v11_level1/blocked_time_high_tail/residual_by_station.csv", "M4_like; M7_like; L1_full_dynamic", "station residuals", "blocked-date CV", "Station residual diagnostics document remaining spatial/station bias.", "Must not be interpreted as local-cell adjustment.", "yes"),
        EvidenceSpec("Sprint 2B", "metrics_csv", "outputs/v11_level1/blocked_time_high_tail/s142_sensitivity_metrics.csv", "S142 sensitivity", "official WBGT high events", "blocked-date CV sensitivity", "S142 sensitivity checked because high events are station-concentrated.", "ge33 and station-heavy tails remain exploratory.", "yes"),
        EvidenceSpec("Sprint 2C", "report", "outputs/v11_level1/event_calibration/sprint2c_event_calibration_report.md", "event score thresholds", "ge31/ge32/ge33", "blocked-time threshold scan", "Event calibration established diagnostic thresholds and advisory mapping candidates.", "Thresholds are not official warnings.", "yes"),
        EvidenceSpec("Sprint 2C", "metrics_csv", "outputs/v11_level1/event_calibration/operating_point_summary.csv", "M4_like; M7_like; L1_full_dynamic", "ge31/ge32/ge33", "blocked-time operating points", "Best-F1 ge31 requires lower score threshold than nominal 31 C.", "ge33 performance is sparse and unstable.", "yes"),
        EvidenceSpec("Sprint 2C", "metrics_csv", "outputs/v11_level1/event_calibration/advisory_mapping_candidates.csv", "event score candidates", "advisory mapping", "blocked-time diagnostic", "Mapping candidates are available for reporting and research review.", "Not a public-health warning policy.", "yes"),
        EvidenceSpec("Sprint 2C", "metrics_csv", "outputs/v11_level1/event_calibration/threshold_stability_summary.csv", "event score candidates", "threshold stability", "blocked-time diagnostic", "Threshold stability informs conservative event-score caveats.", "Stability is diagnostic, not prospective validation.", "yes"),
        EvidenceSpec("Sprint 2C", "metrics_csv", "outputs/v11_level1/event_calibration/score_bin_event_rates.csv", "event score candidates", "binned event rates", "blocked-time diagnostic", "Event rates by score bin support probability-companion motivation.", "Bin monotonicity and support vary.", "yes"),
        EvidenceSpec("Sprint 2C", "metrics_csv", "outputs/v11_level1/event_calibration/event_calibration_by_station.csv", "event score candidates", "station event rates", "blocked-time diagnostic", "Station-level event calibration shows residual station bias.", "Station bias cannot be promoted to cell-level WBGT.", "yes"),
        EvidenceSpec("Sprint 3A", "report", "outputs/v11_level1/formula_v2/sprint3a_formula_v2_proxy_benchmark_report.md", "formula candidates; event scores", "hourly max official WBGT; ge31/ge33", "LOSO; future-block diagnostics", "Formula-v2 proxy benchmark passed but simple formula/k-sweep/affine candidates do not solve high-tail compression.", "No formula-v2 implementation is promoted here.", "yes"),
        EvidenceSpec("Sprint 3A", "metrics_csv", "outputs/v11_level1/formula_v2/formula_candidate_registry.csv", "existing proxy; k-sweep; affine candidates", "formula input availability", "registry/feasibility", "Advanced physics formulas remain feasibility-only without validated implementation.", "Do not implement physics formula from memory.", "yes"),
        EvidenceSpec("Sprint 3A", "metrics_csv", "outputs/v11_level1/formula_v2/formula_vs_event_score_comparison.csv", "formula candidates vs event scores", "ge31/ge33; high tail", "diagnostic comparison", "Simple formula alternatives underperform event-score diagnostics for high-tail handling.", "Companion audit only; no retroactive recalibration.", "yes"),
        EvidenceSpec("Sprint 3A", "metrics_csv", "outputs/v11_level1/formula_v2/advanced_formula_feasibility.csv", "advanced formula feasibility", "formula-v2 feasibility", "availability audit", "Advanced formula path is separated from current Level 1 package.", "Feasibility does not equal implementation.", "yes"),
        EvidenceSpec("Sprint 3B", "report", "outputs/v11_level1/probability_calibration/sprint3b_pge31_probability_calibration_report.md", "P_ge31 candidates", "ge31", "station-grouped; blocked-date calibration", "Probability calibration companion passed and selected conservative diagnostic default.", "Diagnostic probability is retrospective, not an official warning probability.", "yes"),
        EvidenceSpec("Sprint 3B", "metrics_csv", "outputs/v11_level1/probability_calibration/probability_model_selection_summary.csv", "M4_like + logistic", "ge31", "blocked-date calibration", "M4_like + logistic + blocked-date selected as conservative p_ge31_diagnostic.", "Selection is diagnostic and retrospective.", "yes"),
        EvidenceSpec("Sprint 3B", "metrics_csv", "outputs/v11_level1/probability_calibration/probability_calibration_metrics.csv", "probability calibration candidates", "ge31", "station-grouped; blocked-date", "Calibration metrics provide Brier/ECE/AUC comparison.", "Residual station bias remains.", "yes"),
        EvidenceSpec("Sprint 3B", "metrics_csv", "outputs/v11_level1/probability_calibration/probability_threshold_metrics.csv", "probability thresholds", "ge31", "probability threshold scan", "Probability threshold diagnostics available for screening flags.", "Screening flags are optional and not official advisory levels.", "yes"),
        EvidenceSpec("Sprint 3B", "metrics_csv", "outputs/v11_level1/probability_calibration/probability_vs_event_score_mapping.csv", "probability/event score mapping", "ge31", "diagnostic mapping", "Mapping relates probability output to event score for interpretation.", "Mapping should not be treated as warning policy.", "yes"),
        EvidenceSpec("Sprint 3B", "metrics_csv", "outputs/v11_level1/probability_calibration/reliability_summary.csv", "probability candidates", "ge31", "reliability bins", "Reliability summaries support caveats around monotonicity and calibration.", "Reliability varies by model/validation context.", "yes"),
        EvidenceSpec("Sprint 3B", "metrics_csv", "outputs/v11_level1/probability_calibration/probability_by_station.csv", "M4_like + logistic", "ge31", "station diagnostic", "Station probability bias examples quantify residual station effects.", "Station bias is not a cell-level modifier.", "yes"),
        EvidenceSpec("Sprint 3B", "sample_source_csv", "outputs/v11_level1/probability_calibration/p_ge31_diagnostic_predictions.csv", "M4_like + logistic", "p_ge31_diagnostic", "blocked-date calibration", "Source exists for a small contract sample export.", "Full export is not created in Sprint 4A.", "yes"),
        EvidenceSpec("Architecture docs", "doc", "docs/v11/SystemA_Level1_Level2_architecture_discussion_record_CN.md", "System A Level 1/2", "architecture boundary", "architecture discussion", "If present, would support System A/System B boundary wording.", "Missing in current checkout if exists=False.", "gap_if_missing"),
        EvidenceSpec("Architecture docs", "doc", "docs/v11/OpenHeat_SystemA_next_development_plan_GPT_Codex_CN.md", "System A plan", "development plan", "planning doc", "If present, would support next-step wording.", "Missing in current checkout if exists=False.", "gap_if_missing"),
        EvidenceSpec("Architecture docs", "doc", "docs/handoff/OpenHeat_v1_1_v1_2_canonical_development_handoff_2026-05-24.md", "canonical handoff", "v1.1/v1.2 boundary", "handoff", "Handoff exists but terminal preview may be encoding-sensitive; AGENTS guidance controls claim boundary.", "Do not rely on garbled terminal text for exact quotes.", "yes_with_encoding_caveat"),
    ]


def write_evidence_ledger(specs: list[EvidenceSpec]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for spec in specs:
        path = rel(spec.artifact_path)
        rows.append(
            {
                "sprint_id": spec.sprint_id,
                "artifact_type": spec.artifact_type,
                "artifact_path": spec.artifact_path,
                "exists": str(path.exists()),
                "row_count_if_csv": count_csv_rows(path),
                "key_models": spec.key_models,
                "key_targets": spec.key_targets,
                "validation_schemes": spec.validation_schemes,
                "key_findings_short": spec.key_findings_short,
                "limitations_short": spec.limitations_short,
                "can_support_model_card_claims": spec.can_support_model_card_claims,
            }
        )
    out_path = rel("outputs/v11_level1/model_card/system_a_level1_evidence_ledger.csv")
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_claim_boundary_matrix() -> None:
    rows = [
        {
            "claim": "System A estimates background WBGT-like heat-stress score",
            "status": "allowed_with_caveat",
            "evidence_source": "Sprint 1/1c LOSO reproduction; Sprint 2A/2B diagnostics",
            "required_wording": "System A Level 1 provides a retrospective WBGT_A background heat-stress score.",
            "forbidden_wording": "System A validates local WBGT prediction.",
            "notes": "Use WBGT-like score language; keep station-network and retrospective caveats.",
        },
        {
            "claim": "System A predicts 100m local WBGT",
            "status": "forbidden",
            "evidence_source": "Claim boundary and no Level 2/local-cell validation",
            "required_wording": "No local-cell WBGT is produced by Level 1.",
            "forbidden_wording": "100m local WBGT prediction; wbgt_cell_c; local_wbgt_c.",
            "notes": "Cell-level local WBGT is outside Sprint 4A and System A Level 1.",
        },
        {
            "claim": "P_ge31_diagnostic estimates retrospective probability of official WBGT >=31",
            "status": "allowed_with_caveat",
            "evidence_source": "Sprint 3B probability calibration",
            "required_wording": "p_ge31_diagnostic is a retrospective diagnostic probability that official station-network WBGT >=31.",
            "forbidden_wording": "Official warning probability; prospective forecast probability.",
            "notes": "Selected package: M4_like + logistic_score_calibration + blocked_date_calibration.",
        },
        {
            "claim": "P_ge31_diagnostic is an official warning probability",
            "status": "forbidden",
            "evidence_source": "Sprint 3B caveats; no public-warning validation",
            "required_wording": "Diagnostic companion only; not an official advisory.",
            "forbidden_wording": "Official warning probability; public health alert probability.",
            "notes": "No policy threshold is defined here.",
        },
        {
            "claim": "M4_like is the best LOSO regression baseline",
            "status": "allowed_with_caveat",
            "evidence_source": "Sprint 1c formal-hourly and Sprint 2A ablation metrics",
            "required_wording": "M4_like is the current conservative default regression score under retrospective LOSO/formal-hourly diagnostics.",
            "forbidden_wording": "M4_like is universally best or operationally validated.",
            "notes": "Blocked-date metrics are weaker; alternatives remain sensitivity candidates.",
        },
        {
            "claim": "M4_like is temporally robust as sole primary",
            "status": "allowed_with_caveat",
            "evidence_source": "Sprint 2B blocked-date/future-holdout diagnostics",
            "required_wording": "M4_like remains usable as current default, with blocked-time caveats and future prospective evaluation required.",
            "forbidden_wording": "M4_like has proven prospective operational robustness.",
            "notes": "Sprint 4B should design prospective forecast evaluation.",
        },
        {
            "claim": "ge33 is ready for operational use",
            "status": "forbidden",
            "evidence_source": "Sprint 2C and Sprint 3B sparse-event diagnostics",
            "required_wording": "ge33 remains exploratory only.",
            "forbidden_wording": "ge33 operational alert or reliable classifier.",
            "notes": "Sparse events and weak/unstable performance.",
        },
        {
            "claim": "Level 1 outputs can be consumed by System B as temporal severity",
            "status": "allowed_with_caveat",
            "evidence_source": "Output contract; claim boundary",
            "required_wording": "System B may consume timestamp_sgt, wbgt_a_score_c, p_ge31_diagnostic, and optional severity/screening flags as temporal severity inputs.",
            "forbidden_wording": "System B may treat Level 1 as local WBGT.",
            "notes": "System B consumption must preserve temporal-score semantics.",
        },
        {
            "claim": "Level 1 station residual can be used as cell modifier",
            "status": "forbidden",
            "evidence_source": "Sprint 2A/2B station residual diagnostics; contract forbidden outputs",
            "required_wording": "Station residuals are diagnostics only.",
            "forbidden_wording": "Station residual correction becomes cell-level WBGT modifier.",
            "notes": "Would silently upgrade Level 1 to Level 2/local-cell behavior.",
        },
        {
            "claim": "System A output is prospective forecast skill",
            "status": "forbidden",
            "evidence_source": "Retrospective validation context",
            "required_wording": "Prospective forecast skill is not yet established.",
            "forbidden_wording": "Operational forecast skill; real-time warning skill.",
            "notes": "Sprint 4B should design the prospective evaluation.",
        },
    ]
    out_path = rel("outputs/v11_level1/model_card/system_a_level1_claim_boundary_matrix.csv")
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_contract_yaml() -> None:
    text = f"""version: "v1.1-sprint4a-level1-interim"
generated_date: "{GENERATED_DATE}"
scope:
  system: "System A"
  level: "Level 1"
  geography: "Toa Payoh / station-network background context"
  status: "interim_retrospective_not_operational"
  trains_models: false
  changes_models: false
allowed_outputs:
  - name: "wbgt_a_score_c"
    model_id: "M4_like_inertia_ridge"
    interpretation: "WBGT-like background heat-stress regression score in degrees C."
    caveat: "Not calibrated nominal fixed-threshold crossing; not local WBGT."
  - name: "p_ge31_diagnostic"
    score_source: "M4_like_inertia_ridge"
    calibrator: "logistic_score_calibration"
    validation_context: "blocked_date_calibration"
    interpretation: "Retrospective diagnostic probability that official WBGT >= 31 C."
    caveat: "Not an official warning probability and not a prospective forecast."
  - name: "ge31_screening_flag_best_f1_optional"
    interpretation: "Optional diagnostic screening flag if a downstream report explicitly chooses a threshold."
    caveat: "No official advisory meaning."
  - name: "ge31_screening_flag_high_recall_optional"
    interpretation: "Optional diagnostic high-recall screening flag."
    caveat: "Expected to trade higher false alarms for recall."
  - name: "p_ge33_exploratory_optional"
    interpretation: "Exploratory ge33 diagnostic placeholder only."
    caveat: "Sparse events and unstable performance; not operational."
forbidden_outputs:
  - "cell_id"
  - "local_wbgt_c"
  - "wbgt_cell_c"
  - "delta_wbgt_cell"
  - "risk_score"
  - "m_rad"
  - "tmrt"
  - "solweig"
  - "exposure"
  - "vulnerability"
model_components:
  regression_score:
    output_name: "wbgt_a_score_c"
    model_id: "M4_like_inertia_ridge"
    target_context:
      - "hourly_max formal-hourly diagnostics"
      - "hourly_mean formal-hourly diagnostics"
    purpose: "WBGT-like background heat-stress score."
    caveat: "Not calibrated nominal fixed-threshold crossing."
  probability_companion:
    output_name: "p_ge31_diagnostic"
    score_source: "M4_like_inertia_ridge"
    calibrator: "logistic_score_calibration"
    validation_context: "blocked_date_calibration"
    purpose: "Retrospective diagnostic probability that official WBGT >= 31 C."
    caveat: "Not an official warning probability; not a prospective forecast."
  ge33:
    status: "exploratory_only"
    reason: "Sparse events and weak/unstable performance."
  sensitivity_candidates:
    - "M7_like_compact_weather_ridge"
    - "L1_full_dynamic"
    - "L1_proxy_radiation"
column_schema:
  timestamp_sgt:
    type: "datetime_with_timezone"
    required: true
    description: "Prediction timestamp in Singapore time."
  timestamp_utc:
    type: "datetime_with_timezone"
    required: true
    description: "Same timestamp converted to UTC."
  station_id:
    type: "string"
    required: true
    description: "Station identifier for Level 1 station-network diagnostics."
  dataset_label:
    type: "string"
    required: true
    allowed_examples: ["hourly_max", "hourly_mean"]
  wbgt_a_score_c:
    type: "float"
    required: true
    units: "degrees_C"
  wbgt_a_score_model_id:
    type: "string"
    required: true
    expected: "M4_like_inertia_ridge"
  wbgt_a_score_version:
    type: "string"
    required: true
  p_ge31_diagnostic:
    type: "float"
    required: false
    range: [0, 1]
  p_ge31_calibrator_id:
    type: "string"
    required: false
    expected: "logistic_score_calibration"
  p_ge31_validation_context:
    type: "string"
    required: false
    expected: "blocked_date_calibration"
  ge31_screening_flag_best_f1_optional:
    type: "boolean"
    required: false
  ge31_screening_flag_high_recall_optional:
    type: "boolean"
    required: false
  p_ge33_exploratory_optional:
    type: "float"
    required: false
    range: [0, 1]
  is_retrospective:
    type: "boolean"
    required: true
    expected: true
  source_prediction_context:
    type: "string"
    required: true
  quality_flag:
    type: "string"
    required: true
  notes:
    type: "string"
    required: false
quality_flags:
  ok_retrospective_sample: "Small retrospective sample row from prior diagnostic predictions."
  schema_only_no_source_predictions: "Contract schema emitted but no prediction source was available."
  sample_only_retrospective: "Not a full export and not operational."
  missing_probability: "Probability companion unavailable for this row."
  source_gap: "Required upstream evidence artifact was missing."
validation_context:
  regression:
    schemes:
      - "LOSO"
      - "formal-hourly OOF-derived diagnostics"
      - "blocked-date CV"
      - "future-holdout diagnostic"
    nature: "retrospective"
  probability:
    event_target: "official WBGT >= 31 C"
    selected_default: "M4_like_inertia_ridge + logistic_score_calibration + blocked_date_calibration"
    nature: "retrospective diagnostic companion"
downstream_consumers:
  research_reports: "allowed"
  System_B_temporal_severity: "allowed_with_rules"
  public_warning: "forbidden"
  health_risk_forecast: "forbidden"
system_b_consumption_rules:
  allowed:
    - "timestamp_sgt"
    - "wbgt_a_score_c"
    - "p_ge31_diagnostic"
    - "optional S_WBGT or event screening flags"
  forbidden:
    - "local WBGT"
    - "station residual as cell modifier"
    - "Level 2 station adjustment as cell value"
"""
    rel("configs/v11/system_a_level1_output_contract.yaml").write_text(text, encoding="utf-8")


def sgt_to_utc(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return ""


def write_sample_output() -> tuple[int, str]:
    source = rel("outputs/v11_level1/probability_calibration/p_ge31_diagnostic_predictions.csv")
    out_path = rel("outputs/v11_level1/model_card/system_a_level1_current_outputs_sample.csv")
    rows_out: list[dict[str, Any]] = []
    if source.exists():
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for index, row in enumerate(reader):
                if index >= SAMPLE_LIMIT:
                    break
                rows_out.append(
                    {
                        "timestamp_sgt": row.get("timestamp_sgt", ""),
                        "timestamp_utc": sgt_to_utc(row.get("timestamp_sgt", "")),
                        "station_id": row.get("station_id", ""),
                        "dataset_label": row.get("dataset_label", ""),
                        "wbgt_a_score_c": row.get("score", ""),
                        "wbgt_a_score_model_id": row.get("model_id", "M4_like_inertia_ridge"),
                        "wbgt_a_score_version": "v1.1_sprint4a_interim",
                        "p_ge31_diagnostic": row.get("p_ge31", ""),
                        "p_ge31_calibrator_id": row.get("probability_calibrator_id", "logistic_score_calibration"),
                        "p_ge31_validation_context": row.get("validation_scheme", "blocked_date_calibration"),
                        "ge31_screening_flag_best_f1_optional": "",
                        "ge31_screening_flag_high_recall_optional": "",
                        "p_ge33_exploratory_optional": "",
                        "is_retrospective": "true",
                        "source_prediction_context": "p_ge31_diagnostic_predictions_sample",
                        "quality_flag": "sample_only_retrospective",
                        "notes": "Sprint 4A sample only; source labels/official observations are not exported as contract outputs.",
                    }
                )
        note = f"Sampled {len(rows_out)} rows from {source.relative_to(ROOT).as_posix()}."
    else:
        note = "Source p_ge31 diagnostic predictions file missing; schema-only CSV written with no rows."
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CONTRACT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows_out)
    return len(rows_out), note


def collect_numbers() -> dict[str, str]:
    formal = read_csv_rows(rel("outputs/v11_level1/formal_hourly_reproduction/formal_hourly_oof_derived_metrics.csv"))
    ablation = read_csv_rows(rel("outputs/v11_level1/feature_ablation/feature_ablation_metrics.csv"))
    blocked = read_csv_rows(rel("outputs/v11_level1/blocked_time_high_tail/blocked_time_metrics.csv"))
    future = read_csv_rows(rel("outputs/v11_level1/blocked_time_high_tail/future_holdout_metrics.csv"))
    event_ops = read_csv_rows(rel("outputs/v11_level1/event_calibration/operating_point_summary.csv"))
    formula_cmp = read_csv_rows(rel("outputs/v11_level1/formula_v2/formula_vs_event_score_comparison.csv"))
    probability = read_csv_rows(rel("outputs/v11_level1/probability_calibration/probability_model_selection_summary.csv"))
    station_prob = read_csv_rows(rel("outputs/v11_level1/probability_calibration/probability_by_station.csv"))

    m4_hourly_max = find_row(formal, dataset_label="hourly_max", model="M4_inertia_ridge")
    m4_hourly_mean = find_row(formal, dataset_label="hourly_mean", model="M4_inertia_ridge")
    m4_like_ablation = find_row(ablation, dataset_label="hourly_max", ablation_model="M4_like_inertia_ridge")
    m7_like_ablation = find_row(ablation, dataset_label="hourly_max", ablation_model="M7_like_compact_weather_ridge")
    full_dynamic = find_row(ablation, dataset_label="hourly_max", ablation_model="L1_full_dynamic")
    m4_blocked = find_row(blocked, validation_scheme="blocked_date_cv", dataset_label="hourly_max", ablation_model="M4_like_inertia_ridge")
    m4_future = find_row(future, validation_scheme="future_holdout_last_block", dataset_label="hourly_max", ablation_model="M4_like_inertia_ridge")
    m4_best_f1 = find_row(
        event_ops,
        prediction_source="blocked_time",
        dataset_label="hourly_max",
        model="M4_like_inertia_ridge",
        event_target="ge31",
        operating_point="best_F1",
    )
    formula_raw = find_row(formula_cmp, source_type="best_raw_formula_candidate")
    formula_affine = find_row(formula_cmp, source_type="best_simple_affine_formula_candidate")
    prob_default = find_row(
        probability,
        model="M4_like_inertia_ridge",
        calibrator="logistic_score_calibration",
        validation_scheme="blocked_date_calibration",
    )
    station_s142 = find_row(station_prob, station_id="S142")
    station_s139 = find_row(station_prob, station_id="S139")

    return {
        "formal_hourly_max_n": m4_hourly_max.get("n", "unavailable"),
        "formal_hourly_max_station_count": m4_hourly_max.get("station_count", "unavailable"),
        "formal_hourly_max_mae": fmt(m4_hourly_max.get("mae")),
        "formal_hourly_max_rmse": fmt(m4_hourly_max.get("rmse")),
        "formal_hourly_max_r2": fmt(m4_hourly_max.get("r2")),
        "formal_hourly_max_fixed31_f1": fmt(m4_hourly_max.get("fixed_31_f1")),
        "formal_hourly_mean_mae": fmt(m4_hourly_mean.get("mae")),
        "formal_hourly_mean_rmse": fmt(m4_hourly_mean.get("rmse")),
        "formal_hourly_mean_r2": fmt(m4_hourly_mean.get("r2")),
        "m4_like_mae": fmt(m4_like_ablation.get("MAE")),
        "m4_like_rmse": fmt(m4_like_ablation.get("RMSE")),
        "m4_like_r2": fmt(m4_like_ablation.get("R2")),
        "m4_like_high_tail_bias": fmt(m4_like_ablation.get("bias_official_ge_31")),
        "m4_like_high_tail_mae": fmt(m4_like_ablation.get("MAE_official_ge_31")),
        "m7_like_mae": fmt(m7_like_ablation.get("MAE")),
        "full_dynamic_mae": fmt(full_dynamic.get("MAE")),
        "blocked_m4_mae": fmt(m4_blocked.get("MAE")),
        "blocked_m4_rmse": fmt(m4_blocked.get("RMSE")),
        "blocked_m4_r2": fmt(m4_blocked.get("R2")),
        "future_m4_mae": fmt(m4_future.get("MAE")),
        "future_m4_rmse": fmt(m4_future.get("RMSE")),
        "future_m4_r2": fmt(m4_future.get("R2")),
        "best_f1_score_threshold": fmt(m4_best_f1.get("score_threshold_c"), 1),
        "best_f1_offset": "-1.5",
        "best_f1_precision": fmt(m4_best_f1.get("precision")),
        "best_f1_recall": fmt(m4_best_f1.get("recall")),
        "best_f1_f1": fmt(m4_best_f1.get("F1")),
        "formula_raw_threshold": fmt(formula_raw.get("best_F1_threshold_ge31"), 1),
        "formula_raw_high_tail_bias": fmt(formula_raw.get("high_tail_bias")),
        "formula_affine_threshold": fmt(formula_affine.get("best_F1_threshold_ge31"), 1),
        "formula_affine_high_tail_bias": fmt(formula_affine.get("high_tail_bias")),
        "prob_brier": fmt(prob_default.get("Brier")),
        "prob_ece": fmt(prob_default.get("ECE_10")),
        "prob_roc_auc": fmt(prob_default.get("ROC_AUC")),
        "prob_avg_precision": fmt(prob_default.get("average_precision")),
        "prob_mean_p": fmt(prob_default.get("mean_predicted_probability")),
        "prob_event_rate": fmt(prob_default.get("observed_event_rate")),
        "prob_threshold_precision": fmt(prob_default.get("best_F1_train_selected_precision")),
        "prob_threshold_recall": fmt(prob_default.get("best_F1_train_selected_recall")),
        "prob_threshold_f1": fmt(prob_default.get("best_F1_train_selected_F1")),
        "s142_bias": fmt(station_s142.get("probability_bias")),
        "s142_event_rate": fmt(station_s142.get("observed_event_rate")),
        "s142_mean_p": fmt(station_s142.get("mean_predicted_probability")),
        "s139_bias": fmt(station_s139.get("probability_bias")),
        "s139_event_rate": fmt(station_s139.get("observed_event_rate")),
        "s139_mean_p": fmt(station_s139.get("mean_predicted_probability")),
    }


def write_contract_markdown() -> None:
    text = """# System A Level 1 输出契约

本契约只覆盖 System A Level 1 的临时、回顾性输出。它定义的是站点网络背景热应激分数和 ge31 诊断概率，不定义 100m 网格本地 WBGT、风险分数、SOLWEIG/Tmrt 输出或公共预警。

## 字段解释

| 字段 | 含义 | 允许解释 | 禁止解释 |
|---|---|---|---|
| timestamp_sgt | 新加坡时间戳 | Level 1 时间严重度对齐键 | 实时预警发布时间 |
| timestamp_utc | UTC 时间戳 | 跨系统/日志对齐键 | 本地微气候空间键 |
| station_id | 站点编号 | 站点网络诊断单元 | 100m cell_id |
| dataset_label | hourly_max / hourly_mean 等诊断标签 | 表明目标聚合语境 | 模型族或风险等级 |
| wbgt_a_score_c | WBGT_A 回归分数 | 背景 WBGT-like 热应激强度 | validated local WBGT 或官方 WBGT |
| wbgt_a_score_model_id | 回归分数模型 ID | 当前默认 M4_like_inertia_ridge | 模型性能证明 |
| wbgt_a_score_version | 输出版本 | 追踪 Sprint 4A 契约版本 | 训练版本或部署版本 |
| p_ge31_diagnostic | ge31 诊断概率 | 回顾性官方 WBGT >=31 的诊断概率 | 官方预警概率或前瞻 forecast 概率 |
| p_ge31_calibrator_id | 概率校准器 | logistic_score_calibration | 新模型训练声明 |
| p_ge31_validation_context | 概率验证语境 | blocked_date_calibration | 线上前瞻验证 |
| ge31_screening_flag_best_f1_optional | 可选 best-F1 筛查标记 | 研究报告中的诊断筛查 | 官方 advisory |
| ge31_screening_flag_high_recall_optional | 可选高召回筛查标记 | 研究报告中偏保守筛查 | 精准警报 |
| p_ge33_exploratory_optional | ge33 探索占位 | 仅探索性分析 | 运营输出 |
| is_retrospective | 是否回顾性 | 必须为 true | 可被理解为 live forecast |
| source_prediction_context | 来源语境 | OOF / blocked-date 诊断来源说明 | 线上生产环境 |
| quality_flag | 质量标记 | 标记样本、缺失、schema-only 等 | 风险等级 |
| notes | 备注 | 解释行级 caveat | 额外输出禁止字段 |

## 允许解释

System A Level 1 当前可以被解释为：一个站点网络背景热应激评分层。`wbgt_a_score_c` 是 WBGT-like 回归分数，`p_ge31_diagnostic` 是基于该分数的 ge31 回顾性诊断概率。它们适合用于研究报告、回顾性分析、方法比较和 System B 的时间严重度输入。

## 禁止解释

不得把任何 Level 1 字段解释为 100m cell 本地 WBGT、健康风险、公共预警、实时 forecast skill、SOLWEIG/Tmrt 结果、暴露或脆弱性结果。也不得把站点残差转写成 cell modifier。

## System B 示例用法

允许：System B 读取 `timestamp_sgt`、`wbgt_a_score_c`、`p_ge31_diagnostic`，把它们作为同一时间片下的背景热严重度门控信号，再与独立定义的辐射/形态 hazard modifier 组合。组合后的量仍应叫 hazard score 或 prioritisation score，而不是 local WBGT。

## 误用示例

禁止：把 `wbgt_a_score_c + station_residual + cell_modifier` 输出为 `local_wbgt_c`。这会把站点网络诊断分数静默升级成未验证的 100m 本地 WBGT。

## 质量标记

- `ok_retrospective_sample`: 来自既有诊断预测的小样本行。
- `sample_only_retrospective`: Sprint 4A 样本导出，不是完整运营导出。
- `schema_only_no_source_predictions`: 源预测缺失时，仅写出表头。
- `missing_probability`: 该行概率伴随输出不可用。
- `source_gap`: 上游证据文件缺失。

## 回顾性与前瞻性 caveat

本契约默认 `is_retrospective=true`。当前证据来自 LOSO、formal-hourly OOF-derived、blocked-date 和 historical future-block 诊断。它们支持回顾性诊断和报告，不支持“已经证明实时 forecast skill”。
"""
    rel("outputs/v11_level1/model_card/system_a_level1_output_contract.md").write_text(text, encoding="utf-8")


def write_recommendations() -> None:
    text = """# System A Level 1 当前推荐

## 当前回归分数

使用 `M4_like_inertia_ridge` 作为当前默认 `wbgt_a_score_c`。推荐措辞是“WBGT-like background heat-stress score”或“Level 1 背景热应激分数”，不要写成 validated local WBGT。

## 当前 P_ge31 诊断伴随输出

使用 `M4_like_inertia_ridge + logistic_score_calibration + blocked_date_calibration`，输出名为 `p_ge31_diagnostic`。它表示回顾性诊断概率：官方 WBGT >=31 的概率信号。它不是官方预警概率，也不是前瞻 forecast。

## 不应使用

- 不使用 ge33 作为运营输出；ge33 只保留探索性状态。
- 不把 M7_like、L1_full_dynamic、L1_proxy_radiation 提升为默认，只列为敏感性候选。
- 不输出 `cell_id`、`local_wbgt_c`、`wbgt_cell_c`、`delta_wbgt_cell`、`risk_score`、`m_rad`、`tmrt`、`solweig`、`exposure` 或 `vulnerability`。
- 不把 station residual 当成 cell modifier。
- 不创建完整预测大导出；Sprint 4A 只允许小样本或 schema。

## 下一步

1. Sprint 4B: 设计 prospective forecast evaluation。
2. Sprint 4C: 加固 `p_ge31_diagnostic` 导出、reliability 和质量标记。
3. Advanced formula implementation 作为独立 track，不回填本模型卡。
4. Level 2 station-context preflight 稍后再做。
5. 模型族比较等输出/前瞻边界清楚后再进入。

## 可提交内容

可提交本 Sprint 4A 的小型文档、YAML 契约、证据 ledger、claim boundary matrix、recommendations、integration report，以及 <=200 行的样本 CSV。

## 应保持本地或不纳入本 sprint 的内容

不要提交大预测导出、raw archive、raster/SOLWEIG/QGIS/v12 产物、patch zip packages、任何 `.tif/.tiff`，以及非本 sprint 需要的历史未跟踪文件。
"""
    rel("outputs/v11_level1/model_card/system_a_level1_current_recommendations.md").write_text(text, encoding="utf-8")


def write_model_card(numbers: dict[str, str], ledger_rows: list[dict[str, str]]) -> None:
    branch = get_branch_name()
    missing = [row["artifact_path"] for row in ledger_rows if row["exists"] == "False"]
    text = f"""# OpenHeat System A Level 1 Interim Model Card

## 0. Document metadata

- Project: OpenHeat-ToaPayoh
- Date: {GENERATED_DATE}
- Repo: `Urban-Analytics-Portfolio/06-openheat_grid`
- Branch: `{branch}`
- Model card status: interim / retrospective / not operational
- Covered sprints: Sprint 1, Sprint 1b/1c, Sprint 2A, Sprint 2B, Sprint 2C, Sprint 3A, Sprint 3B, Sprint 4A packaging

## 1. Intended use

Allowed:

- 回顾性 `WBGT_A` 分数分析。
- 站点网络 / AOI 背景热应激严重度描述。
- `p_ge31_diagnostic` 诊断概率伴随输出。
- System B 的 temporal severity input。
- 研究、报告、质量说明和后续评估设计。

Not intended:

- 100m 本地 WBGT。
- 公共运营预警。
- 健康风险 forecast。
- 前瞻 forecast skill claim。
- station context 或 station residual 的因果解释。

## 2. System A Level 1 architecture

System A Level 1 当前是一个站点网络背景层。输入来自冻结/既有的站点官方 WBGT 目标、Open-Meteo 动态 forcing、v09 proxy 与滞后/辐射/时间特征。输出分两层：

1. `wbgt_a_score_c`: `M4_like_inertia_ridge` 的 WBGT-like 回归分数。
2. `p_ge31_diagnostic`: 基于 `M4_like_inertia_ridge` 分数、`logistic_score_calibration`、`blocked_date_calibration` 的 ge31 回顾性诊断概率。

不包含：Level 2、System B、SOLWEIG、Tmrt、rasters、QGIS、risk map、local WBGT、exposure、vulnerability 或 formula-v2 部署。

## 3. Data and validation context

- Formal-hourly OOF-derived diagnostics: `hourly_max` / `hourly_mean`，station count {numbers["formal_hourly_max_station_count"]}，M4 `hourly_max` n={numbers["formal_hourly_max_n"]}。
- Targets: `official_wbgt_c_max` and `official_wbgt_c_mean` in hourly formal diagnostics; ge31 event target is official WBGT >=31 C.
- Validation schemes: LOSO, formal-hourly OOF-derived diagnostics, blocked-date CV, future-block diagnostic, station-grouped / blocked-date probability calibration。
- Nature: 全部为 retrospective diagnostics；不是 prospective operational validation。

Evidence gaps recorded in the ledger:

{format_missing_list(missing)}

## 4. Model components

### 4.1 WBGT_A regression score

Default model: `M4_like_inertia_ridge`。

Selected because it is the current conservative Level 1 default with strong retrospective LOSO/formal-hourly regression performance and a clear evidence chain through Sprint 1/1c/2A/2B. It should be described as a WBGT-like background heat-stress score, not as calibrated fixed-threshold crossing.

Sensitivity candidates:

- `M7_like_compact_weather_ridge`
- `L1_full_dynamic`
- `L1_proxy_radiation`

Limitations: high-tail underprediction remains, station-level bias remains, and blocked-date diagnostics are weaker than LOSO.

### 4.2 P_ge31 diagnostic companion

Default: `M4_like_inertia_ridge + logistic_score_calibration + blocked_date_calibration`，output name `p_ge31_diagnostic`。

Selected because Sprint 3B identified it as the conservative diagnostic companion: it preserves the M4_like score source, uses a simple logistic calibration layer, and uses blocked-date validation context. It estimates retrospective diagnostic probability that official WBGT >=31 C.

Limitations: not official warning probability, not prospective forecast, residual station bias remains.

### 4.3 ge33 exploratory

`ge33` remains exploratory only. The event count is sparse, fixed nominal ge33 prediction is weak/zero in several diagnostics, and threshold behavior is unstable. Do not promote ge33 to operational output.

## 5. Evidence summary by sprint

| Sprint | Purpose | Key outputs | Main finding | Impact on next step |
|---|---|---|---|---|
| Sprint 1 | M2 recovery, station pairing, M3/M4/M7 reproduction | recovery/pairing/reproduction reports and metrics | Core Level 1 evidence chain passed; no fallback in canonical reproduction | Enabled formal-hourly reference |
| Sprint 1b/1c | Formal-hourly OOF-derived reference | formal_hourly_oof_derived_metrics.csv | M4 formal-hourly metrics available without retraining | Anchored model-card regression numbers |
| Sprint 2A | Dynamic feature ablation | ablation metrics, deltas, station/high-tail diagnostics | M4_like remains conservative default; high-tail compression persists | Required event/probability companion |
| Sprint 2B | Blocked-time and high-tail diagnostics | blocked-date/future-holdout metrics | Temporal diagnostics are weaker and retrospective | Prospective evaluation remains needed |
| Sprint 2C | Event calibration | operating points, threshold stability, score bins | ge31 best-F1 requires threshold below nominal 31; ge33 weak | Motivated probability companion |
| Sprint 3A | Formula-v2 proxy benchmark | formula registry/comparison/feasibility | simple formula/k-sweep/affine candidates do not solve high-tail compression | Keep formula-v2 separate |
| Sprint 3B | P_ge31 probability calibration | model selection, metrics, reliability, predictions | selected `p_ge31_diagnostic` conservative default | Sprint 4A output contract and sample |

## 6. Key quantitative findings

- M4 formal-hourly `hourly_max`: n={numbers["formal_hourly_max_n"]}, MAE={numbers["formal_hourly_max_mae"]}, RMSE={numbers["formal_hourly_max_rmse"]}, R2={numbers["formal_hourly_max_r2"]}, fixed ge31 F1={numbers["formal_hourly_max_fixed31_f1"]}。
- M4 formal-hourly `hourly_mean`: MAE={numbers["formal_hourly_mean_mae"]}, RMSE={numbers["formal_hourly_mean_rmse"]}, R2={numbers["formal_hourly_mean_r2"]}。
- M4_like Sprint 2A `hourly_max`: MAE={numbers["m4_like_mae"]}, RMSE={numbers["m4_like_rmse"]}, R2={numbers["m4_like_r2"]}; official ge31 high-tail MAE={numbers["m4_like_high_tail_mae"]}, bias={numbers["m4_like_high_tail_bias"]}。
- Sensitivity candidates, `hourly_max` LOSO MAE: M7_like={numbers["m7_like_mae"]}, L1_full_dynamic={numbers["full_dynamic_mae"]}。
- Blocked-date M4_like `hourly_max`: MAE={numbers["blocked_m4_mae"]}, RMSE={numbers["blocked_m4_rmse"]}, R2={numbers["blocked_m4_r2"]}。
- Future-holdout M4_like `hourly_max`: MAE={numbers["future_m4_mae"]}, RMSE={numbers["future_m4_rmse"]}, R2={numbers["future_m4_r2"]}。
- ge31 best-F1 threshold for M4_like event score: score threshold {numbers["best_f1_score_threshold"]} C, offset {numbers["best_f1_offset"]} C versus nominal 31 C, precision={numbers["best_f1_precision"]}, recall={numbers["best_f1_recall"]}, F1={numbers["best_f1_f1"]}。
- Formula-v2 benchmark: best raw formula ge31 best-F1 threshold={numbers["formula_raw_threshold"]} C with high-tail bias={numbers["formula_raw_high_tail_bias"]}; best simple affine threshold={numbers["formula_affine_threshold"]} C with high-tail bias={numbers["formula_affine_high_tail_bias"]}。These candidates did not solve high-tail compression.
- Probability default `M4_like + logistic + blocked-date`: Brier={numbers["prob_brier"]}, ECE_10={numbers["prob_ece"]}, ROC_AUC={numbers["prob_roc_auc"]}, average precision={numbers["prob_avg_precision"]}, mean p={numbers["prob_mean_p"]}, observed event rate={numbers["prob_event_rate"]}。
- Probability threshold diagnostic for the default: precision={numbers["prob_threshold_precision"]}, recall={numbers["prob_threshold_recall"]}, F1={numbers["prob_threshold_f1"]}。
- Station probability bias examples: S142 event rate={numbers["s142_event_rate"]}, mean p={numbers["s142_mean_p"]}, bias={numbers["s142_bias"]}; S139 event rate={numbers["s139_event_rate"]}, mean p={numbers["s139_mean_p"]}, bias={numbers["s139_bias"]}。

## 7. Recommended output contract

Use `configs/v11/system_a_level1_output_contract.yaml` as the machine-readable contract and `outputs/v11_level1/model_card/system_a_level1_output_contract.md` as the Chinese interpretation guide.

Required conceptual outputs:

- `wbgt_a_score_c`
- `wbgt_a_score_model_id`
- `p_ge31_diagnostic`
- `p_ge31_calibrator_id`
- `p_ge31_validation_context`
- `is_retrospective`
- `quality_flag`

Forbidden conceptual outputs:

- `cell_id`, `local_wbgt_c`, `wbgt_cell_c`, `delta_wbgt_cell`, `risk_score`, `m_rad`, `tmrt`, `solweig`, `exposure`, `vulnerability`。

## 8. Known limitations

- Retrospective, not prospective。
- Station-network limited。
- High-tail compression remains。
- Nominal threshold crossing is not calibrated。
- ge33 is exploratory。
- Station-level bias remains。
- No Level 2 yet。
- No local WBGT。
- No System B integration yet。

## 9. Safety / claim boundary

Allowed claims:

- calibrated hourly WBGT temporal baseline。
- WBGT-like background heat-stress score。
- retrospective `p_ge31_diagnostic` companion。
- System B temporal severity input, with contract rules。
- first-order local heat hazard prioritisation only after System B keeps hazard-score wording.

Forbidden claims:

- validated local WBGT prediction。
- real-time heat risk forecast。
- official warning probability。
- SOLWEIG Tmrt equals WBGT。
- station residual as cell modifier。
- hazard map equals risk map。
- feature importance proves real-world causal heat-risk drivers。

## 10. Recommended next steps

1. Sprint 4B prospective forecast evaluation design。
2. Sprint 4C P_ge31 export/reliability hardening。
3. Advanced formula implementation as separate track。
4. Level 2 station-context preflight later。
5. Model-family comparison only after output/prospective boundary is clean。

## 11. File inventory

- `docs/v11/SystemA_Level1_Interim_Model_Card_CN.md`
- `configs/v11/system_a_level1_output_contract.yaml`
- `outputs/v11_level1/model_card/system_a_level1_output_contract.md`
- `outputs/v11_level1/model_card/system_a_level1_evidence_ledger.csv`
- `outputs/v11_level1/model_card/system_a_level1_claim_boundary_matrix.csv`
- `outputs/v11_level1/model_card/system_a_level1_current_recommendations.md`
- `outputs/v11_level1/model_card/system_a_level1_current_outputs_sample.csv`
- `outputs/v11_level1/model_card/sprint4a_model_card_integration_report.md`
- `scripts/v11_l1_export_system_a_output_sample.py`

## 12. Short one-paragraph summary

System A Level 1 当前应被视为一个回顾性、站点网络背景热应激评分包：默认回归输出是 `M4_like_inertia_ridge` 的 `wbgt_a_score_c`，默认概率伴随输出是 `M4_like_inertia_ridge + logistic_score_calibration + blocked_date_calibration` 的 `p_ge31_diagnostic`。它可以服务研究、报告和 System B temporal severity 输入，但不能被描述为 100m 本地 WBGT、官方预警概率、实时 forecast skill 或完整风险模型。
"""
    rel("docs/v11/SystemA_Level1_Interim_Model_Card_CN.md").write_text(text, encoding="utf-8")


def format_missing_list(missing: list[str]) -> str:
    if not missing:
        return "- No requested evidence gaps detected."
    return "\n".join(f"- Missing: `{path}`" for path in missing)


def write_integration_report(
    ledger_rows: list[dict[str, str]],
    sample_count: int,
    sample_note: str,
) -> None:
    created = [
        "docs/v11/SystemA_Level1_Interim_Model_Card_CN.md",
        "configs/v11/system_a_level1_output_contract.yaml",
        "outputs/v11_level1/model_card/system_a_level1_output_contract.md",
        "outputs/v11_level1/model_card/system_a_level1_evidence_ledger.csv",
        "outputs/v11_level1/model_card/system_a_level1_claim_boundary_matrix.csv",
        "outputs/v11_level1/model_card/system_a_level1_current_recommendations.md",
        "outputs/v11_level1/model_card/system_a_level1_current_outputs_sample.csv",
        "outputs/v11_level1/model_card/sprint4a_model_card_integration_report.md",
        "scripts/v11_l1_export_system_a_output_sample.py",
    ]
    found = [row["artifact_path"] for row in ledger_rows if row["exists"] == "True"]
    missing = [row["artifact_path"] for row in ledger_rows if row["exists"] == "False"]
    forbidden_created = [path for path in created if csv_has_forbidden_path(path)]
    text = f"""# Sprint 4A Model Card Integration Report

## Files created

{format_bullets(created)}

## Evidence sources found

Found {len(found)} evidence artifacts.

{format_bullets(found)}

## Evidence sources missing / gaps

{format_missing_list(missing)}

## Primary paths

- Model card: `docs/v11/SystemA_Level1_Interim_Model_Card_CN.md`
- Output contract YAML: `configs/v11/system_a_level1_output_contract.yaml`
- Output contract markdown: `outputs/v11_level1/model_card/system_a_level1_output_contract.md`
- Evidence ledger: `outputs/v11_level1/model_card/system_a_level1_evidence_ledger.csv`
- Claim boundary matrix: `outputs/v11_level1/model_card/system_a_level1_claim_boundary_matrix.csv`
- Sample output: `outputs/v11_level1/model_card/system_a_level1_current_outputs_sample.csv`

## Sample output

{sample_note}

Rows written: {sample_count}. Full prediction export was not created.

## Current model package definition

- Regression score: `M4_like_inertia_ridge` -> `wbgt_a_score_c`。
- Probability companion: `M4_like_inertia_ridge + logistic_score_calibration + blocked_date_calibration` -> `p_ge31_diagnostic`。
- ge33: exploratory only。
- Sensitivity candidates only: `M7_like_compact_weather_ridge`, `L1_full_dynamic`, `L1_proxy_radiation`。

## Compliance notes

- No forbidden files touched by Sprint 4A outputs: {str(not forbidden_created)}。
- Forbidden-created path check: {", ".join(forbidden_created) if forbidden_created else "none"}。
- No fallback used。
- No new model training。
- No M3/M4/M7 rerun, feature ablation rerun, formula benchmark rerun, or probability calibration rerun。
- No formula-v2 implementation。
- No System B/v12/SOLWEIG/QGIS/rasters/archive collector/GitHub Actions archive lane touched。
- No full prediction export; sample is capped at {SAMPLE_LIMIT} rows。
- No commit/stage performed by this script。

## Next recommended action

Proceed to Sprint 4B prospective forecast evaluation design, then Sprint 4C `p_ge31_diagnostic` export/reliability hardening.
"""
    rel("outputs/v11_level1/model_card/sprint4a_model_card_integration_report.md").write_text(text, encoding="utf-8")


def format_bullets(items: list[str]) -> str:
    if not items:
        return "- None."
    return "\n".join(f"- `{item}`" for item in items)


def main() -> None:
    ensure_dirs()
    specs = evidence_specs()
    ledger_rows = write_evidence_ledger(specs)
    write_claim_boundary_matrix()
    write_contract_yaml()
    write_contract_markdown()
    sample_count, sample_note = write_sample_output()
    numbers = collect_numbers()
    write_model_card(numbers, ledger_rows)
    write_recommendations()
    write_integration_report(ledger_rows, sample_count, sample_note)
    print("Sprint 4A System A Level 1 packaging complete.")
    print(f"Sample rows written: {sample_count}")


if __name__ == "__main__":
    main()
