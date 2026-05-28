"""Score B8.7a N300 candidates for manual QA reduction.

Inputs:
    B8.7 candidate design, B8.7 manual checklist/audits, B8.6g compact feature
    table, candidate universe, and optional manual review input declared in
    configs/v12/systemb_b87a_n300_design_qa_patch.yaml.
Outputs:
    b87a_auto_qa_scored_candidates.csv, b87a_auto_exclusion_candidates.csv,
    and b87a_water_pure_river_review_queue.csv under the B8.7a output folder.
Saved metrics:
    Candidate-level water/pure-river risk, outside-pedestrian-relevance review
    flags, west_south review flags, typology concentration context, anchor and
    neutral diversity context, sparse/OOD flags, connected-shade source-missing
    flags, feature-coverage missing flags, and candidate_status. The scoring is
    a candidate-design QA aid only and creates no raster, QGIS/SOLWEIG, N300
    execution manifest, AOI-wide prediction, B9, local WBGT, hazard/risk/
    exposure/vulnerability score, observed-truth, causal feature-importance,
    Tmrt-to-WBGT conversion, or System A/B coupling output.
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
    as_bool,
    as_float,
    candidate_context,
    config_list,
    load_config,
    load_manual_review,
    output_path,
    pipe_join,
    read_csv,
    write_csv,
)


@dataclass(frozen=True)
class AutoQAScoringResult:
    """B8.7a auto QA scoring result."""

    status: str
    scored_candidates: int
    review_candidates: int
    auto_exclusion_candidates: int
    water_review_queue_count: int


def contains_water_label(row: pd.Series) -> bool:
    """Return whether typology or land-use text looks water-like."""
    fields = [
        row.get("typology", ""),
        row.get("typology_label", ""),
        row.get("land_use_hint", ""),
        row.get("land_use_raw", ""),
    ]
    text = " ".join(str(value).lower() for value in fields if value is not None)
    return any(token in text for token in ["water", "river", "canal", "reservoir", "pond"])


def high_water_proxy(row: pd.Series, threshold: float) -> bool:
    """Return whether available compact water proxies are high."""
    candidates = [
        as_float(row.get("water_fraction"), 0.0),
        as_float(row.get("dynamic_world_water_fraction"), 0.0),
        as_float(row.get("water_edge_contact_frac"), 0.0),
    ]
    return any(value >= threshold for value in candidates)


def low_pedestrian_proxy(row: pd.Series, threshold: float) -> bool:
    """Return whether pedestrian-shade or hardscape relevance proxies are low."""
    ped = max(
        as_float(row.get("ped_access_shade_frac"), 0.0),
        as_float(row.get("ped_access_shade_frac_proxy"), 0.0),
        as_float(row.get("pedestrian_shelter_fraction"), 0.0),
    )
    hardscape = max(as_float(row.get("hardscape_edge_contact_frac"), 0.0), as_float(row.get("road_fraction"), 0.0))
    built = as_float(row.get("built_up_fraction"), 0.0)
    return ped <= threshold and hardscape <= 0.05 and built <= 0.25


def hard_invalid_metadata(row: pd.Series) -> bool:
    """Return whether compact metadata says the candidate is clearly unusable."""
    geometry_available = row.get("geometry_available", True)
    if str(geometry_available).strip() != "" and not as_bool(geometry_available):
        return True
    for column in ["human_qa_exclusion_reason", "exclusion_reason"]:
        value = row.get(column, "")
        if value is not None and not pd.isna(value) and str(value).strip():
            return True
    eligible = row.get("eligible", True)
    if str(eligible).strip() != "" and not as_bool(eligible):
        return True
    return False


def connected_shade_missing(config: dict[str, Any]) -> bool:
    """Return whether the B8.7 feature coverage audit records missing shade-corridor source."""
    coverage = read_csv(config["b87_feature_coverage_path"])
    if "feature_family" not in coverage.columns:
        return False
    mask = coverage["feature_family"].astype(str).str.contains("connected shade corridor", case=False, na=False)
    if not mask.any():
        return False
    rows = coverage.loc[mask].astype(str)
    text = " ".join(str(item) for item in rows.to_numpy().ravel()).lower()
    return "not_available" in text or "requires" in text


def score_row(row: pd.Series, config: dict[str, Any], connected_missing: bool, manual_decision: str) -> dict[str, Any]:
    """Score one candidate row for QA flags and candidate status."""
    typology = str(row.get("typology", "")).strip()
    water_typologies = set(config_list(config, "water_review_typologies", ["water"]))
    park_typologies = set(config_list(config, "park_review_typologies", ["park_open_space"]))
    over_typologies = set(config_list(config, "overconcentrated_typologies", ["residential", "transport"]))
    under_typologies = set(config_list(config, "undercovered_typologies", ["park_open_space", "commercial"]))
    neutral_under = set(config_list(config, "neutral_underrepresented_cells", []))
    p90 = float(config.get("sparse_p90_threshold", 0.90))
    p95 = float(config.get("sparse_p95_threshold", 0.95))
    water_threshold = float(config.get("high_water_fraction_threshold", 0.50))
    ped_threshold = float(config.get("low_pedestrian_shade_proxy_threshold", 0.01))

    water_risk = typology in water_typologies or contains_water_label(row) or high_water_proxy(row, water_threshold)
    outside_ped = (typology in water_typologies.union(park_typologies).union({"other"}) or water_risk) and low_pedestrian_proxy(row, ped_threshold)
    west_south = str(row.get("spatial_bin", "")) == "west_south"
    concentration = typology in over_typologies
    undercoverage_context = typology in under_typologies
    anchor_shortfall = str(row.get("nearest_anchor_cell", "")) in {"TP_0037", "TP_0433"}
    neutral_context = str(row.get("nearest_neutral_cell", "")) in neutral_under
    distance_pct = as_float(row.get("nearest_n150_distance_percentile"), 0.0)
    sparse_flag = "p95_or_higher" if distance_pct >= p95 else ("p90_or_higher" if distance_pct >= p90 else "")
    feature_missing = str(row.get("feature_version", "")).strip() == ""
    hard_invalid = hard_invalid_metadata(row)

    flags = []
    if water_risk:
        flags.append("pure_water_or_river_risk")
    if outside_ped:
        flags.append("outside_pedestrian_relevance_risk")
    if west_south:
        flags.append("west_south_review")
    if concentration:
        flags.append("residential_transport_concentration")
    if undercoverage_context:
        flags.append("park_commercial_undercoverage_context")
    if anchor_shortfall:
        flags.append("anchor_shortfall_context")
    if neutral_context:
        flags.append("neutral_diversity_context")
    if sparse_flag:
        flags.append(f"sparse_ood_risk_{sparse_flag}")
    if connected_missing:
        flags.append("connected_shade_corridor_source_missing")
    if feature_missing:
        flags.append("feature_coverage_missing")
    if hard_invalid:
        flags.append("hard_invalid_metadata")

    if hard_invalid:
        status = "REPLACE_CANDIDATE"
        action = "replace_candidate_due_to_hard_metadata"
    elif any(flag in flags for flag in [
        "pure_water_or_river_risk",
        "outside_pedestrian_relevance_risk",
        "west_south_review",
        "residential_transport_concentration",
        "park_commercial_undercoverage_context",
        "anchor_shortfall_context",
        "neutral_diversity_context",
    ]) or sparse_flag:
        status = "REVIEW"
        action = "manual_review"
    elif connected_missing or feature_missing:
        status = "SOURCE_REVIEW"
        action = "source_review_before_execution_precheck"
    else:
        status = "PASS"
        action = "keep"

    if manual_decision in {"exclude", "replace"}:
        action = "manual_replacement_required"

    return {
        "pure_water_or_river_risk": water_risk,
        "outside_pedestrian_relevance_risk": outside_ped,
        "west_south_review": west_south,
        "residential_transport_concentration": concentration,
        "park_commercial_undercoverage_context": undercoverage_context,
        "anchor_shortfall_context": anchor_shortfall,
        "neutral_diversity_context": neutral_context,
        "sparse_ood_risk": sparse_flag or "below_p90",
        "connected_shade_corridor_source_missing": connected_missing,
        "feature_coverage_missing": feature_missing,
        "hard_invalid_metadata": hard_invalid,
        "qa_focus_flags": pipe_join(flags),
        "candidate_status": status,
        "auto_recommended_action": action,
    }


def score_candidates(config: dict[str, Any]) -> pd.DataFrame:
    """Return candidate-level B8.7a auto QA scoring."""
    candidates = candidate_context(config)
    manual = load_manual_review(config)
    manual_map = dict(zip(manual["cell_id"].astype(str), manual["manual_decision"].astype(str))) if not manual.empty else {}
    connected_missing = connected_shade_missing(config)
    rows: list[dict[str, Any]] = []
    for _, row in candidates.iterrows():
        cell_id = str(row["cell_id"])
        manual_decision = manual_map.get(cell_id, "not_reviewed")
        scored = score_row(row, config, connected_missing, manual_decision)
        output = {
            "cell_id": cell_id,
            "selected_priority_rank": row.get("selected_priority_rank", ""),
            "primary_role": row.get("primary_role", ""),
            "spatial_bin": row.get("spatial_bin", ""),
            "typology": row.get("typology", ""),
            "nearest_anchor_cell": row.get("nearest_anchor_cell", ""),
            "nearest_neutral_cell": row.get("nearest_neutral_cell", ""),
            "nearest_n150_distance_percentile": row.get("nearest_n150_distance_percentile", ""),
            "water_fraction": row.get("water_fraction", ""),
            "dynamic_world_water_fraction": row.get("dynamic_world_water_fraction", ""),
            "water_edge_contact_frac": row.get("water_edge_contact_frac", ""),
            "ped_access_shade_frac_proxy": row.get("ped_access_shade_frac_proxy", ""),
            "pedestrian_shelter_fraction": row.get("pedestrian_shelter_fraction", ""),
            "hardscape_edge_contact_frac": row.get("hardscape_edge_contact_frac", ""),
            "road_fraction": row.get("road_fraction", ""),
            "land_use_hint": row.get("land_use_hint", ""),
            "land_use_raw": row.get("land_use_raw", ""),
            "manual_decision": manual_decision,
            **scored,
            "sampling_boundary": "candidate_design_only_not_N300_run_ready",
            "claim_boundary": CLAIM_BOUNDARY,
        }
        rows.append(output)
    return pd.DataFrame(rows)


def water_review_queue(scored: pd.DataFrame) -> pd.DataFrame:
    """Build the water/pure-river review queue for quick manual glances."""
    if scored.empty:
        return pd.DataFrame()
    mask = (
        scored["pure_water_or_river_risk"].astype(bool)
        | scored["outside_pedestrian_relevance_risk"].astype(bool)
        | scored["qa_focus_flags"].astype(str).str.contains("pure_water|outside_pedestrian", case=False, na=False)
    )
    queue = scored.loc[mask].copy()
    if queue.empty:
        return pd.DataFrame(
            columns=[
                "cell_id",
                "typology",
                "water_fraction",
                "dynamic_world_water_fraction",
                "water_edge_contact_frac",
                "reason_for_review",
                "auto_recommended_action",
                "manual_decision",
                "replacement_required",
                "claim_boundary",
            ]
        )
    queue["reason_for_review"] = queue["qa_focus_flags"]
    queue["replacement_required"] = queue["manual_decision"].astype(str).isin({"exclude", "replace"}).map({True: "yes", False: "manual_review_first"})
    columns = [
        "cell_id",
        "typology",
        "water_fraction",
        "dynamic_world_water_fraction",
        "water_edge_contact_frac",
        "ped_access_shade_frac_proxy",
        "pedestrian_shelter_fraction",
        "land_use_hint",
        "land_use_raw",
        "reason_for_review",
        "auto_recommended_action",
        "manual_decision",
        "replacement_required",
        "claim_boundary",
    ]
    return queue.loc[:, [column for column in columns if column in queue.columns]].copy()


def run(config_path: Path = DEFAULT_CONFIG) -> AutoQAScoringResult:
    """Run B8.7a auto QA scoring."""
    config = load_config(config_path)
    scored = score_candidates(config)
    exclusions = scored.loc[scored["candidate_status"].astype(str).eq("REPLACE_CANDIDATE")].copy()
    water_queue = water_review_queue(scored)
    write_csv(scored, output_path(config, "auto_qa_scored_candidates_path"))
    write_csv(exclusions, output_path(config, "auto_exclusion_candidates_path"))
    write_csv(water_queue, output_path(config, "water_pure_river_review_queue_path"))
    return AutoQAScoringResult(
        status="B87A_AUTO_QA_SCORED",
        scored_candidates=len(scored),
        review_candidates=int(scored["candidate_status"].astype(str).isin({"REVIEW", "REPLACE_CANDIDATE", "SOURCE_REVIEW"}).sum()),
        auto_exclusion_candidates=len(exclusions),
        water_review_queue_count=len(water_queue),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Score B8.7a N300 candidates for manual QA reduction. Writes compact "
            "CSV scoring and water-review queue outputs only; no raster/QGIS/"
            "SOLWEIG/manifest/AOI/B9/WBGT/hazard/risk output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
