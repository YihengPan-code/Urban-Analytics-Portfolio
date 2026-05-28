"""Discover and classify SOLWEIG protocol batches for B8.7b.3p.

Inputs:
    B8.7b.3p config plus compact manifests/status files from v10-epsilon,
    B8.5-F3/F4/F5, B8.6/B8.7, and B87C precheck lanes when present.
Outputs:
    b87b3p_batch_discovery_inventory.csv,
    b87b3p_batch_role_classification.csv,
    b87b3p_nonfinal_smoke_batch_register.csv.
Saved metrics:
    Batch role, sample size, evidence files, manifest/label/run-log paths,
    forcing-day/hour/scenario sets, and protocol confidence. This script only
    reads compact text/CSV evidence; it does not run QGIS/SOLWEIG, read raster
    pixels, open svfs.zip, create a run-ready manifest, stage, or commit.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from v12_b87b3p_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    as_list,
    clean,
    csv_profile,
    load_config,
    metadata_for_path,
    out_path,
    read_csv_rows,
    read_text,
    repo_path,
    unique_values,
    write_csv_rows,
)


ROLE_FINAL = "final_ml_label_source"
ROLE_VALIDATION = "formal_validation_label_source"
ROLE_PLANNED = "planned_n300_label_source"
ROLE_SMOKE = "smoke_diagnostic_only"
ROLE_DEPRECATED = "deprecated"
ROLE_UNKNOWN = "unknown"

ROLE_ORDER = {
    ROLE_FINAL: 0,
    ROLE_PLANNED: 1,
    ROLE_VALIDATION: 2,
    ROLE_SMOKE: 3,
    ROLE_DEPRECATED: 4,
    ROLE_UNKNOWN: 5,
}


def configured_inputs(config: dict[str, Any]) -> dict[str, str]:
    """Return configured input paths as strings."""
    inputs = config.get("inputs", {})
    return {clean(key): clean(value) for key, value in inputs.items()} if isinstance(inputs, dict) else {}


def status_from_markdown(path: str) -> str:
    """Extract a compact status token from a Markdown status/report file."""
    resolved = repo_path(path)
    if not resolved.exists():
        return "MISSING"
    try:
        text = read_text(resolved)
    except Exception as exc:
        return f"READ_ERROR:{clean(exc)}"
    patterns = [
        r"Status:\s*`?([A-Za-z0-9_\-]+)`?",
        r"## Status\s*\n\s*`?([A-Za-z0-9_\-]+)`?",
        r"Final decision:\s*`?([A-Za-z0-9_\-]+)`?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clean(match.group(1))
    return "STATUS_NOT_FOUND"


def csv_dimensions(path: str) -> tuple[str, str, str, str, str]:
    """Return CSV row/cell/forcing/hour/scenario summaries."""
    resolved = repo_path(path)
    if not resolved.exists():
        return "", "", "", "", ""
    try:
        rows = read_csv_rows(resolved)
    except Exception:
        return "", "", "", "", ""
    cell_set = unique_values(rows, "cell_id")
    forcing_set = unique_values(rows, "forcing_day_id")
    hour_column = "hour_sgt" if any("hour_sgt" in row for row in rows[:1]) else "hour"
    hour_set = unique_values(rows, hour_column)
    scenario_set = unique_values(rows, "scenario")
    return clean(len(rows)), clean(len(cell_set)), "|".join(forcing_set), "|".join(hour_set), "|".join(scenario_set)


def batch_specs(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return known batch specs, with paths resolved from config."""
    inputs = configured_inputs(config)
    return [
        {
            "batch_id": "v10_epsilon_selected_cell_diagnostics",
            "lane": "v10-epsilon",
            "role": ROLE_DEPRECATED,
            "manifest_path": "configs/v10/v10_epsilon_solweig_config.example.json",
            "output_label_path": "",
            "run_log_path": "",
            "sample_size_hint": "selected cells / diagnostic",
            "evidence_files": [
                "configs/v10/v10_epsilon_solweig_config.example.json",
                inputs.get("source_recovery_note", ""),
                "docs/v10/V10_EPSILON_SOLWEIG_GUIDE_CN.md",
            ],
            "classification_reason": "Earlier selected-cell diagnostic/source-of-truth lineage; not a current System B final ML label table.",
        },
        {
            "batch_id": "v12_wave0_reuse_v10_smoke",
            "lane": "v12 wave0",
            "role": ROLE_SMOKE,
            "manifest_path": "configs/v12/v12_solweig_wave0_reuse_v10_manifest.csv",
            "output_label_path": "",
            "run_log_path": "",
            "sample_size_hint": "1",
            "evidence_files": [
                "configs/v12/v12_solweig_wave0_reuse_v10_manifest.csv",
                inputs.get("v12_typology_config", ""),
                inputs.get("source_recovery_note", ""),
            ],
            "classification_reason": "Wave0 technical smoke reuses one v10 tile and is not a final ML label source.",
        },
        {
            "batch_id": "core8_optional_or_planned",
            "lane": "v12 beta Core-8 / N8",
            "role": ROLE_SMOKE,
            "manifest_path": "configs/v12/OpenHeat_v12_SOLWEIG_typology_core8_run_matrix.csv",
            "output_label_path": "",
            "run_log_path": "",
            "sample_size_hint": "8",
            "evidence_files": [
                "configs/v12/OpenHeat_v12_SOLWEIG_typology_core8_run_matrix.csv",
                "docs/v12/OpenHeat_v12_SOLWEIG_typology_pilot_runbook_CN.md",
            ],
            "classification_reason": "Early Core-8/N8 planning or diagnostic evidence only; not the F5 final ML label table.",
        },
        {
            "batch_id": "b85_f3a_microbatch",
            "lane": "B8.5-F3a",
            "role": ROLE_SMOKE,
            "manifest_path": inputs.get("f3a_manifest", ""),
            "output_label_path": "",
            "run_log_path": "C:/OpenHeat-local/solweig/b85_f3a_microbatch/run_logs/b85_f3a_microbatch_qgis_run_log.csv",
            "sample_size_hint": "1",
            "evidence_files": [inputs.get("f3a_status", ""), inputs.get("f3a_config", ""), inputs.get("f3a_manifest", "")],
            "classification_reason": "Microbatch execution/QA diagnostic only.",
        },
        {
            "batch_id": "b85_f3b_onecell",
            "lane": "B8.5-F3b",
            "role": ROLE_SMOKE,
            "manifest_path": inputs.get("f3b_manifest", ""),
            "output_label_path": "",
            "run_log_path": "C:/OpenHeat-local/solweig/b85_f3b_onecell/run_logs/b85_f3b_onecell_qgis_run_log.csv",
            "sample_size_hint": "1",
            "evidence_files": [inputs.get("f3b_status", ""), inputs.get("f3b_config", ""), inputs.get("f3b_manifest", "")],
            "classification_reason": "One-cell full-slice diagnostic only.",
        },
        {
            "batch_id": "b85_f3c_n24",
            "lane": "B8.5-F3c / N24",
            "role": ROLE_VALIDATION,
            "manifest_path": inputs.get("f3c_manifest", ""),
            "output_label_path": inputs.get("f3c_pairwise_label", ""),
            "run_log_path": "C:/OpenHeat-local/solweig/b85_f3c_n24/run_logs/b85_f3c_n24_qgis_run_log.csv",
            "sample_size_hint": "24",
            "evidence_files": [inputs.get("f3c_status", ""), inputs.get("f3c_config", ""), inputs.get("f3c_manifest", ""), inputs.get("f3c_pairwise_label", "")],
            "classification_reason": "Formal N24 stability/validation label source; not the current final N150 ML training label source.",
        },
        {
            "batch_id": "b85_f4_n24_decision",
            "lane": "B8.5-F4 / N24 decision",
            "role": ROLE_VALIDATION,
            "manifest_path": "",
            "output_label_path": "",
            "run_log_path": "",
            "sample_size_hint": "24",
            "evidence_files": [inputs.get("f4_status", ""), "outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_decision_matrix.csv"],
            "classification_reason": "Formal decision matrix over F3c compact evidence; no new label generation.",
        },
        {
            "batch_id": "b85_f5_n150_multiforcing",
            "lane": "B8.5-F5 / N150",
            "role": ROLE_FINAL,
            "manifest_path": inputs.get("f5_manifest", ""),
            "output_label_path": inputs.get("f5_pairwise_label", ""),
            "run_log_path": "C:/OpenHeat-local/solweig/b85_f5_n150/run_logs/b85_f5_n150_qgis_run_log.csv",
            "sample_size_hint": "150",
            "evidence_files": [
                inputs.get("f5_status", ""),
                inputs.get("f5_config", ""),
                inputs.get("f5_manifest", ""),
                inputs.get("f5_pairwise_label", ""),
                inputs.get("f5_label_merge_plan", ""),
            ],
            "classification_reason": "Current System B ML target source according to B8.6b+ label inventories.",
        },
        {
            "batch_id": "b87c_n300_planned_from_b87b3_source_lock",
            "lane": "B8.7/B87C planned N300",
            "role": ROLE_PLANNED,
            "manifest_path": "",
            "output_label_path": "",
            "run_log_path": "",
            "sample_size_hint": "150 new cells / 300 total context",
            "evidence_files": [
                inputs.get("b87b3_status", ""),
                inputs.get("b87b3_version_lock_decision", ""),
                inputs.get("b87b3_svf_scenario_model", ""),
                inputs.get("b87b_new_candidate_sample_index", ""),
                inputs.get("b86g3_n300_design_v4_source_reviewed", ""),
            ],
            "classification_reason": "Planned B87C source/protocol lock; no run-ready manifest and no SOLWEIG execution in this lane.",
        },
    ]


