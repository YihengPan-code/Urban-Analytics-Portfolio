"""Sprint B2 System B N=24 sample design and SOLWEIG manifest preflight.

Inputs:
    Existing CSV/MD/JSON summary, config, and grid metadata files only. The
    script reads System B target-robustness outputs, Core 8 summary CSVs, v12
    candidate metadata, and v10 non-raster grid feature tables when present.

Outputs:
    outputs/v12_systemb_n24_sample_design/b1_consistency_precheck.csv
    outputs/v12_systemb_n24_sample_design/b1_consistency_precheck.md
    outputs/v12_systemb_n24_sample_design/b2_input_inventory.csv
    outputs/v12_systemb_n24_sample_design/n24_candidate_pool.csv
    outputs/v12_systemb_n24_sample_design/n24_candidate_roles_long.csv
    outputs/v12_systemb_n24_sample_design/n24_selected_cells.csv
    outputs/v12_systemb_n24_sample_design/n24_alternate_cells.csv
    outputs/v12_systemb_n24_sample_design/n24_typology_coverage_matrix.csv
    outputs/v12_systemb_n24_sample_design/n24_diagnostic_role_coverage.csv
    configs/v12/v12_solweig_n24_base_manifest.csv
    configs/v12/v12_solweig_n24_overhead_manifest.csv
    configs/v12/v12_solweig_n24_run_matrix.csv
    outputs/v12_systemb_n24_sample_design/n24_solweig_manifest_preflight.csv
    outputs/v12_systemb_n24_sample_design/n24_solweig_manifest_preflight.md
    docs/v12/OpenHeat_SystemB_N24_companion_metric_plan_CN.md
    docs/v12/OpenHeat_SystemB_N24_SOLWEIG_manifest_execution_guide_CN.md
    outputs/v12_systemb_n24_sample_design/sprint_b2_n24_sample_design_report.md

Saved metrics:
    B1 consistency checks, input inventory, candidate feature availability,
    diagnostic role coverage, N=24 selected/alternate rationale, future-run
    manifest counts, duplicate checks, and boundary checks.

This script does not run SOLWEIG, run QGIS, read rasters, read or write .tif or
.tiff files, train models, create a surrogate, create hazard/risk maps, create
local WBGT, or perform System A/B coupling.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


OUTPUT_DIR = Path("outputs/v12_systemb_n24_sample_design")
DOCS_DIR = Path("docs/v12")
CONFIG_DIR = Path("configs/v12")
HOURS = [10, 12, 13, 15, 16]
SCENARIOS = ["base", "overhead_as_canopy"]
CORE8_CELLS = ["TP_0059", "TP_0326", "TP_0366", "TP_0542", "TP_0565", "TP_0627", "TP_0835", "TP_0986"]
LEGACY_CONTINUITY = ["TP_0565", "TP_0986", "TP_0088", "TP_0916", "TP_0433"]
REQUIRED_NEW = ["TP_0088", "TP_0916", "TP_0433", "TP_0857", "TP_0828", "TP_0802", "TP_0492"]
STATUS_BLOCKED = "BLOCKED_PENDING_B1_PATCH"


INPUT_FILES = [
    "outputs/v12_systemb_target_robustness/systemb_target_robustness_report.md",
    "outputs/v12_systemb_target_robustness/systemb_target_decision_matrix.csv",
    "outputs/v12_systemb_target_robustness/normalized_tmrt_targets_long.csv",
    "outputs/v12_systemb_target_robustness/normalized_modifier_targets_long.csv",
    "outputs/v12_systemb_target_robustness/target_rank_correlation.csv",
    "outputs/v12_systemb_target_robustness/target_topk_overlap.csv",
    "outputs/v12_systemb_target_robustness/base_vs_overhead_sensitivity_summary.csv",
    "outputs/v12_systemb_target_robustness/hour_stability_rank_correlation.csv",
    "outputs/v12_systemb_target_robustness/hour_stability_consistent_cells.csv",
    "outputs/v12_systemb_target_robustness/typology_interpretability_audit.csv",
    "outputs/v12_solweig_typology_pilot/core8_base_summary/tmrt_cell_summary_long.csv",
    "outputs/v12_solweig_typology_pilot/core8_base_summary/modifier_targets_long.csv",
    "outputs/v12_solweig_typology_pilot/core8_base_summary/modifier_reference_table.csv",
    "outputs/v12_solweig_typology_pilot/core8_overhead_summary/tmrt_cell_summary_long.csv",
    "outputs/v12_solweig_typology_pilot/core8_overhead_summary/modifier_targets_long.csv",
    "outputs/v12_solweig_typology_pilot/core8_overhead_summary/core8_base_vs_overhead_delta.csv",
    "outputs/v12_solweig_typology_pilot/core8_overhead_summary/core8_base_vs_overhead_delta_by_cell.csv",
    "outputs/v12_solweig_typology_pilot/wave1_base_summary/v12_solweig_typology_aggregation_report.md",
    "outputs/v12_solweig_typology_pilot/overhead_smoke_summary/overhead_smoke_vs_base_h13.md",
    "configs/v12/v12_solweig_core8_base_manifest.csv",
    "configs/v12/v12_solweig_core8_overhead_manifest.csv",
    "configs/v12/v12_solweig_overhead_smoke_h13_manifest.csv",
    "configs/v12/v12_solweig_typology_config.example.json",
    "data/grid/v12/solweig_typology_cell_candidates.csv",
    "data/grid/v10/toa_payoh_grid_v10_features_overhead_sensitivity.csv",
    "data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv",
    "data/grid/v10/toa_payoh_grid_v10_umep_morphology_with_veg.csv",
    "docs/v12/OpenHeat_SystemB_product_taxonomy_CN.md",
    "docs/v12/OpenHeat_SystemB_target_robustness_protocol_CN.md",
    "docs/v12/OpenHeat_modifier_target_spec_CN.md",
    "docs/v12/OpenHeat_v12_SOLWEIG_typology_pilot_interim_findings_CN.md",
    "docs/v10/V10_EPSILON_SOLWEIG_final_findings_report_CN.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Sprint B2 N=24 System B sample design and future SOLWEIG manifest preflight."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root.")
    return parser.parse_args()


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def read_csv_if_exists(root: Path, rel_path: str) -> pd.DataFrame:
    path = root / rel_path
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def read_text_if_exists(root: Path, rel_path: str) -> str:
    path = root / rel_path
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def ensure_dirs(root: Path) -> None:
    for directory in [root / OUTPUT_DIR, root / DOCS_DIR, root / CONFIG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def lower_columns(df: pd.DataFrame) -> set[str]:
    return {str(c).lower() for c in df.columns}


def contains_any(columns: set[str], tokens: list[str]) -> bool:
    return any(any(token in c for token in tokens) for c in columns)


def inventory_file(root: Path, rel_path: str) -> dict[str, Any]:
    path = root / rel_path
    row: dict[str, Any] = {
        "path": rel_path,
        "exists": path.exists(),
        "row_count_if_easy": "",
        "columns_if_csv": "",
        "contains_cell_id": False,
        "contains_typology": False,
        "contains_tmrt_metrics": False,
        "contains_m_rad_pct": False,
        "contains_overhead_metrics": False,
        "contains_svf": False,
        "contains_shade_fraction": False,
        "contains_building_density": False,
        "contains_gvi_or_tree_canopy": False,
        "contains_water_or_grass": False,
        "contains_pedestrian_relevance_proxy": False,
        "notes": "",
    }
    if not path.exists():
        row["notes"] = "missing"
        return row
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path)
        columns = lower_columns(df)
        row.update(
            {
                "row_count_if_easy": len(df),
                "columns_if_csv": "|".join(df.columns),
                "contains_cell_id": "cell_id" in columns,
                "contains_typology": contains_any(columns, ["typology", "label", "role"]),
                "contains_tmrt_metrics": contains_any(columns, ["tmrt_", "delta_tmrt"]),
                "contains_m_rad_pct": "m_rad_pct" in columns,
                "contains_overhead_metrics": contains_any(columns, ["overhead", "viaduct", "covered_walkway"]),
                "contains_svf": contains_any(columns, ["svf"]),
                "contains_shade_fraction": contains_any(columns, ["shade_fraction", "shade_proxy"]),
                "contains_building_density": contains_any(columns, ["building_density", "building_pixel"]),
                "contains_gvi_or_tree_canopy": contains_any(columns, ["gvi", "tree_canopy", "tree_fraction"]),
                "contains_water_or_grass": contains_any(columns, ["water", "grass"]),
                "contains_pedestrian_relevance_proxy": contains_any(
                    columns, ["bus_stop", "school", "preschool", "pedestrian", "walkway", "shelter"]
                ),
            }
        )
    elif suffix in {".md", ".txt"}:
        text = path.read_text(encoding="utf-8", errors="replace")
        row["row_count_if_easy"] = text.count("\n") + (1 if text else 0)
        row["notes"] = "text file; row_count is line_count"
    elif suffix == ".json":
        try:
            obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            row["row_count_if_easy"] = len(obj) if isinstance(obj, list) else 1
            row["notes"] = "json metadata"
        except json.JSONDecodeError as exc:
            row["notes"] = f"json_read_error: {exc}"
    else:
        row["notes"] = f"not parsed suffix {suffix}"
    return row


def b1_precheck(root: Path) -> tuple[str, pd.DataFrame]:
    report = read_text_if_exists(root, "outputs/v12_systemb_target_robustness/systemb_target_robustness_report.md")
    matrix = read_csv_if_exists(root, "outputs/v12_systemb_target_robustness/systemb_target_decision_matrix.csv")
    rows = []
    checks = {
        "b1_report_exists": bool(report),
        "p90_provisional_primary_candidate": "provisional primary System B target candidate" in report,
        "p90_not_canonical": "do not promote it to canonical target yet" in report,
        "next_action_says_b2": "B2 N=24 scaled sample design" in report and "B3 N=24 scaled sample design" not in report,
        "old_downgrade_wording_absent": "Downgrade p90 pending more samples" not in report
        and "downgrade p90 pending more samples" not in report,
        "decision_matrix_p90_status_ok": False,
        "threshold_area_marked_missing_future_companion": False,
    }
    if not matrix.empty and "metric" in matrix.columns:
        p90 = matrix[matrix["metric"] == "tmrt_p90_c"]
        checks["decision_matrix_p90_status_ok"] = (
            not p90.empty
            and str(p90.iloc[0].get("recommended_status", "")) == "provisional_primary_candidate"
        )
        threshold = matrix[matrix["metric"].astype(str).str.startswith("pct_pixels_tmrt_ge_")]
        checks["threshold_area_marked_missing_future_companion"] = (
            len(threshold) >= 4
            and (threshold["recommended_status"] == "missing_required_future_companion").all()
        )
    for name, passed in checks.items():
        rows.append({"check": name, "passed": bool(passed), "notes": "" if passed else "requires review"})
    status = "PASS" if all(checks.values()) else "BLOCKED_PENDING_B1_PATCH"
    out = pd.DataFrame(rows)
    out["b2_status"] = status
    return status, out


def write_precheck(root: Path, status: str, precheck: pd.DataFrame) -> None:
    precheck.to_csv(root / OUTPUT_DIR / "b1_consistency_precheck.csv", index=False)
    failed = precheck[~precheck["passed"]]
    lines = [
        "# Sprint B2 B1 Consistency Precheck",
        "",
        f"Status: {status}",
        "",
        "Checks:",
    ]
    for row in precheck.itertuples(index=False):
        mark = "PASS" if row.passed else "FAIL"
        lines.append(f"- {mark}: {row.check}")
    if not failed.empty:
        lines.append("")
        lines.append("B2 must stop until B1 wording is patched.")
    (root / OUTPUT_DIR / "b1_consistency_precheck.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_inventory(root: Path) -> pd.DataFrame:
    rows = [inventory_file(root, path) for path in INPUT_FILES]
    inventory = pd.DataFrame(rows)
    inventory.to_csv(root / OUTPUT_DIR / "b2_input_inventory.csv", index=False)
    return inventory


def first_available(row: pd.Series, names: list[str]) -> Any:
    for name in names:
        if name in row.index and pd.notna(row[name]):
            return row[name]
    return pd.NA


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def load_feature_table(root: Path) -> pd.DataFrame:
    overhead = read_csv_if_exists(root, "data/grid/v10/toa_payoh_grid_v10_features_overhead_sensitivity.csv")
    features = read_csv_if_exists(root, "data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv")
    morphology = read_csv_if_exists(root, "data/grid/v10/toa_payoh_grid_v10_umep_morphology_with_veg.csv")
    base = overhead if not overhead.empty else features
    if base.empty:
        base = morphology
    return base.copy()


def aggregate_metric_targets(root: Path) -> pd.DataFrame:
    modifier = read_csv_if_exists(root, "outputs/v12_systemb_target_robustness/normalized_modifier_targets_long.csv")
    if modifier.empty:
        return pd.DataFrame(columns=["cell_id"])
    rows = []
    for cell_id, group in modifier.groupby("cell_id"):
        base = group[group["scenario"] == "base"]
        overhead = group[group["scenario"] == "overhead_as_canopy"]
        h13_base = base[base["hour"] == 13]
        source = h13_base if not h13_base.empty else base
        row: dict[str, Any] = {
            "cell_id": cell_id,
            "existing_solweig_base_available": not base.empty,
            "existing_solweig_overhead_available": not overhead.empty,
        }
        for metric, out_col in [
            ("tmrt_p90_c", "tmrt_p90_base_mean_or_h13"),
            ("tmrt_p95_c", "tmrt_p95_base_mean_or_h13"),
            ("tmrt_max_c", "tmrt_max_base_mean_or_h13"),
            ("m_rad_pct", "m_rad_pct_mean_or_h13"),
        ]:
            row[out_col] = numeric(source[metric]).mean() if metric in source else pd.NA
        rows.append(row)
    return pd.DataFrame(rows)


def aggregate_overhead_delta(root: Path) -> pd.DataFrame:
    delta = read_csv_if_exists(root, "outputs/v12_solweig_typology_pilot/core8_overhead_summary/core8_base_vs_overhead_delta.csv")
    if delta.empty:
        return pd.DataFrame(columns=["cell_id"])
    rows = []
    for cell_id, group in delta.groupby("cell_id"):
        h13 = group[group["hour_sgt"] == 13] if "hour_sgt" in group.columns else pd.DataFrame()
        source = h13 if not h13.empty else group
        row = {
            "cell_id": cell_id,
            "overhead_delta_p90_available": "delta_tmrt_p90_overhead_minus_base" in group.columns,
            "overhead_delta_p90_mean_or_h13": numeric(source.get("delta_tmrt_p90_overhead_minus_base", pd.Series(dtype=float))).mean(),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def core8_labels(root: Path) -> pd.DataFrame:
    tmrt = read_csv_if_exists(root, "outputs/v12_solweig_typology_pilot/core8_base_summary/tmrt_cell_summary_long.csv")
    if tmrt.empty:
        return pd.DataFrame(columns=["cell_id", "core8_typology_label"])
    cols = ["cell_id"]
    if "typology_label" in tmrt.columns:
        cols.append("typology_label")
    out = tmrt[cols].drop_duplicates("cell_id").copy()
    if "typology_label" in out.columns:
        out = out.rename(columns={"typology_label": "core8_typology_label"})
    else:
        out["core8_typology_label"] = ""
    return out


def v12_candidates(root: Path) -> pd.DataFrame:
    path = "data/grid/v12/solweig_typology_cell_candidates.csv"
    df = read_csv_if_exists(root, path)
    if df.empty:
        return pd.DataFrame(columns=["cell_id"])
    rename = {
        "typology_label": "v12_typology_label",
        "role": "v12_candidate_role",
        "selection_status": "v12_selection_status",
        "expected_direction": "v12_expected_direction",
        "notes": "v12_candidate_notes",
    }
    return df.rename(columns=rename)


def classify_group(label: str, row: pd.Series) -> str:
    text = " ".join(
        str(x).lower()
        for x in [
            label,
            row.get("land_use_hint", ""),
            row.get("land_use_raw", ""),
            row.get("overhead_interpretation", ""),
            row.get("v12_candidate_role", ""),
        ]
    )
    if any(t in text for t in ["school", "bus_stop", "bus stop", "waiting"]):
        return "pedestrian_waiting_node"
    if any(t in text for t in ["viaduct", "transport_deck", "elevated_road", "elevated rail", "transport"]):
        return "transport_overhead_or_viaduct"
    if any(t in text for t in ["walkway", "shelter", "covered"]):
        return "covered_walkway_or_pedestrian_overhead"
    if any(t in text for t in ["water", "river", "blue"]):
        return "water_edge_or_blue_green"
    if any(t in text for t in ["grass", "park", "green"]):
        return "grass_or_open_park"
    if any(t in text for t in ["shade", "tree", "canopy"]):
        return "shaded_or_canopy_reference"
    if any(t in text for t in ["canyon", "wall", "hdb", "high_rise"]):
        return "street_canyon_wall_adjacent"
    if any(t in text for t in ["hardscape", "paved", "parking", "open_paved"]):
        return "open_paved_hardscape"
    return "mixed_urban_context"


def boolish(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "none", "nan"}
    return bool(value)


def build_candidate_pool(root: Path) -> pd.DataFrame:
    features = load_feature_table(root)
    if features.empty or "cell_id" not in features.columns:
        seed_ids = sorted(set(CORE8_CELLS + LEGACY_CONTINUITY))
        features = pd.DataFrame({"cell_id": seed_ids})
    candidates = v12_candidates(root)
    targets = aggregate_metric_targets(root)
    overhead_delta = aggregate_overhead_delta(root)
    labels = core8_labels(root)

    pool = features.merge(candidates, on="cell_id", how="outer")
    pool = pool.merge(labels, on="cell_id", how="left")
    pool = pool.merge(targets, on="cell_id", how="left")
    pool = pool.merge(overhead_delta, on="cell_id", how="left")

    rows = []
    for _, row in pool.iterrows():
        cell_id = str(row["cell_id"])
        typology = first_available(row, ["core8_typology_label", "v12_typology_label", "land_use_hint", "land_use_raw"])
        if pd.isna(typology):
            typology = ""
        selection_sources = []
        if cell_id in CORE8_CELLS:
            selection_sources.append("core8")
        if cell_id in LEGACY_CONTINUITY:
            selection_sources.append("v10_epsilon_continuity")
        if pd.notna(row.get("v12_candidate_role", pd.NA)):
            selection_sources.append("v12_candidate_seed")
        if pd.notna(row.get("svf_umep_mean_open_v10", pd.NA)) or pd.notna(row.get("svf", pd.NA)):
            selection_sources.append("v10_non_raster_features")
        if not selection_sources:
            selection_sources.append("v10_feature_pool")

        out = {
            "cell_id": cell_id,
            "in_core8": cell_id in CORE8_CELLS,
            "in_v10_epsilon": cell_id in LEGACY_CONTINUITY,
            "in_existing_wave1": boolish(row.get("existing_solweig_base_available", False)),
            "typology_label": typology,
            "typology_group": classify_group(str(typology), row),
            "selection_source": "|".join(dict.fromkeys(selection_sources)),
            "existing_solweig_base_available": boolish(row.get("existing_solweig_base_available", False)),
            "existing_solweig_overhead_available": boolish(row.get("existing_solweig_overhead_available", False)),
            "tmrt_p90_base_mean_or_h13": row.get("tmrt_p90_base_mean_or_h13", pd.NA),
            "tmrt_p95_base_mean_or_h13": row.get("tmrt_p95_base_mean_or_h13", pd.NA),
            "tmrt_max_base_mean_or_h13": row.get("tmrt_max_base_mean_or_h13", pd.NA),
            "m_rad_pct_mean_or_h13": row.get("m_rad_pct_mean_or_h13", pd.NA),
            "overhead_delta_p90_available": boolish(row.get("overhead_delta_p90_available", False)),
            "overhead_delta_p90_mean_or_h13": row.get("overhead_delta_p90_mean_or_h13", pd.NA),
            "svf": first_available(row, ["svf_umep_mean_open_v10", "svf_umep_selected", "svf"]),
            "shade_fraction": first_available(
                row,
                ["shade_fraction_umep_13_15_open_v10", "shade_fraction_umep_selected", "shade_fraction"],
            ),
            "building_density": first_available(row, ["v10_building_density", "building_density", "building_pixel_fraction_v10"]),
            "tree_canopy_or_gvi": first_available(row, ["tree_canopy_fraction", "dynamic_world_tree_fraction", "gvi_percent"]),
            "grass_fraction": first_available(row, ["grass_fraction", "dynamic_world_grass_fraction"]),
            "water_fraction": first_available(row, ["water_fraction", "dynamic_world_water_fraction"]),
            "overhead_fraction": first_available(row, ["overhead_fraction_total", "overhead_shade_proxy"]),
            "road_fraction": row.get("road_fraction", pd.NA),
            "pedestrian_relevance_proxy": first_available(
                row,
                [
                    "pedestrian_shelter_fraction",
                    "bus_stop_count",
                    "preschool_count",
                    "node_vulnerability_score",
                ],
            ),
            "land_use_hint": row.get("land_use_hint", ""),
            "notes": first_available(row, ["v12_candidate_notes", "overhead_sensitivity_note", "umep_morphology_notes"]),
        }
        rows.append(out)
    out = pd.DataFrame(rows).drop_duplicates("cell_id")
    numeric_cols = [
        "tmrt_p90_base_mean_or_h13",
        "tmrt_p95_base_mean_or_h13",
        "tmrt_max_base_mean_or_h13",
        "m_rad_pct_mean_or_h13",
        "overhead_delta_p90_mean_or_h13",
        "svf",
        "shade_fraction",
        "building_density",
        "tree_canopy_or_gvi",
        "grass_fraction",
        "water_fraction",
        "overhead_fraction",
        "road_fraction",
        "pedestrian_relevance_proxy",
    ]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.sort_values("cell_id").reset_index(drop=True)


def add_role(rows: list[dict[str, Any]], cell_id: str, role: str, evidence: str, confidence: str, source: str, caveat: str = "") -> None:
    rows.append(
        {
            "cell_id": cell_id,
            "diagnostic_role": role,
            "evidence": evidence,
            "confidence": confidence,
            "source_file": source,
            "caveat": caveat,
        }
    )


def assign_roles(pool: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    p90_rank = pool["tmrt_p90_base_mean_or_h13"].rank(ascending=False, method="min")
    p95_rank = pool["tmrt_p95_base_mean_or_h13"].rank(ascending=False, method="min")
    max_rank = pool["tmrt_max_base_mean_or_h13"].rank(ascending=False, method="min")
    for idx, row in pool.iterrows():
        cell_id = row["cell_id"]
        label = str(row.get("typology_label", "")).lower()
        source = "n24_candidate_pool.csv"
        if row.get("in_core8", False):
            add_role(rows, cell_id, "core_continuity", "Existing Core 8 cell retained for continuity.", "high", source)
        if cell_id in {"TP_0565", "TP_0986"}:
            add_role(rows, cell_id, "confident_hot_anchor_continuity", "B1/Core or v10-epsilon hot-anchor continuity cell.", "high", source)
        if cell_id in {"TP_0088", "TP_0916"}:
            add_role(rows, cell_id, "overhead_confounded_legacy_diagnostic", "Legacy overhead-confounded diagnostic; sensitivity only.", "high", source)
        if any(t in label for t in ["shade", "tree", "canopy"]) or cell_id in {"TP_0542", "TP_0433", "TP_0835"}:
            add_role(rows, cell_id, "shaded_or_canopy_reference", "Label or legacy role indicates shade/canopy reference.", "high", source)
        if row.get("svf", math.nan) >= 0.78 and row.get("shade_fraction", math.nan) <= 0.12:
            add_role(rows, cell_id, "open_paved_hardscape", "High SVF and low shade fraction.", "medium", source)
        if row.get("svf", math.nan) <= 0.30 or row.get("building_density", math.nan) >= 0.55 or any(t in label for t in ["canyon", "wall"]):
            add_role(rows, cell_id, "street_canyon_wall_adjacent", "Low SVF, high building density, or canyon/wall label.", "medium", source)
        if row.get("overhead_fraction", math.nan) >= 0.03 or row.get("pedestrian_relevance_proxy", math.nan) > 0:
            add_role(rows, cell_id, "covered_walkway_or_pedestrian_overhead", "Overhead or pedestrian shelter proxy is present.", "medium", source)
        if row.get("overhead_fraction", math.nan) >= 0.20 or "transport" in label or "viaduct" in label:
            add_role(rows, cell_id, "transport_overhead_or_viaduct", "Transport/viaduct or high overhead fraction diagnostic.", "medium", source, "Sensitivity only.")
        if row.get("water_fraction", math.nan) > 0 or "water" in label or "river" in label:
            add_role(rows, cell_id, "water_edge_or_blue_green", "Water/river label or water fraction present.", "medium", source)
        if row.get("grass_fraction", math.nan) > 0 or "grass" in label or "park" in label:
            add_role(rows, cell_id, "grass_or_open_park", "Grass/park/open green label or grass fraction present.", "medium", source)
        if any(t in label for t in ["school", "bus_stop", "bus stop", "waiting"]) or row.get("pedestrian_relevance_proxy", math.nan) >= 1:
            add_role(rows, cell_id, "school_gate_bus_stop_waiting_node", "School, bus-stop, or waiting-node cue.", "medium", source)
            add_role(rows, cell_id, "pedestrian_relevance_probe", "Pedestrian relevance proxy or label cue.", "medium", source)
        if pd.notna(p90_rank.iloc[idx]) and pd.notna(p95_rank.iloc[idx]) and abs(p90_rank.iloc[idx] - p95_rank.iloc[idx]) >= 2:
            add_role(rows, cell_id, "p90_p95_disagreement_probe", "Existing p90 and p95 ranks diverge within Core 8.", "medium", source)
        if pd.notna(p90_rank.iloc[idx]) and pd.notna(max_rank.iloc[idx]) and abs(p90_rank.iloc[idx] - max_rank.iloc[idx]) >= 2:
            add_role(rows, cell_id, "p90_p95_disagreement_probe", "Existing p90 and max ranks diverge within Core 8.", "medium", source)
            add_role(rows, cell_id, "max_extreme_probe", "Existing p90 and max ranks diverge within Core 8.", "medium", source)
        if row.get("svf", math.nan) >= 0.70 or row.get("shade_fraction", math.nan) <= 0.20 or row.get("tmrt_max_base_mean_or_h13", math.nan) >= 60:
            add_role(rows, cell_id, "threshold_area_probe", "Expected to test future threshold-area exceedance metrics.", "medium", source)
        if row.get("overhead_delta_p90_available", False) or row.get("overhead_fraction", math.nan) >= 0.03:
            add_role(rows, cell_id, "overhead_sensitivity_probe", "Existing or expected base-vs-overhead sensitivity.", "medium", source)
    return pd.DataFrame(rows).drop_duplicates(["cell_id", "diagnostic_role"])


def role_cells(roles: pd.DataFrame, role: str, selected: set[str]) -> list[str]:
    if roles.empty:
        return []
    cells = roles[roles["diagnostic_role"] == role]["cell_id"].astype(str).tolist()
    return [c for c in cells if c not in selected]


def pick_best(pool: pd.DataFrame, cells: list[str], selected: set[str], count: int, sort_cols: list[str]) -> list[str]:
    candidates = pool[pool["cell_id"].isin(cells) & ~pool["cell_id"].isin(selected)].copy()
    if candidates.empty:
        return []
    for col in sort_cols:
        if col not in candidates.columns:
            candidates[col] = pd.NA
    ascending = [False for _ in sort_cols] + [True]
    candidates = candidates.sort_values(sort_cols + ["cell_id"], ascending=ascending, na_position="last")
    return candidates["cell_id"].head(count).astype(str).tolist()


def select_cells(pool: pd.DataFrame, roles: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected: list[str] = []
    status: dict[str, str] = {}

    def add(cell_id: str, sel_status: str) -> None:
        if cell_id in set(pool["cell_id"].astype(str)) and cell_id not in selected and len(selected) < 24:
            selected.append(cell_id)
            status[cell_id] = sel_status

    for cell_id in CORE8_CELLS:
        add(cell_id, "selected_core")
    for cell_id in REQUIRED_NEW:
        add(cell_id, "selected_legacy_diagnostic" if cell_id in {"TP_0088", "TP_0916", "TP_0433"} else "selected_new")

    selected_set = set(selected)
    role_requirements = [
        ("open_paved_hardscape", 2, ["svf", "road_fraction"]),
        ("shaded_or_canopy_reference", 2, ["shade_fraction", "tree_canopy_or_gvi"]),
        ("covered_walkway_or_pedestrian_overhead", 2, ["overhead_fraction", "pedestrian_relevance_proxy"]),
        ("transport_overhead_or_viaduct", 2, ["overhead_fraction", "road_fraction"]),
        ("street_canyon_wall_adjacent", 2, ["building_density", "shade_fraction"]),
        ("water_edge_or_blue_green", 2, ["water_fraction", "tree_canopy_or_gvi"]),
        ("school_gate_bus_stop_waiting_node", 2, ["pedestrian_relevance_proxy", "road_fraction"]),
        ("p90_p95_disagreement_probe", 3, ["tmrt_p95_base_mean_or_h13", "tmrt_p90_base_mean_or_h13"]),
        ("threshold_area_probe", 3, ["svf", "tmrt_max_base_mean_or_h13"]),
    ]
    for role, minimum, sort_cols in role_requirements:
        current = len(set(selected) & set(roles[roles["diagnostic_role"] == role]["cell_id"].astype(str)))
        need = max(0, minimum - current)
        for cell_id in pick_best(pool, role_cells(roles, role, selected_set), selected_set, need, sort_cols):
            add(cell_id, "selected_new")
            selected_set = set(selected)

    # Fill remaining slots with typology-diverse, feature-rich cells.
    while len(selected) < 24:
        remaining = pool[~pool["cell_id"].isin(selected)].copy()
        remaining["feature_richness"] = remaining[
            ["svf", "shade_fraction", "building_density", "overhead_fraction", "road_fraction", "water_fraction", "grass_fraction"]
        ].notna().sum(axis=1)
        remaining["underrepresented_bonus"] = remaining["typology_group"].map(
            lambda g: 1 / (1 + pool[pool["cell_id"].isin(selected)]["typology_group"].eq(g).sum())
        )
        remaining = remaining.sort_values(
            ["underrepresented_bonus", "feature_richness", "overhead_fraction", "svf", "cell_id"],
            ascending=[False, False, False, False, True],
            na_position="last",
        )
        if remaining.empty:
            break
        add(str(remaining.iloc[0]["cell_id"]), "selected_new")

    selected_rows = []
    for rank, cell_id in enumerate(selected, start=1):
        row = pool[pool["cell_id"] == cell_id].iloc[0]
        cell_roles = roles[roles["cell_id"] == cell_id]["diagnostic_role"].tolist()
        primary = cell_roles[0] if cell_roles else "typology_coverage"
        secondary = "|".join(cell_roles[1:])
        tier = "core8" if cell_id in CORE8_CELLS else "added16"
        if status[cell_id] == "selected_legacy_diagnostic":
            tier = "added16"
        selected_rows.append(
            {
                "selection_rank": rank,
                "cell_id": cell_id,
                "final_selection_status": status[cell_id],
                "selection_tier": tier,
                "primary_role": primary,
                "secondary_roles": secondary,
                "typology_label": row.get("typology_label", ""),
                "rationale": rationale_for(row, cell_roles, status[cell_id]),
                "evidence_summary": evidence_summary(row),
                "expected_target_test": "p90 provisional target with mean/p75/p95/max companions",
                "expected_p90_p95_max_question": p90_question(cell_roles),
                "expected_threshold_area_question": threshold_question(cell_roles),
                "expected_overhead_question": overhead_question(cell_roles),
                "expected_pedestrian_relevance_question": pedestrian_question(cell_roles),
                "caveat": "Design-only selection; requires human map QA before execution.",
                "source_files": row.get("selection_source", ""),
            }
        )
    selected_df = pd.DataFrame(selected_rows)

    alternates = pool[~pool["cell_id"].isin(selected)].copy()
    alt_rows = []
    role_pref = roles.groupby("cell_id")["diagnostic_role"].apply(lambda s: "|".join(s)).to_dict()
    alternates["role_count"] = alternates["cell_id"].map(lambda c: len(str(role_pref.get(c, "")).split("|")) if role_pref.get(c) else 0)
    alternates = alternates.sort_values(
        ["role_count", "overhead_fraction", "svf", "shade_fraction", "cell_id"],
        ascending=[False, False, False, True, True],
        na_position="last",
    ).head(12)
    for _, row in alternates.iterrows():
        roles_text = role_pref.get(row["cell_id"], "typology_coverage")
        alt_rows.append(
            {
                "cell_id": row["cell_id"],
                "typology_label": row.get("typology_label", ""),
                "typology_group": row.get("typology_group", ""),
                "candidate_roles": roles_text,
                "alternate_rationale": "Alternate for the same or adjacent diagnostic role coverage.",
                "would_replace": suggested_replacement(str(row.get("typology_group", "")), selected_df),
                "caveat": "Not selected in first N=24; keep for human review or B2.1 gap patch.",
            }
        )
    return selected_df, pd.DataFrame(alt_rows)


def rationale_for(row: pd.Series, roles: list[str], status: str) -> str:
    if status == "selected_core":
        return "Retained Core 8 continuity cell for direct comparison with B1."
    if "overhead_confounded_legacy_diagnostic" in roles:
        return "Legacy overhead-confounded diagnostic retained as sensitivity-only probe."
    if "confident_hot_anchor_continuity" in roles:
        return "v10-epsilon continuity hot-anchor retained for upper-tail target validation."
    if "shaded_or_canopy_reference" in roles:
        return "Shaded/canopy reference strengthens exposed-vs-shaded contrast."
    if "street_canyon_wall_adjacent" in roles:
        return "Canyon/wall-adjacent morphology tests low-SVF structural contrast."
    if "transport_overhead_or_viaduct" in roles:
        return "Transport overhead/viaduct diagnostic tests overhead sensitivity without treating it as ordinary hotspot."
    return "Selected to improve typology and diagnostic coverage."


def evidence_summary(row: pd.Series) -> str:
    parts = []
    for label, col in [
        ("svf", "svf"),
        ("shade", "shade_fraction"),
        ("bldg_density", "building_density"),
        ("overhead", "overhead_fraction"),
        ("p90", "tmrt_p90_base_mean_or_h13"),
    ]:
        val = row.get(col, pd.NA)
        if pd.notna(val):
            parts.append(f"{label}={float(val):.3f}")
    return "; ".join(parts) if parts else "metadata-only candidate"


def p90_question(roles: list[str]) -> str:
    if "p90_p95_disagreement_probe" in roles or "max_extreme_probe" in roles:
        return "Does p90 remain stable when p95/max emphasize a different upper-tail behavior?"
    return "Does p90 align with p75/p95/max companions for this typology?"


def threshold_question(roles: list[str]) -> str:
    if "threshold_area_probe" in roles:
        return "Does future threshold-area exceedance identify the same cells as p90?"
    return "Use as companion threshold-area check when aggregator adds pct_pixels_tmrt_ge_*."


def overhead_question(roles: list[str]) -> str:
    if "overhead_sensitivity_probe" in roles or "overhead_confounded_legacy_diagnostic" in roles:
        return "How much does overhead_as_canopy change p90 and companion metrics?"
    return "Expected low or contextual overhead sensitivity."


def pedestrian_question(roles: list[str]) -> str:
    if "pedestrian_relevance_probe" in roles or "school_gate_bus_stop_waiting_node" in roles:
        return "Does the cell represent a pedestrian-relevant waiting/walking context?"
    return "Pedestrian relevance requires future accessible-mask QA."


def suggested_replacement(group: str, selected_df: pd.DataFrame) -> str:
    matches = selected_df[selected_df["typology_label"].astype(str).str.lower().str.contains(group.split("_")[0], na=False)]
    if not matches.empty:
        return str(matches.iloc[-1]["cell_id"])
    return "human_review_same_role"


def coverage(selected: pd.DataFrame, alternates: pd.DataFrame, roles: pd.DataFrame, root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    typology = selected.groupby("selection_tier").size().reset_index(name="selected_count")
    by_group = selected.groupby("typology_label").size().reset_index(name="selected_count")
    by_group["coverage_type"] = "typology_label"
    tier = typology.rename(columns={"selection_tier": "typology_label"})
    tier["coverage_type"] = "selection_tier"
    coverage_matrix = pd.concat([tier, by_group], ignore_index=True)
    coverage_matrix["core8_retained_count"] = int((selected["final_selection_status"] == "selected_core").sum())
    coverage_matrix["new_cell_count"] = int((selected["final_selection_status"] == "selected_new").sum())
    coverage_matrix["legacy_diagnostic_count"] = int((selected["final_selection_status"] == "selected_legacy_diagnostic").sum())
    coverage_matrix["alternates_count"] = len(alternates)
    coverage_matrix.to_csv(root / OUTPUT_DIR / "n24_typology_coverage_matrix.csv", index=False)

    selected_roles = roles[roles["cell_id"].isin(selected["cell_id"])]
    role_counts = selected_roles.groupby("diagnostic_role")["cell_id"].nunique().reset_index(name="selected_cell_count")
    required_min = {
        "core_continuity": 8,
        "confident_hot_anchor_continuity": 2,
        "overhead_confounded_legacy_diagnostic": 2,
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
    full = pd.DataFrame(
        [{"diagnostic_role": role, "required_minimum": minimum} for role, minimum in required_min.items()]
    ).merge(role_counts, on="diagnostic_role", how="left")
    full["selected_cell_count"] = full["selected_cell_count"].fillna(0).astype(int)
    full["required_role_missing"] = full["selected_cell_count"] < full["required_minimum"]
    full["overrepresented_typology"] = ""
    full.to_csv(root / OUTPUT_DIR / "n24_diagnostic_role_coverage.csv", index=False)
    return coverage_matrix, full


def write_manifests(root: Path, selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    for scenario in SCENARIOS:
        for cell_id in selected["cell_id"].astype(str):
            typology = selected.loc[selected["cell_id"] == cell_id, "typology_label"].iloc[0]
            for hour in HOURS:
                run_id = f"v12_n24_{scenario}_{cell_id}_h{hour:02d}"
                rows.append(
                    {
                        "run_id": run_id,
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
                        "notes": f"Future-run manifest only; typology={typology}; do not execute in Sprint B2.",
                    }
                )
    run_matrix = pd.DataFrame(rows)
    base = run_matrix[run_matrix["scenario"] == "base"].copy()
    overhead = run_matrix[run_matrix["scenario"] == "overhead_as_canopy"].copy()
    base.to_csv(root / CONFIG_DIR / "v12_solweig_n24_base_manifest.csv", index=False)
    overhead.to_csv(root / CONFIG_DIR / "v12_solweig_n24_overhead_manifest.csv", index=False)
    run_matrix.to_csv(root / CONFIG_DIR / "v12_solweig_n24_run_matrix.csv", index=False)
    return base, overhead, run_matrix


def manifest_preflight(root: Path, selected: pd.DataFrame, base: pd.DataFrame, overhead: pd.DataFrame, run_matrix: pd.DataFrame) -> pd.DataFrame:
    checks = []

    def add(name: str, passed: bool, observed: Any, expected: Any, notes: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "observed": observed, "expected": expected, "notes": notes})

    selected_cells = set(selected["cell_id"].astype(str))
    add("base_manifest_rows", len(base) == 120, len(base), "24*5=120")
    add("overhead_manifest_rows", len(overhead) == 120, len(overhead), "24*5=120")
    add("total_manifest_rows", len(run_matrix) == 240, len(run_matrix), "24*2*5=240")
    add("selected_cells_in_base", set(base["cell_id"]) == selected_cells, len(set(base["cell_id"])), 24)
    add("selected_cells_in_overhead", set(overhead["cell_id"]) == selected_cells, len(set(overhead["cell_id"])), 24)
    hours_ok = run_matrix.groupby(["cell_id", "scenario"])["hour"].apply(lambda s: set(s) == set(HOURS)).all()
    add("all_required_hours_per_cell_scenario", hours_ok, "checked", "10,12,13,15,16")
    add("no_duplicate_run_id", not run_matrix["run_id"].duplicated().any(), int(run_matrix["run_id"].duplicated().sum()), 0)
    text_blob = run_matrix.astype(str).to_string()
    add("no_tif_files_created", ".tif" not in text_blob.lower() and ".tiff" not in text_blob.lower(), "manifest text checked", "no .tif/.tiff strings")
    add("paths_are_templates", run_matrix["tmrt_output_expected"].astype(str).str.startswith("future_template_").all(), "checked", "future_template_*")
    add("raw_outputs_marked_do_not_commit", run_matrix["do_not_commit_raw_output"].eq(True).all(), "checked", "all true")
    forbidden = ["system_a", "local_wbgt_c", "risk_score", "hazard_score"]
    for token in forbidden:
        add(f"no_{token}", token not in text_blob.lower(), "checked", f"no {token}")
    out = pd.DataFrame(checks)
    out.to_csv(root / OUTPUT_DIR / "n24_solweig_manifest_preflight.csv", index=False)
    status = "PASS" if out["passed"].all() else "PARTIAL"
    lines = [
        "# N24 SOLWEIG Manifest Preflight",
        "",
        f"Status: {status}",
        "",
        f"- Base manifest rows: {len(base)}",
        f"- Overhead manifest rows: {len(overhead)}",
        f"- Total future main runs: {len(run_matrix)}",
        "- No raster files were created.",
        "- Expected paths are future template strings only.",
        "- Raw outputs are marked do_not_commit.",
    ]
    (root / OUTPUT_DIR / "n24_solweig_manifest_preflight.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def write_docs(root: Path) -> None:
    companion = """# OpenHeat System B N24 Companion Metric Plan

