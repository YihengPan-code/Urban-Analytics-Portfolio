"""Run the full B8.6g vector/compact feature acquisition suite.

Inputs:
    configs/v12/systemb_b86g_feature_acquisition.yaml and all compact/vector
    metadata inputs declared there.
Outputs:
    All B8.6g inventories, family feature tables, feature schema, N150/N300
    feature datasets, coverage/quality/readiness matrices, failure-context
    join, future prompts, report, lane status, and UTF-8 Chinese documentation.
Saved metrics:
    Source discovery, source readiness, cell geometry readiness, feature family
    coverage, feature quality checks, failure-context coverage, feature-gap
    closure, retest readiness, AOI/B9 boundary status, and next-lane decision.
    This runner does not create AOI-wide predictions, B9 outputs, N300 SOLWEIG
    manifests, QGIS runners, local WBGT, hazard/risk scores, exposure or
    vulnerability scores, target-derived predictors, observed-truth claims,
    causal feature-importance claims, raster reads/writes, SOLWEIG/QGIS runs,
    Tmrt-to-WBGT conversion, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b86g_cell_geometry import run as run_cell_geometry
from v12_b86g_compact_feature_builders import run as run_compact_features
from v12_b86g_failure_context_join import run as run_failure_join
from v12_b86g_feature_readiness import run as run_feature_readiness
from v12_b86g_feature_schema import run as run_feature_schema
from v12_b86g_source_inventory import DEFAULT_CONFIG, run as run_source_inventory
from v12_b86g_vector_feature_builders import run as run_vector_features
from v12_b86g_workflow_decision import run as run_workflow_decision


@dataclass(frozen=True)
class FeatureAcquisitionRunResult:
    """Full B8.6g run result."""

    status: str
    sources_scanned: int
    usable_sources: int
    n150_shape: tuple[int, int]
    n300_shape: tuple[int, int]
    retest_readiness_status: str
    aoi_b9_status: str
    recommended_next_lane: str


def run(config_path: Path = DEFAULT_CONFIG) -> FeatureAcquisitionRunResult:
    """Run the complete B8.6g feature acquisition workflow."""
    inventory = run_source_inventory(config_path)
    print(inventory)
    if inventory.status == "B86G_BLOCKED_INPUT":
        return FeatureAcquisitionRunResult(
            status="B86G_BLOCKED_INPUT",
            sources_scanned=inventory.sources_scanned,
            usable_sources=inventory.usable_sources,
            n150_shape=(0, 0),
            n300_shape=(0, 0),
            retest_readiness_status="BLOCKED_INPUT",
            aoi_b9_status="AOI_PREFLIGHT_BLOCKED / B9_BLOCKED",
            recommended_next_lane="fix required compact inputs",
        )
    cell = run_cell_geometry(config_path)
    print(cell)
    vector = run_vector_features(config_path)
    print(vector)
    compact = run_compact_features(config_path)
    print(compact)
    schema = run_feature_schema(config_path)
    print(schema)
    readiness = run_feature_readiness(config_path)
    print(readiness)
    failure = run_failure_join(config_path)
    print(failure)
    decision = run_workflow_decision(config_path)
    print(decision)
    return FeatureAcquisitionRunResult(
        status=decision.status,
        sources_scanned=inventory.sources_scanned,
        usable_sources=inventory.usable_sources,
        n150_shape=readiness.n150_shape,
        n300_shape=readiness.n300_shape,
        retest_readiness_status=decision.retest_readiness_status,
        aoi_b9_status=decision.aoi_b9_status,
        recommended_next_lane=decision.recommended_next_lane,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run the full B8.6g compact/vector feature acquisition suite.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
