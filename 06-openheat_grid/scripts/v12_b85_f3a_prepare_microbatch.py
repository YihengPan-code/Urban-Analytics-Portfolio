"""Prepare the B8.5-F3a controlled QGIS/SOLWEIG micro-batch package.

Inputs:
    configs/v12/systemb_b85_f3a_microbatch_execution.yaml
    outputs/v12_surrogate/b8_5_f2d_readiness_final/B8_5_F2D_STATUS.md
    outputs/v12_surrogate/b8_5_f2d_readiness_final/b85_f2d_readiness_summary.csv
    outputs/v12_surrogate/b8_5_f2d_readiness_final/b85_f2d_run_readiness.csv
    scripts/qgis/v12_b85_qgis_solweig_execution_SKELETON.py
    outputs/v12_surrogate/b8_5_execution_package/b85_f1_qgis_parameter_contract.csv

Outputs:
    docs/v12/OpenHeat_SystemB_B8_5_F3a_microbatch_execution_CN.md
    outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_microbatch_manifest.csv
    outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_pre_execution_asset_check.csv
    outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_expected_run_log_schema.csv
    outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_manual_qgis_run_instructions.md
    outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_postrun_validation.csv
    outputs/v12_surrogate/b8_5_f3a_microbatch/B8_5_F3A_STATUS.md

Saved metrics:
    Selected cell_id, four-run manifest rows, per-run pre-execution readiness
    flags, expected run-log schema, expected local-only SOLWEIG output paths,
    postrun placeholder status, and final preparation decision status.

This script does not run QGIS, run SOLWEIG, create/copy/open rasters, copy/open
svfs.zip, create AOI-wide predictions, compute local WBGT, create hazard_score
or risk_score outputs, create System A/B coupling outputs, stage files, or
commit files. It consumes F2d readiness metadata and writes compact CSV/Markdown
control artifacts only.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f3a_microbatch_execution.yaml"

YES = "yes"
NO = "no"
PASS = "PASS"
BLOCKED = "BLOCKED"
FAILED = "FAILED"
READY_FOR_HUMAN_MICROBATCH = "READY_FOR_HUMAN_MICROBATCH"
NOT_RUN_YET = "NOT_RUN_YET"

FORBIDDEN_SCOPE_TRUE_KEYS = {
    "qgis_executed_by_codex",
    "solweig_executed_by_codex",
    "create_rasters",
    "copy_rasters",
    "open_rasters",
    "copy_svf_zip",
    "open_svf_zip",
    "create_aoi_predictions",
    "create_local_wbgt",
    "create_hazard_score",
    "create_risk_score",
    "create_system_ab_coupling",
    "stage_changes",
    "commit_changes",
}


@dataclass(frozen=True)
class PrepareResult:
    """Compact result for the F3a preparation run."""

    decision_status: str
    selected_cell_id: str
    microbatch_run_count: int
    pre_execution_ready_count: int
    postrun_status: str
    local_run_log_path: Path
    files_created: list[Path]


def now_stamp() -> str:
    """Return a local timestamp for reports."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def path_text(path: Path | str) -> str:
    """Return a slash-separated path string without touching path contents."""
    return Path(path).as_posix()


def repo_path(value: str | Path) -> Path:
    """Resolve repository-relative paths against the OpenHeat subdirectory."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    """Return a repository-relative POSIX path when possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by project configs."""
    stripped = value.strip()
    if stripped == "[]":
        return []
    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"yes", "no"}:
        return lowered
    if lowered in {"null", "none", "~"}:
        return None
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        return stripped.strip("\"'")


def read_simple_yaml(path: Path) -> dict[str, Any]:
    """Read the simple nested YAML shape used by OpenHeat configs."""
    lines = [
        line.rstrip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for idx, line in enumerate(lines):
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if text.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"Unsupported YAML list placement: {line}")
            item_text = text[2:].strip()
            if ":" in item_text:
                key, _, raw_value = item_text.partition(":")
                item: dict[str, Any] = {key.strip(): parse_scalar(raw_value.strip())}
                parent.append(item)
                stack.append((indent, item))
            else:
                parent.append(parse_scalar(item_text))
            continue
        key, _, raw_value = text.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            if not isinstance(parent, dict):
                raise ValueError(f"Unsupported YAML mapping placement: {line}")
            parent[key] = parse_scalar(raw_value)
            continue
        next_container: Any = {}
        for future in lines[idx + 1 :]:
            future_indent = len(future) - len(future.lstrip(" "))
            future_text = future.strip()
            if future_indent <= indent:
                break
            next_container = [] if future_text.startswith("- ") else {}
            break
        if not isinstance(parent, dict):
            raise ValueError(f"Unsupported YAML parent for key: {line}")
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def read_config(path: Path) -> dict[str, Any]:
    """Load YAML, preferring PyYAML with a no-dependency fallback."""
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Config did not parse to a mapping: {path}")
        return loaded
    except ImportError:
        return read_simple_yaml(path)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV file into dictionaries."""
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """Write a compact UTF-8 CSV artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_text(path: Path, text: str) -> None:
    """Write a UTF-8 Markdown artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def normalize_yes(value: Any) -> bool:
    """Return True for project yes-like values."""
    return clean(value).lower() in {"yes", "true", "pass", "ready_for_manual_qgis"}