## Purpose
`tmrt_p90_c` remains the provisional primary System B target candidate because Sprint B1 showed strong hour stability and strong agreement with p75, but it is not canonical yet. N=24 validation is required before any canonical target claim.

## Required companions
- `tmrt_mean_c`: mixed-cell background radiant exposure.
- `tmrt_p75_c`: lower upper-tail shoulder check.
- `tmrt_p95_c`: more extreme upper-tail check.
- `tmrt_max_c`: upper-bound sensitivity only.
- `delta_tmrt_p90_c`: p90-derived scenario/reference-normalized physical delta.
- `m_rad_pct`: p90/delta-derived normalized rank modifier.
- `pct_pixels_tmrt_ge_40/45/50/55`: future threshold-area companions to add in the next aggregation pass where available.

## N24 validation questions
N=24 should test p90 vs p95, p90 vs max, p90 vs area-above-threshold, overhead sensitivity, hour stability, typology interpretability, and pedestrian relevance. The sample is designed to include exposed hardscape, shaded/canopy references, street canyon or wall-adjacent contexts, water/blue-green contexts, pedestrian waiting nodes, and overhead/viaduct sensitivity diagnostics.

## Boundary
This plan is System B only. It does not create local WBGT, observed heat truth, risk, official warnings, hazard maps, or System A/B coupling.
"""
    guide = """# OpenHeat System B N24 SOLWEIG Manifest Execution Guide

