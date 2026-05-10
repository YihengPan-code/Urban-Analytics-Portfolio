from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, Optional

import geopandas as gpd
import pandas as pd

from v10_figures_style_v2 import ensure_dir, INTERPRETATION_LABELS


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_csv_optional(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        print(f"[WARN] Missing optional CSV: {p}")
        return pd.DataFrame()
    return pd.read_csv(p)


def first_present(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def merge_unique(base: pd.DataFrame, other: pd.DataFrame, on: str = "cell_id", suffix: str = "") -> pd.DataFrame:
    if other.empty or on not in other.columns:
        return base
    keep = [on]
    for c in other.columns:
        if c == on:
            continue
        if c not in base.columns:
            keep.append(c)
        elif suffix:
            other = other.rename(columns={c: f"{c}{suffix}"})
            keep.append(f"{c}{suffix}")
    return base.merge(other[keep].drop_duplicates(on), on=on, how="left")


def build_interpretation(cfg: dict) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    paths = cfg["paths"]
    crs = cfg.get("map", {}).get("crs", "EPSG:3414")
    geom = gpd.read_file(paths["grid_geojson"])
    if geom.crs is None:
        geom = geom.set_crs(crs)
    geom = geom.to_crs(crs)
    if "cell_id" not in geom.columns:
        raise KeyError("grid_geojson must contain cell_id")
    geom = geom[["cell_id", "geometry"]].drop_duplicates("cell_id")

    gamma = read_csv_optional(paths.get("v10_gamma_ranking_csv", ""))
    v08v10 = read_csv_optional(paths.get("v08_v10_rank_comparison_csv", ""))
    overhead = read_csv_optional(paths.get("base_overhead_rank_comparison_csv", ""))
    fp = read_csv_optional(paths.get("old_false_positive_candidates_csv", ""))
    morph = read_csv_optional(paths.get("basic_morphology_csv", ""))
    umep = read_csv_optional(paths.get("v10_umep_features_csv", ""))
    ohgrid = read_csv_optional(paths.get("overhead_sensitivity_grid_csv", ""))

    df = pd.DataFrame({"cell_id": geom["cell_id"].astype(str).unique()})
    for d, suffix in [(gamma, "_gamma"), (v08v10, ""), (overhead, "_oh"), (morph, "_morph"), (umep, "_umep"), (ohgrid, "_ohgrid")]:
        if not d.empty:
            d = d.copy()
            d["cell_id"] = d["cell_id"].astype(str)
        df = merge_unique(df, d, suffix=suffix)

    # false-positive candidate membership from explicit list
    df["is_old_dsm_gap_fp_candidate"] = False
    if not fp.empty and "cell_id" in fp.columns:
        fp_cells = set(fp["cell_id"].astype(str))
        df["is_old_dsm_gap_fp_candidate"] = df["cell_id"].astype(str).isin(fp_cells)

    top_n = int(cfg.get("thresholds", {}).get("top_n", 20))
    dsm_gap_rank_min = float(cfg.get("thresholds", {}).get("dsm_gap_v10_rank_min", 21))
    dense_thr = float(cfg.get("thresholds", {}).get("dense_built_threshold", 0.85))

    # Find ranking columns robustly.
    v10_rank_col = first_present(df, ["rank_v10_hazard_score", "risk_rank_v10", "rank_v10", "rank"])
    base_rank_col = first_present(df, ["rank_base_v10_hazard_score", "rank_base_hazard_score", "rank_v10_hazard_score"])
    overhead_rank_col = first_present(df, ["rank_overhead_sens_hazard_score", "rank_overhead_hazard_score"])
    v08_rank_col = first_present(df, ["rank_v08_hazard_score", "hazard_rank_true_v08", "rank_proxy_v07_hazard_score"])

    if v10_rank_col:
        df["is_v10_top20"] = pd.to_numeric(df[v10_rank_col], errors="coerce") <= top_n
    elif "hazard_score" in df.columns:
        df["is_v10_top20"] = df["hazard_score"].rank(ascending=False, method="min") <= top_n
    else:
        df["is_v10_top20"] = False

    if base_rank_col:
        df["is_base_top20"] = pd.to_numeric(df[base_rank_col], errors="coerce") <= top_n
    else:
        df["is_base_top20"] = df["is_v10_top20"]

    if overhead_rank_col:
        df["is_overhead_top20"] = pd.to_numeric(df[overhead_rank_col], errors="coerce") <= top_n
    else:
        df["is_overhead_top20"] = False

    if v08_rank_col:
        df["is_v08_top20"] = pd.to_numeric(df[v08_rank_col], errors="coerce") <= top_n
    else:
        df["is_v08_top20"] = False

    # Dense and overhead columns.
    density_col = first_present(df, ["v10_building_density", "building_density", "building_pixel_fraction_v10"])
    if density_col:
        df["_density"] = pd.to_numeric(df[density_col], errors="coerce").fillna(0)
    else:
        df["_density"] = 0.0

    overhead_frac_col = first_present(df, ["overhead_fraction_total", "overhead_fraction_total_ohgrid", "overhead_fraction_total_oh"])
    if overhead_frac_col:
        df["_overhead_fraction"] = pd.to_numeric(df[overhead_frac_col], errors="coerce").fillna(0)
    else:
        df["_overhead_fraction"] = 0.0

    # manual special cells
    cells = cfg.get("final_hotspot_cells", {})
    confident = set(cells.get("confident_hotspot", []))
    overhead_validated = set(cells.get("overhead_confounded_validated", []))
    shaded_reference = set(cells.get("shaded_reference", []))
    dense_edge = set(cells.get("dense_built_edge_case", []))

    df["interpretation_class"] = "other"

    # Less important categories first, so important validated cells override.
    df.loc[df["is_v10_top20"], "interpretation_class"] = "v10_base_top_hazard"

    # DSM-gap corrected: explicitly flagged FP candidates that dropped outside v10 top20.
    if v10_rank_col:
        v10rank = pd.to_numeric(df[v10_rank_col], errors="coerce")
        df.loc[df["is_old_dsm_gap_fp_candidate"] & (v10rank >= dsm_gap_rank_min), "interpretation_class"] = "dsm_gap_corrected"
    else:
        df.loc[df["is_old_dsm_gap_fp_candidate"] & (~df["is_v10_top20"]), "interpretation_class"] = "dsm_gap_corrected"

    # Overhead-confounded: base top20 dropped under overhead sensitivity, or major overhead fraction in v10 top20.
    overhead_conf = (df["is_base_top20"] & (~df["is_overhead_top20"])) | (df["is_v10_top20"] & (df["_overhead_fraction"] >= cfg.get("thresholds", {}).get("overhead_major_threshold", 0.10)))
    df.loc[overhead_conf, "interpretation_class"] = "overhead_confounded"

    # Dense edge cases.
    df.loc[df["_density"] >= dense_thr, "interpretation_class"] = "dense_built_edge_case"

    # Manual validated overrides.
    df.loc[df["cell_id"].isin(overhead_validated), "interpretation_class"] = "overhead_confounded"
    df.loc[df["cell_id"].isin(shaded_reference), "interpretation_class"] = "shaded_reference"
    df.loc[df["cell_id"].isin(dense_edge), "interpretation_class"] = "dense_built_edge_case"
    df.loc[df["cell_id"].isin(confident), "interpretation_class"] = "confident_hotspot"

    df["interpretation_label"] = df["interpretation_class"].map(INTERPRETATION_LABELS).fillna(df["interpretation_class"])

    gdf = geom.merge(df, on="cell_id", how="left")
    gdf["interpretation_class"] = gdf["interpretation_class"].fillna("other")
    gdf["interpretation_label"] = gdf["interpretation_label"].fillna("Other cells")
    return gdf, df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/v10/v10_final_figures_config.v2.json")
    args = parser.parse_args()
    cfg = read_json(Path(args.config))
    out_dir = ensure_dir(Path(cfg["paths"]["output_dir"]))
    gdf, df = build_interpretation(cfg)

    table_path = out_dir / "v10_final_hotspot_interpretation_table.csv"
    map_path = out_dir / "v10_final_hotspot_interpretation_map.geojson"
    counts_path = out_dir / "v10_final_hotspot_interpretation_counts.csv"

    df.to_csv(table_path, index=False)
    gdf.to_file(map_path, driver="GeoJSON")
    counts = gdf["interpretation_class"].value_counts().rename_axis("interpretation_class").reset_index(name="n_cells")
    counts.to_csv(counts_path, index=False)

    print(f"[OK] interpretation table: {table_path}")
    print(f"[OK] interpretation map: {map_path}")
    print(f"[OK] counts: {counts_path}")
    print(counts.to_string(index=False))


if __name__ == "__main__":
    main()