def normalize_pass(value: Any) -> bool:
    """Return True for project PASS-like values."""
    return clean(value).upper() == PASS


def sorted_unique(values: Iterable[Any]) -> list[str]:
    """Return sorted unique non-empty values."""
    return sorted({clean(value) for value in values if clean(value)})


def ensure_scope_is_preparation_only(config: dict[str, Any]) -> None:
    """Refuse a config that asks Python/Codex to cross execution boundaries."""
    scope = config.get("scope", {})
    bad = [key for key in FORBIDDEN_SCOPE_TRUE_KEYS if bool(scope.get(key))]
    if bad:
        raise ValueError(f"Forbidden scope flags must remain false: {', '.join(sorted(bad))}")
    if not bool(scope.get("microbatch_execution_package_only")):
        raise ValueError("scope.microbatch_execution_package_only must be true.")
    if not bool(scope.get("dry_run_default_for_repo_runner")):
        raise ValueError("scope.dry_run_default_for_repo_runner must be true.")


def expected_combo_count(config: dict[str, Any]) -> int:
    """Return the expected micro-batch run count from forcing days x scenarios."""
    micro = config["microbatch"]
    return len(micro["forcing_days"]) * len(micro["scenarios"])


def is_target_row(config: dict[str, Any], row: dict[str, str]) -> bool:
    """Return whether an F2d readiness row belongs to the requested micro-batch."""
    micro = config["microbatch"]
    return (
        row.get("forcing_day_id") in set(micro["forcing_days"])
        and clean(row.get("hour_sgt")) == clean(micro["hour_sgt"])
        and row.get("scenario") in set(micro["scenarios"])
    )


def f2d_row_ready(row: dict[str, str]) -> bool:
    """Return whether the F2d readiness row passes all required prechecks."""
    return (
        normalize_yes(row.get("cell_geometry_ready"))
        and normalize_yes(row.get("raster_tiles_ready"))
        and normalize_yes(row.get("svf_ready"))
        and normalize_yes(row.get("met_forcing_ready"))
        and normalize_yes(row.get("output_root_ready"))
        and normalize_pass(row.get("qgis_manual_check_status"))
        and normalize_yes(row.get("ready_for_manual_qgis"))
        and clean(row.get("run_readiness")).lower() == "ready_for_manual_qgis"
    )


def select_cell_id(config: dict[str, Any], rows: list[dict[str, str]]) -> str:
    """Choose TP_0037 if present, otherwise the first fully ready F2d cell."""
    target_rows = [row for row in rows if is_target_row(config, row)]
    preferred = str(config["microbatch"]["preferred_cell_id"])
    expected = expected_combo_count(config)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in target_rows:
        grouped[row.get("cell_id", "")].append(row)

    if len(grouped.get(preferred, [])) == expected:
        return preferred

    for cell_id in sorted(grouped):
        cell_rows = grouped[cell_id]
        if len(cell_rows) == expected and all(f2d_row_ready(row) for row in cell_rows):
            return cell_id
    raise ValueError("No F2d cell has the requested four ready micro-batch rows.")


def ordered_selected_rows(config: dict[str, Any], rows: list[dict[str, str]], cell_id: str) -> list[dict[str, str]]:
    """Return selected F2d rows ordered by forcing day then scenario."""
    selected = [row for row in rows if row.get("cell_id") == cell_id and is_target_row(config, row)]
    by_key = {(row["forcing_day_id"], row["scenario"]): row for row in selected}
    ordered: list[dict[str, str]] = []
    for forcing_day in config["microbatch"]["forcing_days"]:
        for scenario in config["microbatch"]["scenarios"]:
            key = (forcing_day, scenario)
            if key not in by_key:
                raise ValueError(f"Missing F2d readiness row for {cell_id} {forcing_day} {scenario}.")
            ordered.append(by_key[key])
    return ordered


