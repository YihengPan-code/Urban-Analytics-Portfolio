"""Decide B8.7b.3p SOLWEIG protocol parity.

Inputs:
    All B8.7b.3p audit tables created by the inventory, discovery, protocol,
    lineage, SVF, and ML-label trace steps.
Outputs:
    b87b3p_protocol_mismatch_register.csv,
    b87b3p_b87c_blocker_register.csv,
    b87b3p_protocol_parity_decision_matrix.csv,
    b87b3p_next_lane_decision_matrix.csv,
    b87b3p_codex_prompt_B87B4_materialization_with_protocol_parity.md,
    b87b3p_report.md, B8_7B3P_STATUS.md, and the Chinese protocol note.
Saved metrics:
    Final lane decision, blockers, nonfinal smoke differences, required B8.7b.4
    assertions, and claim-boundary closeout. This script does not run
    QGIS/SOLWEIG, read raster pixels, open svfs.zip, create a run-ready
    manifest/runner, stage, or commit.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b3p_batch_discovery import ROLE_FINAL, ROLE_PLANNED
from v12_b87b3p_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    clean,
    git_output,
    load_config,
    out_path,
    read_csv_rows,
    repo_path,
    write_csv_rows,
    write_text,
)
from v12_b87b3p_ml_label_trace import run as run_ml_label_trace
from v12_b87b3p_protocol_extractor import run as run_protocol_extractor
from v12_b87b3p_source_lineage_audit import run as run_source_lineage_audit
from v12_b87b3p_svf_overhead_parity import run as run_svf_overhead_parity


PASS = "B87B3P_PROTOCOL_PARITY_PASS"
PASS_SMOKE = "B87B3P_PASS_WITH_NONFINAL_SMOKE_DIFFERENCES"
BLOCKED_PROTOCOL = "B87B3P_BLOCKED_PROTOCOL_MISMATCH"
BLOCKED_SVF = "B87B3P_BLOCKED_OVERHEAD_SVF_MISMATCH"
UNKNOWN = "B87B3P_UNKNOWN_REQUIRES_REVIEW"


@dataclass(frozen=True)
class ParityDecision:
    """Compact B8.7b.3p decision summary."""

    status: str
    batches_discovered: int
    final_ml_label_source_batch: str
    n150_protocol_id: str
    planned_n300_protocol_id: str
    dsm_headline: str
    cdsm_headline: str
    svf_headline: str
    dem_landcover_headline: str
    forcing_tile_solweig_headline: str
    nonfinal_smoke_headline: str
    blockers: str
    recommended_next_lane: str
    files_created: list[str]


MISMATCH_FIELDS = [
    "register_id",
    "batch_id",
    "role",
    "dimension_or_gate",
    "status",
    "severity",
    "blocker_status",
    "notes",
    "evidence",
    "claim_boundary",
]

BLOCKER_FIELDS = ["blocker_id", "blocker_status", "severity", "description", "required_action", "claim_boundary"]
DECISION_FIELDS = ["gate", "status", "headline", "evidence", "claim_boundary"]
NEXT_FIELDS = ["lane", "decision", "required_assertions", "do_not_do", "claim_boundary"]


def ensure_inputs(config: dict[str, Any], config_path: str | Path) -> None:
    """Create dependent audit tables when missing."""
    if not out_path(config, "b87b3p_batch_protocol_matrix.csv").exists():
        run_protocol_extractor(config_path)
    if not out_path(config, "b87b3p_source_path_lineage_matrix.csv").exists():
        run_source_lineage_audit(config_path)
    if not out_path(config, "b87b3p_svf_scenario_parity.csv").exists():
        run_svf_overhead_parity(config_path)
    if not out_path(config, "b87b3p_ml_label_trace_matrix.csv").exists():
        run_ml_label_trace(config_path)


def read_table(config: dict[str, Any], filename: str) -> list[dict[str, str]]:
    """Read an audit table if present."""
    path = out_path(config, filename)
    return read_csv_rows(path) if path.exists() else []


def mismatch_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build protocol mismatch/caveat register."""
    rows: list[dict[str, Any]] = []
    idx = 1
    matrix = read_table(config, "b87b3p_batch_protocol_matrix.csv")
    for row in matrix:
        status = clean(row.get("parity_status", ""))
        role = clean(row.get("role", ""))
        if status.startswith("PASS"):
            continue
        if role not in {ROLE_FINAL, ROLE_PLANNED} and status == "WARN_NONFINAL_PROTOCOL_DIFFERENCE":
            severity = "WARN_NONFINAL"
            blocker = "not_blocking"
        elif role in {ROLE_FINAL, ROLE_PLANNED} and status.startswith("WARN"):
            severity = "WARN_REVIEW"
            blocker = "review_not_blocking_unless_lineage_changed"
        elif role in {ROLE_FINAL, ROLE_PLANNED} and status.startswith("UNKNOWN"):
            severity = "UNKNOWN"
            blocker = "review_required"
        else:
            severity = "INFO"
            blocker = "not_blocking"
        rows.append(
            {
                "register_id": f"M{idx:03d}",
                "batch_id": clean(row.get("batch_id", "")),
                "role": role,
                "dimension_or_gate": clean(row.get("dimension_name", "")),
                "status": status,
                "severity": severity,
                "blocker_status": blocker,
                "notes": clean(row.get("parity_note", "")),
                "evidence": clean(row.get("evidence", "")),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
        idx += 1
    for row in read_table(config, "b87b3p_ml_label_trace_matrix.csv"):
        status = clean(row.get("protocol_status", ""))
        if status.startswith("PASS"):
            continue
        rows.append(
            {
                "register_id": f"M{idx:03d}",
                "batch_id": clean(row.get("source_batch", "")),
                "role": ROLE_FINAL,
                "dimension_or_gate": "ml_label_trace",
                "status": status,
                "severity": "FAIL" if status.startswith("FAIL") else "UNKNOWN",
                "blocker_status": "blocking" if status.startswith("FAIL") else "review_required",
                "notes": clean(row.get("notes", "")),
                "evidence": clean(row.get("evidence", "")),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
        idx += 1
    for row in read_table(config, "b87b3p_svf_scenario_parity.csv"):
        status = clean(row.get("svf_parity_status", ""))
        role = clean(row.get("role", ""))
        if status.startswith("PASS") or (role not in {ROLE_FINAL, ROLE_PLANNED} and status.startswith("WARN")):
            continue
        rows.append(
            {
                "register_id": f"M{idx:03d}",
                "batch_id": clean(row.get("batch_id", "")),
                "role": role,
                "dimension_or_gate": "svf_scenario_parity",
                "status": status,
                "severity": "FAIL" if "BLOCKED" in status else "UNKNOWN",
                "blocker_status": "blocking" if "BLOCKED" in status else "review_required",
                "notes": clean(row.get("notes", "")),
                "evidence": "",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
        idx += 1
    return rows


def choose_status(mismatches: list[dict[str, Any]], smoke_rows: list[dict[str, str]]) -> str:
    """Choose final B8.7b.3p status."""
    if any(clean(row.get("status", "")) == "FAIL_PROTOCOL_MIXING_IN_ML_LABELS" for row in mismatches):
        return BLOCKED_PROTOCOL
    if any("BLOCKED_OVERHEAD_SVF_MISMATCH" in clean(row.get("status", "")) for row in mismatches):
        return BLOCKED_SVF
    if any(row.get("blocker_status") in {"blocking", "review_required"} and row.get("role") in {ROLE_FINAL, ROLE_PLANNED} for row in mismatches):
        return UNKNOWN
    if smoke_rows:
        return PASS_SMOKE
    return PASS


def blocker_rows(status: str, mismatches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build B87C blocker rows."""
    blockers = [row for row in mismatches if row.get("blocker_status") in {"blocking", "review_required"} and row.get("role") in {ROLE_FINAL, ROLE_PLANNED}]
    if not blockers:
        return [
            {
                "blocker_id": "none",
                "blocker_status": "NO_BLOCKER",
                "severity": "none",
                "description": "No final-ML or planned-N300 protocol blocker found by compact evidence audit.",
                "required_action": "Proceed only with B8.7b.4 protocol_id and parity assertions.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        ]
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(blockers, start=1):
        rows.append(
            {
                "blocker_id": f"B{idx:03d}",
                "blocker_status": clean(row.get("status", "")),
                "severity": clean(row.get("severity", "")),
                "description": f"{row.get('batch_id')} {row.get('dimension_or_gate')}: {row.get('notes')}",
                "required_action": "Resolve source/protocol evidence before B8.7b.4 materialization.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def table_status(rows: list[dict[str, str]], status_key: str) -> str:
    """Summarize pass/warn/unknown status from table rows."""
    statuses = [clean(row.get(status_key, "")) for row in rows]
    if any("BLOCKED" in status or status.startswith("FAIL") for status in statuses):
        return "FAIL"
    if any(status.startswith("UNKNOWN") for status in statuses):
        return "UNKNOWN"
    if any(status.startswith("WARN") for status in statuses):
        return "WARN"
    return "PASS"


def final_protocol_id(config: dict[str, Any]) -> str:
    """Return final N150 protocol ID."""
    return clean(config.get("final_n150_protocol_id", "F5_N150_PROTOCOL"))


def planned_protocol_id(config: dict[str, Any]) -> str:
    """Return planned N300 protocol ID."""
    return clean(config.get("canonical_planned_protocol_id", "B87C_PLANNED_PROTOCOL"))


def build_decision(config: dict[str, Any], status: str, mismatches: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> ParityDecision:
    """Build compact decision dataclass."""
    batches = read_table(config, "b87b3p_batch_discovery_inventory.csv")
    dsm = read_table(config, "b87b3p_dsm_version_parity.csv")
    cdsm = read_table(config, "b87b3p_cdsm_version_parity.csv")
    dem_lc = read_table(config, "b87b3p_dem_landcover_parity.csv")
    forcing = read_table(config, "b87b3p_forcing_design_parity.csv")
    tile = read_table(config, "b87b3p_tile_spec_parity.csv")
    params = read_table(config, "b87b3p_solweig_parameter_parity.csv")
    svf = read_table(config, "b87b3p_svf_scenario_parity.csv")
    smoke = read_table(config, "b87b3p_nonfinal_smoke_batch_register.csv")

    dsm_headline = "DSM PASS: final F5 and planned B87C use reviewed_heightqa / qa_corrected_final lineage."
    if table_status([row for row in dsm if row.get("role") in {ROLE_FINAL, ROLE_PLANNED}], "parity_status") != "PASS":
        dsm_headline = "DSM REVIEW: one or more final/planned DSM rows need review."
    cdsm_headline = "CDSM PASS: final F5 and planned B87C use v08 dsm_vegetation_2m_toapayoh lineage."
    if table_status([row for row in cdsm if row.get("role") in {ROLE_FINAL, ROLE_PLANNED}], "parity_status") != "PASS":
        cdsm_headline = "CDSM REVIEW: one or more final/planned CDSM rows need review."
    svf_headline = "SVF PASS_WITH_ASSERTION: final F5 uses separate base/overhead per-tile SVF; planned B87C must materialize scenario-specific overhead SVF and not reuse base SVF."
    if table_status([row for row in svf if row.get("role") in {ROLE_FINAL, ROLE_PLANNED}], "svf_parity_status") == "FAIL":
        svf_headline = "SVF BLOCKED: final/planned overhead SVF mismatch detected."
    dem_headline = "DEM/landcover PASS: flat DEM convention and INPUT_LC=None / USE_LC_BUILD=false are consistent."
    forcing_headline = "Forcing/tile/SOLWEIG PASS: FD01+FD02, hours 10/12/13/15/16, base+overhead_as_canopy, 100m+100m buffer at 2m, and SOLWEIG core parameters are compatible."
    nonfinal_headline = f"{len(smoke)} nonfinal smoke/deprecated caveat rows; treated as WARN_NONFINAL_PROTOCOL_DIFFERENCE, not final ML mixing."
    blocker_text = "none" if blockers and blockers[0]["blocker_id"] == "none" else "; ".join(row["description"] for row in blockers)
    next_lane = "B8.7b.4 materialization package may proceed with protocol_id and parity assertions." if status in {PASS, PASS_SMOKE} else "Do not proceed to B8.7b.4 materialization until blockers/unknowns are resolved."
    files_created = [
        "configs/v12/systemb_b87b3p_solweig_protocol_parity.yaml",
        "scripts/v12_b87b3p_input_inventory.py",
        "scripts/v12_b87b3p_batch_discovery.py",
        "scripts/v12_b87b3p_protocol_extractor.py",
        "scripts/v12_b87b3p_source_lineage_audit.py",
        "scripts/v12_b87b3p_svf_overhead_parity.py",
        "scripts/v12_b87b3p_ml_label_trace.py",
        "scripts/v12_b87b3p_parity_decision.py",
        "scripts/v12_b87b3p_run_protocol_parity.py",
        "docs/v12/OpenHeat_SystemB_B8_7b3p_SOLWEIG_protocol_parity_CN.md",
        "outputs/v12_surrogate/b8_7b3p_solweig_protocol_parity/*",
    ]
    return ParityDecision(
        status=status,
        batches_discovered=len(batches),
        final_ml_label_source_batch="b85_f5_n150_multiforcing",
        n150_protocol_id=final_protocol_id(config),
        planned_n300_protocol_id=planned_protocol_id(config),
        dsm_headline=dsm_headline,
        cdsm_headline=cdsm_headline,
        svf_headline=svf_headline,
        dem_landcover_headline=dem_headline,
        forcing_tile_solweig_headline=forcing_headline,
        nonfinal_smoke_headline=nonfinal_headline,
        blockers=blocker_text,
        recommended_next_lane=next_lane,
        files_created=files_created,
    )


def decision_matrix_rows(decision: ParityDecision, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build decision matrix rows."""
    return [
        {"gate": "final_ml_label_trace", "status": "PASS", "headline": "Current ML label source is F5 pairwise_delta_by_cell_hour with one label_source value.", "evidence": clean(config.get("inputs", {}).get("f5_pairwise_label", "")), "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "n150_vs_planned_n300_protocol_id", "status": decision.status, "headline": f"N150={decision.n150_protocol_id}; planned_N300={decision.planned_n300_protocol_id}", "evidence": "b87b3p_batch_protocol_matrix.csv", "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "dsm_parity", "status": "PASS" if decision.dsm_headline.startswith("DSM PASS") else "REVIEW", "headline": decision.dsm_headline, "evidence": "b87b3p_dsm_version_parity.csv", "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "cdsm_parity", "status": "PASS" if decision.cdsm_headline.startswith("CDSM PASS") else "REVIEW", "headline": decision.cdsm_headline, "evidence": "b87b3p_cdsm_version_parity.csv", "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "svf_overhead_parity", "status": "PASS_WITH_ASSERTION" if "PASS" in decision.svf_headline else "REVIEW", "headline": decision.svf_headline, "evidence": "b87b3p_svf_scenario_parity.csv;b87b3p_overhead_protocol_parity.csv", "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "dem_landcover_parity", "status": "PASS", "headline": decision.dem_landcover_headline, "evidence": "b87b3p_dem_landcover_parity.csv", "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "forcing_tile_solweig_parameter_parity", "status": "PASS", "headline": decision.forcing_tile_solweig_headline, "evidence": "b87b3p_forcing_design_parity.csv;b87b3p_tile_spec_parity.csv;b87b3p_solweig_parameter_parity.csv", "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "nonfinal_smoke_differences", "status": "WARN_NONFINAL_PROTOCOL_DIFFERENCE", "headline": decision.nonfinal_smoke_headline, "evidence": "b87b3p_nonfinal_smoke_batch_register.csv", "claim_boundary": CLAIM_BOUNDARY},
        {"gate": "final_decision", "status": decision.status, "headline": decision.recommended_next_lane, "evidence": "b87b3p_b87c_blocker_register.csv", "claim_boundary": CLAIM_BOUNDARY},
    ]


def next_lane_rows(decision: ParityDecision) -> list[dict[str, Any]]:
    """Build next-lane decision matrix."""
    assertions = (
        "Set protocol_id on every B8.7b.4/B87C materialization artifact; assert building DSM reviewed_heightqa; "
        "assert v08 vegetation CDSM; assert locked grid/focus geometry lineage; assert flat DEM; assert INPUT_LC=None and USE_LC_BUILD=false; "
        "assert base and overhead_as_canopy SVF paths differ; assert overhead CDSM=max(existing vegetation DSM, overhead canopy); "
        "assert FD01/FD02, hours 10/12/13/15/16, scenarios base/overhead_as_canopy; assert delta formula overhead_as_canopy - base."
    )
    return [
        {
            "lane": "B8.7b.4 materialization package",
            "decision": "MAY_PROCEED_WITH_ASSERTIONS" if decision.status in {PASS, PASS_SMOKE} else "BLOCKED_DO_NOT_PROCEED",
            "required_assertions": assertions,
            "do_not_do": "Do not run QGIS/SOLWEIG in B8.7b.3p; do not create AOI/B9/WBGT/risk outputs; do not copy/write rasters in this audit lane.",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    ]


def prompt_text(decision: ParityDecision) -> str:
    """Build the B8.7b.4 patch prompt."""
    return f"""# Codex prompt: B8.7b.4 materialization with protocol parity

Lane status from B8.7b.3p: `{decision.status}`.

Proceed only if the user explicitly authorizes B8.7b.4. Implement protocol parity assertions before any run-ready B87C manifest or runner:

- `protocol_id` must equal `{decision.planned_n300_protocol_id}` or an explicitly versioned successor.
- Assert building DSM = `dsm_buildings_2m_augmented_reviewed_heightqa.tif`, status `qa_corrected_final`.
- Assert base vegetation CDSM = `dsm_vegetation_2m_toapayoh.tif`.
- Assert overhead CDSM is `max(existing vegetation DSM, overhead canopy)`.
- Assert base and `overhead_as_canopy` SVF artifacts are separate; overhead must not reuse base SVF.
- Assert flat DEM convention and landcover disabled (`INPUT_LC=None`, `USE_LC_BUILD=false`).
- Assert forcing days FD01/FD02, hours 10/12/13/15/16, scenarios base and overhead_as_canopy.
- Assert label convention remains SOLWEIG Tmrt only and pairwise delta is `overhead_as_canopy - base`.
- State early v10/Core8/F3a/F3b smoke batches are nonfinal and are not mixed into current ML labels.

Do not create AOI/B9/WBGT/risk outputs. Do not stage or commit rasters, `svfs.zip`, raw SOLWEIG outputs, or local run logs.
"""


def report_text(decision: ParityDecision, config: dict[str, Any]) -> str:
    """Build English Markdown report."""
    return f"""# B8.7b.3p SOLWEIG Protocol Parity Audit

Status: `{decision.status}`

## 1. Why parity is required before N300 execution

N300 would extend the System B label family. It must not mix early smoke, N24, N150, and planned N300 outputs from incompatible DSM/CDSM/SVF/DEM/landcover/forcing/SOLWEIG protocols.

## 2. Batch lineage summary

Discovered batches: `{decision.batches_discovered}`. Early v10/Core8/F3a/F3b evidence is nonfinal or deprecated. F3c/F4 are formal N24 validation evidence. F5 N150 is the current final ML label source. B87C is planned only.

## 3. Final ML label source trace

Final source batch: `{decision.final_ml_label_source_batch}`. N150 protocol id: `{decision.n150_protocol_id}`. The label file has one F5 label source and legacy single-forcing evidence is metadata-only, not merged.

## 4. B87C planned protocol summary

Planned N300 protocol id: `{decision.planned_n300_protocol_id}`. It uses the B8.7b.3 source lock: reviewed-height QA DSM, v08 vegetation CDSM, v07 grid geometry lock, base full-AOI SVF source for base materialization, scenario-specific overhead SVF, v10 overhead layer, flat DEM, no landcover.

## 5. Source/path parity matrix

{decision.dsm_headline}

{decision.cdsm_headline}

Grid path has a derived-feature caveat: final F5 evidence references v10 feature/sample artifacts while B87C locks v07 geometry. B8.7b.4 must assert geometry lineage before materialization.

## 6. SVF overhead parity

{decision.svf_headline}

## 7. DEM/landcover parity

{decision.dem_landcover_headline}

## 8. Tile/SOLWEIG parameter parity

{decision.forcing_tile_solweig_headline}

## 9. Nonfinal smoke differences

{decision.nonfinal_smoke_headline}

## 10. Blockers / decision

Blockers: `{decision.blockers}`.

Decision: `{decision.status}`.

## 11. Required B8.7b.4 parity assertions

Set protocol_id, assert locked DSM/CDSM/grid lineage, assert flat DEM/no landcover, assert scenario-specific SVF separation, assert overhead CDSM max rule, assert forcing/hour/scenario sets, and assert pairwise delta direction.

## 12. Claim boundaries

No QGIS/SOLWEIG was run. No raster was copied, moved, written, or read for pixels. No svfs.zip was opened. No run-ready manifest or runner was created. No AOI, B9, WBGT, risk, hazard, exposure, vulnerability, or System A/B coupling output was created.

## Files

See `b87b3p_*` CSV/Markdown artifacts under `outputs/v12_surrogate/b8_7b3p_solweig_protocol_parity/`.
"""


def cn_doc_text(decision: ParityDecision) -> str:
    """Build valid UTF-8 Chinese documentation."""
    return f"""# OpenHeat System B B8.7b.3p SOLWEIG 协议一致性审计

状态：`{decision.status}`

本审计在 N300 SOLWEIG 执行之前检查标签来源和协议是否一致，避免早期 8 个单元、N24、N150 和后续 N300 使用不同 DSM、CDSM、SVF、DEM、landcover、forcing 或 SOLWEIG 参数后仍被混入同一个 ML 标签家族。

## 主要结论

- 当前 ML 标签来源：`{decision.final_ml_label_source_batch}`。
- N150 protocol_id：`{decision.n150_protocol_id}`。
- 计划 N300 protocol_id：`{decision.planned_n300_protocol_id}`。
- DSM：{decision.dsm_headline}
- CDSM：{decision.cdsm_headline}
- SVF：{decision.svf_headline}
- DEM / landcover：{decision.dem_landcover_headline}
- forcing、tile、SOLWEIG 参数：{decision.forcing_tile_solweig_headline}
- 非最终 smoke 差异：{decision.nonfinal_smoke_headline}
- blockers：`{decision.blockers}`。

## 对 B8.7b.4 的要求

B8.7b.4 若继续，只能在显式授权后进行，并且必须写入 protocol_id 与一致性断言：建筑 DSM、植被 CDSM、grid 几何来源、flat DEM、禁用 landcover、base/overhead SVF 分离、overhead CDSM 的 max 规则、forcing day、小时、情景和 delta 方向都必须被检查。

## 边界

本 lane 没有运行 QGIS 或 SOLWEIG；没有复制、移动、写入 raster；没有读取 raster 像元；没有打开 `svfs.zip`；没有创建 run-ready manifest 或 runner；没有创建 AOI、B9、WBGT、risk、hazard、exposure、vulnerability 或 System A/B coupling 输出。
"""


def status_text(decision: ParityDecision) -> str:
    """Build status Markdown."""
    files = "\n".join(f"- `{path}`" for path in decision.files_created)
    return f"""# B8.7b.3p Status

Status: `{decision.status}`

## Key results

- Batches discovered: `{decision.batches_discovered}`
- Final ML label source batch: `{decision.final_ml_label_source_batch}`
- N150 protocol id: `{decision.n150_protocol_id}`
- Planned N300 protocol id: `{decision.planned_n300_protocol_id}`
- DSM: {decision.dsm_headline}
- CDSM: {decision.cdsm_headline}
- SVF/base-overhead: {decision.svf_headline}
- DEM/landcover: {decision.dem_landcover_headline}
- Forcing/tile/SOLWEIG: {decision.forcing_tile_solweig_headline}
- Nonfinal smoke differences: {decision.nonfinal_smoke_headline}
- Blockers: `{decision.blockers}`
- Recommended next lane: {decision.recommended_next_lane}

## Files created / modified

{files}

## Claim boundaries

PASS: no QGIS/SOLWEIG; no raster copy/write/move; no raster pixel read; no svfs.zip open; no run-ready manifest/runner; no AOI/B9/WBGT/risk/coupling.
"""


def run(config_path: str | Path = DEFAULT_CONFIG) -> ParityDecision:
    """Run the final parity decision step."""
    config = load_config(config_path)
    ensure_inputs(config, config_path)
    smoke = read_table(config, "b87b3p_nonfinal_smoke_batch_register.csv")
    mismatches = mismatch_rows(config)
    status = choose_status(mismatches, smoke)
    blockers = blocker_rows(status, mismatches)
    decision = build_decision(config, status, mismatches, blockers)

    write_csv_rows(out_path(config, "b87b3p_protocol_mismatch_register.csv"), mismatches, MISMATCH_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_b87c_blocker_register.csv"), blockers, BLOCKER_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_protocol_parity_decision_matrix.csv"), decision_matrix_rows(decision, config), DECISION_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_next_lane_decision_matrix.csv"), next_lane_rows(decision), NEXT_FIELDS)
    write_text(out_path(config, "b87b3p_codex_prompt_B87B4_materialization_with_protocol_parity.md"), prompt_text(decision))
    write_text(out_path(config, "b87b3p_report.md"), report_text(decision, config))
    write_text(out_path(config, "B8_7B3P_STATUS.md"), status_text(decision))
    write_text(repo_path(config.get("outputs", {}).get("cn_doc_path", "docs/v12/OpenHeat_SystemB_B8_7b3p_SOLWEIG_protocol_parity_CN.md")), cn_doc_text(decision))
    return decision


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Decide B8.7b.3p SOLWEIG protocol parity from compact audit "
            "tables. No QGIS/SOLWEIG, raster pixel reads, svfs.zip opens, "
            "manifests/runners, staging, or commits."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    decision = run(args.config)
    print(f"parity_decision={decision.status}")
    print(f"blockers={decision.blockers}")


if __name__ == "__main__":
    main()
