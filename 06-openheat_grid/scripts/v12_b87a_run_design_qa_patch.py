"""Run the full B8.7a N300 design-QA patch suite.

Inputs:
    configs/v12/systemb_b87a_n300_design_qa_patch.yaml and all compact inputs
    declared there.
Outputs:
    B8.7a input inventory, manual QA template/instructions/status, auto QA
    scoring, water review queue, replacement pool, v3 patched design/diff/log,
    after-patch audits, freeze readiness matrix, next-lane matrix, future
    prompts, report, status, and Chinese documentation.
Saved metrics:
    Manual input presence, water/pure-river review queue count, replacement
    candidate count, v3 row count, duplicate count, N150 overlap count, role/
    spatial/typology/anchor/neutral/sparse/control/feature coverage status,
    source-review blocker headline, freeze readiness, and next-lane
    recommendation. This suite creates no raster, QGIS/SOLWEIG, N300 execution
    manifest, local runner, AOI-wide prediction, B9, local WBGT, hazard/risk/
    exposure/vulnerability score, observed-truth, causal feature-importance,
    Tmrt-to-WBGT conversion, or System A/B coupling output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b87a_auto_qa_scoring import run as run_auto_qa
from v12_b87a_candidate_replacement import run as run_replacement_pool
from v12_b87a_design_patch import run as run_design_patch
from v12_b87a_input_inventory import DEFAULT_CONFIG
from v12_b87a_input_inventory import run as run_input_inventory
from v12_b87a_manual_template import run as run_manual_template
from v12_b87a_patch_audit import PatchAuditResult
from v12_b87a_patch_audit import run as run_patch_audit


@dataclass(frozen=True)
class B87ARunResult:
    """Full B8.7a run result."""

    status: str
    manual_input_found: bool
    water_queue_count: int
    auto_replacement_candidates: int
    v3_rows: int
    n150_overlap_count: int
    duplicate_cell_count: int
    role_headline: str
    spatial_typology_anchor_neutral_headline: str
    source_review_blocker_headline: str
    next_lane_recommendation: str


def run(config_path: Path = DEFAULT_CONFIG) -> B87ARunResult:
    """Run the complete B8.7a design-QA patch suite."""
    inventory = run_input_inventory(config_path)
    print(inventory)
    if inventory.status == "B87A_BLOCKED_INPUT":
        raise RuntimeError(f"B8.7a blocked by input inventory: {inventory}")
    auto_qa = run_auto_qa(config_path)
    print(auto_qa)
    manual = run_manual_template(config_path)
    print(manual)
    replacement = run_replacement_pool(config_path)
    print(replacement)
    patch = run_design_patch(config_path)
    print(patch)
    audit: PatchAuditResult = run_patch_audit(config_path)
    print(audit)
    return B87ARunResult(
        status=audit.status,
        manual_input_found=audit.manual_input_found,
        water_queue_count=audit.water_queue_count,
        auto_replacement_candidates=audit.auto_replacement_candidates,
        v3_rows=audit.v3_rows,
        n150_overlap_count=audit.n150_overlap_count,
        duplicate_cell_count=audit.duplicate_cell_count,
        role_headline=audit.role_headline,
        spatial_typology_anchor_neutral_headline=audit.spatial_typology_anchor_neutral_headline,
        source_review_blocker_headline=audit.source_review_blocker_headline,
        next_lane_recommendation=audit.next_lane_recommendation,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Run B8.7a N300 manual-QA reducer and design patch package. "
            "No raster/QGIS/SOLWEIG/manifest/local runner/AOI/B9/WBGT/hazard/"
            "risk/exposure/vulnerability output is created."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