This is a future execution guide, not execution evidence. Sprint B2 did not run QGIS or SOLWEIG.

## Future human execution outline
1. Review the N=24 selected cells and alternates.
2. In QGIS Python Console, prepare wall-height, wall-aspect, and SVF preprocessing inputs for the approved cells and scenarios.
3. Run the SOLWEIG loop from `configs/v12/v12_solweig_n24_run_matrix.csv` only after human approval.
4. Expect 240 main SOLWEIG runs: 24 cells x 2 scenarios x 5 hours.
5. Use resume / skip-completed behavior keyed by `run_id` and `expected_summary_row_key`.
6. Write failure logs for missing preprocess outputs, failed SOLWEIG runs, and incomplete summaries.
7. Aggregate Tmrt after execution to produce mean, p75, p90, p95, max, delta p90, m_rad_pct, and threshold-area metrics where available.

## Stop conditions before execution
- Any selected cell lacks human map QA.
- Any manifest path points to raw output intended for commit.
- Any required preprocessing output is missing.
- Any script would read existing rasters during this design sprint.
- Any output would imply local WBGT, risk, or System A/B coupling.

## Never commit
Raw SOLWEIG outputs, raster files, `.tif` / `.tiff` files, raw API dumps, `data/solweig/`, and `data/rasters/` must not be committed.
"""
    (root / DOCS_DIR / "OpenHeat_SystemB_N24_companion_metric_plan_CN.md").write_text(companion, encoding="utf-8")
    (root / DOCS_DIR / "OpenHeat_SystemB_N24_SOLWEIG_manifest_execution_guide_CN.md").write_text(guide, encoding="utf-8")


def write_blocked_report(root: Path, reason: str, inventory: pd.DataFrame) -> None:
    lines = [
        "# Sprint B2 - N=24 System B Sample Design + SOLWEIG Manifest Preflight",
        "",
        "## Status",
        "BLOCKED",
        "",
        "## Scope",
        "- sample design + manifest preflight only",
        "- no SOLWEIG execution",
        "- no QGIS",
        "- no rasters",
        "- no surrogate",
        "- no hazard map",
        "- no risk map",
        "- no local WBGT",
        "- no System A/B coupling",
        "",
        "## Blocker",
        reason,
        "",
        "## Inputs inspected",
        f"Inventory rows: {len(inventory)}",
    ]
    (root / OUTPUT_DIR / "sprint_b2_n24_sample_design_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(
    root: Path,
    status: str,
    inventory: pd.DataFrame,
    pool: pd.DataFrame,
    selected: pd.DataFrame,
    alternates: pd.DataFrame,
    coverage_matrix: pd.DataFrame,
    role_coverage: pd.DataFrame,
    preflight: pd.DataFrame,
) -> None:
    core = selected[selected["final_selection_status"] == "selected_core"]
    legacy = selected[selected["final_selection_status"] == "selected_legacy_diagnostic"]
    new = selected[selected["final_selection_status"] == "selected_new"]
    missing_roles = role_coverage[role_coverage["required_role_missing"]]
    input_lines = []
    for row in inventory[inventory["exists"]].itertuples(index=False):
        if row.row_count_if_easy != "":
            input_lines.append(f"- {row.path}: rows={row.row_count_if_easy}")
    role_lines = [
        f"- {row.diagnostic_role}: {row.selected_cell_count}"
        for row in role_coverage.sort_values("diagnostic_role").itertuples(index=False)
    ]
    selected_lines = [
        f"- {row.cell_id}: {row.typology_label} ({row.primary_role})"
        for row in selected.itertuples(index=False)
    ]
    alternate_lines = [
        f"- {row.cell_id}: replaces {row.would_replace}; {row.typology_group}"
        for row in alternates.itertuples(index=False)
    ]
    report_status = status if status != "PASS" else ("PASS" if preflight["passed"].all() and len(selected) == 24 else "PARTIAL")
    lines = [
        "# Sprint B2 - N=24 System B Sample Design + SOLWEIG Manifest Preflight",
        "",
        "## Status",
        report_status,
        "",
        "## Scope",
        "- sample design + manifest preflight only",
        "- no SOLWEIG execution",
        "- no QGIS",
        "- no rasters",
        "- no surrogate",
        "- no hazard map",
        "- no risk map",
        "- no local WBGT",
        "- no System A/B coupling",
        "",
        "## Inputs inspected",
        "\n".join(input_lines[:40]) if input_lines else "- none",
        "",
        "## B1 continuity",
        "B1/B1.1/B1.2 conclusion is preserved: `tmrt_p90_c` is a provisional primary System B target candidate, not canonical. Companion metrics are required, including mean, p75, p95, max, delta p90, m_rad_pct, and future threshold-area metrics. N=24 validation is required.",
        "",
        "## Candidate pool",
        f"Candidate pool rows: {len(pool)}. Non-raster feature columns available include SVF, shade, building density, tree/GVI, grass, water, road, and overhead proxies where present.",
        "",
        "## N=24 selected sample",
        f"Core 8 retained: {len(core)}. New/added cells: {len(new)}. Legacy diagnostics: {len(legacy)}. Alternates: {len(alternates)}.",
        "",
        "Selected cells:",
        "\n".join(selected_lines),
        "",
        "Alternates:",
        "\n".join(alternate_lines) if alternate_lines else "- none",
        "",
        "## Coverage",
        "\n".join(role_lines),
        "",
        f"Required roles missing: {', '.join(missing_roles['diagnostic_role'].tolist()) if not missing_roles.empty else 'none'}",
        "",
        "## Why these cells",
        "The N=24 design keeps Core 8 continuity while adding legacy overhead diagnostics, shaded/canopy references, exposed hardscape, low-SVF canyon/wall-adjacent cells, water/green contexts, pedestrian-sensitive waiting nodes, and probes for p90/p95/max disagreement. Threshold-area probe cells are included so future `pct_pixels_tmrt_ge_40/45/50/55` metrics can be evaluated after the next aggregation pass.",
        "",
        "## SOLWEIG manifest preflight",
        f"Expected future main runs: {len(preflight)} preflight checks over 240 manifest rows. Base rows = 120, overhead rows = 120, total rows = 240. The manifest uses future template strings only and marks raw outputs do_not_commit.",
        "",
        "## Caveats",
        "- design only",
        "- N=24 still not full-domain validation",
        "- no pedestrian-accessible mask unless present",
        "- threshold-area metrics may require future aggregator changes",
        "- no local WBGT",
        "- no risk",
        "- no System A/B coupling",
        "",
        "## Next recommended action",
        "1. Human review of N=24 design.",
        "",
        "## Boundary confirmation",
        "- no rasters touched",
        "- no .tif touched",
        "- no SOLWEIG rerun",
        "- no QGIS",
        "- no model training",
        "- no surrogate",
        "- no hazard map",
        "- no risk map",
        "- no local WBGT",
        "- no System A/B coupling performed",
        "- no commit/stage performed",
    ]
    (root / OUTPUT_DIR / "sprint_b2_n24_sample_design_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    root = args.repo_root.resolve()
    ensure_dirs(root)
    status, precheck = b1_precheck(root)
    write_precheck(root, status, precheck)
    inventory = write_inventory(root)
    if status == STATUS_BLOCKED:
        write_blocked_report(root, "B1 wording still contains blocked or inconsistent target conclusion.", inventory)
        return
    candidate_path = root / "data/grid/v12/solweig_typology_cell_candidates.csv"
    feature_path = root / "data/grid/v10/toa_payoh_grid_v10_features_overhead_sensitivity.csv"
    if not candidate_path.exists() or not feature_path.exists():
        write_blocked_report(root, "Key candidate or v10 non-raster feature table is missing; no raster search attempted.", inventory)
        return
    pool = build_candidate_pool(root)
    pool.to_csv(root / OUTPUT_DIR / "n24_candidate_pool.csv", index=False)
    roles = assign_roles(pool)
    roles.to_csv(root / OUTPUT_DIR / "n24_candidate_roles_long.csv", index=False)
    selected, alternates = select_cells(pool, roles)
    selected.to_csv(root / OUTPUT_DIR / "n24_selected_cells.csv", index=False)
    alternates.to_csv(root / OUTPUT_DIR / "n24_alternate_cells.csv", index=False)
    coverage_matrix, role_coverage = coverage(selected, alternates, roles, root)
    base, overhead, run_matrix = write_manifests(root, selected)
    preflight = manifest_preflight(root, selected, base, overhead, run_matrix)
    write_docs(root)
    write_report(root, "PASS", inventory, pool, selected, alternates, coverage_matrix, role_coverage, preflight)


if __name__ == "__main__":
    main()
