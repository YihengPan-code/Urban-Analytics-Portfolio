"""Extract protocol dimensions for B8.7b.3p parity auditing.

Inputs:
    B8.7b.3p config, B8.5/F5 configs, B8.7b.3 source-lock tables, and batch
    discovery output.
Outputs:
    b87b3p_protocol_dimension_registry.csv and
    b87b3p_batch_protocol_matrix.csv.
Saved metrics:
    Protocol values across the 22 requested dimensions, evidence files, and
    parity status against the planned B87C source lock. This script reads only
    compact text/CSV/JSON/YAML evidence; no QGIS/SOLWEIG, raster pixel reads,
    svfs.zip opens, run-ready manifest creation, staging, or commits.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from v12_b87b3p_batch_discovery import ROLE_FINAL, ROLE_PLANNED, ROLE_SMOKE, ROLE_UNKNOWN, run as run_batch_discovery
from v12_b87b3p_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    as_list,
    clean,
    load_config,
    nested_get,
    out_path,
    read_csv_rows,
    read_json,
    repo_path,
    write_csv_rows,
)


DIMENSIONS = [
    {
        "dimension_id": "D01",
        "dimension_name": "building_dsm_path",
        "audit_question": "Which building DSM source generated the SOLWEIG geometry?",
        "criticality": "core_source",
        "fail_condition": "Final ML labels or planned N300 use mixed building DSM sources.",
    },
    {
        "dimension_id": "D02",
        "dimension_name": "building_dsm_version_status",
        "audit_question": "Is the building DSM the qa-corrected final reviewed-height version?",
        "criticality": "core_source",
        "fail_condition": "Final/planned protocols use non-final or mixed DSM versions.",
    },
    {
        "dimension_id": "D03",
        "dimension_name": "vegetation_cdsm_path",
        "audit_question": "Which base vegetation CDSM source was used?",
        "criticality": "core_source",
        "fail_condition": "Final/planned protocols use mixed base vegetation CDSM sources.",
    },
    {
        "dimension_id": "D04",
        "dimension_name": "vegetation_cdsm_version_status",
        "audit_question": "Is the vegetation CDSM version consistent?",
        "criticality": "core_source",
        "fail_condition": "Final/planned protocols use inconsistent vegetation CDSM status.",
    },
    {
        "dimension_id": "D05",
        "dimension_name": "grid_geometry_path",
        "audit_question": "Which cell geometry/grid source determines the focus cells?",
        "criticality": "geometry_source",
        "fail_condition": "Final/planned cells come from incompatible cell geometries.",
    },
    {
        "dimension_id": "D06",
        "dimension_name": "base_svf_source_or_generation_method",
        "audit_question": "How is base scenario SVF sourced or generated?",
        "criticality": "scenario_svf",
        "fail_condition": "Final/planned base SVF lineage is mixed or unknown.",
    },
    {
        "dimension_id": "D07",
        "dimension_name": "overhead_svf_source_or_generation_method",
        "audit_question": "How is overhead_as_canopy SVF sourced or generated?",
        "criticality": "scenario_svf",
        "fail_condition": "Overhead scenario reuses base SVF or has unknown scenario-specific SVF in final/planned labels.",
    },
    {
        "dimension_id": "D08",
        "dimension_name": "overhead_layer_path",
        "audit_question": "Which overhead source layer drives overhead_as_canopy?",
        "criticality": "core_source",
        "fail_condition": "Final/planned protocols use incompatible overhead layers.",
    },
    {
        "dimension_id": "D09",
        "dimension_name": "overhead_as_canopy_rule",
        "audit_question": "What rule turns overhead into CDSM?",
        "criticality": "scenario_protocol",
        "fail_condition": "Final/planned protocols do not use max(existing vegetation DSM, overhead canopy) or equivalent.",
    },
    {
        "dimension_id": "D10",
        "dimension_name": "DEM mode",
        "audit_question": "Is DEM flat/generated or a real DEM?",
        "criticality": "core_protocol",
        "fail_condition": "Final/planned protocols mix flat DEM with real DEM.",
    },
    {
        "dimension_id": "D11",
        "dimension_name": "landcover mode",
        "audit_question": "Is landcover disabled consistently?",
        "criticality": "core_protocol",
        "fail_condition": "Final/planned protocols mix disabled and enabled landcover.",
    },
    {
        "dimension_id": "D12",
        "dimension_name": "tile extent / tile buffer / tile resolution",
        "audit_question": "What tile geometry convention is used?",
        "criticality": "tile_protocol",
        "fail_condition": "Final/planned protocols use materially incompatible tile buffers/resolutions.",
    },
    {
        "dimension_id": "D13",
        "dimension_name": "per-cell asset layout",
        "audit_question": "What per-cell files/folders are expected?",
        "criticality": "tile_protocol",
        "fail_condition": "Final/planned protocol expects incompatible asset layouts.",
    },
    {
        "dimension_id": "D14",
        "dimension_name": "SVF artifact type",
        "audit_question": "Is SVF full-AOI raster, per-tile svfs.zip, generated in QGIS, or unknown?",
        "criticality": "scenario_svf",
        "fail_condition": "Final labels use invalid/pure-building/pure-vegetation SVF, or planned N300 reuses base SVF for overhead.",
    },
    {
        "dimension_id": "D15",
        "dimension_name": "SOLWEIG parameters",
        "audit_question": "Which stable SOLWEIG parameters are set?",
        "criticality": "core_protocol",
        "fail_condition": "Final/planned protocols use incompatible SOLWEIG scientific parameters.",
    },
    {
        "dimension_id": "D16",
        "dimension_name": "QGIS/UMEP algorithm id",
        "audit_question": "Which SOLWEIG algorithm ID is used?",
        "criticality": "execution_protocol",
        "fail_condition": "Final/planned protocols use incompatible QGIS/UMEP algorithm IDs.",
    },
    {
        "dimension_id": "D17",
        "dimension_name": "forcing_day_id set",
        "audit_question": "Which forcing-day IDs are included?",
        "criticality": "label_design",
        "fail_condition": "Final/planned protocols use incompatible forcing-day sets.",
    },
    {
        "dimension_id": "D18",
        "dimension_name": "hour_sgt set",
        "audit_question": "Which SGT hours are included?",
        "criticality": "label_design",
        "fail_condition": "Final/planned protocols use incompatible hour sets.",
    },
    {
        "dimension_id": "D19",
        "dimension_name": "scenarios",
        "audit_question": "Which scenarios are run?",
        "criticality": "label_design",
        "fail_condition": "Final/planned protocols use incompatible scenario sets.",
    },
    {
        "dimension_id": "D20",
        "dimension_name": "output target / Tmrt extraction convention",
        "audit_question": "What SOLWEIG target is extracted?",
        "criticality": "label_definition",
        "fail_condition": "Final/planned protocols mix Tmrt conventions or convert to WBGT/risk.",
    },
    {
        "dimension_id": "D21",
        "dimension_name": "postrun label extraction convention",
        "audit_question": "How are scenario rasters merged into labels?",
        "criticality": "label_definition",
        "fail_condition": "Final/planned protocols mix label extraction conventions.",
    },
    {
        "dimension_id": "D22",
        "dimension_name": "pairwise delta formula",
        "audit_question": "Which pairwise delta formula is used?",
        "criticality": "label_definition",
        "fail_condition": "Final/planned protocols mix delta direction or target metric.",
    },
]


def canonical_protocol(config: dict[str, Any]) -> dict[str, str]:
    """Return planned B87C protocol values from the canonical source lock."""
    sources = config.get("canonical_sources", {})
    return {
        "building_dsm_path": clean(sources.get("building_dsm_path", "")),
        "building_dsm_version_status": clean(sources.get("building_dsm_version_status", "")),
        "vegetation_cdsm_path": clean(sources.get("vegetation_cdsm_path", "")),
        "vegetation_cdsm_version_status": clean(sources.get("vegetation_cdsm_version_status", "")),
        "grid_geometry_path": clean(sources.get("grid_geometry_path", "")),
        "base_svf_source_or_generation_method": clean(sources.get("base_svf_source_or_generation_method", "")),
        "overhead_svf_source_or_generation_method": clean(sources.get("overhead_svf_source_or_generation_method", "")),
        "overhead_layer_path": clean(sources.get("overhead_layer_path", "")),
        "overhead_as_canopy_rule": clean(sources.get("overhead_as_canopy_rule", "")),
        "DEM mode": clean(sources.get("dem_mode", "")),
        "landcover mode": clean(sources.get("landcover_mode", "")),
        "tile extent / tile buffer / tile resolution": f"focus_cell=100m; buffer={sources.get('tile_buffer_m')}m; resolution={sources.get('tile_resolution_m')}m",
        "per-cell asset layout": clean(sources.get("per_cell_asset_layout", "")),
        "SVF artifact type": clean(sources.get("svf_artifact_type", "")),
        "SOLWEIG parameters": "INPUTMET; LEAF_START=1; LEAF_END=366; UTC=8; TRANS_VEG=3; INPUT_THEIGHT=25.0; OUTPUT_TMRT=true; other flux outputs=false",
        "QGIS/UMEP algorithm id": clean(sources.get("qgis_umep_algorithm_id", "")),
        "forcing_day_id set": "|".join(clean(item) for item in as_list(sources.get("forcing_day_ids", []))),
        "hour_sgt set": "|".join(clean(item) for item in as_list(sources.get("hours_sgt", []))),
        "scenarios": "|".join(clean(item) for item in as_list(sources.get("scenarios", []))),
        "output target / Tmrt extraction convention": clean(sources.get("output_target_extraction_convention", "")),
        "postrun label extraction convention": clean(sources.get("postrun_label_extraction_convention", "")),
        "pairwise delta formula": clean(sources.get("pairwise_delta_formula", "")),
    }


def b85_protocol_from_configs(config: dict[str, Any]) -> dict[str, str]:
    """Extract B8.5/N150 protocol values from compact configs."""
    inputs = config.get("inputs", {})
    f1 = {}
    n150 = {}
    try:
        f1 = load_config(repo_path(inputs.get("f1_config", "")))
    except Exception:
        f1 = {}
    try:
        n150 = read_json(inputs.get("n150_execution_config", ""))
    except Exception:
        n150 = {}
    f5 = {}
    try:
        f5 = load_config(repo_path(inputs.get("f5_config", "")))
    except Exception:
        f5 = {}

    asset_templates = nested_get(f5, ["asset_templates"], {})
    qgis_execution = nested_get(f5, ["qgis_execution"], {})
    solweig_params = nested_get(f5, ["solweig_parameters"], {})
    f1_inputs = nested_get(f1, ["inputs"], {})
    return {
        "building_dsm_path": clean(f1_inputs.get("building_dsm_path", n150.get("building_dsm_path", ""))),
        "building_dsm_version_status": "qa_corrected_final inferred from reviewed_heightqa filename and F1/B8.7b.3 source lock",
        "vegetation_cdsm_path": clean(f1_inputs.get("vegetation_dsm_path", n150.get("vegetation_dsm_path", ""))),
        "vegetation_cdsm_version_status": "likely_final_base_vegetation_dsm inferred from v08 dsm_vegetation_2m_toapayoh source",
        "grid_geometry_path": clean(f1_inputs.get("grid_feature_path", n150.get("grid_feature_path", ""))),
        "base_svf_source_or_generation_method": f"per-cell {asset_templates.get('svf_base_zip', 'svf_base/svfs.zip')} referenced by F5 manifest/precheck",
        "overhead_svf_source_or_generation_method": f"per-cell {asset_templates.get('svf_overhead_zip', 'svf_overhead_as_canopy/svfs.zip')} referenced separately by F5 manifest/precheck",
        "overhead_layer_path": clean(f1_inputs.get("overhead_vector_path", n150.get("overhead_vector_path", ""))),
        "overhead_as_canopy_rule": "max(existing vegetation DSM, overhead canopy) documented by v12_solweig_prepare_rasters and source-recovery configs",
        "DEM mode": f"flat per-cell tile ({asset_templates.get('dem_name', 'dsm_dem_flat_tile.tif')})",
        "landcover mode": "INPUT_LC=None; USE_LC_BUILD=false",
        "tile extent / tile buffer / tile resolution": f"focus_cell=100m; buffer={n150.get('tile_buffer_m', 100)}m; resolution={n150.get('raster_resolution_m', 2)}m",
        "per-cell asset layout": "focus_cell.geojson, dsm_buildings_tile.tif, dsm_dem_flat_tile.tif, dsm_vegetation_tile_base.tif, dsm_vegetation_tile_overhead_as_canopy.tif, wall_height.tif, wall_aspect.tif, svf_base/svfs.zip, svf_overhead_as_canopy/svfs.zip",
        "SVF artifact type": "per-tile svfs.zip for base and overhead_as_canopy",
        "SOLWEIG parameters": "; ".join(f"{key}={value}" for key, value in sorted(solweig_params.items())) or "INPUTMET; LEAF_START=1; LEAF_END=366; UTC=8; TRANS_VEG=3; INPUT_THEIGHT=25.0; OUTPUT_TMRT=true",
        "QGIS/UMEP algorithm id": clean(qgis_execution.get("qgis_algorithm_id_hint", "umep:Outdoor Thermal Comfort: SOLWEIG")),
        "forcing_day_id set": "|".join(clean(item) for item in as_list(f5.get("forcing_days", n150.get("forcing_days", [])))),
        "hour_sgt set": "|".join(clean(item) for item in as_list(f5.get("hours_sgt", n150.get("hours_sgt", [])))),
        "scenarios": "|".join(clean(item) for item in as_list(f5.get("scenarios", n150.get("scenarios", [])))),
        "output target / Tmrt extraction convention": "SOLWEIG Tmrt_average.tif summarized to p90 and cell/hour/scenario compact tables",
        "postrun label extraction convention": "F5 raster_stats -> cell_hour_summary -> pairwise_delta_by_cell_hour",
        "pairwise delta formula": "delta_tmrt_p90_c = overhead_as_canopy - base",
    }


def smoke_protocol(batch_id: str, b85_protocol: dict[str, str], canonical: dict[str, str]) -> dict[str, str]:
    """Return smoke/deprecated protocol values."""
    if "v10_epsilon" in batch_id or "wave0" in batch_id:
        protocol = dict(canonical)
        protocol["base_svf_source_or_generation_method"] = "v10-epsilon or wave0 reuse smoke SVF; provenance only"
        protocol["overhead_svf_source_or_generation_method"] = "not final ML label source; may be absent or diagnostic"
        protocol["SVF artifact type"] = "smoke/deprecated SVF provenance only"
        protocol["forcing_day_id set"] = "FD01_high_shortwave_hot_20260507"
        protocol["scenarios"] = "base or diagnostic subset"
        return protocol
    return dict(b85_protocol)


def protocol_for_batch(row: dict[str, str], config: dict[str, Any], canonical: dict[str, str], b85: dict[str, str]) -> tuple[str, dict[str, str], str]:
    """Return protocol ID, values, and evidence path for a batch."""
    role = clean(row.get("role", ""))
    batch_id = clean(row.get("batch_id", ""))
    if role == ROLE_PLANNED:
        return clean(config.get("canonical_planned_protocol_id", "B87C_PLANNED_PROTOCOL")), canonical, clean(row.get("evidence_files", ""))
    if role == ROLE_FINAL:
        return clean(config.get("final_n150_protocol_id", "F5_N150_PROTOCOL")), b85, clean(row.get("evidence_files", ""))
    if role == ROLE_UNKNOWN:
        return "UNKNOWN_PROTOCOL_REQUIRES_REVIEW", {dimension["dimension_name"]: "unknown" for dimension in DIMENSIONS}, clean(row.get("evidence_files", ""))
    return f"{batch_id.upper()}_NONFINAL_PROTOCOL", smoke_protocol(batch_id, b85, canonical), clean(row.get("evidence_files", ""))


def parity_status(dimension_name: str, value: str, reference_value: str, role: str) -> tuple[str, str]:
    """Classify value parity against the planned reference."""
    value_lower = value.lower()
    ref_lower = reference_value.lower()
    if role in {ROLE_SMOKE, "deprecated"}:
        return "WARN_NONFINAL_PROTOCOL_DIFFERENCE", "Nonfinal diagnostic/deprecated batch; not a final ML mixing failure."
    if value_lower in {"", "unknown"}:
        return "UNKNOWN_REQUIRES_REVIEW", "Protocol value is missing or unknown."
    if dimension_name == "grid_geometry_path" and value_lower != ref_lower:
        return "WARN_DERIVED_GRID_FEATURE_SOURCE", "F5 references derived v10 feature/sample artifacts; planned B87C locks v07 geometry. Review lineage if geometry edits are suspected."
    if dimension_name in {"base_svf_source_or_generation_method", "SVF artifact type"} and "per-tile" in value_lower and "full-aoi" in ref_lower:
        return "PASS_GENERATION_METHOD_COMPATIBLE", "Final labels used per-tile SOLWEIG SVF; B87C source lock requires per-tile materialization from the full-AOI source."
    if dimension_name == "overhead_svf_source_or_generation_method" and "per-cell" in value_lower and "scenario-specific" in ref_lower:
        return "PASS_SCENARIO_SPECIFIC", "Final and planned protocols require separate overhead scenario SVF."
    if dimension_name == "SOLWEIG parameters" and all(token in value_lower for token in ["inputmet", "output_tmrt"]) and "inputmet" in ref_lower:
        return "PASS_PARAMETER_CORE_MATCH", "Core SOLWEIG parameter contract matches; extra explicit false outputs are compatible."
    if dimension_name == "QGIS/UMEP algorithm id" and "solweig" in value_lower and "solweig" in ref_lower:
        return "PASS", "SOLWEIG algorithm family matches."
    if value_lower == ref_lower:
        return "PASS", "Exact value match."
    if dimension_name in {"building_dsm_path", "vegetation_cdsm_path", "overhead_layer_path"} and Path(value).name.lower() == Path(reference_value).name.lower():
        return "PASS_FILENAME_MATCH", "Relative/absolute path form differs but canonical filename matches."
    if dimension_name in {"building_dsm_version_status", "vegetation_cdsm_version_status"} and any(token in value_lower for token in ref_lower.split("_") if len(token) > 3):
        return "PASS_STATUS_COMPATIBLE", "Version-status wording is compatible."
    return "WARN_REVIEW_VALUE_DIFFERENCE", "Value differs from planned reference; evaluate whether this is lineage-only or protocol-critical."


REGISTRY_FIELDS = ["dimension_id", "dimension_name", "audit_question", "criticality", "fail_condition", "claim_boundary"]
MATRIX_FIELDS = [
    "batch_id",
    "role",
    "protocol_id",
    "dimension_id",
    "dimension_name",
    "protocol_value",
    "planned_b87c_reference_value",
    "parity_status",
    "parity_note",
    "evidence",
    "claim_boundary",
]


def read_or_build_batches(config: dict[str, Any], config_path: str | Path) -> list[dict[str, str]]:
    """Read batch discovery rows, creating them first if needed."""
    path = out_path(config, "b87b3p_batch_discovery_inventory.csv")
    if not path.exists():
        run_batch_discovery(config_path)
    return read_csv_rows(path)


def run(config_path: str | Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Extract and write protocol matrices."""
    config = load_config(config_path)
    canonical = canonical_protocol(config)
    b85 = b85_protocol_from_configs(config)
    batches = read_or_build_batches(config, config_path)

    registry_rows = [{**dimension, "claim_boundary": CLAIM_BOUNDARY} for dimension in DIMENSIONS]
    matrix_rows: list[dict[str, Any]] = []
    for batch in batches:
        protocol_id, values, evidence = protocol_for_batch(batch, config, canonical, b85)
        role = clean(batch.get("role", ""))
        for dimension in DIMENSIONS:
            name = dimension["dimension_name"]
            value = clean(values.get(name, "unknown"))
            reference = clean(canonical.get(name, ""))
            status, note = parity_status(name, value, reference, role)
            matrix_rows.append(
                {
                    "batch_id": batch["batch_id"],
                    "role": role,
                    "protocol_id": protocol_id,
                    "dimension_id": dimension["dimension_id"],
                    "dimension_name": name,
                    "protocol_value": value,
                    "planned_b87c_reference_value": reference,
                    "parity_status": status,
                    "parity_note": note,
                    "evidence": evidence,
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )

    write_csv_rows(out_path(config, "b87b3p_protocol_dimension_registry.csv"), registry_rows, REGISTRY_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_batch_protocol_matrix.csv"), matrix_rows, MATRIX_FIELDS)
    return matrix_rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Extract protocol dimensions for B8.7b.3p parity auditing. Reads "
            "compact evidence only; does not run QGIS/SOLWEIG or touch raster "
            "contents."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    rows = run(args.config)
    print(f"protocol_matrix_rows={len(rows)}")


if __name__ == "__main__":
    main()
