#!/usr/bin/env python
"""Run A-L1H.0b weather-regime residual merge.

Inputs:
    - configs/v11/systema_l1h_weather_regime_merge.yaml
    - Existing residual and weather-source files declared in the config.

Outputs:
    - Weather-source inventory, merged residual/weather input, regime summaries,
      bias report, and status Markdown under
      outputs/v11_systema_l1_high_tail/weather_regime_merge/.

Saved metrics:
    - Selected weather source, merge row retention, recovered weather columns,
      residual summaries, fixed ge31 miss concentration, and next-step note.

This runner does not stage, commit, train models, implement formula-v2,
calibrate probabilities, run high-tail regression, start A-L2, touch System B,
or touch SOLWEIG/raster/archive hot-path outputs.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import v11_l1h_weather_regime_merge as merge


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Run A-L1H.0b weather-regime residual merge.")
    parser.add_argument("--config", default="configs/v11/systema_l1h_weather_regime_merge.yaml")
    args = parser.parse_args()

    result = merge.run_merge(ROOT / args.config)
    print(f"[status] {result.status}")
    print(f"[selected_weather_source] {result.selected_weather_source}")
    print(f"[retention] {result.matched_rows}/{result.residual_rows} ({result.retention_rate:.1%})")
    print(f"[recovered_weather_columns] {', '.join(result.recovered_weather_columns) if result.recovered_weather_columns else 'none'}")
    print(f"[key_interaction] {result.plausible_interaction}")
    print(f"[next_action] {result.next_action}")
    return 0 if result.status in {"PASS", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
