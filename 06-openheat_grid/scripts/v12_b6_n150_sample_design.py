"""Sprint B6 System B N150 sample design and manifest builder.

Inputs:
    Frozen B5 target-family reports under outputs/v12_systemb_target_freeze.
    Frozen B2.2/B3/B4 N24 CSV/Markdown outputs.
    CSV-only candidate grid feature tables under data/grid/v12 and data/grid/v10.

Outputs:
    Machine-readable validation, candidate universe, sampling matrix, selected
    cells, alternates, QA, coverage diagnostics, advisory split labels, manifest
    preflight, and a Sprint B6 Markdown report under
    outputs/v12_systemb_n150_sample_design.
    Future SOLWEIG run-matrix CSV manifests under configs/v12.
    Chinese design and manifest notes under docs/v12.

Saved metrics:
    Input pass/block status, eligible candidate counts, retained N24 count,
    new-cell count, alternate count, sampling method, feature missingness,
    stratum/geographic coverage, auto-QA counts, and manifest row counts.

This script does not run QGIS, does not run SOLWEIG, does not read rasters,
does not train surrogate models, and does not compute local WBGT, hazard_score,
risk_score, or System A/B coupled outputs.
"""

from __future__ import annotations

import hashlib
import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from pandas.errors import PerformanceWarning


warnings.filterwarnings("ignore", category=PerformanceWarning)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "v12_systemb_n150_sample_design"
CONFIG_DIR = ROOT / "configs" / "v12"
DOC_DIR = ROOT / "docs" / "v12"

SAMPLE_VERSION = "systemb_n150_sample_v0_1_b6"
TARGET_VERSION = "systemb_target_family_v0_1_b5"
REFERENCE_DOMAIN_FUTURE = "n150_training_future"
SCENARIOS = ["base", "overhead_as_canopy"]
HOURS = [10, 12, 13, 15, 16]
RANDOM_SEED = 42
TOTAL_N = 150
N24_N = 24
NEW_N = 126
ALTERNATE_N = 30

REPLACEMENT_IN = ["TP_0141", "TP_0301", "TP_0773", "TP_0676", "TP_0575"]
REPLACED_OUT = ["TP_0058", "TP_0828", "TP_0802", "TP_0675", "TP_0916"]

INPUTS = {
    "b5_report": ROOT / "outputs/v12_systemb_target_freeze/sprint_b5_target_freeze_report.md",
    "b5_target_family": ROOT / "outputs/v12_systemb_target_freeze/systemb_target_family_freeze.csv",
    "b5_reference_rules": ROOT / "outputs/v12_systemb_target_freeze/systemb_modifier_reference_rules.md",
    "b5_schema": ROOT / "outputs/v12_systemb_target_freeze/systemb_target_output_schema.csv",
    "b5_contract": ROOT / "outputs/v12_systemb_target_freeze/systemb_surrogate_label_contract.csv",
    "b5_config": ROOT / "configs/v12/systemb_target_freeze_config.example.yaml",
    "b5_reference_config": ROOT / "configs/v12/systemb_modifier_reference_definition.example.yaml",
    "n24_selected": ROOT / "outputs/v12_systemb_n24_sample_design/n24_selected_cells_b2_2_human_qa_freeze.csv",
    "n24_replacements": ROOT / "outputs/v12_systemb_n24_sample_design/n24_human_qa_replacements.csv",
    "n24_replaced_out": ROOT / "outputs/v12_systemb_n24_sample_design/n24_replaced_out_cells.csv",
    "n24_focus": ROOT / "outputs/v12_solweig_n24_execution/n24_focus_tmrt_summary.csv",
    "n24_delta": ROOT / "outputs/v12_solweig_n24_execution/n24_base_vs_overhead_delta.csv",
    "b3_report": ROOT / "outputs/v12_solweig_n24_execution/sprint_b3_n24_solweig_execution_report.md",
    "b4_report": ROOT / "outputs/v12_systemb_n24_target_robustness/sprint_b4_n24_target_robustness_report.md",
}

CANDIDATE_SOURCES = [
    ROOT / "data/grid/v12/solweig_typology_cell_candidates.csv",
    ROOT / "data/grid/v10/toa_payoh_grid_v10_features_overhead_sensitivity.csv",
    ROOT / "data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv",
    ROOT / "data/grid/v10/toa_payoh_grid_v10_umep_morphology_with_veg.csv",
    ROOT / "data/grid/v10/toa_payoh_grid_v10_basic_morphology.csv",
]

CANONICAL_ALIASES = {
    "centroid_x": ["centroid_x", "centroid_x_svy21", "x", "lon", "longitude"],
    "centroid_y": ["centroid_y", "centroid_y_svy21", "y", "lat", "latitude"],
    "lon": ["lon", "longitude"],
    "lat": ["lat", "latitude"],
    "svf": [
        "svf",
        "morph_svf",
        "svf_umep_selected",
        "svf_umep_mean_open_v10",
        "svf_umep_mean_open_with_veg",
    ],
    "shade_fraction_base_v10": [
        "shade_fraction_base_v10",
        "shade_fraction_umep_10_16_open_v10",
        "shade_fraction_umep_10_16_open_with_veg",
        "shade_fraction",
    ],
    "shade_fraction_overhead_sens": ["shade_fraction_overhead_sens"],
    "building_density": ["v10_building_density", "building_density", "building_pixel_fraction_v10"],
    "mean_building_height": [
        "v10_building_height_mean_m",
        "dsm_building_height_mean_m_v10",
        "mean_building_height_m",
    ],
    "building_height_p90": [
        "v10_building_height_p90_m",
        "dsm_building_height_p90_m_v10",
        "dsm_building_height_max_m_v10",
        "max_building_height_m",
    ],
    "open_pixel_fraction": ["v10_open_pixel_fraction", "open_pixel_fraction_v10", "open_pixel_fraction"],
    "road_fraction": ["road_fraction"],
    "tree_canopy_fraction": ["tree_canopy_fraction", "dynamic_world_tree_fraction"],
    "gvi_percent": ["gvi_percent"],
    "ndvi_mean": ["ndvi_mean"],
    "grass_fraction": ["grass_fraction", "dynamic_world_grass_fraction"],
    "water_fraction": ["water_fraction", "dynamic_world_water_fraction"],
    "built_up_fraction": ["built_up_fraction", "dynamic_world_built_up_fraction"],
    "impervious_fraction": ["impervious_fraction"],
    "overhead_fraction_total": ["overhead_fraction_total"],
    "overhead_fraction_elevated_road": ["overhead_fraction_elevated_road"],
    "overhead_fraction_elevated_rail": ["overhead_fraction_elevated_rail"],
    "overhead_area_pedestrian_bridge_m2": ["overhead_area_pedestrian_bridge_m2"],
    "overhead_area_covered_walkway_m2": ["overhead_area_covered_walkway_m2"],
    "n_overhead_features": ["n_overhead_features"],
    "pedestrian_shelter_fraction": ["pedestrian_shelter_fraction"],
    "transport_deck_fraction": ["transport_deck_fraction"],
    "distance_to_water": ["distance_to_water", "water_distance_m"],
    "distance_to_park": ["distance_to_park", "park_distance_m", "large_park_distance_m"],
    "distance_to_road": ["distance_to_road"],
}

SAMPLING_FEATURES = [
    "svf_or_open_sky",
    "shade_fraction",
    "building_density",
    "building_height_or_canyon_proxy",
    "road_or_hardscape_fraction",
    "tree_or_gvi_fraction",
    "grass_fraction",
    "water_edge_or_water_fraction",
    "overhead_fraction",
    "impervious_or_built_fraction",
    "centroid_x_normalized",
    "centroid_y_normalized",
]

BROAD_STRATA = [
    "open_hardscape_high_svf",
    "shaded_canopy_low_svf",
    "street_canyon_or_wall_adjacent",
    "overhead_or_transport_structure",
    "covered_walkway_or_pedestrian_overhead",
    "water_edge_or_blue_green_mixed",
    "grass_or_open_park",
    "road_edge_or_high_road_fraction",
    "dense_built_or_low_open_pixel",
    "mixed_upper_tail_probe_proxy",
    "max_extreme_probe_proxy",
]


@dataclass
class SelectionContext:
    selected: list[str]
    reasons: dict[str, dict[str, str]]
    trace_rows: list[dict[str, Any]]
    method: str


def rel(path: Path) -> str:
    """Return a repository-relative path with POSIX separators."""
    return path.relative_to(ROOT).as_posix()


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def status_pass(path: Path) -> bool:
    text = read_text(path).lower()
    return "## status" in text and "pass" in text


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"cell_id": "string"})


def first_existing(row: pd.Series, aliases: list[str]) -> Any:
    for col in aliases:
        if col in row.index and pd.notna(row[col]):
            return row[col]
    return np.nan


def coalesce_columns(df: pd.DataFrame, output_col: str, aliases: list[str]) -> None:
    values = pd.Series(np.nan, index=df.index, dtype="object")
    for col in aliases:
        if col in df.columns:
            values = values.where(values.notna(), df[col])
    df[output_col] = values


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def quantile_score(series: pd.Series) -> pd.Series:
    vals = numeric(series)
    out = pd.Series(np.nan, index=series.index, dtype=float)
    ok = vals.notna()
    if ok.sum() <= 1:
        out.loc[ok] = 0.5
        return out
    ranks = vals.loc[ok].rank(method="average")
    out.loc[ok] = (ranks - 1.0) / (ok.sum() - 1.0)
    return out


