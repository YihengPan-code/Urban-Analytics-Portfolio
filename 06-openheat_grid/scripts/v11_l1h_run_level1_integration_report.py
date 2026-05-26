#!/usr/bin/env python
"""Run System A A-L1H.2b Level 1 high-tail integration report generation.

Inputs:
    - configs/v11/systema_l1h_level1_integration.yaml
    - Existing source reports declared in the config.

Outputs:
    - Compact CSV evidence ledger, output contract, claim boundary matrix,
      decision matrix, station/regime caveats, next-gate recommendations,
      English Markdown integration report, Chinese model-card note, and lane
      status under the configured output paths.

Saved metrics:
    - Current companion definition and diagnostic operating-point metrics.
    - Reliability, high-tail, A-L2, and A-L1H.3 decisions.

This runner does not stage, commit, train models, rerun base WBGT models,
implement formula-v2, implement probability calibration again, implement
high-tail regression, start A-L2, touch System B or SOLWEIG outputs, or modify
archive collector paths.
"""
from __future__ import annotations

import argparse

import v11_l1h_make_level1_integration_report as integration


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L1H.2b Level 1 integration report.")
    parser.add_argument("--config", default="configs/v11/systema_l1h_level1_integration.yaml")
    args = parser.parse_args()

    result = integration.run_integration(integration.resolve_path(args.config))
    print(f"[status] {result.status}")
    print(f"[decision_status] {result.decision_status}")
    print(f"[current_companion_definition] {result.current_companion_definition}")
    print(f"[reliability_assessment] {result.reliability_assessment}")
    print(f"[high_tail_assessment] {result.high_tail_assessment}")
    print(f"[a_l2_decision] {result.a_l2_decision}")
    print(f"[a_l1h3_decision] {result.a_l1h3_decision}")
    print("[files_created]")
    for path in result.output_paths:
        print(f"- {integration.rel(path)}")
    if result.missing_sources:
        print("[missing_sources]")
        for path in result.missing_sources:
            print(f"- {integration.rel(path)}")
    return 0 if result.status in {"PASS", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
