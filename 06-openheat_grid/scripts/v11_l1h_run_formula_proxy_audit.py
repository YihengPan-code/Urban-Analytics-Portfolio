#!/usr/bin/env python
"""Run System A A-L1H.1 formula-v2 / physical proxy diagnostic audit.

Inputs:
    - configs/v11/systema_l1h_formula_proxy_audit.yaml
    - Residual/weather, residual decomposition, OOF prediction, and optional
      discovery inputs declared in the config.

Outputs:
    - Candidate registry, predictions, metrics, regime diagnostics, Markdown
      report, and lane status under
      outputs/v11_systema_l1_high_tail/formula_proxy_audit/.

Saved metrics:
    - Input inventory, candidate registry, overall metrics, fixed 31/33
      threshold metrics, high-tail residual summaries, radiation-regime miss
      diagnostics, and component/radiation-sensitivity diagnostics.

This runner does not stage, commit, train ML models, calibrate probabilities,
implement high-tail regression, start A-L2, touch System B or SOLWEIG outputs,
or modify archive collector paths.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import v11_l1h_formula_proxy_audit as audit


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L1H.1 formula/proxy diagnostic audit.")
    parser.add_argument("--config", default="configs/v11/systema_l1h_formula_proxy_audit.yaml")
    args = parser.parse_args()

    result = audit.run_audit(ROOT / args.config)
    print(f"[acceptance_status] {result.acceptance_status}")
    print(f"[decision_status] {result.decision_status}")
    print(f"[best_formula_candidate] {result.best_formula_candidate}")
    print(f"[comparator_reference] {result.comparator_reference}")
    print(f"[high_tail_comparison] {result.high_tail_comparison}")
    print(f"[fixed31_result] {result.fixed31_result}")
    print(f"[radiation_hot_result] {result.radiation_hot_result}")
    print(f"[next_recommended_action] {result.next_recommended_action}")
    return 0 if result.acceptance_status in {"PASS", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
