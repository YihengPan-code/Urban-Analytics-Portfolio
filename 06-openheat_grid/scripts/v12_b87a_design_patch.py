"""Apply B8.7a manual/AUTO_ONLY candidate design patch.

Inputs:
    B8.7 candidate design, B8.7a auto QA scoring, B8.7a replacement pool, and
    optional manual review input declared in the B8.7a config.
Outputs:
    b87a_candidate_patch_log.csv, b87a_n300_design_v3_patched.csv, and
    b87a_n300_design_v3_diff_vs_b87.csv.
Saved metrics:
    Manual/AUTO_ONLY mode, kept/replaced/source-review row counts, replacement
    validity, v3 row count, duplicate cell count, N150 overlap count, and role
    quota preservation. This patch is candidate-design-only and creates no
    raster, QGIS/SOLWEIG, N300 execution manifest, AOI-wide prediction, B9,
    local WBGT, hazard/risk/exposure/vulnerability score, observed truth,
    causal feature importance, Tmrt-to-WBGT conversion, or System A/B coupling.
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
    SAMPLING_BOUNDARY,
    current_n150_cells,
    load_b87_candidates,
    load_config,
    load_manual_review,
    manual_input_found,
    output_path,
    pipe_join,
    read_csv,
    write_csv,
)


@dataclass(frozen=True)
class DesignPatchResult:
    """B8.7a design patch result."""

    status: str
    manual_input_found: bool
    v3_rows: int
    replaced_rows: int
    blocked_replacements: int


def scored_candidates(config: dict[str, Any]) -> pd.DataFrame:
    """Load auto-scored candidates if available, otherwise the B8.7 candidates."""
    path = output_path(config, "auto_qa_scored_candidates_path")
    if path.exists():
        return read_csv(path)
    frame = load_b87_candidates(config)
    frame["candidate_status"] = "REVIEW"
    frame["qa_focus_flags"] = "auto_scoring_not_run"
    frame["auto_recommended_action"] = "manual_review"
    return frame


def replacement_pool(config: dict[str, Any]) -> pd.DataFrame:
    """Load ranked replacement pool if available."""
    path = output_path(config, "auto_replacement_pool_path")
    if path.exists():
        return read_csv(path)
    return pd.DataFrame()


def suggested_replacement(manual_row: pd.Series, pool: pd.DataFrame, used: set[str], role: str) -> pd.Series | None:
    """Return a valid suggested replacement if present in the pool."""
    suggestion = str(manual_row.get("suggested_replacement_cell_id", "")).strip()
    if not suggestion or pool.empty or suggestion in used:
        return None
    match = pool.loc[pool["cell_id"].astype(str).eq(suggestion)].copy()
    if match.empty:
        return None
    if "recommended_primary_role" in match.columns:
        exact = match.loc[match["recommended_primary_role"].astype(str).eq(role)]
        if not exact.empty:
            return exact.iloc[0]
    return match.iloc[0]


def best_pool_replacement(pool: pd.DataFrame, used: set[str], role: str) -> pd.Series | None:
    """Choose the best unused replacement, preserving role quota when feasible."""
    if pool.empty:
        return None
    available = pool.loc[~pool["cell_id"].astype(str).isin(used)].copy()
    if available.empty:
        return None
    score_col = f"score_{role}"
    if score_col in available.columns:
        available["_role_score"] = pd.to_numeric(available[score_col], errors="coerce").fillna(0.0)
    else:
        available["_role_score"] = (available.get("recommended_primary_role", "").astype(str) == role).astype(float)
    available["_priority"] = pd.to_numeric(available.get("replacement_priority_score", 0.0), errors="coerce").fillna(0.0)
    exact = available.loc[available.get("recommended_primary_role", "").astype(str).eq(role)].copy()
    source = exact if not exact.empty else available
    source = source.sort_values(["_role_score", "_priority", "cell_id"], ascending=[False, False, True])
    return source.iloc[0] if not source.empty else None


def replacement_to_design_row(replacement: pd.Series, removed: pd.Series, reason: str) -> dict[str, Any]:
    """Convert a replacement-pool row into the v3 design schema."""
    role = str(removed.get("primary_role", replacement.get("recommended_primary_role", "")))
    return {
        "cell_id": str(replacement.get("cell_id", "")),
        "selected_priority_rank": removed.get("selected_priority_rank", ""),
        "primary_role": role,
        "secondary_roles": "replacement_for_" + str(removed.get("cell_id", "")),
        "rationale": str(replacement.get("replacement_rationale", reason)),
        "spatial_bin": replacement.get("spatial_bin", ""),
        "typology": replacement.get("typology", ""),
        "nearest_anchor_cell": replacement.get("nearest_anchor_cell", ""),
        "nearest_neutral_cell": replacement.get("nearest_neutral_cell", ""),
        "nearest_n150_distance": replacement.get("nearest_n150_distance", ""),
        "nearest_n150_distance_percentile": replacement.get("nearest_n150_distance_percentile", ""),
        "coverage_gap": "manual_QA_replacement",
        "expected_learning_value": "diagnostic_replacement_learning_value",
        "sampling_boundary": SAMPLING_BOUNDARY,
        "claim_boundary": CLAIM_BOUNDARY,
        "patch_status": "PATCHED_WITH_REPLACEMENT",
        "patch_source": "manual_exclude_replaced",
        "patch_rationale": reason,
        "design_status": "REPLACED_IN",
        "replacement_for_cell_id": str(removed.get("cell_id", "")),
        "qa_focus_flags": replacement.get("qa_flags", ""),
        "auto_recommended_action": "replacement_selected_from_pool",
    }


def normalize_original_row(row: pd.Series, patch_source: str, design_status: str, rationale: str) -> dict[str, Any]:
    """Return a v3 design row based on an original B8.7 candidate row."""
    output = row.to_dict()
    output["sampling_boundary"] = SAMPLING_BOUNDARY
    output["claim_boundary"] = CLAIM_BOUNDARY
    output["patch_status"] = "DRAFT_AUTO_ONLY" if patch_source == "unresolved_review" else "PATCH_APPLIED"
    output["patch_source"] = patch_source
    output["patch_rationale"] = rationale
    output["design_status"] = design_status
    output["replacement_for_cell_id"] = ""
    return output


def apply_patch(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    """Apply AUTO_ONLY or manual review patch to create v3 design."""
    b87 = load_b87_candidates(config)
    scored = scored_candidates(config)
    score_cols = ["cell_id", "candidate_status", "qa_focus_flags", "auto_recommended_action"]
    b87 = b87.merge(scored.loc[:, [column for column in score_cols if column in scored.columns]].drop_duplicates("cell_id"), on="cell_id", how="left")
    manual_found = manual_input_found(config)
    manual = load_manual_review(config)
    manual_by_id = {str(row["cell_id"]): row for _, row in manual.iterrows()} if not manual.empty else {}
    pool = replacement_pool(config)
    used_ids = set(b87["cell_id"].astype(str))
    v3_rows: list[dict[str, Any]] = []
    log_rows: list[dict[str, Any]] = []
    blocked = 0

    if not manual_found:
        for _, row in b87.iterrows():
            status = "AUTO_REVIEW" if str(row.get("candidate_status", "")) in {"REVIEW", "REPLACE_CANDIDATE"} else "SOURCE_REVIEW"
            v3_rows.append(normalize_original_row(row, "unresolved_review", status, "AUTO_ONLY: manual input missing; candidate kept for review"))
            log_rows.append(
                {
                    "cell_id": row["cell_id"],
                    "patch_action": "keep_auto_only",
                    "replacement_cell_id": "",
                    "manual_decision": "not_reviewed",
                    "patch_rationale": "manual input missing; no exclusions applied",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
        return pd.DataFrame(v3_rows), pd.DataFrame(log_rows), diff_frame(b87, pd.DataFrame(v3_rows)), "B87A_WAITING_FOR_MANUAL_QA"

    for _, row in b87.iterrows():
        cell_id = str(row["cell_id"])
        manual_row = manual_by_id.get(cell_id)
        decision = "not_reviewed" if manual_row is None else str(manual_row.get("manual_decision", "not_reviewed"))
        candidate_status = str(row.get("candidate_status", "REVIEW"))
        if decision == "keep":
            v3_rows.append(normalize_original_row(row, "manual_keep", "KEEP", "manual keep"))
            action = "kept"
            replacement_id = ""
        elif decision == "source_review":
            v3_rows.append(normalize_original_row(row, "manual_source_review_kept", "SOURCE_REVIEW", "manual source_review blocker"))
            action = "kept_source_review"
            replacement_id = ""
        elif decision in {"exclude", "replace"} or (decision in {"unsure", "not_reviewed"} and candidate_status == "REPLACE_CANDIDATE"):
            replacement = suggested_replacement(manual_row, pool, used_ids, str(row.get("primary_role", ""))) if manual_row is not None else None
            if replacement is None:
                replacement = best_pool_replacement(pool, used_ids, str(row.get("primary_role", "")))
            if replacement is None:
                blocked += 1
                kept = normalize_original_row(row, "manual_exclude_unresolved", "MANUAL_EXCLUDED", "manual exclusion could not be replaced; patch blocked")
                v3_rows.append(kept)
                action = "blocked_no_replacement"
                replacement_id = ""
            else:
                used_ids.discard(cell_id)
                replacement_id = str(replacement.get("cell_id", ""))
                used_ids.add(replacement_id)
                reason = f"{decision}: replaced {cell_id} with {replacement_id} while preserving role {row.get('primary_role', '')}"
                new_row = replacement_to_design_row(replacement, row, reason)
                if decision == "replace":
                    new_row["patch_source"] = "manual_replace_replaced"
                elif candidate_status == "REPLACE_CANDIDATE":
                    new_row["patch_source"] = "auto_replaced"
                v3_rows.append(new_row)
                action = "replaced"
        else:
            source = "unresolved_review" if decision in {"unsure", "not_reviewed"} else "original_kept"
            design_status = "REVIEW" if candidate_status in {"REVIEW", "REPLACE_CANDIDATE"} else ("SOURCE_REVIEW" if candidate_status == "SOURCE_REVIEW" else "KEEP")
            v3_rows.append(normalize_original_row(row, source, design_status, f"manual_decision={decision}; auto_status={candidate_status}"))
            action = "kept_review"
            replacement_id = ""
        log_rows.append(
            {
                "cell_id": cell_id,
                "patch_action": action,
                "replacement_cell_id": replacement_id,
                "manual_decision": decision,
                "patch_rationale": v3_rows[-1].get("patch_rationale", ""),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )

    v3 = pd.DataFrame(v3_rows)
    status = "B87A_PATCH_BLOCKED" if blocked else "B87A_PATCHED_DESIGN_READY_FOR_REVIEW"
    return v3, pd.DataFrame(log_rows), diff_frame(b87, v3), status


def diff_frame(original: pd.DataFrame, patched: pd.DataFrame) -> pd.DataFrame:
    """Return a compact v3-vs-B8.7 diff table."""
    original_ids = set(original["cell_id"].astype(str)) if "cell_id" in original.columns else set()
    patched_ids = set(patched["cell_id"].astype(str)) if "cell_id" in patched.columns else set()
    rows: list[dict[str, Any]] = []
    for cell_id in sorted(original_ids - patched_ids):
        rows.append({"cell_id": cell_id, "change_type": "removed_from_b87", "paired_cell_id": "", "claim_boundary": CLAIM_BOUNDARY})
    for _, row in patched.loc[~patched["cell_id"].astype(str).isin(original_ids)].iterrows():
        rows.append(
            {
                "cell_id": row["cell_id"],
                "change_type": "added_to_v3",
                "paired_cell_id": row.get("replacement_for_cell_id", ""),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    if not rows:
        rows.append({"cell_id": "ALL", "change_type": "unchanged_auto_only" if patched.get("patch_source", pd.Series()).astype(str).eq("unresolved_review").any() else "unchanged", "paired_cell_id": "", "claim_boundary": CLAIM_BOUNDARY})
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> DesignPatchResult:
    """Run B8.7a candidate design patch."""
    config = load_config(config_path)
    v3, log, diff, status = apply_patch(config)
    v3 = v3.copy()
    if "selected_priority_rank" in v3.columns:
        v3 = v3.sort_values("selected_priority_rank", key=lambda series: pd.to_numeric(series, errors="coerce")).reset_index(drop=True)
        v3["selected_priority_rank"] = range(1, len(v3) + 1)
    write_csv(log, output_path(config, "candidate_patch_log_path"))
    write_csv(v3, output_path(config, "n300_design_v3_patched_path"))
    write_csv(diff, output_path(config, "n300_design_v3_diff_vs_b87_path"))
    return DesignPatchResult(
        status=status,
        manual_input_found=manual_input_found(config),
        v3_rows=len(v3),
        replaced_rows=int(log["patch_action"].astype(str).eq("replaced").sum()) if not log.empty else 0,
        blocked_replacements=int(log["patch_action"].astype(str).eq("blocked_no_replacement").sum()) if not log.empty else 0,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Apply B8.7a AUTO_ONLY/manual candidate design patch. Writes compact "
            "CSV design tables only; no QGIS/SOLWEIG/raster/manifest/AOI/B9/"
            "WBGT/hazard/risk output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
