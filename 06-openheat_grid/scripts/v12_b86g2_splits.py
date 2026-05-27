"""Create deterministic B8.6g2 validation split inventory.

Inputs:
    b86g2_modeling_dataset.csv.
Outputs:
    b86g2_validation_splits.csv.
Saved metrics:
    Fold-level row/cell/forcing-day/hour counts for forcing-day, cell-group,
    spatial, typology, and hour holdouts. Random row split is disabled and is
    not main evidence.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from v12_b86g2_common import DEFAULT_CONFIG, fold_inventory, load_config, output_path, read_csv, validation_folds, write_csv


@dataclass(frozen=True)
class SplitResult:
    """Split inventory result."""

    status: str
    folds: int
    split_families: int


def run(config_path: Path = DEFAULT_CONFIG) -> SplitResult:
    """Write deterministic validation folds."""
    config = load_config(config_path)
    dataset = read_csv(output_path(config, "modeling_dataset"))
    folds = validation_folds(dataset, config)
    inventory = fold_inventory(dataset, folds)
    write_csv(inventory, output_path(config, "validation_splits"))
    return SplitResult("B86G2_SPLITS_READY", len(folds), int(inventory["split_family"].nunique()))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Write deterministic B8.6g2 validation folds for blocked validation families."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
