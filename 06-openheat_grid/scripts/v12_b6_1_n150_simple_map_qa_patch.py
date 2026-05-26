"""Sprint B6.1 N150 simple map-QA package and consistency patch.

Inputs:
    B6 N150 selected-cell, new-cell, alternate, candidate-universe, QA flag,
    stratum coverage, coverage summary, quantile coverage, and manifest CSVs
    under outputs/v12_systemb_n150_sample_design and configs/v12.

Outputs:
    Simple whole-sample map-QA checklist CSV/Markdown, review point
    GeoJSON/KML, replacement suggestions, multi-label stratum summary,
    primary-stratum caveat, and a B6.1 patch report under
    outputs/v12_systemb_n150_sample_design.

Patched output:
    n150_new_cells.csv is rebuilt from n150_selected_cells.csv selected_new
    rows so review fields remain synchronized.

Saved metrics:
    B6 validation counts, unchanged selected/retained/new counts, unchanged
    manifest row counts, flagged checklist count, review-point availability,
    replacement-suggestion coverage, and synchronization status.

This script does not resample cells, does not change selected cell IDs, does
not regenerate manifests, does not run QGIS/SOLWEIG/qgis_process, does not
read rasters, does not train surrogate models, and does not compute local
WBGT, hazard_score, risk_score, or System A/B coupled outputs.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "v12_systemb_n150_sample_design"
CONFIG_DIR = ROOT / "configs" / "v12"

SELECTED_PATH = OUT_DIR / "n150_selected_cells.csv"
NEW_PATH = OUT_DIR / "n150_new_cells.csv"
ALTERNATES_PATH = OUT_DIR / "n150_alternate_cells.csv"
CANDIDATE_UNIVERSE_PATH = OUT_DIR / "n150_candidate_universe.csv"
AUTO_QA_PATH = OUT_DIR / "n150_auto_qa_flags.csv"
SPOT_CHECK_PATH = OUT_DIR / "n150_spot_check_suggestions.csv"
STRATUM_COVERAGE_PATH = OUT_DIR / "n150_stratum_coverage_matrix.csv"
SAMPLING_COVERAGE_PATH = OUT_DIR / "n150_sampling_coverage_summary.csv"
QUANTILE_COVERAGE_PATH = OUT_DIR / "n150_quantile_bin_coverage.csv"
SAMPLING_FEATURE_MATRIX_PATH = OUT_DIR / "n150_sampling_feature_matrix.csv"
FULL_MATRIX_PATH = CONFIG_DIR / "v12_solweig_n150_full_run_matrix.csv"
NEW_MATRIX_PATH = CONFIG_DIR / "v12_solweig_n150_new_run_matrix.csv"
REPORT_PATH = OUT_DIR / "sprint_b6_1_n150_simple_map_qa_patch_report.md"

REPLACED_OUT = {"TP_0058", "TP_0828", "TP_0802", "TP_0675", "TP_0916"}
REPLACEMENT_IN = {"TP_0141", "TP_0301", "TP_0773", "TP_0676", "TP_0575"}
ONLY_QUESTION = (
    "Is this obviously unsuitable, e.g. almost pure water, invalid geometry, "
    "pure rooftop/building body, AOI edge artifact, or clearly wrong type?"
)
REPLACE_IF = (
    "Replace only if almost pure water, invalid geometry, pure rooftop/building body, "
    "AOI edge artifact, clearly wrong type, or excessive near-duplicate with no added value."
)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"cell_id": "string"})


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def as_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def split_strata(value: Any) -> list[str]:
    if pd.isna(value):
        return []
    tokens = re.split(r"[|;,]", str(value))
    return [token.strip() for token in tokens if token.strip()]


def unique_strata(row: pd.Series) -> set[str]:
    labels = set(split_strata(row.get("secondary_sampling_strata", "")))
    primary = str(row.get("primary_sampling_stratum", "")).strip()
    if primary:
        labels.add(primary)
    return labels


def validation_rows() -> tuple[list[dict[str, Any]], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        rows.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    for path in [
        SELECTED_PATH,
        NEW_PATH,
        ALTERNATES_PATH,
        CANDIDATE_UNIVERSE_PATH,
        STRATUM_COVERAGE_PATH,
        SAMPLING_COVERAGE_PATH,
        QUANTILE_COVERAGE_PATH,
        FULL_MATRIX_PATH,
        NEW_MATRIX_PATH,
    ]:
        check(f"{path.name}_exists", path.exists(), str(path.relative_to(ROOT)))

    selected = read_csv(SELECTED_PATH) if SELECTED_PATH.exists() else pd.DataFrame()
    full_matrix = read_csv(FULL_MATRIX_PATH) if FULL_MATRIX_PATH.exists() else pd.DataFrame()
    new_matrix = read_csv(NEW_MATRIX_PATH) if NEW_MATRIX_PATH.exists() else pd.DataFrame()

    selected_ids = set(selected.get("cell_id", pd.Series(dtype=str)).dropna().astype(str))
    retained_count = int(selected.get("selection_status", pd.Series(dtype=str)).eq("retained_n24").sum())
    selected_new_count = int(
        (
            selected.get("selection_status", pd.Series(dtype=str)).eq("selected_new")
            | selected.get("selection_tier", pd.Series(dtype=str)).eq("added126")
        ).sum()
    )
    check("selected_rows_150", len(selected) == 150, f"selected rows = {len(selected)}")
    check("selected_unique_cell_id_150", len(selected_ids) == 150, f"unique cell_id = {len(selected_ids)}")
    check("retained_n24_count_24", retained_count == 24, f"retained_n24 = {retained_count}")
    check("selected_new_count_126", selected_new_count == 126, f"selected_new = {selected_new_count}")
    check("full_run_matrix_rows_1500", len(full_matrix) == 1500, f"full rows = {len(full_matrix)}")
    check("new_run_matrix_rows_1260", len(new_matrix) == 1260, f"new rows = {len(new_matrix)}")
    check("b2_2_replaced_out_absent", not (selected_ids & REPLACED_OUT), f"intersection = {sorted(selected_ids & REPLACED_OUT)}")
    check("b2_2_replacement_in_present", REPLACEMENT_IN <= selected_ids, f"missing = {sorted(REPLACEMENT_IN - selected_ids)}")
    return rows, selected, full_matrix, new_matrix


def write_blocked_report(rows: list[dict[str, Any]]) -> None:
    failed = [row for row in rows if row["status"] == "FAIL"]
    lines = [
        "# Sprint B6.1 - N150 Simple Map-QA Package Patch",
        "",
        "## Status",
        "BLOCKED",
        "",
        "B6.1 validation failed; no further outputs were patched.",
        "",
        "## Failed checks",
        "",
    ]
    if failed:
        lines.extend([f"- {row['check']}: {row['detail']}" for row in failed])
    else:
        lines.append("- No failed check was recorded, but validation did not pass.")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync_new_cells(selected: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    selected_new = selected.loc[
        selected["selection_status"].eq("selected_new") | selected["selection_tier"].eq("added126")
    ].copy()
    old_ids = set(read_csv(NEW_PATH)["cell_id"].astype(str)) if NEW_PATH.exists() else set()
    new_ids = set(selected_new["cell_id"].astype(str))
    selected_new = selected_new.sort_values("selection_rank")
    selected_new.to_csv(NEW_PATH, index=False)
    return selected_new, old_ids == new_ids


def build_multilabel_summary(selected: pd.DataFrame) -> pd.DataFrame:
    primary_counts = selected["primary_sampling_stratum"].fillna("").value_counts().to_dict()
    secondary_counts: dict[str, int] = {}
    combined_counts: dict[str, int] = {}
    retained_counts: dict[str, int] = {}
    new_counts: dict[str, int] = {}

    for _, row in selected.iterrows():
        secondary = set(split_strata(row.get("secondary_sampling_strata", "")))
        combined = unique_strata(row)
        for label in secondary:
            secondary_counts[label] = secondary_counts.get(label, 0) + 1
        for label in combined:
            combined_counts[label] = combined_counts.get(label, 0) + 1
            if row.get("selection_status") == "retained_n24":
                retained_counts[label] = retained_counts.get(label, 0) + 1
            elif row.get("selection_status") == "selected_new":
                new_counts[label] = new_counts.get(label, 0) + 1

    labels = sorted(set(primary_counts) | set(secondary_counts) | set(combined_counts))
    summary = pd.DataFrame(
        [
            {
                "stratum": label,
                "primary_count": int(primary_counts.get(label, 0)),
                "secondary_multilabel_count": int(secondary_counts.get(label, 0)),
                "combined_primary_or_secondary_count": int(combined_counts.get(label, 0)),
                "retained_n24_combined_count": int(retained_counts.get(label, 0)),
                "selected_new_combined_count": int(new_counts.get(label, 0)),
            }
            for label in labels
        ]
    ).sort_values(["combined_primary_or_secondary_count", "stratum"], ascending=[False, True])
    summary.to_csv(OUT_DIR / "n150_stratum_multilabel_summary.csv", index=False)

    top_primary = selected["primary_sampling_stratum"].fillna("").value_counts().head(3).to_dict()
    caveat = [
        "# N150 primary stratum caveat",
        "",
        "`primary_sampling_stratum` is a coarse automatic label used for compact reporting. It is affected by label priority/order and should not be read as a one-class scientific typology.",
        "",
        f"Top primary-stratum counts in the current selected N150 are: `{top_primary}`.",
        "",
        "Use `secondary_sampling_strata`, the multi-label summary, quantile-bin coverage, and numeric sampling features for B8 validation design and any future typology holdout planning.",
        "",
        "This caveat does not invalidate the B6 sample selection or manifests; it only clarifies how the labels should be interpreted.",
    ]
    (OUT_DIR / "n150_primary_stratum_caveat.md").write_text("\n".join(caveat) + "\n", encoding="utf-8")
    return summary


def load_selected_with_coords(selected: pd.DataFrame) -> pd.DataFrame:
    universe = read_csv(CANDIDATE_UNIVERSE_PATH)
    coord_cols = [
        "cell_id",
        "geometry_available",
        "lon",
        "lat",
        "centroid_x",
        "centroid_y",
        "source_feature_completeness",
    ]
    for col in coord_cols:
        if col not in universe.columns:
            universe[col] = np.nan
    merged = selected.merge(universe[coord_cols], on="cell_id", how="left", suffixes=("", "_universe"))
    lon = numeric(merged["lon"])
    lat = numeric(merged["lat"])
    x = numeric(merged["centroid_x"])
    y = numeric(merged["centroid_y"])
    use_wgs84 = lon.between(-180, 180) & lat.between(-90, 90)
    merged["longitude_or_x"] = np.where(use_wgs84, lon, x)
    merged["latitude_or_y"] = np.where(use_wgs84, lat, y)
    merged["coordinate_kind"] = np.where(use_wgs84, "wgs84_lon_lat", "projected_or_unknown_xy")
    has_pair = pd.notna(merged["longitude_or_x"]) & pd.notna(merged["latitude_or_y"])
    geom_flag = as_bool(merged.get("geometry_available", pd.Series(False, index=merged.index)))
    merged["geometry_or_centroid_available"] = has_pair | geom_flag
    return merged


def feature_distance_columns(df: pd.DataFrame) -> list[str]:
    return [col for col in df.columns if col.endswith("_q01")]


def build_replacement_suggestions(selected: pd.DataFrame) -> pd.DataFrame:
    alternates = read_csv(ALTERNATES_PATH)
    selected_ids = set(selected["cell_id"].astype(str))
    alternates = alternates.loc[
        ~alternates["cell_id"].astype(str).isin(selected_ids | REPLACED_OUT)
    ].copy()

    if SAMPLING_FEATURE_MATRIX_PATH.exists():
        fm = read_csv(SAMPLING_FEATURE_MATRIX_PATH)
        qcols = feature_distance_columns(fm)
        merge_cols = ["cell_id"] + qcols
        selected = selected.merge(fm[merge_cols], on="cell_id", how="left")
        alternates = alternates.merge(fm[merge_cols], on="cell_id", how="left", suffixes=("", "_fm"))
    else:
        qcols = feature_distance_columns(alternates)

    suggestions: list[dict[str, Any]] = []
    for _, row in selected.iterrows():
        row_strata = unique_strata(row)
        scored = alternates.copy()
        scored["_stratum_overlap"] = scored.apply(lambda alt: len(row_strata & unique_strata(alt)), axis=1)
        scored["_primary_match"] = scored["primary_sampling_stratum"].astype(str).eq(str(row.get("primary_sampling_stratum", ""))).astype(int)
        scored["_feature_completeness"] = numeric(scored.get("source_feature_completeness", pd.Series(0, index=scored.index))).fillna(0)
        if qcols and all(col in row.index for col in qcols):
            row_vec = numeric(pd.Series([row.get(col) for col in qcols])).to_numpy(dtype=float)
            distances = []
            for _, alt in scored.iterrows():
                alt_vec = numeric(pd.Series([alt.get(col) for col in qcols])).to_numpy(dtype=float)
                valid = ~np.isnan(row_vec) & ~np.isnan(alt_vec)
                if valid.any():
                    distances.append(float(np.sqrt(((row_vec[valid] - alt_vec[valid]) ** 2).mean())))
                else:
                    distances.append(1.0)
            scored["_feature_distance"] = distances
        else:
            scored["_feature_distance"] = 1.0
        scored["_score"] = (
            3.0 * scored["_primary_match"]
            + 1.5 * scored["_stratum_overlap"]
            + 0.5 * scored["_feature_completeness"]
            - 0.75 * scored["_feature_distance"]
        )
        scored = scored.sort_values(["_score", "_stratum_overlap", "_feature_completeness", "cell_id"], ascending=[False, False, False, True])
        top = scored.head(3).to_dict("records")

        if str(row.get("auto_qa_flag", "")).strip():
            reason = str(row.get("auto_qa_flag"))
        elif row.get("selection_status") == "selected_new":
            reason = "selected_new advisory replacement only if quick map check marks REPLACE"
        else:
            reason = "retained_n24 continuity anchor; replacement discouraged unless obviously unsuitable"

        out = {
            "cell_id": row["cell_id"],
            "reason_for_possible_replacement": reason,
            "replacement_candidate_1": "",
            "replacement_candidate_1_reason": "",
            "replacement_candidate_2": "",
            "replacement_candidate_2_reason": "",
            "replacement_candidate_3": "",
            "replacement_candidate_3_reason": "",
            "replacement_gap": len(top) == 0,
        }
        for idx, alt in enumerate(top, start=1):
            reasons = []
            if int(alt.get("_primary_match", 0)) == 1:
                reasons.append("same primary stratum")
            if int(alt.get("_stratum_overlap", 0)) > 0:
                reasons.append(f"{int(alt['_stratum_overlap'])} shared strata")
            reasons.append(f"feature completeness {float(alt.get('_feature_completeness', 0.0)):.2f}")
            if math.isfinite(float(alt.get("_feature_distance", 1.0))):
                reasons.append(f"feature distance {float(alt['_feature_distance']):.3f}")
            out[f"replacement_candidate_{idx}"] = alt["cell_id"]
            out[f"replacement_candidate_{idx}_reason"] = "; ".join(reasons)
        suggestions.append(out)

    out_df = pd.DataFrame(suggestions)
    out_df.to_csv(OUT_DIR / "n150_replacement_suggestions.csv", index=False)
    return out_df


def build_checklist(selected_with_coords: pd.DataFrame, suggestions: pd.DataFrame) -> pd.DataFrame:
    suggestion_cols = [
        "cell_id",
        "replacement_candidate_1",
        "replacement_candidate_2",
        "replacement_candidate_3",
    ]
    checklist = selected_with_coords.merge(suggestions[suggestion_cols], on="cell_id", how="left")
    checklist["quick_map_check_status"] = "pending"
    checklist["only_question"] = ONLY_QUESTION
    checklist["replace_if"] = REPLACE_IF
    checklist["reviewer_notes"] = ""

    cols = [
        "selection_rank",
        "cell_id",
        "selection_status",
        "selection_tier",
        "existing_solweig_label_status",
        "primary_sampling_stratum",
        "secondary_sampling_strata",
        "typology_label",
        "auto_qa_flag",
        "quick_map_check_status",
        "only_question",
        "replace_if",
        "replacement_candidate_1",
        "replacement_candidate_2",
        "replacement_candidate_3",
        "reviewer_notes",
        "geometry_or_centroid_available",
        "longitude_or_x",
        "latitude_or_y",
    ]
    for col in cols:
        if col not in checklist.columns:
            checklist[col] = ""
    flagged = checklist["auto_qa_flag"].fillna("").astype(str).str.strip().ne("")
    new = checklist["selection_status"].eq("selected_new")
    checklist["_sort_flagged"] = flagged.astype(int)
    checklist["_sort_new"] = new.astype(int)
    checklist = checklist.sort_values(["_sort_flagged", "_sort_new", "selection_rank"], ascending=[False, False, True])
    checklist[cols].to_csv(OUT_DIR / "n150_simple_map_qa_checklist.csv", index=False)

    write_checklist_md(checklist[cols])
    return checklist[cols]


def markdown_table(df: pd.DataFrame, columns: list[str]) -> list[str]:
    if df.empty:
        return ["_None._"]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        values = [str(row.get(col, "")).replace("|", "/") for col in columns]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_checklist_md(checklist: pd.DataFrame) -> None:
    flagged = checklist["auto_qa_flag"].fillna("").astype(str).str.strip().ne("")
    retained = checklist["selection_status"].eq("retained_n24")
    new = checklist["selection_status"].eq("selected_new")
    lines = [
        "# N150 simple map-QA checklist",
        "",
        "This is a quick map sanity pass, not validation. Default KEEP. Mark REPLACE only for obvious bad samples.",
        "",
        f"- Selected total: {len(checklist)}",
        f"- Retained N24: {int(retained.sum())}",
        f"- New cells: {int(new.sum())}",
        f"- Auto-flagged cells: {int(flagged.sum())}",
        "",
        "Only question: Is this obviously unsuitable, e.g. almost pure water, invalid geometry, pure rooftop/building body, AOI edge artifact, or clearly wrong type?",
        "",
        "## Auto-flagged cells",
        "",
    ]
    table_cols = ["selection_rank", "cell_id", "selection_status", "primary_sampling_stratum", "auto_qa_flag", "replacement_candidate_1", "quick_map_check_status"]
    lines.extend(markdown_table(checklist.loc[flagged], table_cols))
    lines.extend(["", "## Remaining cells", ""])
    lines.extend(markdown_table(checklist.loc[~flagged], table_cols))
    (OUT_DIR / "n150_simple_map_qa_checklist.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_review_points(checklist: pd.DataFrame) -> tuple[bool, str, int]:
    lon = numeric(checklist["longitude_or_x"])
    lat = numeric(checklist["latitude_or_y"])
    usable = lon.between(-180, 180) & lat.between(-90, 90)
    usable_df = checklist.loc[usable].copy()
    if usable_df.empty:
        return False, "No WGS84 lon/lat coordinates were available for GeoJSON/KML point helpers.", 0

    features = []
    for _, row in usable_df.iterrows():
        props = {
            "cell_id": row["cell_id"],
            "selection_rank": int(row["selection_rank"]),
            "selection_tier": row.get("selection_tier", ""),
            "primary_sampling_stratum": row.get("primary_sampling_stratum", ""),
            "secondary_sampling_strata": row.get("secondary_sampling_strata", ""),
            "auto_qa_flag": row.get("auto_qa_flag", ""),
            "quick_map_check_status": "pending",
            "only_question": ONLY_QUESTION,
            "replacement_candidate_1": row.get("replacement_candidate_1", ""),
            "replacement_candidate_2": row.get("replacement_candidate_2", ""),
            "review_helper_only": True,
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(row["longitude_or_x"]), float(row["latitude_or_y"])]},
                "properties": props,
            }
        )
    geojson = {
        "type": "FeatureCollection",
        "name": "n150_review_points",
        "crs_note": "WGS84 lon/lat point helpers derived from candidate-universe centroid columns; review helper only, not hazard/risk/SOLWEIG input.",
        "features": features,
    }
    (OUT_DIR / "n150_review_points.geojson").write_text(json.dumps(geojson, indent=2), encoding="utf-8")

    kml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        "  <Document>",
        "    <name>N150 review points</name>",
    ]
    for _, row in usable_df.iterrows():
        desc = (
            f"rank={row['selection_rank']}; tier={row.get('selection_tier', '')}; "
            f"primary={row.get('primary_sampling_stratum', '')}; flags={row.get('auto_qa_flag', '')}; "
            f"question={ONLY_QUESTION}; replacement_1={row.get('replacement_candidate_1', '')}"
        )
        kml_lines.extend(
            [
                "    <Placemark>",
                f"      <name>{escape(str(row['selection_rank']))} {escape(str(row['cell_id']))}</name>",
                f"      <description>{escape(desc)}</description>",
                "      <Point>",
                f"        <coordinates>{float(row['longitude_or_x'])},{float(row['latitude_or_y'])},0</coordinates>",
                "      </Point>",
                "    </Placemark>",
            ]
        )
    kml_lines.extend(["  </Document>", "</kml>"])
    (OUT_DIR / "n150_review_points.kml").write_text("\n".join(kml_lines) + "\n", encoding="utf-8")
    return True, "WGS84 lon/lat review points generated from candidate-universe centroid columns.", len(usable_df)


def write_report(
    rows: list[dict[str, Any]],
    selected: pd.DataFrame,
    selected_new: pd.DataFrame,
    full_matrix: pd.DataFrame,
    new_matrix: pd.DataFrame,
    checklist: pd.DataFrame,
    suggestions: pd.DataFrame,
    new_ids_unchanged: bool,
    review_points_ok: bool,
    review_points_note: str,
    review_points_count: int,
) -> None:
    validation_ok = all(row["status"] == "PASS" for row in rows)
    flagged_count = int(checklist["auto_qa_flag"].fillna("").astype(str).str.strip().ne("").sum())
    retained_count = int(selected["selection_status"].eq("retained_n24").sum())
    new_count = int(selected_new["cell_id"].nunique())
    status = "PASS" if validation_ok and new_ids_unchanged else "PARTIAL"

    lines = [
        "# Sprint B6.1 - N150 Simple Map-QA Package Patch",
        "",
        "## Status",
        status,
        "",
        "## Scope",
        "- simple map-QA package only",
        "- no resampling",
        "- no selected-cell changes",
        "- no manifest changes",
        "- no QGIS",
        "- no SOLWEIG",
        "- no raster reads",
        "- no local WBGT",
        "- no hazard_score",
        "- no risk_score",
        "- no surrogate",
        "- no System A/B coupling",
        "",
        "## Why this patch exists",
        "B6 mechanically passed, but before B7 the user wants one short whole-sample map sanity QA to remove obvious bad samples only.",
        "",
        "## B6 validation",
        f"- Selected rows: {len(selected)}",
        f"- Unique selected cells: {selected['cell_id'].nunique()}",
        f"- Retained N24: {retained_count}",
        f"- New selected cells: {new_count}",
        f"- Full run matrix rows: {len(full_matrix)}",
        f"- New-run-only rows: {len(new_matrix)}",
        "- B2.2 replaced-out cells absent.",
        "- B2.2 replacement-in N24 cells present.",
        "",
        "## New QA philosophy",
        "- Default KEEP.",
        "- REPLACE only obvious bad cells.",
        "- No AMBER.",
        "- No full 150-cell semantic QA.",
        "- No pedestrian-accessibility pass/fail.",
        "- No street-view forensic review.",
        "",
        "## New files",
        "- `n150_simple_map_qa_checklist.csv` / `.md`",
        "- `n150_review_points.geojson` / `.kml`",
        "- `n150_replacement_suggestions.csv`",
        "- `n150_stratum_multilabel_summary.csv`",
        "- `n150_primary_stratum_caveat.md`",
        "",
        "## Review points",
        f"- Generated: {review_points_ok}",
        f"- Usable point count: {review_points_count}",
        f"- Note: {review_points_note}",
        "",
        "## Consistency patch",
        f"`n150_new_cells.csv` was synchronized from `n150_selected_cells.csv` for selected_new rows so review flags are not lost. New-cell ID set unchanged: {new_ids_unchanged}.",
        "",
        "## Primary stratum caveat",
        "Primary-stratum labels are coarse automatic labels and are skewed by label priority/order. Use multi-label strata, feature bins, and numeric sampling features for B8 validation design.",
        "",
        "## Checklist and replacements",
        f"- Checklist rows: {len(checklist)}",
        f"- Auto-flagged rows first in checklist: {flagged_count}",
        f"- Replacement suggestion rows: {len(suggestions)}",
        "",
        "## Next recommended action",
        "User performs quick KEEP/REPLACE map sanity pass. If replacements exist, B6.2 should apply replacements and regenerate manifests. If no replacements exist, proceed to B7 new-run-only N150 SOLWEIG execution.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, selected, full_matrix, new_matrix = validation_rows()
    if any(row["status"] == "FAIL" for row in rows):
        write_blocked_report(rows)
        print("B6.1 status: BLOCKED")
        return

    selected_new, new_ids_unchanged = sync_new_cells(selected)
    build_multilabel_summary(selected)
    suggestions = build_replacement_suggestions(selected)
    selected_with_coords = load_selected_with_coords(selected)
    checklist = build_checklist(selected_with_coords, suggestions)
    review_points_ok, review_points_note, review_points_count = build_review_points(checklist)
    write_report(
        rows=rows,
        selected=selected,
        selected_new=selected_new,
        full_matrix=full_matrix,
        new_matrix=new_matrix,
        checklist=checklist,
        suggestions=suggestions,
        new_ids_unchanged=new_ids_unchanged,
        review_points_ok=review_points_ok,
        review_points_note=review_points_note,
        review_points_count=review_points_count,
    )
    print("B6.1 status: PASS" if new_ids_unchanged else "B6.1 status: PARTIAL")
    print(f"selected={len(selected)} retained_n24={int(selected['selection_status'].eq('retained_n24').sum())} new={len(selected_new)}")
    print(f"manifest_rows_full={len(full_matrix)} manifest_rows_new={len(new_matrix)}")
    print(f"checklist_rows={len(checklist)} review_points={review_points_count} replacement_suggestions={len(suggestions)}")


if __name__ == "__main__":
    main()