def scenario_dir(scenario: str) -> str:
    """Return the compact scenario folder name used by historical outputs."""
    if scenario == "base":
        return "base"
    if scenario == "overhead_as_canopy":
        return "overhead"
    raise ValueError(f"Unknown scenario: {scenario}")


def build_manifest_rows(config: dict[str, Any], rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Build the four-row F3a manifest from selected F2d readiness metadata."""
    output_root = Path(str(config["microbatch"]["local_solweig_output_root"]))
    prefix = str(config["microbatch"]["output_group_prefix"])
    manifest_rows: list[dict[str, str]] = []
    for row in rows:
        hour = int(clean(row["hour_sgt"]))
        scen_dir = scenario_dir(row["scenario"])
        run_id = f"b85_f3a_{row['forcing_day_id']}_{row['cell_id']}_{scen_dir}_h{hour:02d}"
        output_group = f"{prefix}/{row['forcing_day_id']}/{row['cell_id']}/{scen_dir}/h{hour:02d}"
        output_dir = output_root / output_group
        tmrt_path = output_dir / "Tmrt_average.tif"
        manifest_rows.append(
            {
                "run_id": run_id,
                "cell_id": row["cell_id"],
                "forcing_day_id": row["forcing_day_id"],
                "date": row["date"],
                "hour_sgt": str(hour),
                "scenario": row["scenario"],
                "expected_output_group": output_group,
                "expected_output_dir": output_dir.as_posix(),
                "expected_tmrt_path": tmrt_path.as_posix(),
                "expected_output_paths": tmrt_path.as_posix(),
                "source_f2d_run_id": row.get("run_id", ""),
                "source_f2d_expected_output_dir": row.get("expected_output_dir", ""),
                "qgis_solweig_executed": NO,
            }
        )
    return manifest_rows


def blocker_text(row: dict[str, str]) -> str:
    """Return a compact blocker summary for one F2d row."""
    blockers: list[str] = []
    if not normalize_yes(row.get("cell_geometry_ready")):
        blockers.append("cell_geometry_not_ready")
    if not normalize_yes(row.get("raster_tiles_ready")):
        blockers.append("raster_tiles_not_ready")
    if not normalize_yes(row.get("svf_ready")):
        blockers.append("svf_not_ready")
    if not normalize_yes(row.get("met_forcing_ready")):
        blockers.append("met_forcing_not_ready")
    if not normalize_yes(row.get("output_root_ready")):
        blockers.append("output_root_not_ready")
    if not normalize_pass(row.get("qgis_manual_check_status")):
        blockers.append("qgis_manual_check_not_pass")
    if not normalize_yes(row.get("ready_for_manual_qgis")):
        blockers.append("f2d_ready_for_manual_qgis_not_yes")
    return "none" if not blockers else "; ".join(blockers)


def build_precheck_rows(
    manifest_rows: list[dict[str, str]], selected_f2d_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Build the per-run pre-execution asset check."""
    precheck_rows: list[dict[str, str]] = []
    for manifest_row, f2d_row in zip(manifest_rows, selected_f2d_rows):
        ready = f2d_row_ready(f2d_row)
        blockers = blocker_text(f2d_row)
        precheck_rows.append(
            {
                "run_id": manifest_row["run_id"],
                "cell_id": manifest_row["cell_id"],
                "forcing_day_id": manifest_row["forcing_day_id"],
                "date": manifest_row["date"],
                "hour_sgt": manifest_row["hour_sgt"],
                "scenario": manifest_row["scenario"],
                "cell_geometry_ready": clean(f2d_row.get("cell_geometry_ready")),
                "raster_tiles_ready": clean(f2d_row.get("raster_tiles_ready")),
                "svf_ready": clean(f2d_row.get("svf_ready")),
                "met_forcing_ready": clean(f2d_row.get("met_forcing_ready")),
                "output_root_ready": clean(f2d_row.get("output_root_ready")),
                "qgis_manual_check_status": clean(f2d_row.get("qgis_manual_check_status")),
                "run_ready": YES if ready else NO,
                "pre_execution_status": PASS if ready else BLOCKED,
                "blockers": blockers,
                "notes": "Derived from F2d readiness metadata; no raster or svfs.zip content opened.",
            }
        )
    return precheck_rows


def expected_run_log_schema_rows() -> list[dict[str, str]]:
    """Return the expected local QGIS run-log schema."""
    return [
        {
            "column_name": "run_id",
            "dtype": "string",
            "required": YES,
            "allowed_values_or_format": "unique F3a manifest run_id",
            "description": "Primary micro-batch run key.",
        },
        {
            "column_name": "cell_id",
            "dtype": "string",
            "required": YES,
            "allowed_values_or_format": "TP_####",
            "description": "Focus cell identifier.",
        },
        {
            "column_name": "forcing_day_id",
            "dtype": "string",
            "required": YES,
            "allowed_values_or_format": "FD01_high_shortwave_hot_20260507|FD02_humid_hot_cloudy_or_diffuse_20260508",
            "description": "Selected forcing day key.",
        },
        {
            "column_name": "date",
            "dtype": "date",
            "required": YES,
            "allowed_values_or_format": "YYYY-MM-DD",
            "description": "Forcing day date in Singapore local time.",
        },
        {
            "column_name": "hour_sgt",
            "dtype": "integer",
            "required": YES,
            "allowed_values_or_format": "13",
            "description": "Execution hour in Singapore Standard Time.",
        },
        {
            "column_name": "scenario",
            "dtype": "string",
            "required": YES,
            "allowed_values_or_format": "base|overhead_as_canopy",
            "description": "SOLWEIG scenario.",
        },
        {
            "column_name": "started_at",
            "dtype": "datetime",
            "required": YES,
            "allowed_values_or_format": "ISO-8601 local timestamp",
            "description": "Manual QGIS attempt start time.",
        },
        {
            "column_name": "completed_at",
            "dtype": "datetime",
            "required": YES,
            "allowed_values_or_format": "ISO-8601 local timestamp",
            "description": "Manual QGIS attempt completion time.",
        },
        {
            "column_name": "status",
            "dtype": "string",
            "required": YES,
            "allowed_values_or_format": "dry_run|success|failed|skipped|blocked",
            "description": "Manual execution status; repo-tracked runner defaults to dry_run.",
        },
        {
            "column_name": "error_message",
            "dtype": "string",
            "required": NO,
            "allowed_values_or_format": "free text",
            "description": "Error details only when status is failed or blocked.",
        },
        {
            "column_name": "expected_output_dir",
            "dtype": "string",
            "required": YES,
            "allowed_values_or_format": "C:/OpenHeat-local/solweig/b85_f1_tiles/...",
            "description": "Local-only SOLWEIG output directory; never Git-tracked.",
        },
        {
            "column_name": "expected_tmrt_path",
            "dtype": "string",
            "required": YES,
            "allowed_values_or_format": "C:/OpenHeat-local/solweig/b85_f1_tiles/.../Tmrt_average.tif",
            "description": "Expected Tmrt raster path for existence/size validation only.",
        },
        {
            "column_name": "expected_output_paths",
            "dtype": "string",
            "required": YES,
            "allowed_values_or_format": "semicolon-separated local-only paths",
            "description": "Expected output paths recorded by the QGIS runner.",
        },
        {
            "column_name": "notes",
            "dtype": "string",
            "required": NO,
            "allowed_values_or_format": "free text",
            "description": "Manual-review comments.",
        },
    ]


def build_postrun_placeholder_rows(manifest_rows: list[dict[str, str]], log_path: Path) -> list[dict[str, str]]:
    """Write NOT_RUN_YET rows before any human QGIS/SOLWEIG run log exists."""
    run_log_exists = YES if log_path.exists() else NO
    status = "RUN_LOG_PRESENT_VALIDATE_NEXT" if log_path.exists() else NOT_RUN_YET
    rows: list[dict[str, str]] = []
    for row in manifest_rows:
        rows.append(
            {
                "run_id": row["run_id"],
                "phase": "PREPARED",
                "postrun_status": status,
                "run_log_exists": run_log_exists,
                "run_log_status": "",
                "expected_tmrt_path": row["expected_tmrt_path"],
                "file_exists": "",
                "file_size_bytes": "",
                "validation_status": status,
                "notes": "No local run log has been validated yet; preparation is separate from execution.",
            }
        )
    return rows


def output_paths(config: dict[str, Any]) -> list[Path]:
    """Return the compact artifacts owned by this lane."""
    outputs = config["outputs"]
    return [
        DEFAULT_CONFIG,
        ROOT / "scripts/v12_b85_f3a_prepare_microbatch.py",
        ROOT / "scripts/v12_b85_f3a_validate_microbatch.py",
        repo_path(config["qgis_execution"]["runner_script"]),
        repo_path(outputs["canonical_note_cn"]),
        repo_path(outputs["manifest"]),
        repo_path(outputs["pre_execution_asset_check"]),
        repo_path(outputs["expected_run_log_schema"]),
        repo_path(outputs["manual_qgis_run_instructions"]),
        repo_path(outputs["postrun_validation"]),
        repo_path(outputs["status"]),
    ]


def write_manual_instructions(
    path: Path,
    config: dict[str, Any],
    selected_cell_id: str,
    decision_status: str,
    ready_count: int,
) -> None:
    """Write the human-only QGIS micro-batch run instructions."""
    manifest = repo_path(config["outputs"]["manifest"])
    runner = repo_path(config["qgis_execution"]["runner_script"])
    local_copy_root = Path(str(config["microbatch"]["local_runner_copy_root"]))
    local_log = Path(str(config["microbatch"]["local_run_log_path"]))
    output_root = Path(str(config["microbatch"]["local_solweig_output_root"]))
    text = f"""# B8.5-F3a Manual QGIS Micro-Batch Instructions

Generated: {now_stamp()}

## Decision

`{decision_status}`

## Micro-Batch

- Cell: `{selected_cell_id}`
- Forcing days: `{', '.join(config['microbatch']['forcing_days'])}`
- Hour SGT: `{config['microbatch']['hour_sgt']}`
- Scenarios: `{', '.join(config['microbatch']['scenarios'])}`
- Expected run count: `{config['microbatch']['expected_run_count']}`
- Pre-execution ready count: `{ready_count}/{config['microbatch']['expected_run_count']}`

## Human Gate

Codex/Python did not run QGIS or SOLWEIG. This package authorizes only a 4-run human-controlled smoke test after review. It is not B9, not local WBGT, not risk, and not permission for a full 480-run execution.

## Required Manual Steps

1. Review the manifest: `{rel(manifest)}`.
2. Review the repo-tracked runner without changing it: `{rel(runner)}`.
3. Copy the runner to a local-only path under `{local_copy_root.as_posix()}`.
4. In the local-only copy only, manually change `DRY_RUN = False` after confirming QGIS/UMEP and all assets.
5. Run only the four manifest rows. DO NOT RUN FULL 480.
6. Keep the run log at `{local_log.as_posix()}`.
7. Keep SOLWEIG outputs under `{output_root.as_posix()}` only.
8. Do not commit rasters, `svfs.zip`, or any local-only output.

## After Manual Execution

Run `python scripts/v12_b85_f3a_validate_microbatch.py --config configs/v12/systemb_b85_f3a_microbatch_execution.yaml`.
Full 480 execution remains blocked until this micro-batch validation passes.
"""
    write_text(path, text)


def write_cn_doc(
    path: Path,
    config: dict[str, Any],
    selected_cell_id: str,
    decision_status: str,
    ready_count: int,
    postrun_status: str,
) -> None:
    """Write the UTF-8 Chinese control note for the F3a micro-batch."""
    text = f"""# OpenHeat System B B8.5-F3a 微批次执行包中文说明

生成时间：{now_stamp()}

## 结论

- 决策状态：`{decision_status}`
- 选择 cell_id：`{selected_cell_id}`
- 微批次数量：`{config['microbatch']['expected_run_count']}`
- 预执行 ready 数量：`{ready_count}/{config['microbatch']['expected_run_count']}`
- postrun 状态：`{postrun_status}`
- 预期本地 run log：`{config['microbatch']['local_run_log_path']}`

## 微批次设计

本轮只准备 4 个由人工控制的 QGIS/SOLWEIG smoke test：

- forcing day：`FD01_high_shortwave_hot_20260507` 与 `FD02_humid_hot_cloudy_or_diffuse_20260508`
- hour_sgt：`13`
- scenario：`base` 与 `overhead_as_canopy`
- 输出根目录只能是：`{config['microbatch']['local_solweig_output_root']}`

## 边界声明

- Codex/Python 没有运行 QGIS/SOLWEIG。
- 本 lane 没有创建、复制或打开任何 raster。
- 本 lane 没有复制或打开 `svfs.zip`。
- 这不是 B9。
- 这不是 local WBGT。
- 这不是 risk。
- 本 lane 没有创建 AOI-wide prediction、local WBGT、hazard_score、risk_score 或 System A/B coupling 输出。
- 本说明只授权 4-run human-controlled micro-batch。
- Full 480 execution 在 micro-batch validation 通过前仍然 blocked。

## 执行方式

仓库中的 QGIS runner 默认 `DRY_RUN=True`。如果人工审查后要真正执行，必须把 runner 复制到本地非 Git 路径，并且只在本地副本中手动改为 `DRY_RUN=False`。真实 SOLWEIG 输出只能写入 `C:/OpenHeat-local/solweig/b85_f1_tiles/...`，run log 只能写入 `C:/OpenHeat-local/solweig/b85_f3a_microbatch/run_logs/...`。

## 验证方式

准备阶段只检查 F2d readiness 元数据并写出 manifest、pre-execution asset check、run-log schema 和人工执行说明。postrun validator 不读取 raster 内容；它只检查本地 run log 状态、预期输出路径是否存在、以及文件大小是否大于 0。若人工尚未执行，validator 会输出 `NOT_RUN_YET`，不会把“未执行”误报为失败。
"""
    write_text(path, text)


def write_status_report(
    path: Path,
    config: dict[str, Any],
    decision_status: str,
    selected_cell_id: str,
    run_count: int,
    ready_count: int,
    postrun_status: str,
    files_created: list[Path],
    notes: str,
) -> None:
    """Write the lane status Markdown."""
    files_block = "\n".join(f"- `{rel(path_item)}`" for path_item in files_created)
    text = f"""# B8.5-F3a Status

Generated: {now_stamp()}

## Status

`{decision_status}`

## Branch

`{config['branch']}`

## Scope

Micro-batch execution package and postrun validator only. Codex/Python did not run QGIS/SOLWEIG. No rasters were created, copied, or opened by this lane. `svfs.zip` was not copied or opened. This is not B9. This is not local WBGT. This is not risk. This authorizes only a 4-run human-controlled micro-batch. Full 480 execution remains blocked until micro-batch validation passes.

## Key Results

- Selected cell_id: `{selected_cell_id}`
- Micro-batch run count: `{run_count}`
- Pre-execution ready count: `{ready_count}/{config['microbatch']['expected_run_count']}`
- Postrun status: `{postrun_status}`
- Local run log path expected: `{config['microbatch']['local_run_log_path']}`
- QGIS/SOLWEIG executed by Codex: `no`
- Notes: {notes}

## Files Created / Modified

{files_block}

## Commands To Verify

- `python -m compileall scripts/v12_b85_f3a_prepare_microbatch.py scripts/v12_b85_f3a_validate_microbatch.py scripts/qgis/v12_b85_f3a_microbatch_qgis_runner.py`
- `python scripts/v12_b85_f3a_prepare_microbatch.py --config configs/v12/systemb_b85_f3a_microbatch_execution.yaml`
- `python scripts/v12_b85_f3a_validate_microbatch.py --config configs/v12/systemb_b85_f3a_microbatch_execution.yaml`
- `git status --short -- .`

## Safe To Commit

Only compact config, scripts, docs, CSV, and Markdown control artifacts listed above after review.

## Not Safe To Commit

Rasters, `data/solweig/`, `data/rasters/`, `.tif`, `.tiff`, `svfs.zip`, raw archive dumps, patch zip packages, and large forecast CSV files.
"""
    write_text(path, text)


def write_outputs(config: dict[str, Any]) -> PrepareResult:
    """Prepare all F3a compact control artifacts."""
    ensure_scope_is_preparation_only(config)
    outputs = config["outputs"]
    f2d_rows = read_csv_rows(repo_path(config["inputs"]["f2d_run_readiness"]))
    selected_cell_id = select_cell_id(config, f2d_rows)
    selected_rows = ordered_selected_rows(config, f2d_rows, selected_cell_id)
    manifest_rows = build_manifest_rows(config, selected_rows)
    expected_runs = int(config["microbatch"]["expected_run_count"])
    if expected_runs != expected_combo_count(config):
        raise ValueError("microbatch.expected_run_count does not match forcing_days x scenarios.")
    if len(manifest_rows) != expected_runs:
        raise ValueError(f"Expected {expected_runs} manifest rows, observed {len(manifest_rows)}.")

    precheck_rows = build_precheck_rows(manifest_rows, selected_rows)
    ready_count = sum(1 for row in precheck_rows if row["run_ready"] == YES)
    local_run_log_path = Path(str(config["microbatch"]["local_run_log_path"]))
    postrun_status = NOT_RUN_YET if not local_run_log_path.exists() else "RUN_LOG_PRESENT_VALIDATE_NEXT"
    decision_status = READY_FOR_HUMAN_MICROBATCH if ready_count == expected_runs else BLOCKED
    notes = "Prepared only; execution has not been performed by Codex/Python."

    write_csv_rows(
        repo_path(outputs["manifest"]),
        manifest_rows,
        [
            "run_id",
            "cell_id",
            "forcing_day_id",
            "date",
            "hour_sgt",
            "scenario",
            "expected_output_group",
            "expected_output_dir",
            "expected_tmrt_path",
            "expected_output_paths",
            "source_f2d_run_id",
            "source_f2d_expected_output_dir",
            "qgis_solweig_executed",
        ],
    )
    write_csv_rows(
        repo_path(outputs["pre_execution_asset_check"]),
        precheck_rows,
        [
            "run_id",
            "cell_id",
            "forcing_day_id",
            "date",
            "hour_sgt",
            "scenario",
            "cell_geometry_ready",
            "raster_tiles_ready",
            "svf_ready",
            "met_forcing_ready",
            "output_root_ready",
            "qgis_manual_check_status",
            "run_ready",
            "pre_execution_status",
            "blockers",
            "notes",
        ],
    )
    write_csv_rows(
        repo_path(outputs["expected_run_log_schema"]),
        expected_run_log_schema_rows(),
        ["column_name", "dtype", "required", "allowed_values_or_format", "description"],
    )
    write_csv_rows(
        repo_path(outputs["postrun_validation"]),
        build_postrun_placeholder_rows(manifest_rows, local_run_log_path),
        [
            "run_id",
            "phase",
            "postrun_status",
            "run_log_exists",
            "run_log_status",
            "expected_tmrt_path",
            "file_exists",
            "file_size_bytes",
            "validation_status",
            "notes",
        ],
    )
    write_manual_instructions(
        repo_path(outputs["manual_qgis_run_instructions"]),
        config,
        selected_cell_id,
        decision_status,
        ready_count,
    )
    write_cn_doc(
        repo_path(outputs["canonical_note_cn"]),
        config,
        selected_cell_id,
        decision_status,
        ready_count,
        postrun_status,
    )
    files_created = output_paths(config)
    write_status_report(
        repo_path(outputs["status"]),
        config,
        decision_status,
        selected_cell_id,
        len(manifest_rows),
        ready_count,
        postrun_status,
        files_created,
        notes,
    )
    return PrepareResult(
        decision_status=decision_status,
        selected_cell_id=selected_cell_id,
        microbatch_run_count=len(manifest_rows),
        pre_execution_ready_count=ready_count,
        postrun_status=postrun_status,
        local_run_log_path=local_run_log_path,
        files_created=files_created,
    )


def prepare(config_path: Path) -> PrepareResult:
    """Load the config and prepare the micro-batch package."""
    config = read_config(repo_path(config_path))
    return write_outputs(config)


def main() -> int:
    """Parse CLI arguments and prepare the F3a micro-batch package."""
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the B8.5-F3a four-run QGIS/SOLWEIG micro-batch control package. "
            "Does not run QGIS/SOLWEIG or open raster/SVF contents."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="F3a YAML config path.")
    args = parser.parse_args()
    try:
        result = prepare(args.config)
    except Exception as exc:
        print(f"Status: {FAILED}")
        print(f"Error: {exc}")
        return 1
    print(f"Status: {result.decision_status}")
    print(f"Selected cell_id: {result.selected_cell_id}")
    print(f"Micro-batch run count: {result.microbatch_run_count}")
    print(f"Pre-execution ready count: {result.pre_execution_ready_count}")
    print(f"Postrun status: {result.postrun_status}")
    print(f"Local run log path expected: {result.local_run_log_path.as_posix()}")
    print("QGIS/SOLWEIG executed by Codex: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {rel(path)}")
    return 0 if result.decision_status == READY_FOR_HUMAN_MICROBATCH else 2


if __name__ == "__main__":
    raise SystemExit(main())
