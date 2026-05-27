"""Run the full B8.7-N300-PRE and B8.6g3 source-review precheck suite.

Inputs:
    configs/v12/systemb_b87_n300_pre.yaml and all compact inputs declared in
    that config.
Outputs:
    All B8.7 compact input inventories, N300 design audits, feature coverage
    audits, true-vector source reviews, manual QA package, decision matrices,
    future prompts, report, status, and Chinese documentation.
Saved metrics:
    Input/schema readiness, N300 row and overlap checks, role/spatial/
    typology/anchor/neutral/sparse/control balance, feature-family coverage,
    true-vector source availability, connected shade corridor status, manual QA
    readiness, AOI/B9 boundary status, and freeze decision. This suite performs
    no SOLWEIG or QGIS execution, no raster I/O, no N300 execution manifest, no
    AOI-wide prediction, no B9 output, no local WBGT, no hazard/risk/exposure/
    vulnerability score, no observed-truth claim, no causal feature-importance
    claim, no Tmrt-to-WBGT conversion, and no System A/B coupling.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b87_candidate_qa_package import run as run_candidate_qa
from v12_b87_feature_schema_audit import run as run_feature_schema_audit
from v12_b87_input_inventory import DEFAULT_CONFIG, InputInventoryResult, load_config
from v12_b87_input_inventory import run as run_input_inventory
from v12_b87_n300_design_audit import run as run_n300_design_audit
from v12_b87_precheck_decision import PrecheckDecisionResult
from v12_b87_precheck_decision import run as run_precheck_decision
from v12_b87_source_availability_review import run as run_source_availability_review


@dataclass(frozen=True)
class B87RunResult:
    """Full B8.7 run result."""

    status: str
    candidate_count: int
    overlap_with_n150: int
    connected_shade_status: str
    recommended_next_lane: str


def blocked_result(inventory: InputInventoryResult) -> B87RunResult:
    """Return a blocked run result."""
    return B87RunResult(
        status="B87_BLOCKED_INPUT",
        candidate_count=0,
        overlap_with_n150=0,
        connected_shade_status="not_reviewed_due_to_blocked_input",
        recommended_next_lane=f"repair compact inputs; missing={inventory.missing_inputs}; schema_errors={inventory.schema_errors}",
    )


def run(config_path: Path = DEFAULT_CONFIG) -> B87RunResult:
    """Run the complete B8.7 design/source review precheck suite."""
    load_config(config_path)
    inventory = run_input_inventory(config_path)
    print(inventory)
    if inventory.status == "B87_BLOCKED_INPUT":
        return blocked_result(inventory)
    design = run_n300_design_audit(config_path)
    print(design)
    if design.status == "B87_BLOCKED_SCHEMA":
        return B87RunResult(
            status="B87_BLOCKED_INPUT",
            candidate_count=design.candidate_count,
            overlap_with_n150=design.overlap_with_n150,
            connected_shade_status="not_reviewed_due_to_blocked_schema",
            recommended_next_lane="repair B8.6f N300 v2 schema before source review",
        )
    feature = run_feature_schema_audit(config_path)
    print(feature)
    if feature.status == "B87_BLOCKED_INPUT":
        return B87RunResult(
            status="B87_BLOCKED_INPUT",
            candidate_count=design.candidate_count,
            overlap_with_n150=design.overlap_with_n150,
            connected_shade_status=feature.connected_shade_status,
            recommended_next_lane="repair B8.6g N300 feature dataset",
        )
    source = run_source_availability_review(config_path)
    print(source)
    qa = run_candidate_qa(config_path)
    print(qa)
    decision: PrecheckDecisionResult = run_precheck_decision(config_path)
    print(decision)
    return B87RunResult(
        status=decision.status,
        candidate_count=decision.candidate_count,
        overlap_with_n150=decision.overlap_with_n150,
        connected_shade_status=decision.connected_shade_status,
        recommended_next_lane=decision.recommended_next_lane,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Run B8.7-N300-PRE design freeze and B8.6g3 source-review precheck. "
            "No SOLWEIG/QGIS/raster/AOI/B9/WBGT/hazard/risk/manifest/execution "
            "output is created."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
