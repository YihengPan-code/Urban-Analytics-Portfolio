"""Create the B8.7b.1 manual local-root template and instructions.

Inputs:
    configs/v12/systemb_b87b1_local_asset_remap.yaml and optional manual input
    path metadata.
Outputs:
    b87b1_manual_local_root_template.csv and
    b87b1_manual_local_root_instructions.md.
Saved metrics:
    Suggested root keys, required flags, valid user statuses, manual input
    presence, and the active metadata-only mode. This script writes only compact
    CSV/Markdown artifacts inside the project output directory.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b1_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean, load_config, out_path
from v12_b87b1_input_inventory import path_exists_metadata, write_csv_rows, write_text


@dataclass(frozen=True)
class ManualRootTemplateResult:
    """Manual template result."""

    status: str
    manual_input_found: bool
    template_rows: int


TEMPLATE_ROWS: list[dict[str, Any]] = [
    {
        "root_key": "b87c_n300_asset_root",
        "local_root_path": "C:/OpenHeat-local/solweig/b87c_n300/assets",
        "required": "yes",
        "description": "N300 new-cell asset root containing per-cell tile folders.",
        "user_status": "unknown",
        "notes": "Set to use only after verifying locally by metadata/path listing.",
    },
    {
        "root_key": "b87c_n300_output_root",
        "local_root_path": "C:/OpenHeat-local/solweig/b87c_n300",
        "required": "yes",
        "description": "Local-only future output root for B8.7c; B8.7b.1 must not create it.",
        "user_status": "unknown",
        "notes": "Use only as a selected root, not as authorization to run SOLWEIG.",
    },
    {
        "root_key": "b85_f1_tiles_root",
        "local_root_path": "C:/OpenHeat-local/solweig/b85_f1_tiles",
        "required": "no",
        "description": "Prior B8.5-F1/F5 local output/tile root that may hold reusable references.",
        "user_status": "unknown",
        "notes": "Metadata reference only; do not copy raster outputs into Git.",
    },
    {
        "root_key": "b85_f2c_met_forcing_root",
        "local_root_path": "C:/OpenHeat-local/solweig/met_forcing/b85_f2c",
        "required": "yes",
        "description": "Prior local-only FD02 met forcing text root reused by F5.",
        "user_status": "unknown",
        "notes": "Check file names and existence only.",
    },
    {
        "root_key": "qgis_manual_check_root",
        "local_root_path": "C:/OpenHeat-local/solweig/qgis_checks",
        "required": "yes",
        "description": "Manual QGIS/UMEP availability check folder.",
        "user_status": "unknown",
        "notes": "This lane reads metadata only and does not run QGIS.",
    },
    {
        "root_key": "prior_f5_run_log_root",
        "local_root_path": "C:/OpenHeat-local/solweig/b85_f5_n150",
        "required": "no",
        "description": "Prior F5 local-only run-log root for context.",
        "user_status": "unknown",
        "notes": "Do not commit raw local logs.",
    },
    {
        "root_key": "optional_existing_cell_asset_map_csv",
        "local_root_path": "",
        "required": "no",
        "description": "Optional compact CSV mapping cell_id to local asset folders.",
        "user_status": "unknown",
        "notes": "If provided, keep it compact and metadata-only.",
    },
    {
        "root_key": "optional_tile_index_csv",
        "local_root_path": "",
        "required": "no",
        "description": "Optional compact tile index CSV for per-cell folders.",
        "user_status": "unknown",
        "notes": "Do not include raster contents or large raw exports.",
    },
]


def instructions_text(config: dict[str, Any], manual_found: bool) -> str:
    """Return manual local-root instructions."""
    mode = "MANUAL_INPUT_FOUND" if manual_found else "AUTO_DISCOVERY_ONLY"
    return f"""# B8.7b.1 Manual Local Root Instructions

Mode: `{mode}`

Fill a manual local-root CSV only if automatic metadata discovery cannot resolve the local asset roots.

Expected input path:

`{clean(config.get("manual_local_root_input_path"))}`

Required columns:

- `root_key`
- `local_root_path`
- `required`
- `description`
- `user_status`
- `notes`

Valid `user_status` values:

- `use`
- `missing`
- `unknown`
- `not_applicable`

Rules:

- Use `use` only for roots you verified locally by path existence/listing.
- Do not copy local assets into Git.
- Do not open `.tif`, `.tiff`, `.vrt`, `.asc`, `.img`, `.nc`, `.grib`, raw SOLWEIG rasters, or `svfs.zip`.
- Do not run QGIS or SOLWEIG in this lane.
- Do not create a run-ready manifest, QGIS runner, local runner, or local execution package.

Claim boundary:

{CLAIM_BOUNDARY}
"""


def run(config_path: Path = DEFAULT_CONFIG) -> ManualRootTemplateResult:
    """Write the manual local-root template and instructions."""
    config = load_config(config_path)
    manual_found = path_exists_metadata(clean(config.get("manual_local_root_input_path")))[0] == "yes"
    write_csv_rows(
        out_path(config, "b87b1_manual_local_root_template.csv"),
        TEMPLATE_ROWS,
        ["root_key", "local_root_path", "required", "description", "user_status", "notes"],
    )
    write_text(out_path(config, "b87b1_manual_local_root_instructions.md"), instructions_text(config, manual_found))
    return ManualRootTemplateResult(
        status="MANUAL_INPUT_FOUND" if manual_found else "AUTO_DISCOVERY_ONLY",
        manual_input_found=manual_found,
        template_rows=len(TEMPLATE_ROWS),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Create the B8.7b.1 manual local-root template and instructions. "
            "Does not modify local asset roots or create execution artifacts."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
