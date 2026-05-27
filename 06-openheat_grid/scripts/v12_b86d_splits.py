"""Create deterministic B8.6d validation split inventory.

Inputs:
    - b86d_two_stage_dataset.csv from the B8.6d dataset builder.
Outputs:
    - b86d_validation_splits.csv
Saved metrics:
    Fold-level row/cell/forcing-day/hour counts for forcing-day, cell-group,
    spatial, typology, and hour holdouts. Random row split is disabled by
    default and never used as main evidence.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b86d_common import DEFAULT_CONFIG, fold_inventory, load_config, output_path, read_csv, validation_folds, write_csv


@dataclass(frozen=True)
class SplitResult:
    """Validation split creation result."""

    status: str
    folds: int
    split_families: int


def run(config_path: Path = DEFAULT_CONFIG) -> SplitResult:
    """Create and write the split inventory."""
    config = load_config(config_path)
    dataset = read_csv(output_path(config, "two_stage_dataset"))
    folds = validation_folds(dataset, config)
    inventory = fold_inventory(dataset, folds)
    write_csv(inventory, output_path(config, "validation_splits"))
    return SplitResult(
        status="B86D_SPLITS_READY",
        folds=len(folds),
        split_families=int(inventory["split_family"].nunique()) if not inventory.empty else 0,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Write deterministic B8.6d validation folds. The script uses no random row split unless the config "
            "sets validation.random_split_diagnostic=true."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