def evidence_status(paths: list[str]) -> tuple[str, str]:
    """Return existing evidence files and status headline."""
    existing: list[str] = []
    missing: list[str] = []
    for path in paths:
        if not clean(path):
            continue
        if repo_path(path).exists():
            existing.append(clean(path))
        else:
            missing.append(clean(path))
    if existing and not missing:
        status = "EVIDENCE_PRESENT"
    elif existing:
        status = "PARTIAL_EVIDENCE"
    else:
        status = "EVIDENCE_MISSING"
    return ";".join(existing), status


def search_term_presence(config: dict[str, Any], batch_id: str) -> str:
    """Return a compact note when search terms appear in path names."""
    terms = [clean(term).lower() for term in as_list(config.get("search_terms", []))]
    roots = [repo_path(root) for root in as_list(config.get("search_roots", []))]
    key_terms = [term for term in terms if term and term.replace(".", "").replace("_", "") in batch_id.lower().replace("_", "")]
    if not key_terms:
        return ""
    matches = 0
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            path_text = path.as_posix().lower()
            if any(term in path_text for term in key_terms):
                matches += 1
                if matches >= 25:
                    return ">=25 path-name search hits for " + "|".join(key_terms)
    return f"{matches} path-name search hits for " + "|".join(key_terms)


