#!/usr/bin/env python
"""Run System A A-L2.1a station-local buffer feature builder.

Inputs:
    - configs/v11/systema_l2_station_buffer_features.yaml
    - Station coordinate sources declared in the config.
    - Read-only local spatial source inventory under configured data roots.

Outputs:
    - Source inventory, long/wide station-buffer feature tables, schema, QA,
      missingness, collinearity screen, Markdown report, and lane status under
      outputs/v11_systema_l2_residual/station_buffer_features/.

Saved metrics:
    - Station count, CRS and buffer-area validation, source coverage status,
      missingness, constant/all-NaN feature checks, and screening-only
      Spearman high-correlation pairs.

Scope guard:
    This runner does not stage, commit, train residual ML models, start A-L2.1
    modelling, touch System B or SOLWEIG outputs, modify archive collectors,
    create local 100 m WBGT, use station_id as a predictive feature, or claim
    station-context causal correction.
"""
from __future__ import annotations

import argparse

import v11_l2_station_buffer_features as builder


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L2.1a station-local buffer feature builder.")
    parser.add_argument("--config", default="configs/v11/systema_l2_station_buffer_features.yaml")
    args = parser.parse_args()

    result = builder.run_builder(builder.resolve_path(args.config))
    print(f"1. {result.decision_status}")
    print(f"2. station count: {result.station_count}")
    print(f"3. feature groups built: {result.feature_groups_built or 'none'}")
    print(f"4. feature groups unavailable: {result.feature_groups_unavailable or 'none'}")
    print(f"5. all-27 coverage summary: {result.all_27_coverage_summary}")
    print(f"6. key exclusions: {result.key_exclusions}")
    print(f"7. next recommended action: {result.next_recommended_action}")
    print("8. files created:")
    for output_path in result.output_paths:
        print(f"   - {builder.rel(output_path)}")
    print("9. git status --short -- .:")
    print(result.git_status_short or "   (clean)")
    return 0 if result.decision_status != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
