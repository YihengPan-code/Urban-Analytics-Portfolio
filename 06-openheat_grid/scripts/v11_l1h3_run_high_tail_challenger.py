#!/usr/bin/env python
"""Run System A A-L1H.3 high-tail challenger benchmark.

Inputs:
    - configs/v11/systema_l1h3_high_tail_challenger.yaml
    - Residual/weather, current companion probability, threshold operating
      point, and Level 1 output-contract inputs declared in the config.

Outputs:
    - Input inventory, no-leakage feature schema, station-held-out OOF
      challenger predictions, overall metrics, threshold metrics,
      reliability metrics, station/regime diagnostics, pairwise comparison,
      Markdown report, and lane status under
      outputs/v11_systema_l1_high_tail/high_tail_challenger/.

Saved metrics:
    - ge31 precision, recall, F1, CSI, false-alarm ratio, miss rate,
      TP/FP/FN/TN, ROC-AUC, PR-AUC, Brier, reliability ECE, probability
      spread, station/regime diagnostics, and pairwise deltas versus the
      current M4+isotonic best-F1 and recall_90 baselines.

This runner does not stage, commit, touch System B, touch SOLWEIG outputs,
modify archive collector paths, start A-L2, claim official warning
probability, claim prospective forecast skill, or claim local 100m WBGT.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import v11_l1h3_high_tail_challenger as challenger


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L1H.3 high-tail challenger benchmark.")
    parser.add_argument("--config", default="configs/v11/systema_l1h3_high_tail_challenger.yaml")
    args = parser.parse_args()

    result = challenger.run_benchmark(challenger.resolve_path(args.config))
    print(f"[acceptance_status] {result.acceptance_status}")
    print(f"[decision_status] {result.decision_status}")
    print(f"[best_challenger] {result.best_challenger}")
    print(f"[comparison_best_f1] {result.comparison_best_f1}")
    print(f"[comparison_recall90] {result.comparison_recall90}")
    print(f"[station_regime_caveats] {result.station_regime_caveats}")
    print(f"[a_l2_recommendation] {result.a_l2_recommendation}")
    return 0 if result.acceptance_status in {"PASS", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
