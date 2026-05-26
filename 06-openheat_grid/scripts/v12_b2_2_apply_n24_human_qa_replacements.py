"""Sprint B2.2 N24 human-QA replacement and selection freeze.

Inputs:
    Existing B2 N24 selected/alternate/candidate/role/preflight CSV and MD
    artifacts, existing future-run N24 manifests, and non-raster grid feature
    CSVs. Replacement cells are looked up only in CSV metadata/features.

Outputs:
    - outputs/v12_systemb_n24_sample_design/n24_selected_cells.csv
    - outputs/v12_systemb_n24_sample_design/n24_selected_cells_b2_2_human_qa_freeze.csv
    - outputs/v12_systemb_n24_sample_design/n24_human_qa_replacements.csv
    - outputs/v12_systemb_n24_sample_design/n24_replaced_out_cells.csv
    - outputs/v12_systemb_n24_sample_design/n24_typology_coverage_matrix.csv
    - outputs/v12_systemb_n24_sample_design/n24_diagnostic_role_coverage.csv
    - outputs/v12_systemb_n24_sample_design/n24_b2_2_coverage_delta_vs_b2.csv
    - configs/v12/v12_solweig_n24_base_manifest.csv
    - configs/v12/v12_solweig_n24_overhead_manifest.csv
    - configs/v12/v12_solweig_n24_run_matrix.csv
    - outputs/v12_systemb_n24_sample_design/n24_solweig_manifest_preflight.csv
    - outputs/v12_systemb_n24_sample_design/n24_solweig_manifest_preflight.md
    - outputs/v12_systemb_n24_sample_design/sprint_b2_2_n24_human_qa_freeze_report.md

This script does not run QGIS, run SOLWEIG, read rasters, read or write .tif or
.tiff files, write data/solweig, write data/rasters, train models, create a
surrogate, create hazard_score, create risk_score, create local_wbgt_c, or
perform System A/B coupling.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd


OUTPUT_DIR = Path("outputs/v12_systemb_n24_sample_design")
CONFIG_DIR = Path("configs/v12")
HOURS = [10, 12, 13, 15, 16]
SCENARIOS = ["base", "overhead_as_canopy"]
FREEZE_VERSION = "b2_2_human_qa_freeze"
REPLACEMENTS = {
    "TP_0058": {
        "replacement": "TP_0141",
        "note": "TP_0058 is almost pure river/water surface. TP_0141 is a better water-edge / blue-green context cell: roughly 30% river and 70% land/grass.",
        "preferred_primary_role": "water_edge_or_blue_green",
    },
    "TP_0828": {"replacement": "TP_0301", "note": "Human QA replacement."},
    "TP_0802": {"replacement": "TP_0773", "note": "Human QA replacement."},
    "TP_0675": {"replacement": "TP_0676", "note": "Human QA replacement."},
    "TP_0916": {
        "replacement": "TP_0575",
        "note": "Human QA replacement. TP_0916 remains an optional v10-epsilon legacy overhead-saturated diagnostic note only and is not in the frozen N24 run matrix.",
    },
}
REPLACED_OUT = set(REPLACEMENTS)
REPLACEMENT_IN = {info["replacement"] for info in REPLACEMENTS.values()}
REQUIRED_MINIMUMS = {
    "core_continuity": 8,
    "confident_hot_anchor_continuity": 2,
    "overhead_confounded_legacy_diagnostic": 1,
    "shaded_or_canopy_reference": 2,
    "open_paved_hardscape": 2,
    "street_canyon_wall_adjacent": 2,
    "covered_walkway_or_pedestrian_overhead": 2,
    "transport_overhead_or_viaduct": 2,
    "water_edge_or_blue_green": 2,
    "grass_or_open_park": 2,
    "school_gate_bus_stop_waiting_node": 2,
    "p90_p95_disagreement_probe": 3,
    "max_extreme_probe": 1,
    "threshold_area_probe": 3,
    "overhead_sensitivity_probe": 1,
    "pedestrian_relevance_probe": 2,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply B2.2 human QA replacements and freeze N24 selection.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root.")
    return parser.parse_args()


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def ensure_dirs(root: Path) -> None:
    (root / OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    (root / CONFIG_DIR).mkdir(parents=True, exist_ok=True)


def load_inputs(root: Path) -> dict[str, pd.DataFrame]:
    return {
        "selected": read_csv(root / OUTPUT_DIR / "n24_selected_cells.csv"),
        "alternates": read_csv(root / OUTPUT_DIR / "n24_alternate_cells.csv"),
        "pool": read_csv(root / OUTPUT_DIR / "n24_candidate_pool.csv"),
        "roles": read_csv(root / OUTPUT_DIR / "n24_candidate_roles_long.csv"),
        "coverage": read_csv(root / OUTPUT_DIR / "n24_diagnostic_role_coverage.csv"),
        "features_overhead": read_csv(root / "data/grid/v10/toa_payoh_grid_v10_features_overhead_sensitivity.csv"),
        "features_umep": read_csv(root / "data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv"),
        "v12_candidates": read_csv(root / "data/grid/v12/solweig_typology_cell_candidates.csv"),
    }


def first_present(row: pd.Series, names: list[str]) -> Any:
    for name in names:
        if name in row.index and pd.notna(row[name]):
            return row[name]
    return pd.NA


def role_list(roles: pd.DataFrame, cell_id: str) -> list[str]:
    if roles.empty:
        return []
    values = roles.loc[roles["cell_id"].astype(str) == cell_id, "diagnostic_role"].dropna().astype(str).tolist()
    return list(dict.fromkeys(values))


def pool_row(pool: pd.DataFrame, cell_id: str) -> pd.Series | None:
    match = pool[pool["cell_id"].astype(str) == cell_id]
    if match.empty:
        return None
    return match.iloc[0]


def feature_row(features: pd.DataFrame, cell_id: str) -> pd.Series | None:
    if features.empty or "cell_id" not in features.columns:
        return None
    match = features[features["cell_id"].astype(str) == cell_id]
    if match.empty:
        return None
    return match.iloc[0]


def synthesize_replacement_row(
    old_row: pd.Series,
    new_cell: str,
    pool: pd.DataFrame,
    roles: pd.DataFrame,
    features: pd.DataFrame,
    replacement_note: str,
    preferred_primary_role: str | None = None,
) -> pd.Series:
    new = old_row.copy()
    new["cell_id"] = new_cell
    new["human_qa_status"] = "replacement_in"
    new["replaced_cell_id"] = old_row["cell_id"]
    new["replacement_cell_id"] = new_cell
    new["human_qa_note"] = replacement_note
    new["selection_freeze_version"] = FREEZE_VERSION
    new["final_selection_status"] = "selected_new"
    new["selection_tier"] = "added16"

    candidate = pool_row(pool, new_cell)
    roles_for_cell = role_list(roles, new_cell)
    if preferred_primary_role:
        primary = preferred_primary_role
        secondary = [role for role in roles_for_cell if role != preferred_primary_role]
        if preferred_primary_role not in roles_for_cell:
            secondary = roles_for_cell
    elif roles_for_cell:
        primary = roles_for_cell[0]
        secondary = roles_for_cell[1:]
    else:
        primary = "human_qa_replacement_pending_role_review"
        secondary = []

    new["primary_role"] = primary
    new["secondary_roles"] = "|".join(secondary)

    if candidate is not None:
        new["typology_label"] = candidate.get("typology_label", new.get("typology_label", ""))
        new["rationale"] = f"Human QA replacement for {old_row['cell_id']}. {replacement_note}"
        new["evidence_summary"] = evidence_summary(candidate)
        new["source_files"] = append_source(str(candidate.get("selection_source", "")), "b2_2_human_qa_replacement")
        new["expected_overhead_question"] = expected_overhead_question(primary, secondary)
        new["expected_threshold_area_question"] = expected_threshold_question(primary, secondary)
        new["expected_pedestrian_relevance_question"] = expected_pedestrian_question(primary, secondary)
        new["caveat"] = "Human QA replacement; role evidence from non-raster candidate pool only."
    else:
        feat = feature_row(features, new_cell)
        if feat is not None:
            new["typology_label"] = first_present(feat, ["land_use_hint", "land_use_raw"])
            new["rationale"] = f"Human QA replacement for {old_row['cell_id']}. {replacement_note}"
            new["evidence_summary"] = evidence_summary_from_feature(feat)
            new["source_files"] = "v10_non_raster_grid_features|b2_2_human_qa_replacement"
            new["caveat"] = "Replacement cell exists in grid features but has missing candidate-role evidence."
        else:
            new["typology_label"] = ""
            new["rationale"] = f"Human QA replacement for {old_row['cell_id']}. {replacement_note}"
            new["evidence_summary"] = "replacement cell not found in candidate_pool or grid features"
            new["source_files"] = "b2_2_human_qa_replacement"
            new["caveat"] = "Replacement cell missing from candidate_pool and grid features; role evidence unavailable."
    if primary == "human_qa_replacement_pending_role_review":
        new["caveat"] = append_note(str(new.get("caveat", "")), "Primary role pending review because no existing candidate roles were available.")
    if new_cell == "TP_0575":
        new["caveat"] = append_note(str(new.get("caveat", "")), "TP_0916 retained only as legacy diagnostic note; not in frozen run matrix.")
    return new


def evidence_summary(row: pd.Series) -> str:
    parts = []
    for label, col in [
        ("svf", "svf"),
        ("shade", "shade_fraction"),
        ("bldg_density", "building_density"),
        ("water", "water_fraction"),
        ("grass", "grass_fraction"),
        ("overhead", "overhead_fraction"),
        ("road", "road_fraction"),
    ]:
        value = row.get(col, pd.NA)
        if pd.notna(value):
            try:
                parts.append(f"{label}={float(value):.3f}")
            except (TypeError, ValueError):
                parts.append(f"{label}={value}")
    return "; ".join(parts) if parts else "metadata-only candidate"


def evidence_summary_from_feature(row: pd.Series) -> str:
    parts = []
    for label, names in [
        ("svf", ["svf_umep_mean_open_v10", "svf"]),
        ("shade", ["shade_fraction_umep_13_15_open_v10", "shade_fraction"]),
        ("bldg_density", ["v10_building_density", "building_density"]),
        ("water", ["water_fraction", "dynamic_world_water_fraction"]),
        ("grass", ["grass_fraction", "dynamic_world_grass_fraction"]),
        ("road", ["road_fraction"]),
    ]:
        value = first_present(row, names)
        if pd.notna(value):
            try:
                parts.append(f"{label}={float(value):.3f}")
            except (TypeError, ValueError):
                parts.append(f"{label}={value}")
    return "; ".join(parts) if parts else "grid metadata only"


def append_source(existing: str, addition: str) -> str:
    items = [item for item in existing.split("|") if item] + [addition]
    return "|".join(dict.fromkeys(items))


def append_note(existing: str, addition: str) -> str:
    return f"{existing} {addition}".strip() if existing else addition


def expected_overhead_question(primary: str, secondary: list[str]) -> str:
    roles = "|".join([primary, *secondary])
    if "overhead" in roles or "viaduct" in roles:
        return "How does overhead_as_canopy affect p90 and companions for the replacement cell?"
    return "Expected low or contextual overhead sensitivity."


def expected_threshold_question(primary: str, secondary: list[str]) -> str:
    roles = "|".join([primary, *secondary])
    if "threshold_area_probe" in roles or "open_paved" in roles or "water_edge" in roles:
        return "Does future threshold-area exceedance align with p90 for this replacement?"
    return "Use as companion threshold-area check when aggregator adds pct_pixels_tmrt_ge_*."


def expected_pedestrian_question(primary: str, secondary: list[str]) -> str:
    roles = "|".join([primary, *secondary])
    if "water_edge" in roles:
        return "Confirm mixed water-edge / land context remains relevant to pedestrian-scale interpretation."
    if "pedestrian" in roles or "covered_walkway" in roles:
        return "Confirm pedestrian relevance if used beyond smoke execution."
    return "Pedestrian relevance requires future accessible-mask QA."


def apply_replacements(inputs: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    selected = inputs["selected"].copy()
    for col in ["human_qa_status", "replaced_cell_id", "replacement_cell_id", "human_qa_note", "selection_freeze_version"]:
        if col not in selected.columns:
            selected[col] = ""
    selected["human_qa_status"] = selected["human_qa_status"].replace("", "keep")
    selected["selection_freeze_version"] = FREEZE_VERSION

    replaced_rows = []
    replacement_log = []
    final_rows = []
    features = inputs["features_overhead"] if not inputs["features_overhead"].empty else inputs["features_umep"]

    for _, row in selected.sort_values("selection_rank").iterrows():
        cell_id = str(row["cell_id"])
        if cell_id not in REPLACEMENTS:
            row = row.copy()
            if cell_id not in REPLACEMENT_IN:
                row["human_qa_status"] = "keep"
                row["replaced_cell_id"] = ""
                row["replacement_cell_id"] = ""
                row["human_qa_note"] = "Passed quick human map sanity check; keep."
                row["selection_freeze_version"] = FREEZE_VERSION
            final_rows.append(row)
            continue

        info = REPLACEMENTS[cell_id]
        new_cell = info["replacement"]
        replaced = row.copy()
        replaced["human_qa_status"] = "replaced_out"
        replaced["replaced_cell_id"] = cell_id
        replaced["replacement_cell_id"] = new_cell
        replaced["human_qa_note"] = info["note"]
        replaced["selection_freeze_version"] = FREEZE_VERSION
        replaced_rows.append(replaced)

        replacement = synthesize_replacement_row(
            row,
            new_cell,
            inputs["pool"],
            inputs["roles"],
            features,
            info["note"],
            info.get("preferred_primary_role"),
        )
        final_rows.append(replacement)
        replacement_log.append(
            {
                "replaced_cell_id": cell_id,
                "replacement_cell_id": new_cell,
                "selection_rank": row["selection_rank"],
                "reason": info["note"],
                "freeze_version": FREEZE_VERSION,
                "replacement_in_final_selected": True,
                "replaced_cell_absent_from_run_matrix_required": True,
            }
        )

    final = pd.DataFrame(final_rows).sort_values("selection_rank").reset_index(drop=True)
    replaced_out = pd.DataFrame(replaced_rows)
    replacement_log_df = pd.DataFrame(replacement_log)
    return final, replaced_out, replacement_log_df


def diagnostic_roles_for_selected(selected: pd.DataFrame, roles: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in selected.iterrows():
        cell_id = str(row["cell_id"])
        cell_roles = role_list(roles, cell_id)
        if row.get("primary_role") and row["primary_role"] not in cell_roles:
            cell_roles.insert(0, str(row["primary_role"]))
        for role in str(row.get("secondary_roles", "")).split("|"):
            if role and role not in cell_roles:
                cell_roles.append(role)
        for role in cell_roles:
            rows.append({"cell_id": cell_id, "diagnostic_role": role})
    return pd.DataFrame(rows).drop_duplicates()


def regenerate_coverage(root: Path, selected: pd.DataFrame, roles: pd.DataFrame, old_coverage: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tier_counts = selected.groupby("selection_tier").size().reset_index(name="selected_count")
    tier_counts = tier_counts.rename(columns={"selection_tier": "category"})
    tier_counts["coverage_type"] = "selection_tier"
    typology_counts = selected.groupby("typology_label").size().reset_index(name="selected_count")
    typology_counts = typology_counts.rename(columns={"typology_label": "category"})
    typology_counts["coverage_type"] = "typology_label"
    coverage_matrix = pd.concat([tier_counts, typology_counts], ignore_index=True)
    coverage_matrix["core8_retained_count"] = int((selected["final_selection_status"] == "selected_core").sum())
    coverage_matrix["new_cell_count"] = int((selected["final_selection_status"] == "selected_new").sum())
    coverage_matrix["legacy_diagnostic_count"] = int((selected["final_selection_status"] == "selected_legacy_diagnostic").sum())
    coverage_matrix["selection_freeze_version"] = FREEZE_VERSION

    selected_roles = diagnostic_roles_for_selected(selected, roles)
    role_counts = selected_roles.groupby("diagnostic_role")["cell_id"].nunique().reset_index(name="selected_cell_count")
    role_coverage = pd.DataFrame(
        [{"diagnostic_role": role, "required_minimum": minimum} for role, minimum in REQUIRED_MINIMUMS.items()]
    ).merge(role_counts, on="diagnostic_role", how="left")
    role_coverage["selected_cell_count"] = role_coverage["selected_cell_count"].fillna(0).astype(int)
    role_coverage["required_role_missing"] = role_coverage["selected_cell_count"] < role_coverage["required_minimum"]
    role_coverage["coverage_warning"] = role_coverage.apply(
        lambda r: "below required minimum after human QA replacement" if r["required_role_missing"] else "",
        axis=1,
    )
    role_coverage["selection_freeze_version"] = FREEZE_VERSION

    if not old_coverage.empty and "diagnostic_role" in old_coverage.columns:
        old = old_coverage[["diagnostic_role", "selected_cell_count"]].rename(columns={"selected_cell_count": "b2_selected_cell_count"})
        delta = role_coverage[["diagnostic_role", "selected_cell_count", "required_minimum", "required_role_missing"]].merge(
            old, on="diagnostic_role", how="left"
        )
        delta["b2_selected_cell_count"] = pd.to_numeric(delta["b2_selected_cell_count"], errors="coerce").fillna(0).astype(int)
        delta["delta_b2_2_minus_b2"] = delta["selected_cell_count"] - delta["b2_selected_cell_count"]
        delta["warning"] = delta.apply(
            lambda r: "material role coverage decrease" if r["delta_b2_2_minus_b2"] < 0 and r["required_role_missing"] else "",
            axis=1,
        )
    else:
        delta = role_coverage.copy()
        delta["b2_selected_cell_count"] = pd.NA
        delta["delta_b2_2_minus_b2"] = pd.NA
        delta["warning"] = "prior coverage unavailable"
    return coverage_matrix, role_coverage, delta


def write_manifests(root: Path, selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    for scenario in SCENARIOS:
        for _, item in selected.sort_values("selection_rank").iterrows():
            cell_id = str(item["cell_id"])
            for hour in HOURS:
                rows.append(
                    {
                        "run_id": f"v12_n24_{scenario}_{cell_id}_h{hour:02d}",
                        "cell_id": cell_id,
                        "scenario": scenario,
                        "hour": hour,
                        "forcing_label": "v10_epsilon_forcing_or_formal_hot_day_placeholder",
                        "building_dsm_source_label": "future_template_reviewed_building_dsm_with_veg",
                        "vegetation_dsm_source_label": "future_template_reviewed_vegetation_dsm",
                        "overhead_source_label": "future_template_overhead_as_canopy" if scenario == "overhead_as_canopy" else "none_for_base",
                        "dem_source_label": "future_template_flat_or_reviewed_dem",
                        "svf_output_dir_expected": f"future_template_outputs/v12_solweig_typology_pilot/n24_preprocess/{cell_id}/{scenario}/svf",
                        "wall_height_expected": f"future_template_outputs/v12_solweig_typology_pilot/n24_preprocess/{cell_id}/{scenario}/wall_height",
                        "wall_aspect_expected": f"future_template_outputs/v12_solweig_typology_pilot/n24_preprocess/{cell_id}/{scenario}/wall_aspect",
                        "tmrt_output_expected": f"future_template_outputs/v12_solweig_typology_pilot/n24_runs/{scenario}/{cell_id}/h{hour:02d}/tmrt_output_raster",
                        "expected_summary_row_key": f"{cell_id}|{scenario}|h{hour:02d}",
                        "do_not_commit_raw_output": True,
                        "notes": f"Future-run manifest only; {FREEZE_VERSION}; do not execute in Sprint B2.2.",
                    }
                )
    matrix = pd.DataFrame(rows)
    base = matrix[matrix["scenario"] == "base"].copy()
    overhead = matrix[matrix["scenario"] == "overhead_as_canopy"].copy()
    base.to_csv(root / CONFIG_DIR / "v12_solweig_n24_base_manifest.csv", index=False)
    overhead.to_csv(root / CONFIG_DIR / "v12_solweig_n24_overhead_manifest.csv", index=False)
    matrix.to_csv(root / CONFIG_DIR / "v12_solweig_n24_run_matrix.csv", index=False)
    return base, overhead, matrix


def preflight(root: Path, selected: pd.DataFrame, base: pd.DataFrame, overhead: pd.DataFrame, matrix: pd.DataFrame) -> pd.DataFrame:
    checks = []

    def add(check: str, passed: bool, observed: Any, expected: Any, notes: str = "") -> None:
        checks.append({"check": check, "passed": bool(passed), "observed": observed, "expected": expected, "notes": notes})

    selected_cells = set(selected["cell_id"].astype(str))
    matrix_cells = set(matrix["cell_id"].astype(str))
    text = matrix.astype(str).to_string().lower()
    add("selected_cell_count", len(selected_cells) == 24, len(selected_cells), 24)
    add("base_manifest_rows", len(base) == 120, len(base), "24*5=120")
    add("overhead_manifest_rows", len(overhead) == 120, len(overhead), "24*5=120")
    add("total_manifest_rows", len(matrix) == 240, len(matrix), "24*2*5=240")
    add("each_selected_cell_has_base", set(base["cell_id"].astype(str)) == selected_cells, len(set(base["cell_id"].astype(str))), 24)
    add("each_selected_cell_has_overhead", set(overhead["cell_id"].astype(str)) == selected_cells, len(set(overhead["cell_id"].astype(str))), 24)
    hours_ok = matrix.groupby(["cell_id", "scenario"])["hour"].apply(lambda s: set(pd.to_numeric(s)) == set(HOURS)).all()
    add("each_selected_cell_has_required_hours", hours_ok, "checked", "10,12,13,15,16")
    add("replaced_out_cells_absent", not bool(REPLACED_OUT & matrix_cells), "|".join(sorted(REPLACED_OUT & matrix_cells)), "none")
    add("replacement_in_cells_present", REPLACEMENT_IN <= matrix_cells, "|".join(sorted(REPLACEMENT_IN & matrix_cells)), "|".join(sorted(REPLACEMENT_IN)))
    add("no_duplicate_run_id", not matrix["run_id"].duplicated().any(), int(matrix["run_id"].duplicated().sum()), 0)
    add("no_tif_files_created", ".tif" not in text and ".tiff" not in text, "manifest text checked", "no .tif/.tiff")
    add("no_data_solweig_files_created", "data/solweig" not in text.replace("\\", "/"), "manifest text checked", "no data/solweig")
    add("template_paths_only", matrix["tmrt_output_expected"].astype(str).str.startswith("future_template_").all(), "checked", "future_template_*")
    add("raw_outputs_do_not_commit", matrix["do_not_commit_raw_output"].eq(True).all(), "checked", "all true")
    for token in ["local_wbgt_c", "hazard_score", "risk_score", "system_a"]:
        add(f"no_{token}", token not in text, "checked", f"no {token}")
    out = pd.DataFrame(checks)
    out.to_csv(root / OUTPUT_DIR / "n24_solweig_manifest_preflight.csv", index=False)
    status = "PASS" if out["passed"].all() else "PARTIAL"
    lines = [
        "# N24 SOLWEIG Manifest Preflight - B2.2 Freeze",
        "",
        f"Status: {status}",
        "",
        f"- Selected cell count: {len(selected_cells)}",
        f"- Base rows: {len(base)}",
        f"- Overhead rows: {len(overhead)}",
        f"- Total rows: {len(matrix)}",
        f"- Replacement-in cells present: {', '.join(sorted(REPLACEMENT_IN & matrix_cells))}",
        f"- Replaced-out cells absent: {'yes' if not bool(REPLACED_OUT & matrix_cells) else 'no'}",
        "- No raster files or .tif/.tiff outputs were created.",
        "- Paths remain future template strings and raw outputs remain do_not_commit.",
    ]
    (root / OUTPUT_DIR / "n24_solweig_manifest_preflight.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_report(
    root: Path,
    selected: pd.DataFrame,
    replacements: pd.DataFrame,
    role_coverage: pd.DataFrame,
    coverage_delta: pd.DataFrame,
    preflight_df: pd.DataFrame,
) -> None:
    status = "PASS" if preflight_df["passed"].all() and len(selected) == 24 else "PARTIAL"
    warnings = role_coverage[role_coverage["required_role_missing"]]
    replacement_lines = [
        f"- {row.replaced_cell_id} -> {row.replacement_cell_id}: {row.reason}"
        for row in replacements.itertuples(index=False)
    ]
    selected_lines = [f"- {cell}" for cell in selected.sort_values("selection_rank")["cell_id"].astype(str)]
    role_lines = [
        f"- {row.diagnostic_role}: {row.selected_cell_count} (minimum {row.required_minimum})"
        for row in role_coverage.itertuples(index=False)
    ]
    base_rows = int(preflight_df.loc[preflight_df["check"] == "base_manifest_rows", "observed"].iloc[0])
    overhead_rows = int(preflight_df.loc[preflight_df["check"] == "overhead_manifest_rows", "observed"].iloc[0])
    total_rows = int(preflight_df.loc[preflight_df["check"] == "total_manifest_rows", "observed"].iloc[0])
    duplicate = preflight_df.loc[preflight_df["check"] == "no_duplicate_run_id", "passed"].iloc[0]
    lines = [
        "# Sprint B2.2 - N24 Human QA Replacement / Selection Freeze",
        "",
        "## Status",
        status,
        "",
        "## Scope",
        "- apply human QA replacements only",
        "- no SOLWEIG",
        "- no QGIS",
        "- no rasters",
        "- no .tif",
        "- no surrogate",
        "- no hazard/risk/local WBGT",
        "- no System A/B coupling",
        "",
        "## Human QA rule",
        "The human QA was a quick map sanity check, not full semantic validation. The goal was to remove clearly unsuitable cells before SOLWEIG execution. No AMBER tier is used. Cells are either KEEP or REPLACE.",
        "",
        "## Replacements applied",
        "\n".join(replacement_lines),
        "",
        "## Frozen N24 selected cells",
        "\n".join(selected_lines),
        "",
        "## Coverage after replacement",
        "\n".join(role_lines),
        "",
        f"Coverage warnings: {', '.join(warnings['diagnostic_role'].astype(str).tolist()) if not warnings.empty else 'none'}.",
        "Coverage delta is written to `n24_b2_2_coverage_delta_vs_b2.csv`.",
        "",
        "## Manifest after replacement",
        f"- base rows = {base_rows}",
        f"- overhead rows = {overhead_rows}",
        f"- total rows = {total_rows}",
        f"- no duplicate run_id = {str(bool(duplicate)).lower()}",
        "- no forbidden paths created",
        "",
        "## Next recommended action",
        "B3-A controlled SOLWEIG execution smoke, not full 240-run yet. Suggested smoke should use 1-2 cells from frozen N24: one trusted hot/continuity anchor such as TP_0565 or TP_0986, and one replacement or diagnostic cell if desired such as TP_0141 or TP_0575. Run only a tiny subset first before full N24.",
        "",
        "## Boundary confirmation",
        "- no rasters touched",
        "- no .tif touched",
        "- no QGIS",
        "- no SOLWEIG",
        "- no API calls",
        "- no model training",
        "- no surrogate",
        "- no risk map",
        "- no local WBGT",
        "- no System A/B coupling",
        "- no commit/stage",
    ]
    (root / OUTPUT_DIR / "sprint_b2_2_n24_human_qa_freeze_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    root = args.repo_root.resolve()
    ensure_dirs(root)
    inputs = load_inputs(root)
    selected = inputs["selected"]
    if selected.empty:
        raise SystemExit("Missing n24_selected_cells.csv; cannot apply B2.2 freeze.")
    final, replaced_out, replacements = apply_replacements(inputs)
    if len(final) != 24:
        raise SystemExit(f"Frozen selection has {len(final)} rows, expected 24.")
    if final["cell_id"].duplicated().any():
        dupes = final.loc[final["cell_id"].duplicated(), "cell_id"].tolist()
        raise SystemExit(f"Frozen selection has duplicate cells: {dupes}")
    if REPLACED_OUT & set(final["cell_id"].astype(str)):
        raise SystemExit("A replaced-out cell remains in final selected list.")
    if not REPLACEMENT_IN <= set(final["cell_id"].astype(str)):
        raise SystemExit("A replacement-in cell is missing from final selected list.")

    final.to_csv(root / OUTPUT_DIR / "n24_selected_cells.csv", index=False)
    final.to_csv(root / OUTPUT_DIR / "n24_selected_cells_b2_2_human_qa_freeze.csv", index=False)
    replacements.to_csv(root / OUTPUT_DIR / "n24_human_qa_replacements.csv", index=False)
    replaced_out.to_csv(root / OUTPUT_DIR / "n24_replaced_out_cells.csv", index=False)

    coverage_matrix, role_coverage, coverage_delta = regenerate_coverage(root, final, inputs["roles"], inputs["coverage"])
    coverage_matrix.to_csv(root / OUTPUT_DIR / "n24_typology_coverage_matrix.csv", index=False)
    role_coverage.to_csv(root / OUTPUT_DIR / "n24_diagnostic_role_coverage.csv", index=False)
    coverage_delta.to_csv(root / OUTPUT_DIR / "n24_b2_2_coverage_delta_vs_b2.csv", index=False)
    base, overhead, matrix = write_manifests(root, final)
    preflight_df = preflight(root, final, base, overhead, matrix)
    write_report(root, final, replacements, role_coverage, coverage_delta, preflight_df)


if __name__ == "__main__":
    main()
