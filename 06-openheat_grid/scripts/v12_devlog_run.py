"""Run the OpenHeat 2026-05-28 development-log generation pipeline.

Inputs:
  - A JSON-compatible YAML config passed with ``--config``.

Outputs:
  - All CSV and Markdown artifacts declared by the config:
    input/file inventories, lane matrices, decision registers, claim boundary
    matrix, future action matrix, status Markdown, report Markdown, handoff
    docs, active dev board, and roadmap update.

Saved metrics:
  - pipeline status, inventoried lane count, missing/unreadable artifact count,
    generated document paths, and forbidden heavy-file status summary.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


FORBIDDEN_PATTERNS = (
    ".tif",
    ".tiff",
    ".vrt",
    ".asc",
    ".img",
    ".nc",
    ".grib",
    "svfs.zip",
    "data/solweig",
    "data/rasters",
    "data/archive",
    "hourly_grid_heatstress_forecast",
)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Run inventory, lane summary, and handoff builders for the devlog."
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to JSON-compatible YAML config declaring inputs and outputs.",
    )
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    """Load a JSON-compatible YAML config."""

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_path(path_value: str, base_dir: Path) -> Path:
    """Resolve a config path relative to the current worktree."""

    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def run_script(script_name: str, config_path: Path) -> None:
    """Run a sibling script with the current Python interpreter."""

    script_path = Path(__file__).resolve().parent / script_name
    subprocess.run(
        [sys.executable, str(script_path), "--config", str(config_path)],
        cwd=Path.cwd(),
        check=True,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read CSV rows."""

    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def git_short_status(cwd: Path) -> str:
    """Return git short status for the current worktree path."""

    result = subprocess.run(
        ["git", "status", "--short", "--", "."],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.rstrip()


def forbidden_heavy_status(git_status: str) -> str:
    """Return a compact forbidden-heavy-file check over git status paths."""

    lowered = git_status.lower().replace("\\", "/")
    hits = [pattern for pattern in FORBIDDEN_PATTERNS if pattern in lowered]
    if not hits:
        return "PASS:no forbidden heavy/status paths in git status --short -- ."
    return "FAIL:" + ";".join(hits)


def main() -> None:
    """CLI entrypoint."""

    args = parse_args()
    cwd = Path.cwd()
    config = load_config(args.config)
    outputs = config["outputs"]

    run_script("v12_devlog_inventory.py", args.config)
    run_script("v12_devlog_summarize_lanes.py", args.config)
    run_script("v12_devlog_build_handoff.py", args.config)

    missing_rows = read_csv(resolve_path(outputs["missing_artifacts_csv"], cwd))
    status_rows = read_csv(resolve_path(outputs["status_matrix_csv"], cwd))
    git_status = git_short_status(cwd)
    heavy_status = forbidden_heavy_status(git_status)

    docs_created = [
        outputs["status_md"],
        outputs["report_md"],
        outputs["full_devlog_doc"],
        outputs["new_chat_context_doc"],
        outputs["active_dev_board_doc"],
        outputs["roadmap_update_doc"],
    ]

    print("=== OPENHEAT DEVLOG 2026-05-28 RESULT ===")
    print("Status: PASS_CREATED_DEVLOG_HANDOFF")
    print("System A current state: frozen/waiting; wbgt_a_c primary; optional diagnostics only")
    print("System B current state: B87G0 external-source-required; AOI/B9/WBGT/risk blocked")
    print("Best System B checkpoint: B87F2 true-vector/proxy feature patch")
    print("Stop/go decision: stop model tuning; external true-vector acquisition or close phase only")
    print("Docs created:")
    for path in docs_created:
        print(f"- {path}")
    print(f"Inventoried lanes: {len(status_rows)}")
    print(f"Missing/unreadable artifacts count: {len(missing_rows)}")
    print(f"Forbidden heavy-file check: {heavy_status}")
    print("Recommended next action: external true-vector acquisition or System B closure note; System A formal snapshot only when real snapshot exists")
    print("git status --short -- .")
    print(git_status if git_status else "(clean)")


if __name__ == "__main__":
    main()
