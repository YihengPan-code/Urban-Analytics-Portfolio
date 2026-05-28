"""Create lane summary matrices for the OpenHeat 2026-05-28 development log.

Inputs:
  - A JSON-compatible YAML config passed with ``--config``.
  - The config declares lane metadata, decisions, claim boundaries, future
    actions, source roots, and output CSV paths.

Outputs:
  - ``openheat_devlog_lane_timeline.csv``
  - ``openheat_devlog_status_matrix.csv``
  - ``openheat_devlog_artifact_matrix.csv``
  - ``openheat_devlog_decision_register.csv``
  - ``openheat_devlog_claim_boundary_matrix.csv``
  - ``openheat_devlog_future_action_matrix.csv``

Saved metrics:
  - lane sequence, status, classification, branch, artifact existence,
    source-root selection, accepted decisions, stop conditions, and forbidden
    actions.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Build lane timeline, status, artifact, decision, claim, and future-action matrices."
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


def source_roots(config: dict[str, Any], base_dir: Path) -> list[dict[str, Any]]:
    """Return configured source roots with resolved paths."""

    roots: list[dict[str, Any]] = []
    for item in config["source_roots"]:
        roots.append({"id": item["id"], "path": resolve_path(item["path"], base_dir)})
    return roots


def find_artifact(relative_path: str, roots: list[dict[str, Any]]) -> tuple[str, str, str]:
    """Find the first matching artifact across roots."""

    rel = Path(relative_path)
    for root in roots:
        candidate = Path(root["path"]) / rel
        if candidate.exists():
            return "yes", str(root["id"]), str(candidate)
    return "no", "", ""


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    """Write rows to CSV with stable field order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def join_values(values: Any) -> str:
    """Join list-like config values for CSV cells."""

    if values is None:
        return ""
    if isinstance(values, list):
        return "; ".join(str(item) for item in values)
    return str(values)


def lane_timeline_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build lane timeline rows."""

    rows: list[dict[str, Any]] = []
    for lane in config["lanes"]:
        rows.append(
            {
                "sequence": lane["sequence"],
                "system": lane["system"],
                "lane_id": lane["lane_id"],
                "lane_name": lane["name"],
                "status": lane["status"],
                "classification": lane["classification"],
                "output_dir": lane["output_dir"],
                "key_quantitative_result": join_values(lane.get("quantitative_results", [])),
                "next_action": lane["next_action"],
            }
        )
    return rows


def status_matrix_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build lane status matrix rows."""

    rows: list[dict[str, Any]] = []
    for lane in config["lanes"]:
        rows.append(
            {
                "system": lane["system"],
                "lane_id": lane["lane_id"],
                "lane_name": lane["name"],
                "status": lane["status"],
                "classification": lane["classification"],
                "branch": lane.get("branch", ""),
                "purpose": lane["purpose"],
                "commands_recorded": join_values(lane.get("commands", [])),
                "configs": join_values(lane.get("configs", [])),
                "scripts": join_values(lane.get("scripts", [])),
                "docs": join_values(lane.get("docs", [])),
                "output_dir": lane["output_dir"],
                "key_outputs": join_values(lane.get("key_outputs", [])),
                "key_findings": join_values(lane.get("key_findings", [])),
                "accepted_conclusion": lane["accepted_conclusion"],
                "caveats": join_values(lane.get("caveats", [])),
                "forbidden_claims": join_values(lane.get("forbidden_claims", [])),
                "next_action": lane["next_action"],
                "reentry_command": lane.get("reentry_command", ""),
            }
        )
    return rows


def artifact_matrix_rows(config: dict[str, Any], roots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build lane artifact rows and resolve existence."""

    rows: list[dict[str, Any]] = []
    artifact_fields = [
        ("config", "configs"),
        ("script", "scripts"),
        ("doc", "docs"),
        ("key_output", "key_outputs"),
    ]
    for lane in config["lanes"]:
        for artifact_type, field in artifact_fields:
            for rel_path in lane.get(field, []):
                exists, root_id, source_path = find_artifact(rel_path, roots)
                rows.append(
                    {
                        "system": lane["system"],
                        "lane_id": lane["lane_id"],
                        "artifact_type": artifact_type,
                        "relative_path": rel_path,
                        "exists": exists,
                        "source_root_id": root_id,
                        "source_path": source_path,
                    }
                )
    return rows


def simple_rows(config: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Return simple matrix rows from config."""

    return [dict(row) for row in config.get(key, [])]


def main() -> None:
    """CLI entrypoint."""

    args = parse_args()
    base_dir = Path.cwd()
    config = load_config(args.config)
    outputs = config["outputs"]
    roots = source_roots(config, base_dir)

    write_csv(
        resolve_path(outputs["lane_timeline_csv"], base_dir),
        lane_timeline_rows(config),
        [
            "sequence",
            "system",
            "lane_id",
            "lane_name",
            "status",
            "classification",
            "output_dir",
            "key_quantitative_result",
            "next_action",
        ],
    )
    write_csv(
        resolve_path(outputs["status_matrix_csv"], base_dir),
        status_matrix_rows(config),
        [
            "system",
            "lane_id",
            "lane_name",
            "status",
            "classification",
            "branch",
            "purpose",
            "commands_recorded",
            "configs",
            "scripts",
            "docs",
            "output_dir",
            "key_outputs",
            "key_findings",
            "accepted_conclusion",
            "caveats",
            "forbidden_claims",
            "next_action",
            "reentry_command",
        ],
    )
    write_csv(
        resolve_path(outputs["artifact_matrix_csv"], base_dir),
        artifact_matrix_rows(config, roots),
        [
            "system",
            "lane_id",
            "artifact_type",
            "relative_path",
            "exists",
            "source_root_id",
            "source_path",
        ],
    )
    write_csv(
        resolve_path(outputs["decision_register_csv"], base_dir),
        simple_rows(config, "decision_register"),
        [
            "decision_id",
            "system",
            "decision",
            "status",
            "evidence",
            "accepted_interpretation",
            "forbidden_interpretation",
        ],
    )
    write_csv(
        resolve_path(outputs["claim_boundary_csv"], base_dir),
        simple_rows(config, "claim_boundaries"),
        ["claim", "decision", "allowed_wording", "forbidden_upgrade", "rationale"],
    )
    write_csv(
        resolve_path(outputs["future_action_csv"], base_dir),
        simple_rows(config, "future_actions"),
        [
            "action_id",
            "allowed_next_action",
            "prerequisites",
            "command_or_prompt_path",
            "expected_benefit",
            "risk",
            "stop_condition",
            "forbidden_action",
        ],
    )
    print(f"summarize_complete lanes={len(config['lanes'])}")


if __name__ == "__main__":
    main()
