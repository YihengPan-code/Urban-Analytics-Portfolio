"""Rank B8.7a candidate replacement pool without creating execution artifacts.

Inputs:
    Candidate universe, current N150 compact cell sources, B8.7 candidates,
    B8.7a auto-scored candidates, and optional manual review input declared in
    the B8.7a config.
Outputs:
    b87a_auto_replacement_pool.csv.
Saved metrics:
    Replacement-pool row count, exclusions for current N150/current kept N300/
    manual-excluded cells, role-fit scores, spatial/anchor/neutral/sparse/
    typology improvement flags, and replacement rationale. This is a design QA
    aid only and creates no raster, QGIS/SOLWEIG, N300 execution manifest,
    AOI-wide prediction, B9, local WBGT, hazard/risk/exposure/vulnerability
    score, observed truth, causal feature importance, Tmrt-to-WBGT conversion,
    or System A/B coupling.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b87a_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    add_spatial_bin,
    as_bool,
    as_float,
    config_list,
    current_n150_cells,
    load_b87_candidates,
    load_candidate_universe,
    load_config,
    load_manual_review,
    nearest_by_features,
    output_path,
    pipe_join,
    safe_numeric_features,
    write_csv,
)


@dataclass(frozen=True)
class ReplacementPoolResult:
    """B8.7a replacement-pool result."""

    status: str
    replacement_candidates: int
    removed_candidate_count: int


ROLE_ORDER = [
    "typology_gap_fill",
    "spatial_gap_fill",
    "anchor_like_replication",
    "neutral_boundary_replication",
    "sparse_feature_space",
    "control_cell",
]


def manual_removed_cells(config: dict[str, Any]) -> set[str]:
    """Return manually excluded/replaced B8.7 candidate IDs."""
    manual = load_manual_review(config)
    if manual.empty:
        return set()
    return set(manual.loc[manual["manual_decision"].astype(str).isin({"exclude", "replace"}), "cell_id"].astype(str))


def metadata_invalid(row: pd.Series) -> bool:
    """Return whether compact universe metadata marks a replacement as invalid."""
    if str(row.get("geometry_available", "")).strip() and not as_bool(row.get("geometry_available")):
        return True
    for column in ["human_qa_exclusion_reason", "exclusion_reason"]:
        value = row.get(column, "")
        if value is not None and not pd.isna(value) and str(value).strip():
            return True
    if str(row.get("eligible", "")).strip() and not as_bool(row.get("eligible")):
        return True
    return False


def attach_nearest_context(config: dict[str, Any], pool: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """Attach nearest N150, anchor, and neutral context to replacement pool."""
    n150_ids = current_n150_cells(config)
    n150_ref = universe.loc[universe["cell_id"].astype(str).isin(n150_ids)].copy()
    features = safe_numeric_features(pd.concat([pool, n150_ref], ignore_index=True), min_non_null=20)
    out = pool.copy()
    nearest_n150 = nearest_by_features(out, n150_ref, features)
    if not nearest_n150.empty:
        out = out.merge(
            nearest_n150.rename(columns={"nearest_cell_id": "nearest_n150_cell", "feature_space_distance": "nearest_n150_distance"}),
            on="cell_id",
            how="left",
        )
        out["nearest_n150_distance_percentile"] = pd.to_numeric(out["nearest_n150_distance"], errors="coerce").rank(pct=True)
    else:
        out["nearest_n150_cell"] = ""
        out["nearest_n150_distance"] = ""
        out["nearest_n150_distance_percentile"] = ""
    anchor_ids = set(str(cell_id) for cell_id in config.get("preferred_anchor_minimum", {}).keys())
    neutral_ids = set(config_list(config, "neutral_underrepresented_cells", []))
    anchor_ref = universe.loc[universe["cell_id"].astype(str).isin(anchor_ids)].copy()
    neutral_ref = universe.loc[universe["cell_id"].astype(str).isin(neutral_ids)].copy()
    anchor = nearest_by_features(out, anchor_ref, features) if not anchor_ref.empty else pd.DataFrame()
    neutral = nearest_by_features(out, neutral_ref, features) if not neutral_ref.empty else pd.DataFrame()
    if not anchor.empty:
        out = out.merge(anchor.rename(columns={"nearest_cell_id": "nearest_anchor_cell", "feature_space_distance": "nearest_anchor_distance"}), on="cell_id", how="left")
    else:
        out["nearest_anchor_cell"] = ""
        out["nearest_anchor_distance"] = ""
    if not neutral.empty:
        out = out.merge(neutral.rename(columns={"nearest_cell_id": "nearest_neutral_cell", "feature_space_distance": "nearest_neutral_distance"}), on="cell_id", how="left")
    else:
        out["nearest_neutral_cell"] = ""
        out["nearest_neutral_distance"] = ""
    return out


def role_fit_scores(row: pd.Series, config: dict[str, Any]) -> dict[str, float]:
    """Compute conservative role-fit scores for one replacement candidate."""
    typology = str(row.get("typology_label", "")).strip()
    spatial_bin = str(row.get("spatial_bin", "")).strip()
    nearest_anchor = str(row.get("nearest_anchor_cell", "")).strip()
    nearest_neutral = str(row.get("nearest_neutral_cell", "")).strip()
    distance_pct = as_float(row.get("nearest_n150_distance_percentile"), 0.0)
    water_fraction = max(as_float(row.get("water_fraction"), 0.0), as_float(row.get("water_edge_contact_frac"), 0.0))
    invalid_water = typology == "water" or water_fraction >= float(config.get("high_water_fraction_threshold", 0.50))
    undercovered = set(config_list(config, "undercovered_typologies", ["park_open_space", "commercial"]))
    overconcentrated = set(config_list(config, "overconcentrated_typologies", ["residential", "transport"]))
    neutral_under = set(config_list(config, "neutral_underrepresented_cells", []))

    scores = {
        "typology_gap_fill": 20.0,
        "spatial_gap_fill": 15.0,
        "anchor_like_replication": 10.0,
        "neutral_boundary_replication": 10.0,
        "sparse_feature_space": 10.0,
        "control_cell": 20.0,
    }
    if typology in undercovered:
        scores["typology_gap_fill"] += 45.0
    if typology not in overconcentrated and not invalid_water:
        scores["typology_gap_fill"] += 20.0
    if spatial_bin == "west_south":
        scores["spatial_gap_fill"] += 60.0
    if nearest_anchor in {"TP_0037", "TP_0433"}:
        scores["anchor_like_replication"] += 65.0
    if nearest_neutral in neutral_under:
        scores["neutral_boundary_replication"] += 65.0
    if distance_pct >= float(config.get("sparse_p95_threshold", 0.95)):
        scores["sparse_feature_space"] += 65.0
    elif distance_pct >= float(config.get("sparse_p90_threshold", 0.90)):
        scores["sparse_feature_space"] += 45.0
    if not invalid_water and typology not in overconcentrated and 0.25 <= distance_pct <= 0.85:
        scores["control_cell"] += 35.0
    if invalid_water:
        scores = {key: value - 50.0 for key, value in scores.items()}
    return scores


def rationale(row: pd.Series, best_role: str, score_columns: dict[str, float], config: dict[str, Any]) -> str:
    """Build a compact replacement rationale with claim boundary."""
    reasons: list[str] = []
    if str(row.get("spatial_bin", "")) == "west_south":
        reasons.append("improves west_south support")
    if str(row.get("nearest_anchor_cell", "")) in {"TP_0037", "TP_0433"}:
        reasons.append(f"supports anchor shortfall {row.get('nearest_anchor_cell')}")
    if str(row.get("nearest_neutral_cell", "")) in set(config_list(config, "neutral_underrepresented_cells", [])):
        reasons.append(f"supports neutral diversity {row.get('nearest_neutral_cell')}")
    if str(row.get("typology_label", "")) in set(config_list(config, "undercovered_typologies", [])):
        reasons.append(f"adds undercovered typology {row.get('typology_label')}")
    if str(row.get("typology_label", "")) not in set(config_list(config, "overconcentrated_typologies", [])):
        reasons.append("does not add residential/transport concentration")
    if as_float(row.get("nearest_n150_distance_percentile"), 0.0) >= float(config.get("sparse_p90_threshold", 0.90)):
        reasons.append("retains sparse feature-space diagnostic value")
    if not reasons:
        reasons.append("safe compact metadata fallback")
    return f"{best_role}; {'; '.join(reasons)}; candidate design replacement only, not run-ready."


def build_replacement_pool(config: dict[str, Any]) -> pd.DataFrame:
    """Build a ranked safe replacement pool."""
    universe = add_spatial_bin(load_candidate_universe(config))
    b87 = load_b87_candidates(config)
    n150_ids = current_n150_cells(config)
    removed = manual_removed_cells(config)
    kept_n300 = set(b87.loc[~b87["cell_id"].astype(str).isin(removed), "cell_id"].astype(str))
    excluded_ids = n150_ids.union(kept_n300).union(removed)
    pool = universe.loc[~universe["cell_id"].astype(str).isin(excluded_ids)].copy()
    if not pool.empty:
        invalid_mask = pool.apply(metadata_invalid, axis=1)
        pool = pool.loc[~invalid_mask].copy()
    pool = attach_nearest_context(config, pool, universe)
    rows: list[dict[str, Any]] = []
    for _, row in pool.iterrows():
        scores = role_fit_scores(row, config)
        best_role = max(ROLE_ORDER, key=lambda role: scores[role])
        flags = []
        if str(row.get("typology_label", "")) == "water" or as_float(row.get("water_fraction"), 0.0) >= float(config.get("high_water_fraction_threshold", 0.50)):
            flags.append("water_review_before_use")
        if str(row.get("spatial_bin", "")) == "west_south":
            flags.append("west_south_improvement")
        if str(row.get("nearest_anchor_cell", "")) in {"TP_0037", "TP_0433"}:
            flags.append("anchor_shortfall_improvement")
        if str(row.get("nearest_neutral_cell", "")) in set(config_list(config, "neutral_underrepresented_cells", [])):
            flags.append("neutral_diversity_improvement")
        output = {
            "cell_id": row.get("cell_id", ""),
            "recommended_primary_role": best_role,
            "replacement_priority_score": round(float(scores[best_role]), 6),
            "spatial_bin": row.get("spatial_bin", ""),
            "typology": row.get("typology_label", ""),
            "nearest_anchor_cell": row.get("nearest_anchor_cell", ""),
            "nearest_neutral_cell": row.get("nearest_neutral_cell", ""),
            "nearest_n150_distance": row.get("nearest_n150_distance", ""),
            "nearest_n150_distance_percentile": row.get("nearest_n150_distance_percentile", ""),
            "water_fraction": row.get("water_fraction", ""),
            "pedestrian_shelter_fraction": row.get("pedestrian_shelter_fraction", ""),
            "overhead_fraction_total": row.get("overhead_fraction_total", ""),
            "qa_flags": pipe_join(flags),
            "replacement_rationale": rationale(row, best_role, scores, config),
            "sampling_boundary": "candidate_design_only_not_N300_run_ready",
            "claim_boundary": CLAIM_BOUNDARY,
        }
        for role in ROLE_ORDER:
            output[f"score_{role}"] = round(float(scores[role]), 6)
        rows.append(output)
    out = pd.DataFrame(rows)
    if out.empty:
        columns = [
            "cell_id",
            "recommended_primary_role",
            "replacement_priority_score",
            "spatial_bin",
            "typology",
            "nearest_anchor_cell",
            "nearest_neutral_cell",
            "nearest_n150_distance",
            "nearest_n150_distance_percentile",
            "qa_flags",
            "replacement_rationale",
            "sampling_boundary",
            "claim_boundary",
        ] + [f"score_{role}" for role in ROLE_ORDER]
        return pd.DataFrame(columns=columns)
    return out.sort_values(["replacement_priority_score", "cell_id"], ascending=[False, True]).reset_index(drop=True)


def run(config_path: Path = DEFAULT_CONFIG) -> ReplacementPoolResult:
    """Run replacement-pool ranking."""
    config = load_config(config_path)
    pool = build_replacement_pool(config)
    write_csv(pool, output_path(config, "auto_replacement_pool_path"))
    return ReplacementPoolResult(
        status="B87A_REPLACEMENT_POOL_READY",
        replacement_candidates=len(pool),
        removed_candidate_count=len(manual_removed_cells(config)),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Rank B8.7a N300 replacement candidates from compact table inputs. "
            "No QGIS/SOLWEIG/raster/manifest/AOI/B9/WBGT/hazard/risk output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
