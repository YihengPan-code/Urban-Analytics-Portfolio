#!/usr/bin/env python
"""Run System A A-L1H.4 probabilistic / exceedance companion suite.

Inputs:
    - configs/v11/systema_l1h4_prob_exceedance_suite.yaml
    - Existing Level 1 residual/weather, OOF prediction, and compact
      companion inputs declared in the config.

Outputs:
    - Input inventory, model input table, feature schema, validation splits,
      deterministic baseline metrics, threshold policy metrics, probability
      metrics and calibration bins, expected exceedance metrics, interval
      metrics, compact OOF predictions, station diagnostics, decision matrix,
      output contract draft, model card, report, Chinese documentation, and
      status under the paths declared by the config.

Saved metrics:
    - LOSO primary and blocked-time secondary threshold, probability,
      exceedance, interval, and station diagnostics.

This runner does not stage, commit, touch System B, touch SOLWEIG outputs,
modify archive collectors, create station-adjusted WBGT, create local 100 m
WBGT, create risk_score/hazard_score, or use target leakage features.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import v11_l1h4_prob_exceedance_suite as suite


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L1H.4 probabilistic / exceedance companion suite.")
    parser.add_argument("--config", default="configs/v11/systema_l1h4_prob_exceedance_suite.yaml")
    args = parser.parse_args()

    result = suite.run_suite(suite.resolve_path(args.config))
    print(f"[status] {result.status}")
    print(f"[rows] n_rows={result.n_rows}; n_stations={result.n_stations}; n_events_ge31={result.n_events_ge31}; n_events_ge33={result.n_events_ge33}")
    print(f"[best_probability] {result.best_probability_headline}")
    print(f"[expected_exceedance] {result.expected_exceedance_headline}")
    print(f"[interval] {result.interval_headline}")
    print(f"[baseline_comparison] {result.baseline_comparison}")
    print(f"[s142_caveat] {result.s142_caveat}")
    print(f"[output_contract] {result.output_contract_recommendation}")
    return 0 if result.status in {"A_L1H4_COMPANION_PROMISING", "A_L1H4_WEAK_COMPANION", "A_L1H4_NOT_IDENTIFIABLE", "BLOCKED_BASELINE_INPUT"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
