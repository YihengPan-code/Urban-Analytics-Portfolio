#!/usr/bin/env python
"""Run System A A-L1H.5 model card and hourly output contract generation.

Inputs:
    - configs/v11/systema_l1h5_model_card_output_contract.yaml
    - Existing A-L1H.4 compact evidence, A-L2.1c evidence if present, and
      prior A-L1H report/status files declared in the config.

Outputs:
    - Evidence inventory, companion decision matrix, output schema, threshold
      policy register, station caveat register, Level 2 boundary register,
      prospective evaluation plan, System A model card, hourly output contract,
      English report, Chinese report, and status under configured paths.

Saved metrics:
    - Contract status, primary output decision, optional companion decisions,
      Level 2 boundary decision, and prospective evaluation next action.

This runner does not stage, commit, train models, touch System B or SOLWEIG
outputs, modify archive collectors, create station-adjusted WBGT, create local
100 m WBGT, create risk_score/hazard_score, or promote P_ge31 to an official
warning probability.
"""
from __future__ import annotations

import argparse

import v11_l1h5_model_card_output_contract as contract


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L1H.5 model card / output contract finalization.")
    parser.add_argument("--config", default="configs/v11/systema_l1h5_model_card_output_contract.yaml")
    args = parser.parse_args()

    result = contract.run_contract(contract.resolve_path(args.config))
    print(f"[status] {result.status}")
    print(f"[primary_output_decision] {result.primary_output_decision}")
    print(f"[p_ge31_decision] {result.p_ge31_decision}")
    print(f"[p_ge33_decision] {result.p_ge33_decision}")
    print(f"[expected_exceedance_decision] {result.expected_exceedance_decision}")
    print(f"[interval_decision] {result.interval_decision}")
    print(f"[level2_boundary_decision] {result.level2_boundary_decision}")
    print(f"[prospective_next_action] {result.prospective_next_action}")
    print("[files_created]")
    for path in result.output_paths:
        print(f"- {contract.rel(path)}")
    if result.missing_required_sources:
        print("[missing_required_sources]")
        for path in result.missing_required_sources:
            print(f"- {contract.rel(path)}")
    return 0 if result.status in {"A_L1H5_CONTRACT_PASS", "A_L1H5_CONTRACT_PARTIAL", "A_L1H5_BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
