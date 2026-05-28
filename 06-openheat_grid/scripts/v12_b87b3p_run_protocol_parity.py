"""Run the complete B8.7b.3p SOLWEIG protocol parity audit.

Inputs:
    configs/v12/systemb_b87b3p_solweig_protocol_parity.yaml and compact
    source/protocol evidence declared there.
Outputs:
    All required B8.7b.3p CSV/Markdown artifacts under
    outputs/v12_surrogate/b8_7b3p_solweig_protocol_parity plus the UTF-8
    Chinese note under docs/v12.
Saved metrics:
    Input inventory, batch discovery/classification, protocol dimension
    registry, batch protocol matrix, source lineage parity, SVF/overhead
    parity, ML label trace, mismatch/blocker registers, final decision,
    next-lane matrix, patch prompt, report, and status. This runner does not
    execute QGIS/SOLWEIG, read raster pixels, write/copy/move rasters, open
    svfs.zip, create a run-ready manifest, create a runner, stage, or commit.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from v12_b87b3p_batch_discovery import run as run_batch_discovery
from v12_b87b3p_input_inventory import DEFAULT_CONFIG, git_output, run as run_input_inventory
from v12_b87b3p_ml_label_trace import run as run_ml_label_trace
from v12_b87b3p_parity_decision import ParityDecision, run as run_parity_decision
from v12_b87b3p_protocol_extractor import run as run_protocol_extractor
from v12_b87b3p_source_lineage_audit import run as run_source_lineage_audit
from v12_b87b3p_svf_overhead_parity import run as run_svf_overhead_parity


def print_final_summary(decision: ParityDecision) -> None:
    """Print the required final lane summary."""
    print(f"1. {decision.status}")
    print(f"2. batches discovered: {decision.batches_discovered}")
    print(f"3. final ML label source batch: {decision.final_ml_label_source_batch}")
    print(f"4. N150 protocol id: {decision.n150_protocol_id}")
    print(f"5. planned N300 protocol id: {decision.planned_n300_protocol_id}")
    print(f"6. DSM parity headline: {decision.dsm_headline}")
    print(f"7. CDSM parity headline: {decision.cdsm_headline}")
    print(f"8. SVF/base-overhead parity headline: {decision.svf_headline}")
    print(f"9. DEM/landcover parity headline: {decision.dem_landcover_headline}")
    print(f"10. forcing/tile/SOLWEIG parameter parity headline: {decision.forcing_tile_solweig_headline}")
    print(f"11. nonfinal smoke differences headline: {decision.nonfinal_smoke_headline}")
    print(f"12. blockers: {decision.blockers}")
    print(f"13. recommended next lane: {decision.recommended_next_lane}")
    print("14. files created:")
    for path in decision.files_created:
        print(f"    - {path}")
    print("15. git status --short -- .:")
    status = git_output(["status", "--short", "--", "."])
    print(status if status else "(clean)")


def run(config_path: Path = DEFAULT_CONFIG) -> ParityDecision:
    """Run all B8.7b.3p steps in dependency order."""
    inventory = run_input_inventory(config_path)
    print(f"input_inventory_status={inventory.status}")
    print(f"batch_discovery_rows={len(run_batch_discovery(config_path))}")
    print(f"protocol_matrix_rows={len(run_protocol_extractor(config_path))}")
    print(f"source_lineage_rows={len(run_source_lineage_audit(config_path))}")
    print(f"svf_parity_rows={len(run_svf_overhead_parity(config_path))}")
    print(f"ml_label_trace_rows={len(run_ml_label_trace(config_path))}")
    decision = run_parity_decision(config_path)
    print_final_summary(decision)
    return decision


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Run B8.7b.3p SOLWEIG protocol/source parity audit. No QGIS/SOLWEIG, "
            "no raster pixel reads, no raster writes/copies/moves, no svfs.zip "
            "opens, no run-ready manifest/runner, no staging, no commits."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    try:
        run(args.config)
    except Exception as exc:
        print("1. FAILED")
        print(f"error: {exc}")
        raise


if __name__ == "__main__":
    main()
