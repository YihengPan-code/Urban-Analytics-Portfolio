#!/usr/bin/env python
"""Run System A A-L2.1b station buffer feature QA.

Inputs:
    - configs/v11/systema_l2_station_feature_qa.yaml
    - A-L2.1a-S1 station buffer feature wide/schema/QA CSVs.
    - A-L2.0 station residual, probability-error, and stability CSVs.

Outputs:
    - Distribution, collinearity, buffer redundancy, residual association,
      key-station profile, candidate-set, manual-review, Markdown report,
      lane status, and UTF-8 Chinese documentation outputs declared in config.

Saved metrics:
    - Decision status, primary candidate count, top residual-associated
      features, excluded high-collinearity groups, key-station caveats,
      A-L2.1c recommendation, created files, and git status.

Scope guard:
    This runner does not stage, commit, train residual ML models, start
    A-L2.1c modelling, create station-adjusted WBGT, create local 100 m WBGT,
    touch System B or SOLWEIG outputs, modify archive collectors, use
    station_id as a predictive feature, or claim station-context causal
    correction.
"""
from __future__ import annotations

import argparse

import v11_l2_station_feature_qa as qa


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L2.1b station buffer feature QA.")
    parser.add_argument("--config", default="configs/v11/systema_l2_station_feature_qa.yaml")
    args = parser.parse_args()

    result = qa.run_feature_qa(qa.resolve_path(args.config))
    print(f"1. {result.decision_status}")
    print(f"2. primary candidate feature count: {result.primary_candidate_count}")
    print(f"3. top residual-associated features: {result.top_residual_features}")
    print(f"4. excluded high-collinearity groups: {result.excluded_high_collinearity_groups}")
    print(f"5. key station caveats: {result.key_station_caveats}")
    print(f"6. A-L2.1c recommendation: {result.a_l2_1c_recommendation}")
    print("7. files created:")
    for output_path in result.files_created:
        print(f"   - {qa.rel(output_path)}")
    print("8. git status --short -- .:")
    print(result.git_status_short or "   (clean)")
    return 0 if result.decision_status != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
