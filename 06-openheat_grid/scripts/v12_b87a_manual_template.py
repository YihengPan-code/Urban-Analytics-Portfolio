"""Create B8.7a manual QA template, instructions, and status table.

Inputs:
    B8.7 candidate table, optional B8.7a auto-scored candidate table, and
    optional manual review input declared in the B8.7a config.
Outputs:
    b87a_manual_review_template.csv, b87a_manual_review_instructions.md, and
    b87a_manual_review_status.csv.
Saved metrics:
    Template row count, manual input presence, reviewed-row count, manual
    decision counts, invalid/unknown decision count, and AUTO_ONLY versus
    manual-input mode. This is manual QA support only and creates no raster,
    QGIS/SOLWEIG, N300 execution manifest, AOI-wide prediction, B9, local WBGT,
    hazard/risk/exposure/vulnerability score, observed-truth claim, causal
    feature-importance claim, Tmrt-to-WBGT conversion, or System A/B coupling.
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
    VALID_MANUAL_DECISIONS,
    candidate_context,
    load_config,
    load_manual_review,
    manual_input_found,
    normalize_manual_decision,
    output_path,
    repo_path,
    write_csv,
    write_text,
)


@dataclass(frozen=True)
class ManualTemplateResult:
    """B8.7a manual template result."""

    status: str
    template_rows: int
    manual_input_found: bool
    reviewed_rows: int


TEMPLATE_COLUMNS = [
    "cell_id",
    "selected_priority_rank",
    "primary_role",
    "spatial_bin",
    "typology",
    "nearest_anchor_cell",
    "nearest_neutral_cell",
    "nearest_n150_distance_percentile",
    "manual_decision",
    "manual_reason",
    "manual_notes",
    "reviewer_initials",
    "review_date",
    "suggested_replacement_cell_id",
    "qa_focus_flags",
    "auto_recommended_action",
]


def fallback_focus(row: pd.Series) -> str:
    """Build a simple focus flag if auto scoring has not yet run."""
    flags: list[str] = []
    if str(row.get("typology", "")).lower() == "water":
        flags.append("pure_water_or_river_risk")
    if str(row.get("spatial_bin", "")) == "west_south":
        flags.append("west_south_review")
    if str(row.get("nearest_anchor_cell", "")) in {"TP_0037", "TP_0433"}:
        flags.append("anchor_shortfall_context")
    if str(row.get("nearest_neutral_cell", "")) in {"TP_0115", "TP_0492", "TP_0301", "TP_0326", "TP_0676"}:
        flags.append("neutral_diversity_context")
    pct = pd.to_numeric(pd.Series([row.get("nearest_n150_distance_percentile")]), errors="coerce").iloc[0]
    if pd.notna(pct) and float(pct) >= 0.90:
        flags.append("sparse_ood_risk")
    return "|".join(flags) if flags else "source_review_before_execution_precheck"


def template_frame(config: dict[str, Any]) -> pd.DataFrame:
    """Build an Excel-friendly one-row-per-candidate manual review template."""
    scored_path = output_path(config, "auto_qa_scored_candidates_path")
    if scored_path.exists():
        scored = pd.read_csv(scored_path, dtype={"cell_id": "string"}, low_memory=False)
    else:
        scored = candidate_context(config)
        scored["qa_focus_flags"] = scored.apply(fallback_focus, axis=1)
        scored["auto_recommended_action"] = "manual_review"
    manual = load_manual_review(config)
    manual_cols = [
        "cell_id",
        "manual_decision",
        "manual_reason",
        "manual_notes",
        "reviewer_initials",
        "review_date",
        "suggested_replacement_cell_id",
    ]
    if not manual.empty:
        keep_cols = [column for column in manual_cols if column in manual.columns]
        scored = scored.merge(manual.loc[:, keep_cols].drop_duplicates("cell_id"), on="cell_id", how="left", suffixes=("", "_manual"))
    for column in TEMPLATE_COLUMNS:
        if column not in scored.columns:
            scored[column] = ""
    scored["manual_decision"] = scored["manual_decision"].map(normalize_manual_decision).fillna("not_reviewed")
    if manual.empty:
        scored["manual_decision"] = "not_reviewed"
    out = scored.loc[:, TEMPLATE_COLUMNS].copy()
    out["manual_decision"] = out["manual_decision"].replace("", "not_reviewed")
    return out.sort_values("selected_priority_rank", key=lambda series: pd.to_numeric(series, errors="coerce")).reset_index(drop=True)


def instruction_text(config: dict[str, Any], manual_found: bool) -> str:
    """Return manual QA instructions for quick candidate review."""
    manual_path = str(config["manual_review_input_path"])
    return f"""# B8.7a N300 Manual QA Instructions

