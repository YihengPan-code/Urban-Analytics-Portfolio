#!/usr/bin/env python
"""Run A-L1H.0c full-period weather-regime residual merge.

Inputs:
    - configs/v11/systema_l1h_full_period_weather_merge.yaml
    - Residual and recovered weather-source files declared in the config.

Outputs:
    - Full-period weather-source inventory, merged residual/weather table,
      regime summaries, decision report, and status Markdown under
      outputs/v11_systema_l1_high_tail/weather_regime_merge_full_period/.

Saved metrics:
    - Selected weather source, provenance, row retention, observed ge31 coverage,
      station coverage, recovered weather columns, weather-regime summaries, and
      next-step recommendation.

This runner does not stage, commit, train models, implement formula-v2,
calibrate probabilities, run high-tail regression, start A-L2, touch System B,
or touch SOLWEIG/raster/archive hot-path outputs.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import v11_l1h_full_period_weather_merge as merge


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L1H.0c full-period weather merge.")
    parser.add_argument("--config", default="configs/v11/systema_l1h_full_period_weather_merge.yaml")
    args = parser.parse_args()

    result = merge.run_merge(ROOT / args.config)
    print(f"[status] {result.status}")
    print(f"[selected_weather_source] {result.selected_weather_source}")
    print(f"[selected_source_provenance] {result.selected_source_base}:{result.selected_source_relative_path}")
    print(f"[retention_rate] {result.retention_rate:.6f}")
    print(f"[matched_rows] {result.matched_rows}/{result.total_residual_rows}")
    print(f"[matched_observed_ge31_rows] {result.matched_observed_ge31_rows}/{result.total_observed_ge31_rows}")
    print(f"[matched_ge31_miss_rows] {result.matched_ge31_miss_rows}")
    print(f"[weather_columns_recovered] {', '.join(result.recovered_weather_columns) if result.recovered_weather_columns else 'none'}")
    print(f"[weather_regime_classification] {result.weather_regime_classification}")
    print(f"[next_recommended_action] {result.next_recommended_action}")
    return 0 if result.status in {"PASS_FULL_PERIOD", "PARTIAL_DIAGNOSTIC", "BLOCKED_FOR_FULL_PERIOD"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
