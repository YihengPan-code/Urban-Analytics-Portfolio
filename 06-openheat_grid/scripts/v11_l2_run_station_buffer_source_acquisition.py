#!/usr/bin/env python
"""Run System A A-L2.1a-S1 station-local source acquisition/extraction.

Inputs:
    - configs/v11/systema_l2_station_buffer_source_acquisition.yaml
    - data/calibration/v09_wbgt_station_pairs.csv
    - Local read-only source roots declared in the config.

Outputs:
    - Source acquisition inventory, normalization inventory, long/wide feature
      tables, schema, QA, missing-source checklist, Markdown report, lane
      status, and UTF-8 Chinese documentation.

Saved metrics:
    - Decision status, station count, all-27 feature groups, unavailable groups,
      assumptions, next action, created files, and current git status.

Scope guard:
    This runner does not stage, commit, train residual ML models, start A-L2.1c
    modelling, touch System B or SOLWEIG outputs, modify archive collectors,
    create local 100 m WBGT, use station_id as a predictive feature, or claim
    station-context causal correction.
"""
from __future__ import annotations

import argparse

import v11_l2_station_buffer_source_acquisition as builder


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L2.1a-S1 station-local source acquisition/extraction.")
    parser.add_argument("--config", default="configs/v11/systema_l2_station_buffer_source_acquisition.yaml")
    args = parser.parse_args()

    result = builder.run_builder(builder.resolve_path(args.config))
    print(f"1. {result.decision_status}")
    print(f"2. station count: {result.station_count}")
    print(f"3. feature groups built with all-27 coverage: {builder.semicolon(result.feature_groups_all_27) or 'none'}")
    print(f"4. feature groups still unavailable: {builder.semicolon(result.feature_groups_unavailable) or 'none'}")
    print(f"5. assumptions made: {builder.semicolon(result.assumptions) or 'none'}")
    print(f"6. next recommended action: {result.next_recommended_action}")
    print("7. files created:")
    for output_path in result.files_created:
        print(f"   - {builder.rel(output_path)}")
    print("8. git status --short -- .:")
    print(result.git_status_short or "   (clean)")
    return 0 if result.decision_status != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