def discover_optional_n50(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Add an N50 row only when N50 evidence exists in configured roots."""
    roots = [repo_path(root) for root in as_list(config.get("search_roots", []))]
    matches: list[str] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if "n50" in path.name.lower() or "N50" in path.as_posix():
                matches.append(path.as_posix())
                if len(matches) >= 25:
                    break
        if len(matches) >= 25:
            break
    if not matches:
        return []
    return [
        {
            "batch_id": "n50_candidate_evidence_unclassified",
            "lane": "N50",
            "role": ROLE_UNKNOWN,
            "manifest_path": "",
            "output_label_path": "",
            "run_log_path": "",
            "sample_size_hint": "unknown",
            "evidence_files": matches[:10],
            "classification_reason": "N50-like path evidence was found, but no configured formal label source was identified.",
        }
    ]


DISCOVERY_FIELDS = [
    "batch_id",
    "lane",
    "sample_size",
    "role",
    "evidence_status",
    "evidence_files",
    "manifest_path",
    "manifest_rows",
    "output_label_path",
    "label_rows",
    "run_log_path",
    "forcing_day_set",
    "hour_sgt_set",
    "scenario_set",
    "protocol_confidence",
    "search_note",
    "classification_reason",
    "claim_boundary",
]

ROLE_FIELDS = [
    "batch_id",
    "lane",
    "role",
    "role_confidence",
    "classification_reason",
    "used_in_current_ml_labels",
    "safe_to_ignore_for_protocol_mixing",
    "evidence_files",
    "claim_boundary",
]

SMOKE_FIELDS = [
    "batch_id",
    "lane",
    "role",
    "difference_status",
    "reason",
    "evidence_files",
    "decision_treatment",
    "claim_boundary",
]


def build_rows(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Build batch discovery, role, and smoke-register rows."""
    discovery_rows: list[dict[str, Any]] = []
    role_rows: list[dict[str, Any]] = []
    smoke_rows: list[dict[str, Any]] = []
    specs = batch_specs(config) + discover_optional_n50(config)
    for spec in sorted(specs, key=lambda item: (ROLE_ORDER.get(item["role"], 99), item["batch_id"])):
        manifest_rows, manifest_cells, forcing_set, hour_set, scenario_set = csv_dimensions(clean(spec.get("manifest_path", "")))
        label_rows, label_cells, label_forcing, label_hours, label_scenarios = csv_dimensions(clean(spec.get("output_label_path", "")))
        sample_size = label_cells or manifest_cells or clean(spec.get("sample_size_hint", ""))
        evidence_files, evidence_status_value = evidence_status([clean(path) for path in spec.get("evidence_files", [])])
        protocol_confidence = "high" if evidence_status_value == "EVIDENCE_PRESENT" and spec["role"] in {ROLE_FINAL, ROLE_PLANNED, ROLE_VALIDATION} else "medium"
        if evidence_status_value == "EVIDENCE_MISSING":
            protocol_confidence = "low"
        discovery_rows.append(
            {
                "batch_id": spec["batch_id"],
                "lane": spec["lane"],
                "sample_size": sample_size,
                "role": spec["role"],
                "evidence_status": evidence_status_value,
                "evidence_files": evidence_files,
                "manifest_path": clean(spec.get("manifest_path", "")),
                "manifest_rows": manifest_rows,
                "output_label_path": clean(spec.get("output_label_path", "")),
                "label_rows": label_rows,
                "run_log_path": clean(spec.get("run_log_path", "")),
                "forcing_day_set": label_forcing or forcing_set,
                "hour_sgt_set": label_hours or hour_set,
                "scenario_set": label_scenarios or scenario_set,
                "protocol_confidence": protocol_confidence,
                "search_note": search_term_presence(config, spec["batch_id"]),
                "classification_reason": spec["classification_reason"],
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
        used = "yes" if spec["role"] == ROLE_FINAL else "no"
        role_rows.append(
            {
                "batch_id": spec["batch_id"],
                "lane": spec["lane"],
                "role": spec["role"],
                "role_confidence": protocol_confidence,
                "classification_reason": spec["classification_reason"],
                "used_in_current_ml_labels": used,
                "safe_to_ignore_for_protocol_mixing": "no" if spec["role"] in {ROLE_FINAL, ROLE_PLANNED} else "yes",
                "evidence_files": evidence_files,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
        if spec["role"] in {ROLE_SMOKE, ROLE_DEPRECATED, ROLE_UNKNOWN}:
            smoke_rows.append(
                {
                    "batch_id": spec["batch_id"],
                    "lane": spec["lane"],
                    "role": spec["role"],
                    "difference_status": "WARN_NONFINAL_PROTOCOL_DIFFERENCE" if spec["role"] != ROLE_UNKNOWN else "UNKNOWN_REQUIRES_REVIEW",
                    "reason": "Nonfinal diagnostic/deprecated evidence is not part of current ML labels." if spec["role"] != ROLE_UNKNOWN else "Unclassified evidence requires review before reuse.",
                    "evidence_files": evidence_files,
                    "decision_treatment": "do_not_fail_final_ml_parity" if spec["role"] != ROLE_UNKNOWN else "review_before_any_reuse",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
    return discovery_rows, role_rows, smoke_rows


def run(config_path: str | Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run batch discovery and role classification."""
    config = load_config(config_path)
    discovery_rows, role_rows, smoke_rows = build_rows(config)
    write_csv_rows(out_path(config, "b87b3p_batch_discovery_inventory.csv"), discovery_rows, DISCOVERY_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_batch_role_classification.csv"), role_rows, ROLE_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_nonfinal_smoke_batch_register.csv"), smoke_rows, SMOKE_FIELDS)
    return discovery_rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Discover and classify SOLWEIG label/protocol batches for B8.7b.3p. "
            "Reads compact CSV/Markdown evidence only; no QGIS/SOLWEIG and no "
            "raster/svfs.zip content access."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    rows = run(args.config)
    print(f"batch_discovery_rows={len(rows)}")
    print("batches=" + ",".join(row["batch_id"] for row in rows))


if __name__ == "__main__":
    main()
