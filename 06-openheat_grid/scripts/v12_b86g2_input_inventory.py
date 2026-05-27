"""Write the B8.6g2 compact input inventory.

Inputs:
    configs/v12/systemb_b86g2_feature_retest.yaml.
Outputs:
    b86g2_input_inventory.csv.
Saved metrics:
    Existence, size, row count, column count, unique cell count, forcing-day
    count, and hour count for configured compact CSV inputs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b86g2_common import DEFAULT_CONFIG, ensure_output_dir, guardrails_are_set, input_inventory_frame, load_config, output_path, write_csv


@dataclass(frozen=True)
class InputInventoryResult:
    """Input inventory result."""

    status: str
    inputs: int
    missing: int


def run(config_path: Path = DEFAULT_CONFIG) -> InputInventoryResult:
    """Write the B8.6g2 input inventory."""
    config = load_config(config_path)
    guardrails_are_set(config)
    ensure_output_dir(config)
    inventory = input_inventory_frame(config)
    write_csv(inventory, output_path(config, "input_inventory"))
    missing = int((~inventory["exists"].astype(bool)).sum()) if not inventory.empty else 0
    return InputInventoryResult("B86G2_INPUT_INVENTORY_READY", len(inventory), missing)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Write B8.6g2 compact input inventory with row/cell/hour counts and no raster IO."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
