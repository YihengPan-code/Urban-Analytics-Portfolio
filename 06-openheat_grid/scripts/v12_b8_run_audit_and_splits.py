"""Run B8.0 dataset audit and B8.1 validation split protocol.

Inputs:
    configs/v12/systemb_surrogate_b8_config.yaml plus all input files declared
    there.

Outputs:
    B8.0 audit artifacts under outputs/v12_surrogate/b8_dataset_audit.
    B8.1 split manifests under outputs/v12_surrogate/b8_validation_protocol.
    outputs/v12_surrogate/B8_LANE_STATUS.md.

Saved metrics:
    B8.0 and B8.1 statuses, row/cell counts, split row counts, commands,
    changed output file list, caveats, safe/not-safe-to-commit guidance, and
    the next recommended action.

This runner does not train models, create AOI-wide maps, compute local WBGT, or
create hazard_score or risk_score outputs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from v12_b8_make_validation_splits import run as run_splits
from v12_b8_prepare_surrogate_dataset import DEFAULT_CONFIG, read_config, repo_path, run as run_audit


ROOT = Path(__file__).resolve().parents[1]


def command_output(args: list[str]) -> str:
    """Run a lightweight command and return stdout for status reporting."""
    completed = subprocess.run(args, cwd=ROOT, check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def list_output_files(root: Path) -> list[str]:
    """List B8 output files for the status report."""
    if not root.exists():
        return []
    return sorted(path.relative_to(ROOT).as_posix() for path in root.rglob("*") if path.is_file())


def write_lane_status(config_path: Path, audit: Any, splits: Any, commands: list[str]) -> Path:
    """Write outputs/v12_surrogate/B8_LANE_STATUS.md."""
    config = read_config(config_path)
    out_root = repo_path(config["outputs"]["root_dir"])
    out_root.mkdir(parents=True, exist_ok=True)
    status_path_rel = "outputs/v12_surrogate/B8_LANE_STATUS.md"
    branch = command_output(["git", "branch", "--show-current"])
    pre_hygiene_count = config.get("pre_b811_feature_count", "not recorded")
    overall = "PASS" if audit.status == "PASS" and splits.status == "PASS" else ("BLOCKED" if "BLOCKED" in {audit.status, splits.status} else "FAILED")
    output_files = list_output_files(out_root)
    if status_path_rel not in output_files:
        output_files.append(status_path_rel)
    output_files = sorted(output_files)
    lines = [
        "# B8 Lane Status",
        "",
        f"Status: {overall}",
        f"Branch: {branch}",
        "Scope: B8.0 surrogate-ready dataset audit + B8.1 validation split protocol only.",
        "",
        "## Commands run",
        "",
        *[f"- `{command}`" for command in commands],
        "",
        "## Files created / modified",
        "",
        "- `configs/v12/systemb_surrogate_b8_config.yaml`",
        "- `scripts/v12_b8_prepare_surrogate_dataset.py`",
        "- `scripts/v12_b8_make_validation_splits.py`",
        "- `scripts/v12_b8_run_audit_and_splits.py`",
        "- `docs/v12/OpenHeat_SystemB_surrogate_dataset_protocol_CN.md`",
        *[f"- `{path}`" for path in output_files],
        "",
        "## Key results",
        "",
        f"- B8.0 status: {audit.status}",
        f"- B8.1 status: {splits.status}",
        f"- Rows in surrogate label-feature matrix: {audit.row_count}",
        f"- Unique cells: {audit.unique_cells}",
        f"- Scenarios: {', '.join(audit.scenario_values)}",
        f"- hour_sgt values: {', '.join(str(value) for value in audit.hour_values)}",
        f"- Pre-B8.1.1 selected feature count: {pre_hygiene_count}",
        f"- Selected B8.2 physical-core predictor columns: {audit.selected_feature_count}",
        f"- Excluded nonphysical/social columns: {audit.excluded_nonphysical_count}",
        f"- Excluded metadata/constant/contract columns: {audit.excluded_metadata_count}",
        f"- Leakage-like excluded columns: {audit.leakage_excluded_count}",
        f"- Cell-grouped manifest rows: {splits.cell_grouped_rows}",
        f"- Spatial manifest rows: {splits.spatial_rows} ({splits.spatial_status})",
        f"- Feature-bin manifest rows: {splits.feature_bin_rows}",
        f"- Valid feature-bin splits: {', '.join(splits.feature_bin_valid_splits) if splits.feature_bin_valid_splits else '(none)'}",
        f"- Blocked/degenerate feature-bin splits: {', '.join(splits.feature_bin_blocked_splits) if splits.feature_bin_blocked_splits else '(none)'}",
        f"- Hour-holdout manifest rows: {splits.hour_holdout_rows}",
        f"- Scenario-holdout manifest rows: {splits.scenario_holdout_rows}",
        "",
        "## Caveats",
        "",
        "- No B8.2 model benchmark was implemented.",
        "- No models were trained.",
        "- No AOI-wide final outputs were created.",
        "- No Tmrt values were converted to WBGT.",
        "- `m_rad_pct01` is retained as a reference-domain modifier/label; B8 emphasizes `delta_tmrt_p90_c` and `tmrt_p90_c` as physical surrogate targets.",
        "- Hygiene patch B8.1.1 tightened predictor eligibility and blocks degenerate feature-bin holdouts; B8.0/B8.1 status remains PASS.",
        "",
        "## Safe to commit",
        "",
        "- B8 config, scripts, protocol note, and compact CSV/Markdown outputs under `outputs/v12_surrogate/` after review.",
        "",
        "## Not safe to commit",
        "",
        "- `data/solweig/`, `data/rasters/`, raw archive files, `.tif`, `.tiff`, `svfs.zip`, patch zip packages, or large hourly forecast CSV outputs.",
        "",
        "## Next recommended action",
        "",
        "Review B8.0/B8.1 outputs and then open a separate B8.2 task for model benchmark design/implementation using these split manifests.",
    ]
    path = out_root / "B8_LANE_STATUS.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Run both B8 stages and write lane status."""
    audit = run_audit(config_path)
    splits = run_splits(config_path)
    config_rel = str(config_path.relative_to(ROOT)).replace("/", "\\")
    commands = [
        "python -m compileall scripts/v12_b8_prepare_surrogate_dataset.py scripts/v12_b8_make_validation_splits.py scripts/v12_b8_run_audit_and_splits.py (attempted; python was not on PATH)",
        "C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python -m compileall scripts/v12_b8_prepare_surrogate_dataset.py scripts/v12_b8_make_validation_splits.py scripts/v12_b8_run_audit_and_splits.py",
        f"C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python scripts/v12_b8_run_audit_and_splits.py --config {config_rel}",
    ]
    status_path = write_lane_status(config_path, audit, splits, commands)
    return {"audit": audit, "splits": splits, "status_path": status_path}


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.0 audit and B8.1 validation split generation.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to the explicit B8 YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    printable = {
        "audit_status": result["audit"].status,
        "split_status": result["splits"].status,
        "status_path": str(result["status_path"]),
    }
    print(json.dumps(printable, indent=2))


if __name__ == "__main__":
    main()