Manual input found: `{'yes' if manual_found else 'no'}`.

Use `b87a_manual_review_template.csv` as the review worksheet. If you choose
to provide manual decisions, save a CSV with the same columns at:

`{manual_path}`

Valid `manual_decision` values are: `keep`, `exclude`, `replace`,
`source_review`, `unsure`, and `not_reviewed`.

## Review Order

1. Focus first on water / river / pure surface candidates.
2. Then review `west_south`.
3. Then review TP_0037 / TP_0433 anchor-like candidates.
4. Then review neutral diversity candidates.
5. Then review `park_open_space` / commercial undercoverage and residential /
   transport overconcentration.

It is okay to review only obvious exclusions. Uncertain rows can stay as
`unsure` or `not_reviewed`; Codex will keep uncertain rows as REVIEW rather
than auto-excluding them.

## Guardrails

- Do not run QGIS.
- Do not run SOLWEIG.
- Do not use rasters.
- Use lightweight map/table inspection only if you choose.
- This worksheet is not B9, not AOI-wide prediction, not local WBGT, not a
  hazard/risk/exposure/vulnerability score, not observed truth, and not causal
  feature importance.
"""


def status_frame(config: dict[str, Any], template: pd.DataFrame) -> pd.DataFrame:
    """Build the manual review status table."""
    manual_found = manual_input_found(config)
    manual_path = repo_path(str(config["manual_review_input_path"]))
    manual = load_manual_review(config)
    reviewed = 0 if manual.empty else int(manual["manual_decision"].astype(str).isin(VALID_MANUAL_DECISIONS - {"not_reviewed"}).sum())
    decision_counts = manual["manual_decision"].astype(str).value_counts().to_dict() if not manual.empty else {}
    rows = [
        {
            "status_item": "manual_input_found",
            "value": "yes" if manual_found else "no",
            "status": "PASS" if manual_found else "WAITING",
            "evidence": manual_path.as_posix(),
        },
        {
            "status_item": "template_rows",
            "value": len(template),
            "status": "PASS",
            "evidence": "one row per B8.7 candidate",
        },
        {
            "status_item": "reviewed_rows",
            "value": reviewed,
            "status": "PASS" if reviewed else "WAITING",
            "evidence": "|".join(f"{key}={value}" for key, value in sorted(decision_counts.items())) if decision_counts else "manual input absent",
        },
        {
            "status_item": "auto_only_mode",
            "value": "no" if manual_found else "yes",
            "status": "WAITING" if not manual_found else "PASS",
            "evidence": "manual input missing; generated template and AUTO_ONLY draft" if not manual_found else "manual decisions available for patching",
        },
    ]
    out = pd.DataFrame(rows)
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def run(config_path: Path = DEFAULT_CONFIG) -> ManualTemplateResult:
    """Create the manual QA template and instructions."""
    config = load_config(config_path)
    template = template_frame(config)
    manual_found = manual_input_found(config)
    status = status_frame(config, template)
    write_csv(template, output_path(config, "manual_review_template_path"))
    write_text(instruction_text(config, manual_found), output_path(config, "manual_review_instructions_path"))
    write_csv(status, output_path(config, "manual_review_status_path"))
    reviewed_rows = int(status.loc[status["status_item"].eq("reviewed_rows"), "value"].iloc[0])
    return ManualTemplateResult(
        status="B87A_MANUAL_INPUT_FOUND" if manual_found else "B87A_WAITING_FOR_MANUAL_QA",
        template_rows=len(template),
        manual_input_found=manual_found,
        reviewed_rows=reviewed_rows,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.7a manual N300 QA template, instructions, and status CSV. "
            "No QGIS/SOLWEIG/raster/manifest/AOI/B9/WBGT/hazard/risk output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
