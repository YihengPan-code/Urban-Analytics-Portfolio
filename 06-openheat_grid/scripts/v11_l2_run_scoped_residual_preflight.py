#!/usr/bin/env python
"""Run System A A-L2.1c scoped station-level residual preflight.

Inputs:
    - configs/v11/systema_l2_scoped_residual_preflight.yaml
    - A-L2.0 residual/probability/stability station summaries.
    - A-L2.1a-S1 station buffer features.
    - A-L2.1b candidate-set and association-screen QA outputs.

Outputs:
    - Station-level model input table, feature-set inventory, null/one-feature/
      Ridge/ElasticNet LOO metrics, fixed permutation null, bootstrap
      coefficient stability, LOO predictions, station diagnostics, decision
      matrix, English report, lane status, and UTF-8 Chinese note declared in
      the config.

Saved metrics:
    - n_stations used by target, best scoped model/feature set by target, null
      baseline comparison, permutation/bootstrap headlines, S142/S139 caveats,
      A-L2.2 recommendation, created files, and git status.

Scope guard:
    This runner does not stage, commit, touch System B/SOLWEIG/archive paths,
    model official WBGT directly, use hourly pseudo-replication, use station_id
    as a feature, create station-adjusted WBGT, create local 100 m WBGT, or
    claim station-context causal correction.
"""
from __future__ import annotations

import argparse

import v11_l2_scoped_residual_preflight as scoped


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L2.1c scoped station-level residual preflight.")
    parser.add_argument("--config", default="configs/v11/systema_l2_scoped_residual_preflight.yaml")
    args = parser.parse_args()

    result = scoped.run_scoped_preflight(scoped.resolve_path(args.config))
    print(f"1. {result.decision_status}")
    print(f"2. n_stations used: {result.n_stations_used}")
    print(f"3. best model / feature set by target: {result.best_models_by_target}")
    print(f"4. null baseline comparison: {result.null_baseline_comparison}")
    print(f"5. permutation / bootstrap headline: {result.permutation_bootstrap_headline}")
    print(f"6. S142/S139 caveats: {result.s142_s139_caveats}")
    print(f"7. A-L2.2 recommendation: {result.a_l2_2_recommendation}")
    print("8. files created:")
    for output_path in result.files_created:
        print(f"   - {scoped.rel(output_path)}")
    print("9. git status --short -- .:")
    print(result.git_status_short or "   (clean)")
    return 0 if result.decision_status != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
