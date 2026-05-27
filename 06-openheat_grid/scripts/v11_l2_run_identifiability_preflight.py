#!/usr/bin/env python
"""Run System A A-L2.0 station-context identifiability preflight.

Inputs:
    - configs/v11/systema_l2_identifiability_preflight.yaml
    - Existing System A Level 1 high-tail residual, probability, station
      caveat, and challenger outputs declared in the config.
    - Optional station-context metadata and explicit station-to-cell mapping
      sources declared in the config.

Outputs:
    - Station-context input inventory, station residual summary, probability
      error summary, bootstrap stability assessment, feature schema,
      identifiability matrix, Markdown report, and lane status under
      outputs/v11_systema_l2_residual/identifiability_preflight/.

Saved metrics:
    - Station residual and probability-error summaries after Level 1 score /
      probability context.
    - Stability labels from deterministic station date/hour bootstraps.
    - Feature availability and low-n identifiability decision.

This runner does not stage, commit, train a final residual ML model, use
station_id as a predictive feature, claim station-context causal correction,
claim operational warning probability, create local 100 m WBGT, touch System B
or SOLWEIG outputs, or modify archive collector paths.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import v11_l2_identifiability_preflight as preflight


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L2.0 station-context identifiability preflight.")
    parser.add_argument("--config", default="configs/v11/systema_l2_identifiability_preflight.yaml")
    args = parser.parse_args()

    result = preflight.run_preflight(preflight.resolve_path(args.config))
    print(f"[acceptance_status] {result.acceptance_status}")
    print(f"[decision_status] {result.decision_status}")
    print(f"[stable_residual] {result.stable_residual_summary}")
    print(f"[s142_s139] {result.s142_s139_summary}")
    print(f"[station_feature_availability] {result.station_feature_availability}")
    print(f"[a_l2_1_recommendation] {result.a_l2_1_recommendation}")
    return 0 if result.acceptance_status in {"PASS", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