def safe_norm(series: pd.Series) -> pd.Series:
    vals = numeric(series)
    lo = vals.quantile(0.05)
    hi = vals.quantile(0.95)
    if pd.isna(lo) or pd.isna(hi) or math.isclose(float(lo), float(hi)):
        return quantile_score(vals).fillna(0.5)
    return ((vals - lo) / (hi - lo)).clip(0, 1)


def stable_bucket(cell_id: str, modulo: int) -> int:
    digest = hashlib.md5(cell_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def write_validation(rows: list[dict[str, Any]], blocked: bool) -> None:
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "b6_input_validation.csv", index=False)
    status = "BLOCKED" if blocked else "PASS"
    failed = df.loc[df["status"].eq("FAIL")]
    lines = [
        "# Sprint B6 input validation",
        "",
        f"Status: **{status}**",
        "",
        f"Checks: {len(df)}",
        f"Failures: {len(failed)}",
        "",
    ]
    if not failed.empty:
        lines.extend(["## Failures", ""])
        for row in failed.to_dict("records"):
            lines.append(f"- {row['check']}: {row['detail']}")
        lines.append("")
    lines.extend(
        [
            "## Scope guards",
            "",
            "- No QGIS execution.",
            "- No SOLWEIG execution.",
            "- No raw raster reads.",
            "- No local WBGT, hazard_score, risk_score, surrogate training, or System A/B coupling.",
        ]
    )
    (OUT_DIR / "b6_input_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_inputs() -> tuple[bool, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        rows.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    for name, path in INPUTS.items():
        check(f"{name}_exists", path.exists(), rel(path) if path.exists() else f"Missing {rel(path)}")

    b5_report = INPUTS["b5_report"]
    check("b5_report_status_pass", status_pass(b5_report), "B5 report has Status PASS")

    target_family = read_csv(INPUTS["b5_target_family"]) if INPUTS["b5_target_family"].exists() else pd.DataFrame()
    target_fields = set(target_family.get("target_field", pd.Series(dtype=str)).astype(str))
    for field in ["tmrt_p90_c", "delta_tmrt_p90_c", "m_rad_pct01"]:
        check(f"b5_target_family_has_{field}", field in target_fields, f"{field} in target freeze")

    reference_text = read_text(INPUTS["b5_reference_rules"])
    check(
        "b5_reference_rules_include_m_rad_pct01",
        "m_rad_pct01" in reference_text
        and "rank_average" in reference_text
        and "n_reference_cells - 1" in reference_text,
        "Reference rule includes m_rad_pct01 percentile-rank method",
    )

    n24 = read_csv(INPUTS["n24_selected"]) if INPUTS["n24_selected"].exists() else pd.DataFrame()
    n24_cells = set(n24.get("cell_id", pd.Series(dtype=str)).astype(str))
    check("n24_selected_unique_count_24", len(n24_cells) == N24_N, f"Unique N24 cells = {len(n24_cells)}")

    focus = read_csv(INPUTS["n24_focus"]) if INPUTS["n24_focus"].exists() else pd.DataFrame()
    check("n24_focus_rows_240", len(focus) == 240, f"N24 focus rows = {len(focus)}")

    check("b3_report_status_pass", status_pass(INPUTS["b3_report"]), "B3 report has Status PASS")
    check("b4_report_status_pass", status_pass(INPUTS["b4_report"]), "B4 report has Status PASS")

    missing_in = sorted(set(REPLACEMENT_IN) - n24_cells)
    present_out = sorted(set(REPLACED_OUT) & n24_cells)
    check("replacement_in_cells_in_n24", not missing_in, f"Missing replacement-in cells: {missing_in}")
    check("replaced_out_cells_absent_from_n24", not present_out, f"Replaced-out cells present: {present_out}")

    full_sources = []
    for path in CANDIDATE_SOURCES:
        if path.exists():
            try:
                header = pd.read_csv(path, nrows=0)
                if "cell_id" in header.columns:
                    full_sources.append(path)
            except Exception:
                pass
    check(
        "candidate_grid_table_with_cell_id_exists",
        bool(full_sources),
        "Candidate sources: " + "; ".join(rel(p) for p in full_sources),
    )

    universe, exclusions, _source_map = build_candidate_universe(n24, focus, write_outputs=False)
    eligible_count = int(universe["eligible"].sum()) if "eligible" in universe.columns else 0
    check("eligible_candidate_universe_at_least_150", eligible_count >= TOTAL_N, f"Eligible cells = {eligible_count}")

    blocked = any(row["status"] == "FAIL" for row in rows)
    write_validation(rows, blocked)
    return blocked, n24, focus, exclusions


def build_candidate_universe(
    n24: pd.DataFrame, focus: pd.DataFrame, write_outputs: bool = True
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frames: list[tuple[Path, pd.DataFrame]] = []
    for path in CANDIDATE_SOURCES:
        if not path.exists():
            continue
        df = pd.read_csv(path, dtype={"cell_id": "string"})
        if "cell_id" not in df.columns:
            continue
        df = df.dropna(subset=["cell_id"]).drop_duplicates("cell_id")
        frames.append((path, df))

    if not frames:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    master = pd.DataFrame({"cell_id": sorted(set().union(*[set(df["cell_id"].astype(str)) for _, df in frames]))})
    master["cell_id"] = master["cell_id"].astype(str)
    master = master.set_index("cell_id")
    source_files = {cell_id: [] for cell_id in master.index}
    source_rows: list[dict[str, Any]] = []

    for path, df in frames:
        df = df.copy()
        df["cell_id"] = df["cell_id"].astype(str)
        df = df.set_index("cell_id")
        for cell_id in df.index:
            source_files.setdefault(cell_id, []).append(rel(path))
        for col in df.columns:
            if col not in master.columns:
                master[col] = df[col]
                source_rows.append({"field": col, "source_file": rel(path), "source_role": "initial"})
            else:
                before_missing = master[col].isna()
                master[col] = master[col].where(master[col].notna(), df[col])
                if before_missing.any() and master[col].notna().any():
                    source_rows.append({"field": col, "source_file": rel(path), "source_role": "fill_missing"})

    universe = master.reset_index()
    universe["candidate_source_files"] = universe["cell_id"].map(lambda c: "|".join(source_files.get(c, [])))

    for out_col, aliases in CANONICAL_ALIASES.items():
        coalesce_columns(universe, out_col, aliases)

    n24_cells = set(n24.get("cell_id", pd.Series(dtype=str)).astype(str))
    completed_cells = set(focus.get("cell_id", pd.Series(dtype=str)).astype(str))
    replaced_out_df = read_csv(INPUTS["n24_replaced_out"]) if INPUTS["n24_replaced_out"].exists() else pd.DataFrame()
    replaced_notes = {
        str(row["cell_id"]): str(row.get("human_qa_note", "B2.2 replaced out"))
        for row in replaced_out_df.to_dict("records")
        if "cell_id" in row
    }

    n24_meta_cols = [
        "cell_id",
        "primary_role",
        "secondary_roles",
        "typology_label",
        "selection_tier",
        "evidence_summary",
    ]
    n24_meta = n24[[c for c in n24_meta_cols if c in n24.columns]].copy()
    if not n24_meta.empty:
        universe = universe.merge(n24_meta, on="cell_id", how="left", suffixes=("", "_n24"))
        if "typology_label_n24" in universe.columns:
            universe["typology_label"] = universe.get("typology_label", pd.Series(np.nan, index=universe.index))
            universe["typology_label"] = universe["typology_label"].where(
                universe["typology_label"].notna(), universe["typology_label_n24"]
            )

    universe["geometry_available"] = (
        numeric(universe.get("centroid_x", pd.Series(index=universe.index))).notna()
        & numeric(universe.get("centroid_y", pd.Series(index=universe.index))).notna()
    ) | (
        numeric(universe.get("lon", pd.Series(index=universe.index))).notna()
        & numeric(universe.get("lat", pd.Series(index=universe.index))).notna()
    )
    universe["in_n24_completed"] = universe["cell_id"].isin(n24_cells)
    universe["in_b2_2_replaced_out"] = universe["cell_id"].isin(REPLACED_OUT)
    universe["human_qa_exclusion_reason"] = universe["cell_id"].map(replaced_notes).fillna("")
    universe["existing_solweig_n24_label_available"] = universe["cell_id"].isin(completed_cells)

    if "typology_label" not in universe.columns:
        universe["typology_label"] = ""
    universe["typology_label"] = universe["typology_label"].fillna(universe.get("land_use_hint", "")).fillna("")

    output_cols = [
        "cell_id",
        "centroid_x",
        "centroid_y",
        "lon",
        "lat",
        "geometry_available",
        "in_n24_completed",
        "in_b2_2_replaced_out",
        "human_qa_exclusion_reason",
        "existing_solweig_n24_label_available",
        "typology_label",
        "candidate_source_files",
        "svf",
        "shade_fraction_base_v10",
        "shade_fraction_overhead_sens",
        "building_density",
        "mean_building_height",
        "building_height_p90",
        "open_pixel_fraction",
        "road_fraction",
        "tree_canopy_fraction",
        "gvi_percent",
        "ndvi_mean",
        "grass_fraction",
        "water_fraction",
        "built_up_fraction",
        "impervious_fraction",
        "overhead_fraction_total",
        "overhead_fraction_elevated_road",
        "overhead_fraction_elevated_rail",
        "overhead_area_pedestrian_bridge_m2",
        "overhead_area_covered_walkway_m2",
        "n_overhead_features",
        "pedestrian_shelter_fraction",
        "transport_deck_fraction",
        "distance_to_water",
        "distance_to_park",
        "distance_to_road",
        "primary_role",
        "secondary_roles",
        "selection_tier",
        "evidence_summary",
        "overhead_confounding_flag",
        "overhead_interpretation",
    ]
    for col in output_cols:
        if col not in universe.columns:
            universe[col] = np.nan

    universe = universe[output_cols + [c for c in universe.columns if c not in output_cols]]

    feature_cols = [
        "svf",
        "shade_fraction_base_v10",
        "building_density",
        "building_height_p90",
        "road_fraction",
        "tree_canopy_fraction",
        "gvi_percent",
        "grass_fraction",
        "water_fraction",
        "overhead_fraction_total",
        "impervious_fraction",
        "built_up_fraction",
    ]
    present_feature_count = pd.DataFrame({c: numeric(universe[c]).notna() for c in feature_cols}).sum(axis=1)
    universe["source_feature_completeness"] = present_feature_count / len(feature_cols)

    water = numeric(universe["water_fraction"]).fillna(0)
    built = numeric(universe["built_up_fraction"]).fillna(0)
    road = numeric(universe["road_fraction"]).fillna(0)
    grass = numeric(universe["grass_fraction"]).fillna(0)
    tree = numeric(universe["tree_canopy_fraction"]).fillna(0)
    shade = numeric(universe["shade_fraction_base_v10"]).fillna(0)
    overhead = numeric(universe["overhead_fraction_total"]).fillna(0)
    pure_water = (water >= 0.80) & (built <= 0.05) & (road <= 0.05) & (grass <= 0.05) & (tree <= 0.05) & (shade <= 0.10) & (overhead <= 0.02)

    reasons: list[list[str]] = [[] for _ in range(len(universe))]
    for idx, flag in enumerate(universe["cell_id"].isin(REPLACED_OUT)):
        if flag:
            reasons[idx].append("b2_2_replaced_out_hard_exclusion")
    for idx, flag in enumerate(pure_water):
        if flag:
            reasons[idx].append("pure_water_high_confidence")
    for idx, flag in enumerate(~universe["geometry_available"]):
        if flag:
            reasons[idx].append("invalid_or_missing_geometry_for_future_tile")
    for idx, count in enumerate(present_feature_count):
        if count < 8:
            reasons[idx].append("missing_core_sampling_features")

    universe["exclusion_reason"] = ["|".join(r) for r in reasons]
    universe["eligible"] = universe["exclusion_reason"].eq("")

    exclusions = universe.loc[~universe["eligible"], [
        "cell_id",
        "in_n24_completed",
        "in_b2_2_replaced_out",
        "human_qa_exclusion_reason",
        "exclusion_reason",
        "water_fraction",
        "source_feature_completeness",
        "candidate_source_files",
    ]].copy()

    source_map = pd.DataFrame(source_rows).drop_duplicates()
    source_map = pd.concat(
        [
            source_map,
            pd.DataFrame(
                [
                    {"field": field, "source_file": ";".join(rel(p) for p, df in frames if any(a in df.columns for a in aliases)), "source_role": "canonical_alias"}
                    for field, aliases in CANONICAL_ALIASES.items()
                ]
            ),
        ],
        ignore_index=True,
    )

    if write_outputs:
        universe.to_csv(OUT_DIR / "n150_candidate_universe.csv", index=False)
        exclusions.to_csv(OUT_DIR / "n150_candidate_universe_exclusions.csv", index=False)
        source_map.to_csv(OUT_DIR / "n150_feature_source_map.csv", index=False)
    return universe, exclusions, source_map


def build_sampling_feature_matrix(universe: pd.DataFrame) -> pd.DataFrame:
    fm = universe.loc[universe["eligible"]].copy()
    fm["svf_or_open_sky"] = numeric(fm["svf"]).where(numeric(fm["svf"]).notna(), numeric(fm["open_pixel_fraction"]))
    fm["shade_fraction"] = numeric(fm["shade_fraction_base_v10"])
    fm["building_density"] = numeric(fm["building_density"])
    height = numeric(fm["building_height_p90"]).where(
        numeric(fm["building_height_p90"]).notna(), numeric(fm["mean_building_height"])
    )
    fm["building_height_or_canyon_proxy"] = height
    fm["road_or_hardscape_fraction"] = numeric(fm["road_fraction"]).where(
        numeric(fm["road_fraction"]).notna(), numeric(fm["impervious_fraction"])
    )
    gvi = numeric(fm["gvi_percent"])
    gvi_unit = np.where(gvi > 1.0, gvi / 100.0, gvi)
    tree = numeric(fm["tree_canopy_fraction"]).where(numeric(fm["tree_canopy_fraction"]).notna(), pd.Series(gvi_unit, index=fm.index))
    fm["tree_or_gvi_fraction"] = tree.where(tree.notna(), numeric(fm["ndvi_mean"]))
    fm["grass_fraction"] = numeric(fm["grass_fraction"])
    water = numeric(fm["water_fraction"])
    if water.notna().sum() == 0 and "distance_to_water" in fm.columns:
        water = 1.0 - safe_norm(fm["distance_to_water"])
    fm["water_edge_or_water_fraction"] = water
    fm["overhead_fraction"] = numeric(fm["overhead_fraction_total"])
    fm["impervious_or_built_fraction"] = numeric(fm["impervious_fraction"]).where(
        numeric(fm["impervious_fraction"]).notna(), numeric(fm["built_up_fraction"])
    )
    fm["centroid_x_normalized"] = safe_norm(fm["centroid_x"])
    fm["centroid_y_normalized"] = safe_norm(fm["centroid_y"])

    schema_rows = []
    missing_rows = []
    scaled_cols = []
    for feature in SAMPLING_FEATURES:
        missing = fm[feature].isna()
        missing_rows.append(
            {
                "feature": feature,
                "missing_count": int(missing.sum()),
                "missing_fraction": float(missing.mean()),
                "available_count": int((~missing).sum()),
            }
        )
        fm[f"{feature}_missing"] = missing
        median = numeric(fm[feature]).median()
        if pd.isna(median):
            median = 0.0
        fm[f"{feature}_imputed"] = numeric(fm[feature]).fillna(median)
        scaled = quantile_score(fm[f"{feature}_imputed"]).fillna(0.5)
        fm[f"{feature}_q01"] = scaled
        scaled_cols.append(f"{feature}_q01")
        schema_rows.append(
            {
                "sampling_feature": feature,
                "scaled_feature": f"{feature}_q01",
                "missing_indicator": f"{feature}_missing",
                "scaling": "within-eligible percentile rank q01 after median imputation",
                "uses_target_label": False,
            }
        )

    fm["sampling_feature_completeness"] = 1.0 - fm[[f"{f}_missing" for f in SAMPLING_FEATURES]].mean(axis=1)
    keep = [
        "cell_id",
        "in_n24_completed",
        "typology_label",
        "primary_role",
        "secondary_roles",
        "source_feature_completeness",
        "sampling_feature_completeness",
        "centroid_x",
        "centroid_y",
    ] + SAMPLING_FEATURES + [f"{f}_missing" for f in SAMPLING_FEATURES] + [f"{f}_q01" for f in SAMPLING_FEATURES]
    for col in keep:
        if col not in fm.columns:
            fm[col] = np.nan
    out = fm[keep].copy()
    out.to_csv(OUT_DIR / "n150_sampling_feature_matrix.csv", index=False)
    pd.DataFrame(schema_rows).to_csv(OUT_DIR / "n150_sampling_feature_schema.csv", index=False)
    pd.DataFrame(missing_rows).to_csv(OUT_DIR / "n150_sampling_feature_missingness.csv", index=False)
    return out


def label_strata(fm: pd.DataFrame) -> pd.DataFrame:
    df = fm.copy()
    q = {
        f: {
            "lo": numeric(df[f]).quantile(0.20),
            "hi": numeric(df[f]).quantile(0.80),
            "top": numeric(df[f]).quantile(0.95),
            "bottom": numeric(df[f]).quantile(0.05),
        }
        for f in SAMPLING_FEATURES
    }

    def labels(row: pd.Series) -> list[str]:
        out: list[str] = []
        svf = row.get("svf_or_open_sky", np.nan)
        shade = row.get("shade_fraction", np.nan)
        bldg = row.get("building_density", np.nan)
        height = row.get("building_height_or_canyon_proxy", np.nan)
        road = row.get("road_or_hardscape_fraction", np.nan)
        tree = row.get("tree_or_gvi_fraction", np.nan)
        grass = row.get("grass_fraction", np.nan)
        water = row.get("water_edge_or_water_fraction", np.nan)
        overhead = row.get("overhead_fraction", np.nan)
        imp = row.get("impervious_or_built_fraction", np.nan)

        if pd.notna(svf) and pd.notna(shade) and svf >= q["svf_or_open_sky"]["hi"] and shade <= q["shade_fraction"]["lo"]:
            out.append("open_hardscape_high_svf")
        if (
            (pd.notna(shade) and shade >= q["shade_fraction"]["hi"])
            or (pd.notna(tree) and tree >= q["tree_or_gvi_fraction"]["hi"])
        ) and pd.notna(svf) and svf <= q["svf_or_open_sky"]["hi"]:
            out.append("shaded_canopy_low_svf")
        if (
            (pd.notna(bldg) and bldg >= q["building_density"]["hi"])
            or (pd.notna(height) and height >= q["building_height_or_canyon_proxy"]["hi"])
        ) and (pd.isna(svf) or svf <= q["svf_or_open_sky"]["hi"]):
            out.append("street_canyon_or_wall_adjacent")
        if pd.notna(overhead) and overhead >= max(0.03, q["overhead_fraction"]["hi"]):
            out.append("overhead_or_transport_structure")
        if (
            str(row.get("secondary_roles", "")).find("covered_walkway") >= 0
            or (pd.notna(overhead) and overhead >= max(0.02, q["overhead_fraction"]["hi"]))
        ):
            out.append("covered_walkway_or_pedestrian_overhead")
        if pd.notna(water) and water >= max(0.03, q["water_edge_or_water_fraction"]["hi"]):
            out.append("water_edge_or_blue_green_mixed")
        if pd.notna(grass) and grass >= max(0.05, q["grass_fraction"]["hi"]):
            out.append("grass_or_open_park")
        if pd.notna(road) and road >= q["road_or_hardscape_fraction"]["hi"]:
            out.append("road_edge_or_high_road_fraction")
        if (
            (pd.notna(bldg) and bldg >= q["building_density"]["hi"])
            or (pd.notna(imp) and imp >= q["impervious_or_built_fraction"]["hi"])
        ) and (pd.isna(svf) or svf <= q["svf_or_open_sky"]["hi"]):
            out.append("dense_built_or_low_open_pixel")
        hetero = sum(
            [
                pd.notna(svf) and q["svf_or_open_sky"]["lo"] < svf < q["svf_or_open_sky"]["hi"],
                pd.notna(shade) and q["shade_fraction"]["lo"] < shade < q["shade_fraction"]["hi"],
                pd.notna(bldg) and bldg > q["building_density"]["lo"],
                pd.notna(tree) and tree > q["tree_or_gvi_fraction"]["lo"],
                pd.notna(road) and road > q["road_or_hardscape_fraction"]["lo"],
            ]
        )
        if hetero >= 4:
            out.append("mixed_upper_tail_probe_proxy")
        if (
            pd.notna(svf)
            and svf >= q["svf_or_open_sky"]["hi"]
            and pd.notna(road)
            and road >= q["road_or_hardscape_fraction"]["hi"]
            and (pd.isna(shade) or shade <= q["shade_fraction"]["lo"])
        ):
            out.append("max_extreme_probe_proxy")
        if not out:
            out.append("background_feature_space_fill")
        return out

    strata = df.apply(labels, axis=1)
    df["secondary_sampling_strata"] = strata.map(lambda xs: "|".join(xs))
    df["primary_sampling_stratum"] = strata.map(lambda xs: xs[0])
    return df


def feature_array(df: pd.DataFrame) -> np.ndarray:
    cols = [f"{f}_q01" for f in SAMPLING_FEATURES]
    return df[cols].apply(pd.to_numeric, errors="coerce").fillna(0.5).to_numpy(float)


def geo_array(df: pd.DataFrame) -> np.ndarray | None:
    if "centroid_x_normalized_q01" in df.columns and "centroid_y_normalized_q01" in df.columns:
        return df[["centroid_x_normalized_q01", "centroid_y_normalized_q01"]].fillna(0.5).to_numpy(float)
    return None


def min_distance_to_selected(candidates: np.ndarray, selected: np.ndarray) -> np.ndarray:
    if len(selected) == 0:
        return np.full(len(candidates), 1.0)
    distances = np.sqrt(((candidates[:, None, :] - selected[None, :, :]) ** 2).sum(axis=2))
    return distances.min(axis=1)


def add_cell(ctx: SelectionContext, cell_id: str, reason: dict[str, str]) -> None:
    if cell_id in ctx.selected or len(ctx.selected) >= TOTAL_N:
        return
    ctx.selected.append(cell_id)
    ctx.reasons[cell_id] = reason
    row = {"selection_rank": len(ctx.selected), "cell_id": cell_id}
    row.update(reason)
    ctx.trace_rows.append(row)


def choose_diverse_candidate(
    df: pd.DataFrame,
    selected_ids: set[str],
    selected_feature_vectors: np.ndarray,
    subset_mask: pd.Series,
) -> str | None:
    pool = df.loc[subset_mask & ~df["cell_id"].isin(selected_ids)].copy()
    if pool.empty:
        return None
    cand = feature_array(pool)
    feat_min = min_distance_to_selected(cand, selected_feature_vectors)
    pool["_score"] = feat_min + 0.15 * numeric(pool["sampling_feature_completeness"]).fillna(0.0)
    pool = pool.sort_values(["_score", "cell_id"], ascending=[False, True])
    return str(pool.iloc[0]["cell_id"])


def selected_vectors(df: pd.DataFrame, selected_ids: Iterable[str]) -> np.ndarray:
    selected_df = df.loc[df["cell_id"].isin(list(selected_ids))]
    return feature_array(selected_df)


def run_sampling(fm: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    df = label_strata(fm)
    n24 = df.loc[df["in_n24_completed"]].sort_values("cell_id")
    if len(n24) != N24_N:
        raise RuntimeError(f"Expected {N24_N} retained N24 cells in eligible feature matrix, found {len(n24)}")

    ctx = SelectionContext(selected=[], reasons={}, trace_rows=[], method="greedy_fallback")
    for _, row in n24.iterrows():
        add_cell(
            ctx,
            str(row["cell_id"]),
            {
                "selection_status": "retained_n24",
                "selection_tier": "n24_seed",
                "existing_solweig_label_status": "completed_n24",
                "quota_reason": "retained_frozen_b2_2_n24",
                "lhs_or_greedy_reason": "",
                "extreme_coverage_reason": "",
                "sampling_feature_coverage_reason": "continuity anchor retained from completed N24 labels",
            },
        )

    quota_target = 8
    for stratum in BROAD_STRATA:
        available = df["secondary_sampling_strata"].str.contains(stratum, regex=False, na=False).sum()
        target = min(quota_target, int(available))
        while len(ctx.selected) < TOTAL_N:
            selected_df = df.loc[df["cell_id"].isin(ctx.selected)]
            current = selected_df["secondary_sampling_strata"].str.contains(stratum, regex=False, na=False).sum()
            if current >= target:
                break
            selected_vecs = selected_vectors(df, ctx.selected)
            chosen = choose_diverse_candidate(
                df,
                set(ctx.selected),
                selected_vecs,
                df["secondary_sampling_strata"].str.contains(stratum, regex=False, na=False),
            )
            if not chosen:
                break
            add_cell(
                ctx,
                chosen,
                {
                    "selection_status": "selected_new",
                    "selection_tier": "added126",
                    "existing_solweig_label_status": "pending_b7_new_run",
                    "quota_reason": f"quota_fill:{stratum}",
                    "lhs_or_greedy_reason": "",
                    "extreme_coverage_reason": "",
                    "sampling_feature_coverage_reason": "broad diagnostic stratum coverage",
                },
            )

    extreme_rules = {
        "top5_high_svf_low_shade": (df["svf_or_open_sky_q01"] >= 0.95) & (df["shade_fraction_q01"] <= 0.20),
        "bottom5_low_svf_high_shade": (df["svf_or_open_sky_q01"] <= 0.05) & (df["shade_fraction_q01"] >= 0.80),
        "high_overhead_fraction": df["overhead_fraction_q01"] >= 0.95,
        "high_water_edge_blue_green": df["water_edge_or_water_fraction_q01"] >= 0.95,
        "high_road_hardscape": df["road_or_hardscape_fraction_q01"] >= 0.95,
        "high_tree_gvi": df["tree_or_gvi_fraction_q01"] >= 0.95,
        "dense_built_high_density": df["building_density_q01"] >= 0.95,
    }
    for name, mask in extreme_rules.items():
        available = int(mask.sum())
        target = min(5, available)
        while len(ctx.selected) < TOTAL_N:
            current = df.loc[df["cell_id"].isin(ctx.selected) & mask].shape[0]
            if current >= target:
                break
            chosen = choose_diverse_candidate(df, set(ctx.selected), selected_vectors(df, ctx.selected), mask)
            if not chosen:
                break
            add_cell(
                ctx,
                chosen,
                {
                    "selection_status": "selected_new",
                    "selection_tier": "added126",
                    "existing_solweig_label_status": "pending_b7_new_run",
                    "quota_reason": "",
                    "lhs_or_greedy_reason": "",
                    "extreme_coverage_reason": name,
                    "sampling_feature_coverage_reason": "forced feature-space edge coverage",
                },
            )

    remaining = TOTAL_N - len(ctx.selected)
    try:
        from scipy.stats import qmc  # type: ignore

        ctx.method = "qmc_lhs"
        sampler = qmc.LatinHypercube(d=len(SAMPLING_FEATURES), seed=RANDOM_SEED)
        desired = sampler.random(n=max(remaining, 1))
        for point in desired:
            if len(ctx.selected) >= TOTAL_N:
                break
            pool = df.loc[~df["cell_id"].isin(ctx.selected)].copy()
            cand = feature_array(pool)
            selected_vecs = selected_vectors(df, ctx.selected)
            target_dist = np.sqrt(((cand - point[None, :]) ** 2).sum(axis=1))
            diversity = min_distance_to_selected(cand, selected_vecs)
            score = target_dist - 0.25 * diversity - 0.05 * numeric(pool["sampling_feature_completeness"]).fillna(0).to_numpy()
            pool["_score"] = score
            chosen = str(pool.sort_values(["_score", "cell_id"], ascending=[True, True]).iloc[0]["cell_id"])
            add_cell(
                ctx,
                chosen,
                {
                    "selection_status": "selected_new",
                    "selection_tier": "added126",
                    "existing_solweig_label_status": "pending_b7_new_run",
                    "quota_reason": "",
                    "lhs_or_greedy_reason": "qmc_lhs_nearest_with_diversity_penalty",
                    "extreme_coverage_reason": "",
                    "sampling_feature_coverage_reason": "Latin Hypercube feature-space coverage",
                },
            )
    except Exception:
        ctx.method = "greedy_fallback"
        while len(ctx.selected) < TOTAL_N:
            chosen = choose_diverse_candidate(
                df,
                set(ctx.selected),
                selected_vectors(df, ctx.selected),
                pd.Series(True, index=df.index),
            )
            if not chosen:
                break
            add_cell(
                ctx,
                chosen,
                {
                    "selection_status": "selected_new",
                    "selection_tier": "added126",
                    "existing_solweig_label_status": "pending_b7_new_run",
                    "quota_reason": "",
                    "lhs_or_greedy_reason": "greedy_maximin_feature_space",
                    "extreme_coverage_reason": "",
                    "sampling_feature_coverage_reason": "greedy maximin feature-space coverage",
                },
            )

    if len(ctx.selected) != TOTAL_N:
        raise RuntimeError(f"Sampling produced {len(ctx.selected)} cells, expected {TOTAL_N}")

    selected = df.loc[df["cell_id"].isin(ctx.selected)].copy()
    rank_map = {cell_id: idx + 1 for idx, cell_id in enumerate(ctx.selected)}
    selected["selection_rank"] = selected["cell_id"].map(rank_map)
    for col in [
        "selection_status",
        "selection_tier",
        "existing_solweig_label_status",
        "quota_reason",
        "lhs_or_greedy_reason",
        "extreme_coverage_reason",
        "sampling_feature_coverage_reason",
    ]:
        selected[col] = selected["cell_id"].map(lambda c: ctx.reasons[str(c)].get(col, ""))
    quota_mask = selected["quota_reason"].astype(str).str.startswith("quota_fill:")
    selected.loc[quota_mask, "primary_sampling_stratum"] = selected.loc[quota_mask, "quota_reason"].str.replace(
        "quota_fill:", "", regex=False
    )
    selected["replacement_of_cell_id"] = ""
    selected["auto_qa_flag"] = ""
    selected["manual_review_required"] = False
    selected["manual_review_reason"] = ""
    selected["notes"] = np.where(
        selected["selection_status"].eq("retained_n24"),
        "Completed N24 label retained as seed / continuity label.",
        "New B7 SOLWEIG run needed; selected by automated B6 feature-space design.",
    )
    selected = selected.sort_values("selection_rank")

    new_cells = selected.loc[selected["selection_status"].eq("selected_new")].copy()
    retained = selected.loc[selected["selection_status"].eq("retained_n24")].copy()

    alternates = []
    temp_selected = list(ctx.selected)
    for alt_rank in range(1, ALTERNATE_N + 1):
        chosen = choose_diverse_candidate(
            df,
            set(temp_selected),
            selected_vectors(df, temp_selected),
            pd.Series(True, index=df.index),
        )
        if not chosen:
            break
        temp_selected.append(chosen)
        alt_row = df.loc[df["cell_id"].eq(chosen)].iloc[0].to_dict()
        selected_vecs = selected_vectors(df, ctx.selected)
        cand_vec = feature_array(pd.DataFrame([alt_row]))
        selected_df = df.loc[df["cell_id"].isin(ctx.selected)].copy()
        dists = np.sqrt(((feature_array(selected_df) - cand_vec[0][None, :]) ** 2).sum(axis=1))
        replace = str(selected_df.iloc[int(np.argmin(dists))]["cell_id"])
        alt_row.update(
            {
                "alternate_rank": alt_rank,
                "selection_status": "alternate",
                "selection_tier": "alternate",
                "existing_solweig_label_status": "pending_if_promoted",
                "replacement_of_cell_id": replace,
                "alternate_reason": "nearest feature-space replacement candidate with maximin diversity",
                "manual_review_required": False,
            }
        )
        alternates.append(alt_row)
    alternates_df = pd.DataFrame(alternates)
    trace = pd.DataFrame(ctx.trace_rows)

    selected_cols = [
        "selection_rank",
        "cell_id",
        "selection_status",
        "selection_tier",
        "existing_solweig_label_status",
        "primary_sampling_stratum",
        "secondary_sampling_strata",
        "typology_label",
        "sampling_feature_coverage_reason",
        "quota_reason",
        "lhs_or_greedy_reason",
        "extreme_coverage_reason",
        "replacement_of_cell_id",
        "source_feature_completeness",
        "auto_qa_flag",
        "manual_review_required",
        "manual_review_reason",
        "notes",
    ]
    selected[selected_cols].to_csv(OUT_DIR / "n150_selected_cells.csv", index=False)
    new_cells[selected_cols].to_csv(OUT_DIR / "n150_new_cells.csv", index=False)
    retained[selected_cols].to_csv(OUT_DIR / "n150_retained_n24_cells.csv", index=False)
    alternates_df.to_csv(OUT_DIR / "n150_alternate_cells.csv", index=False)
    trace.to_csv(OUT_DIR / "n150_sampling_algorithm_trace.csv", index=False)
    return selected, new_cells, retained, alternates_df, ctx.method


def compute_auto_qa(selected: pd.DataFrame, alternates: pd.DataFrame, exclusions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    qa_base = pd.concat(
        [
            selected.assign(selection_group="selected_n150"),
            alternates.assign(selection_group="alternate"),
        ],
        ignore_index=True,
        sort=False,
    )
    flags = []
    rounded_features = qa_base[[f"{f}_q01" for f in SAMPLING_FEATURES]].round(3).astype(str).agg("|".join, axis=1)
    duplicates = rounded_features.duplicated(keep=False)

    x = numeric(qa_base.get("centroid_x", pd.Series(index=qa_base.index)))
    y = numeric(qa_base.get("centroid_y", pd.Series(index=qa_base.index)))
    geo_available = x.notna() & y.notna()
    nn = pd.Series(np.nan, index=qa_base.index)
    if geo_available.sum() > 1:
        coords = np.column_stack([safe_norm(x).fillna(0.5), safe_norm(y).fillna(0.5)])
        distances = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(axis=2))
        np.fill_diagonal(distances, np.nan)
        nn = pd.Series(np.nanmin(distances, axis=1), index=qa_base.index)
    nn_hi = nn.quantile(0.95)

    for idx, row in qa_base.iterrows():
        cell_flags: list[str] = []
        if numeric(pd.Series([row.get("water_edge_or_water_fraction")])).iloc[0] >= 0.65:
            cell_flags.append("pure_water_risk")
        if not bool(row.get("geometry_available", True)) and row.get("selection_group") == "selected_n150":
            cell_flags.append("invalid_geometry")
        if float(row.get("sampling_feature_completeness", 1.0) or 0.0) < 0.75:
            cell_flags.append("missing_core_features")
        extreme_count = 0
        for feat in SAMPLING_FEATURES:
            val = row.get(f"{feat}_q01")
            if pd.notna(val) and (float(val) <= 0.01 or float(val) >= 0.99):
                extreme_count += 1
        if extreme_count >= 3:
            cell_flags.append("extreme_outlier_feature")
        if bool(duplicates.iloc[idx]):
            cell_flags.append("duplicate_feature_vector")
        if pd.notna(nn.iloc[idx]) and pd.notna(nn_hi) and nn.iloc[idx] >= nn_hi:
            cell_flags.append("geographically_isolated_edge_cell")
        overhead_flag = str(row.get("overhead_confounding_flag", "")).lower()
        overhead_interp = str(row.get("overhead_interpretation", "")).lower()
        if "moderate" in overhead_flag or "transport" in overhead_interp:
            cell_flags.append("overhead_semantics_ambiguous")
        if float(row.get("source_feature_completeness", 1.0) or 0.0) < 0.80:
            cell_flags.append("low_feature_confidence")
        for flag in cell_flags:
            flags.append(
                {
                    "cell_id": row["cell_id"],
                    "selection_group": row.get("selection_group", ""),
                    "flag": flag,
                    "risk_score_component": 1,
                    "manual_review_required": False,
                    "notes": "Automated B6 flag; advisory spot-check only unless invalid geometry is present.",
                }
            )

    for cell_id in REPLACED_OUT:
        flags.append(
            {
                "cell_id": cell_id,
                "selection_group": "excluded",
                "flag": "replaced_out_cell_excluded",
                "risk_score_component": 1,
                "manual_review_required": False,
                "notes": "B2.2 hard exclusion retained.",
            }
        )

    qa = pd.DataFrame(flags)
    if qa.empty:
        qa = pd.DataFrame(columns=["cell_id", "selection_group", "flag", "risk_score_component", "manual_review_required", "notes"])
    qa.to_csv(OUT_DIR / "n150_auto_qa_flags.csv", index=False)

    risk = qa.loc[qa["selection_group"].eq("selected_n150")].groupby("cell_id").size().reset_index(name="auto_qa_flag_count")
    spot = selected.merge(risk, on="cell_id", how="left").fillna({"auto_qa_flag_count": 0})
    spot = spot.sort_values(["auto_qa_flag_count", "selection_rank"], ascending=[False, True]).head(15).copy()
    spot["spot_check_reason"] = np.where(
        spot["auto_qa_flag_count"] > 0,
        "highest automated QA risk among selected cells",
        "coverage-sensitive advisory spot-check candidate",
    )
    spot[["cell_id", "selection_rank", "primary_sampling_stratum", "auto_qa_flag_count", "spot_check_reason"]].to_csv(
        OUT_DIR / "n150_spot_check_suggestions.csv", index=False
    )

    manual_md = [
        "# N150 manual review budget",
        "",
        "No full manual QA is required for all 150 cells.",
        "",
        "Recommended optional spot-check budget: 10-15 cells maximum.",
        "",
        "Spot checks are advisory and should focus on cells with the highest automated QA risk, one representative from any undercovered stratum, or cells whose removal would materially reduce feature-space coverage.",
        "",
        "Manifest generation is not blocked unless invalid geometry is detected for a selected cell.",
        "",
        f"Suggested spot-check cells written: {len(spot)}.",
    ]
    (OUT_DIR / "n150_manual_review_budget.md").write_text("\n".join(manual_md) + "\n", encoding="utf-8")
    selected_qa_count = int(qa.loc[qa["selection_group"].eq("selected_n150"), "cell_id"].nunique())
    return qa, spot, selected_qa_count


def coverage_diagnostics(universe: pd.DataFrame, fm: pd.DataFrame, selected: pd.DataFrame, new_cells: pd.DataFrame) -> None:
    groups = {
        "eligible_universe": fm,
        "n24_retained": selected.loc[selected["selection_status"].eq("retained_n24")],
        "n150_selected": selected,
        "added126": new_cells,
    }
    summary_rows = []
    distribution_rows = []
    for feat in SAMPLING_FEATURES:
        universe_vals = numeric(fm[feat])
        for group, gdf in groups.items():
            vals = numeric(gdf[feat])
            summary_rows.append(
                {
                    "feature": feat,
                    "group": group,
                    "count": int(vals.notna().sum()),
                    "min": vals.min(),
                    "max": vals.max(),
                    "mean": vals.mean(),
                    "std": vals.std(),
                }
            )
        selected_vals = numeric(selected[feat])
        uni_range = universe_vals.max() - universe_vals.min()
        sel_range = selected_vals.max() - selected_vals.min()
        smd = (selected_vals.mean() - universe_vals.mean()) / universe_vals.std() if universe_vals.std() not in [0, np.nan] else np.nan
        distribution_rows.append(
            {
                "feature": feat,
                "eligible_min": universe_vals.min(),
                "eligible_max": universe_vals.max(),
                "selected_min": selected_vals.min(),
                "selected_max": selected_vals.max(),
                "feature_range_coverage_ratio": sel_range / uni_range if pd.notna(uni_range) and uni_range != 0 else np.nan,
                "standardized_mean_difference_selected_vs_eligible": smd,
            }
        )
    pd.DataFrame(summary_rows).to_csv(OUT_DIR / "n150_sampling_coverage_summary.csv", index=False)
    pd.DataFrame(distribution_rows).to_csv(OUT_DIR / "n150_feature_distribution_coverage.csv", index=False)

    bin_rows = []
    for feat in SAMPLING_FEATURES:
        vals = numeric(fm[feat])
        quantiles = vals.quantile([0, 0.2, 0.4, 0.6, 0.8, 1.0]).to_numpy()
        for i in range(5):
            lo, hi = quantiles[i], quantiles[i + 1]
            if i == 4:
                uni_mask = (vals >= lo) & (vals <= hi)
                sel_mask = (numeric(selected[feat]) >= lo) & (numeric(selected[feat]) <= hi)
            else:
                uni_mask = (vals >= lo) & (vals < hi)
                sel_mask = (numeric(selected[feat]) >= lo) & (numeric(selected[feat]) < hi)
            bin_rows.append(
                {
                    "feature": feat,
                    "quantile_bin": f"{i * 20}-{(i + 1) * 20}",
                    "eligible_count": int(uni_mask.sum()),
                    "selected_count": int(sel_mask.sum()),
                    "undercovered": bool(sel_mask.sum() == 0 and uni_mask.sum() > 0),
                }
            )
    pd.DataFrame(bin_rows).to_csv(OUT_DIR / "n150_quantile_bin_coverage.csv", index=False)

    stratum_rows = []
    for stratum in BROAD_STRATA + ["background_feature_space_fill"]:
        for group, gdf in groups.items():
            secondary = gdf["secondary_sampling_strata"].astype(str).str.contains(stratum, regex=False, na=False)
            primary = gdf["primary_sampling_stratum"].astype(str).eq(stratum)
            stratum_rows.append(
                {
                    "stratum": stratum,
                    "group": group,
                    "primary_count": int(primary.sum()),
                    "secondary_count": int(secondary.sum()),
                    "missing_stratum_warning": bool(group == "n150_selected" and secondary.sum() == 0),
                }
            )
    pd.DataFrame(stratum_rows).to_csv(OUT_DIR / "n150_stratum_coverage_matrix.csv", index=False)

    geo_rows = []
    if numeric(selected["centroid_x"]).notna().all() and numeric(selected["centroid_y"]).notna().all():
        sx = pd.cut(safe_norm(selected["centroid_x"]), bins=[0, 0.25, 0.5, 0.75, 1.0], include_lowest=True)
        sy = pd.cut(safe_norm(selected["centroid_y"]), bins=[0, 0.25, 0.5, 0.75, 1.0], include_lowest=True)
        geo_counts = selected.assign(x_bin=sx.astype(str), y_bin=sy.astype(str)).groupby(["x_bin", "y_bin"]).size().reset_index(name="selected_count")
        coords = selected[["centroid_x_normalized_q01", "centroid_y_normalized_q01"]].fillna(0.5).to_numpy(float)
        distances = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(axis=2))
        np.fill_diagonal(distances, np.nan)
        nn = np.nanmin(distances, axis=1)
        for _, row in geo_counts.iterrows():
            geo_rows.append(row.to_dict())
        geo_rows.append(
            {
                "x_bin": "nearest_neighbor_summary",
                "y_bin": "selected",
                "selected_count": len(selected),
                "nn_min": float(np.nanmin(nn)),
                "nn_median": float(np.nanmedian(nn)),
                "nn_p95": float(np.nanquantile(nn, 0.95)),
                "clustering_warning": bool((geo_counts["selected_count"].max() / len(selected)) > 0.35),
            }
        )
    pd.DataFrame(geo_rows).to_csv(OUT_DIR / "n150_geographic_coverage.csv", index=False)


def surrogate_split_plan(selected: pd.DataFrame) -> None:
    rows = []
    for _, row in selected.iterrows():
        labels = []
        if row["selection_status"] == "retained_n24":
            labels.append("continuity_anchor")
        if stable_bucket(str(row["cell_id"]), 10) in {0, 1} and row["selection_status"] != "retained_n24":
            labels.append("validation_candidate")
        if stable_bucket(str(row["cell_id"]), 10) == 2 and row["selection_status"] != "retained_n24":
            labels.append("spatial_holdout_candidate")
        if row["primary_sampling_stratum"] in {"overhead_or_transport_structure", "water_edge_or_blue_green_mixed"} and stable_bucket(str(row["cell_id"]), 3) == 0:
            labels.append("typology_holdout_candidate")
        if row.get("extreme_coverage_reason", ""):
            labels.append("stress_test_cell")
        if not labels:
            labels.append("train_candidate")
        rows.append(
            {
                "cell_id": row["cell_id"],
                "selection_status": row["selection_status"],
                "primary_sampling_stratum": row["primary_sampling_stratum"],
                "advisory_split_labels": "|".join(labels),
                "note": "Advisory only; B8 must finalize surrogate CV/holdout design after labels exist.",
            }
        )
    pd.DataFrame(rows).to_csv(OUT_DIR / "n150_surrogate_split_plan_advisory.csv", index=False)
    note = [
        "# N150 surrogate holdout design note",
        "",
        "This B6 output is advisory only and does not train a surrogate.",
        "",
        "N24 cells are marked as continuity anchors so future B8 work can use them for sanity checks or validation continuity. Some added cells are marked as validation, spatial holdout, typology holdout, or stress-test candidates using deterministic rules and B6 strata.",
        "",
        "The final cross-validation and holdout design should be decided after B7 produces the 1260 new SOLWEIG rows and the complete N150 target matrix is aggregated.",
    ]
    (OUT_DIR / "n150_surrogate_holdout_design_note.md").write_text("\n".join(note) + "\n", encoding="utf-8")


def build_manifests(selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    for _, row in selected.sort_values("selection_rank").iterrows():
        for scenario in SCENARIOS:
            scenario_dir = "solweig_base" if scenario == "base" else "solweig_overhead_as_canopy"
            token = "base" if scenario == "base" else "overhead"
            for hour in HOURS:
                is_n24 = row["selection_status"] == "retained_n24"
                rows.append(
                    {
                        "run_id": f"v12_n150_{token}_{row['cell_id']}_h{hour}",
                        "cell_id": row["cell_id"],
                        "scenario": scenario,
                        "hour_sgt": hour,
                        "forcing_label": "b7_future_same_formal_hotday_forcing_as_n24",
                        "target_version": TARGET_VERSION,
                        "reference_domain_version_future": REFERENCE_DOMAIN_FUTURE,
                        "selection_status": row["selection_status"],
                        "raw_output_root_expected": "data/solweig/v12_n150_tiles",
                        "output_dir_expected": f"data/solweig/v12_n150_tiles/{row['cell_id']}/{scenario_dir}/solweig_outputs_h{hour}",
                        "tmrt_output_expected": f"data/solweig/v12_n150_tiles/{row['cell_id']}/{scenario_dir}/solweig_outputs_h{hour}/Tmrt_average.tif",
                        "do_not_commit_raw_output": True,
                        "reuse_existing_n24_label": bool(is_n24),
                        "b5_primary_target": "tmrt_p90_c",
                        "b5_primary_modifier_delta": "delta_tmrt_p90_c",
                        "b5_normalized_modifier": "m_rad_pct01",
                        "execution_status_hint": "completed_n24_existing" if is_n24 else "pending_b7_new_run",
                        "source_existing_summary": "outputs/v12_solweig_n24_execution/n24_focus_tmrt_summary.csv" if is_n24 else "",
                        "notes": "Reuse completed N24 summary; no rerun in B6/B7 manifest." if is_n24 else "Future B7 new-run-only SOLWEIG execution row.",
                    }
                )
    full = pd.DataFrame(rows)
    new = full.loc[full["execution_status_hint"].eq("pending_b7_new_run")].copy()
    base = new.loc[new["scenario"].eq("base")].copy()
    overhead = new.loc[new["scenario"].eq("overhead_as_canopy")].copy()

    full.to_csv(CONFIG_DIR / "v12_solweig_n150_full_run_matrix.csv", index=False)
    new.to_csv(CONFIG_DIR / "v12_solweig_n150_new_run_matrix.csv", index=False)
    base.to_csv(CONFIG_DIR / "v12_solweig_n150_new_base_manifest.csv", index=False)
    overhead.to_csv(CONFIG_DIR / "v12_solweig_n150_new_overhead_manifest.csv", index=False)

    checks = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    selected_cells = set(selected["cell_id"].astype(str))
    new_cells = set(selected.loc[selected["selection_status"].eq("selected_new"), "cell_id"].astype(str))
    check("n150_selected_unique_cells", len(selected_cells) == 150, f"selected cells = {len(selected_cells)}")
    check("retained_n24_count", int(selected["selection_status"].eq("retained_n24").sum()) == 24, f"retained = {int(selected['selection_status'].eq('retained_n24').sum())}")
    check("new_selected_count", len(new_cells) == 126, f"new = {len(new_cells)}")
    check("full_matrix_rows", len(full) == 1500, f"rows = {len(full)}")
    check("new_matrix_rows", len(new) == 1260, f"rows = {len(new)}")
    check("base_new_manifest_rows", len(base) == 630, f"rows = {len(base)}")
    check("overhead_new_manifest_rows", len(overhead) == 630, f"rows = {len(overhead)}")
    check("no_duplicate_run_id", not full["run_id"].duplicated().any(), "run_id duplicate count = 0")
    complete_hours = new.groupby(["cell_id", "scenario"])["hour_sgt"].nunique().eq(len(HOURS)).all()
    check("all_required_hours_present_for_new_cell_scenario", bool(complete_hours), "new cells have 5 hours per scenario")
    check("replaced_out_absent", not (set(REPLACED_OUT) & selected_cells), f"intersection = {sorted(set(REPLACED_OUT) & selected_cells)}")
    check("all_raw_outputs_do_not_commit", bool(full["do_not_commit_raw_output"].all()), "all manifest rows marked do_not_commit_raw_output")
    forbidden = {"local_wbgt_c", "hazard_score", "risk_score"}
    forbidden_cols = forbidden & set(full.columns)
    system_a_cols = [c for c in full.columns if c.lower().startswith("system_a")]
    check("no_local_wbgt_hazard_risk_columns", not forbidden_cols, f"forbidden columns = {sorted(forbidden_cols)}")
    check("no_system_a_fields", not system_a_cols, f"System A columns = {system_a_cols}")

    preflight = pd.DataFrame(checks)
    preflight.to_csv(OUT_DIR / "n150_manifest_preflight.csv", index=False)
    status = "PASS" if preflight["status"].eq("PASS").all() else "BLOCKED"
    md = [
        "# N150 manifest preflight",
        "",
        f"Status: **{status}**",
        "",
        f"- Full expected N150 matrix rows: {len(full)}",
        f"- New-run-only rows: {len(new)}",
        f"- Base new manifest rows: {len(base)}",
        f"- Overhead new manifest rows: {len(overhead)}",
        "- Raw outputs are marked do_not_commit_raw_output=true.",
        "- No local_wbgt_c, hazard_score, risk_score, or System A fields are present.",
    ]
    (OUT_DIR / "n150_manifest_preflight.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return full, new, base, overhead, preflight


def write_config() -> None:
    text = """sample_version: systemb_n150_sample_v0_1_b6
target_version: systemb_target_family_v0_1_b5
total_n: 150
retain_existing_n24: true
n_existing_completed: 24
n_new_to_select: 126
scenarios:
  - base
  - overhead_as_canopy
hours_sgt:
  - 10
  - 12
  - 13
  - 15
  - 16
full_expected_rows: 1500
new_expected_runs: 1260
sampling_strategy: hybrid_quota_lhs_or_greedy_maximin
random_seed: 42
excluded_cells:
  - TP_0058
  - TP_0828
  - TP_0802
  - TP_0675
  - TP_0916
primary_target: tmrt_p90_c
primary_modifier_delta: delta_tmrt_p90_c
normalized_modifier: m_rad_pct01
reference_domain_version_future: n150_training_future
no_manual_full_qa: true
manual_spot_check_budget_max: 15
forbidden_outputs:
  - local_wbgt_c
  - hazard_score
  - risk_score
"""
    (CONFIG_DIR / "systemb_n150_sampling_config.example.yaml").write_text(text, encoding="utf-8")


def write_docs(method: str) -> None:
    sample_doc = f"""# OpenHeat System B N150 样本设计说明（B6）

## 为什么需要 B6

B6 的目标是把已经完成的 N24 SOLWEIG 标签扩展为未来 N150 标签设计，而不是直接进入模型训练。B5 已经冻结 System B 的目标族：主物理目标为 `tmrt_p90_c`，主物理修正量为 `delta_tmrt_p90_c`，归一化候选修正量为 `m_rad_pct01`。

## B5 如何驱动采样

采样只使用形态、遮阴、地表、架空结构和空间覆盖特征，不使用未来目标值来挑选新格网。这样可以为未来 `delta_tmrt_p90_c` 和 `m_rad_pct01` 提供更均衡的特征空间覆盖，同时避免把 N24 的 SOLWEIG 标签泄漏到新增样本选择中。

## 为什么 N150 = N24 + 126

N150 指 150 个总标注格网，而不是新增 150 个格网。已完成的 B2.2/B3 N24 是连续性标签，因此保留为种子样本；B6 只新增 126 个待运行格网。

## 采样特征与配额

脚本优先使用 SVF/开天空、遮阴、建筑密度、高度或街谷代理、道路/硬质铺装、树冠/GVI、草地、水边、架空结构、不透水/建成度，以及归一化质心坐标。诊断分层包括开放硬质高 SVF、低 SVF 遮阴、街谷/墙邻、交通或架空结构、连廊/人行桥、水边蓝绿混合、草地开放公园、道路边、高密建成、混合上尾探针和最大极端探针。

## 特征空间覆盖方法

脚本先保留 N24，再补足可识别的诊断分层配额和极端覆盖。若 SciPy QMC 可用，则使用 Latin Hypercube 目标点并用距离惩罚选择最近且不过度重复的候选；本次记录的填充方法为 `{method}`。若 QMC 不可用，则回退为贪心 maximin 特征空间覆盖。

## 为什么不需要 150 个全量人工 QA

B6 生成自动 QA 标记和最多 10-15 个建议抽查单元。人工抽查是建议性的，不是所有 150 个格网的前置门槛；只有未来发现选中格网存在无效几何时，才应阻断执行。

## 这还不是模型或风险产品

B6 不训练 surrogate/emulator，不计算 local WBGT，不计算 hazard_score 或 risk_score，也不做 System A/B coupling。它只产生未来 B7 可执行的新运行矩阵和 B8 可使用的标签设计基础。
"""
    manifest_doc = """# OpenHeat System B N150 SOLWEIG manifest 计划（B6）

## 运行矩阵含义

完整 N150 期望矩阵包含 150 个格网、2 个情景和 5 个小时，因此为 1500 行。由于 N24 已经完成，B7 未来只需要执行 126 个新增格网、2 个情景和 5 个小时，即 1260 行。

## 已创建的 manifest

- `configs/v12/v12_solweig_n150_full_run_matrix.csv`：完整 N150 期望标签矩阵，包含 N24 复用行和新增待执行行。
- `configs/v12/v12_solweig_n150_new_run_matrix.csv`：B7 应执行的新运行矩阵，排除已完成 N24 和 B2.2 replaced-out cells。
- `configs/v12/v12_solweig_n150_new_base_manifest.csv`：新增 base 情景 630 行。
- `configs/v12/v12_solweig_n150_new_overhead_manifest.csv`：新增 overhead_as_canopy 情景 630 行。

## B7 执行边界

manifest 只描述未来 SOLWEIG 运行计划；B6 本身不运行 QGIS、不运行 SOLWEIG、不读取 raster。所有预期 raw output 路径均标记 `do_not_commit_raw_output=true`，raw 栅格输出仍应保持未提交。

## 与 B5 目标族的关系

每一行 manifest 都携带 `tmrt_p90_c`、`delta_tmrt_p90_c`、`m_rad_pct01` 的 B5 目标族标识，并把未来 reference domain 标记为 `n150_training_future`。这只是未来标签聚合与归一化的契约，不是最终地图、风险分数或 WBGT 产品。
"""
    (DOC_DIR / "OpenHeat_SystemB_N150_sample_design_CN.md").write_text(sample_doc, encoding="utf-8")
    (DOC_DIR / "OpenHeat_SystemB_N150_SOLWEIG_manifest_plan_CN.md").write_text(manifest_doc, encoding="utf-8")


def write_report(
    universe: pd.DataFrame,
    exclusions: pd.DataFrame,
    selected: pd.DataFrame,
    new_cells: pd.DataFrame,
    retained: pd.DataFrame,
    alternates: pd.DataFrame,
    method: str,
    qa_count: int,
    full: pd.DataFrame,
    new: pd.DataFrame,
    base: pd.DataFrame,
    overhead: pd.DataFrame,
    preflight: pd.DataFrame,
) -> None:
    status = "PASS" if preflight["status"].eq("PASS").all() and len(selected) == TOTAL_N else "PARTIAL"
    eligible = int(universe["eligible"].sum())
    source_count = universe["candidate_source_files"].astype(str).str.len().gt(0).sum()
    selected_strata = selected["primary_sampling_stratum"].value_counts().to_dict()
    lines = [
        "# Sprint B6 - System B N150 Sample Design + Manifest",
        "",
        "## Status",
        status,
        "",
        "## Scope",
        "- N150 sample design + manifest only",
        "- no QGIS",
        "- no SOLWEIG",
        "- no raw raster reads",
        "- no local WBGT",
        "- no hazard_score",
        "- no risk_score",
        "- no surrogate",
        "- no System A/B coupling",
        "",
        "## Inputs",
        "B5 target family is frozen around `tmrt_p90_c`, `delta_tmrt_p90_c`, and `m_rad_pct01`. Completed N24 rows are reused as seed / continuity labels and are not rerun in this sprint.",
        "",
        "## Candidate universe",
        f"- Candidate cells with feature sources: {source_count}",
        f"- Eligible cells after hard exclusions / feature checks: {eligible}",
        f"- Excluded cells recorded: {len(exclusions)}",
        "- Feature source and missingness are written to `n150_feature_source_map.csv` and `n150_sampling_feature_missingness.csv`.",
        "",
        "## Sampling strategy",
        f"N24 retention, diagnostic quotas, feature-space extremes, and `{method}` feature-space fill were used. Geographic coordinates were included as normalized sampling features when available.",
        "",
        "## Selected N150",
        f"- Total selected = {len(selected)}",
        f"- Retained N24 = {len(retained)}",
        f"- New cells = {len(new_cells)}",
        f"- Alternates count = {len(alternates)}",
        f"- Replaced-out cells absent = {not bool(set(REPLACED_OUT) & set(selected['cell_id'].astype(str)))}",
        "",
        "## Coverage",
        f"Primary stratum counts: `{selected_strata}`. Feature distribution, quantile-bin, stratum, and geographic diagnostics are written in the B6 output directory.",
        "",
        "## Auto QA",
        f"Selected cells with at least one automated QA flag: {qa_count}. No full manual QA is required; optional spot-check suggestions are capped at 15 cells.",
        "",
        "## Surrogate readiness",
        "This creates a future label design and advisory split labels only. It is not surrogate training and does not finalize B8 cross-validation.",
        "",
        "## Manifest",
        f"- Full matrix rows = {len(full)}",
        f"- New-run-only rows = {len(new)}",
        f"- Base new manifest rows = {len(base)}",
        f"- Overhead new manifest rows = {len(overhead)}",
        "- Raw outputs marked do_not_commit",
        "- B7 should execute the new-run-only matrix and merge with existing N24 summaries.",
        "",
        "## Claim boundaries",
        "No local WBGT, no hazard_score, no risk_score, no surrogate, no A/B coupling.",
        "",
        "## Next recommended action",
        "B7 - execute N150 new-run-only SOLWEIG matrix in QGIS Desktop Python Console, then aggregate and merge with existing N24 summaries.",
    ]
    (OUT_DIR / "sprint_b6_n150_sample_design_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_blocked_report() -> None:
    lines = [
        "# Sprint B6 - System B N150 Sample Design + Manifest",
        "",
        "## Status",
        "BLOCKED",
        "",
        "Input validation failed. See `b6_input_validation.csv` and `b6_input_validation.md`.",
    ]
    (OUT_DIR / "sprint_b6_n150_sample_design_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    blocked, n24, focus, _ = validate_inputs()
    if blocked:
        write_blocked_report()
        return

    universe, exclusions, _source_map = build_candidate_universe(n24, focus, write_outputs=True)
    fm = build_sampling_feature_matrix(universe)
    selected, new_cells, retained, alternates, method = run_sampling(fm.merge(
        universe[[
            "cell_id",
            "eligible",
            "geometry_available",
            "candidate_source_files",
            "overhead_confounding_flag",
            "overhead_interpretation",
        ]],
        on="cell_id",
        how="left",
    ))
    qa, _spot, qa_count = compute_auto_qa(selected, alternates, exclusions)
    selected_flags = qa.loc[qa["selection_group"].eq("selected_n150")].groupby("cell_id")["flag"].apply(lambda s: "|".join(sorted(set(s))))
    selected["auto_qa_flag"] = selected["cell_id"].map(selected_flags).fillna("")
    selected.loc[:, [
        "selection_rank",
        "cell_id",
        "selection_status",
        "selection_tier",
        "existing_solweig_label_status",
        "primary_sampling_stratum",
        "secondary_sampling_strata",
        "typology_label",
        "sampling_feature_coverage_reason",
        "quota_reason",
        "lhs_or_greedy_reason",
        "extreme_coverage_reason",
        "replacement_of_cell_id",
        "source_feature_completeness",
        "auto_qa_flag",
        "manual_review_required",
        "manual_review_reason",
        "notes",
    ]].to_csv(OUT_DIR / "n150_selected_cells.csv", index=False)
    coverage_diagnostics(universe, label_strata(fm), selected, new_cells)
    surrogate_split_plan(selected)
    full, new, base, overhead, preflight = build_manifests(selected)
    write_config()
    write_docs(method)
    write_report(universe, exclusions, selected, new_cells, retained, alternates, method, qa_count, full, new, base, overhead, preflight)
    print(f"B6 status: {'PASS' if preflight['status'].eq('PASS').all() else 'PARTIAL'}")
    print(f"selected_n150={len(selected)} retained_n24={len(retained)} new_cells={len(new_cells)}")
    print(f"manifest_rows full={len(full)} new={len(new)} base={len(base)} overhead={len(overhead)}")
    print(f"sampling_method={method} auto_qa_selected_cell_count={qa_count}")


if __name__ == "__main__":
    main()
