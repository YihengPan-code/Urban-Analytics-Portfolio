#!/usr/bin/env python
"""Run System A A-L1H.2 probability / threshold calibration diagnostics.

Inputs:
    - configs/v11/systema_l1h_probability_threshold_calibration.yaml
    - Residual/weather, residual decomposition, OOF prediction, and formula
      audit context inputs declared in the config.

Outputs:
    - Input inventory, analysis input, station-held-out probability
      predictions, score-bin event rates, reliability bins, calibration
      metrics, threshold operating points, station/regime diagnostics,
      Markdown report, and lane status under
      outputs/v11_systema_l1_high_tail/probability_threshold_calibration/.

Saved metrics:
    - Station-held-out P_ge31 and exploratory P_ge33 calibration metrics.
    - Fixed and quantile reliability diagnostics.
    - Train-station-selected threshold operating points and station/regime
      breakdowns.

This runner does not stage, commit, retrain base WBGT models, implement
formula-v2, implement high-tail regression, start A-L2, touch System B or
SOLWEIG outputs, or modify archive collector paths.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import v11_l1h_probability_threshold_calibration as calibration


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L1H.2 probability / threshold calibration.")
    parser.add_argument("--config", default="configs/v11/systema_l1h_probability_threshold_calibration.yaml")
    args = parser.parse_args()

    result = calibration.run_calibration(calibration.resolve_path(args.config))
    print(f"[acceptance_status] {result.acceptance_status}")
    print(f"[decision_status] {result.decision_status}")
    print(f"[best_probability_candidate] {result.best_probability_candidate}")
    print(f"[brier_pr_auc_reliability] {result.brier_pr_auc_reliability_headline}")
    print(f"[recommended_operating_point] {result.recommended_operating_point}")
    print(f"[station_regime_caveats] {result.station_regime_caveats}")
    print(f"[next_recommended_action] {result.next_recommended_action}")
    return 0 if result.acceptance_status in {"PASS", "PARTIAL", "WEAK", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
