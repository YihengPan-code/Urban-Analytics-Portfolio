#!/usr/bin/env python
"""Create the System A A-L1H.2b Level 1 high-tail integration package.

Inputs:
    - configs/v11/systema_l1h_level1_integration.yaml
    - Existing A-L1H source reports declared in the config. These are checked
      for presence only; no model matrices are read and no models are trained.

Outputs:
    - systema_l1h_evidence_ledger.csv
    - systema_l1h_output_contract.csv
    - systema_l1h_claim_boundary_matrix.csv
    - systema_l1h_decision_matrix.csv
    - systema_l1h_station_regime_caveats.csv
    - systema_l1h_next_gate_recommendations.csv
    - systema_l1h_integration_report.md
    - A_L1H_2B_STATUS.md
    - docs/v11/OpenHeat_SystemA_Level1_high_tail_integration_CN.md

Saved metrics:
    - Evidence-stage status and safe/forbidden claim boundaries.
    - Current System A Level 1 output contract.
    - Decision matrix, station/regime caveats, and next-gate recommendations.

Scope guard:
    This is an integration / model-card / output-contract task. It does not
    stage, commit, train models, rerun base WBGT models, implement formula-v2,
    implement probability calibration again, implement high-tail regression,
    start A-L2, touch System B or SOLWEIG outputs, or modify archive collector
    paths.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - used only in lean runtimes.
    yaml = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class IntegrationResult:
    """Headline result for the A-L1H.2b integration package."""

    status: str
    decision_status: str
    current_companion_definition: str
    reliability_assessment: str
    high_tail_assessment: str
    a_l2_decision: str
    a_l1h3_decision: str
    output_paths: list[Path]
    missing_sources: list[Path]


def rel(path: Path) -> str:
    """Return a project-relative POSIX path when possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(raw_path: str) -> Path:
    """Resolve an absolute or project-relative path."""
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return ROOT / path


def parse_scalar(value: str) -> Any:
    """Parse the scalar subset used by this explicit lane config."""
    value = value.strip()
    if value in {"", "null", "Null", "NULL"}:
        return None
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the narrow YAML subset used by the A-L1H.2b config."""
    raw_lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        raw_lines.append((indent, raw.strip()))

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(raw_lines):
            return {}, index
        if raw_lines[index][1].startswith("- "):
            values: list[Any] = []
            while index < len(raw_lines):
                line_indent, stripped = raw_lines[index]
                if line_indent != indent or not stripped.startswith("- "):
                    break
                item = stripped[2:].strip()
                index += 1
                if not item:
                    if index < len(raw_lines):
                        nested, index = parse_block(index, raw_lines[index][0])
                        values.append(nested)
                    continue
                key, separator, value = item.partition(":")
                if separator:
                    item_dict: dict[str, Any] = {}
                    if value.strip():
                        item_dict[key.strip()] = parse_scalar(value)
                    elif index < len(raw_lines) and raw_lines[index][0] > line_indent:
                        nested, index = parse_block(index, raw_lines[index][0])
                        item_dict[key.strip()] = nested
                    else:
                        item_dict[key.strip()] = {}
                    if index < len(raw_lines) and raw_lines[index][0] > line_indent:
                        extra, index = parse_block(index, raw_lines[index][0])
                        if isinstance(extra, dict):
                            item_dict.update(extra)
                    values.append(item_dict)
                else:
                    values.append(parse_scalar(item))
            return values, index

        mapping: dict[str, Any] = {}
        while index < len(raw_lines):
            line_indent, stripped = raw_lines[index]
            if line_indent != indent or stripped.startswith("- "):
                break
            key, separator, value = stripped.partition(":")
            if not separator:
                raise ValueError(f"Unexpected YAML line: {stripped}")
            index += 1
            if value.strip():
                mapping[key.strip()] = parse_scalar(value)
            elif index < len(raw_lines) and raw_lines[index][0] > line_indent:
                nested, index = parse_block(index, raw_lines[index][0])
                mapping[key.strip()] = nested
            else:
                mapping[key.strip()] = {}
        return mapping, index

    parsed, _ = parse_block(0, 0)
    if not isinstance(parsed, dict):
        raise ValueError("Config root must be a mapping.")
    return parsed


def load_config(path: Path) -> dict[str, Any]:
    """Read the A-L1H.2b YAML config."""
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(text)
    else:
        loaded = parse_simple_yaml(text)
    if not isinstance(loaded, dict):
        raise ValueError("Config root must be a mapping.")
    return loaded


def git_branch() -> str:
    """Return the active git branch when available."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def require_rows(config: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Return a list of mapping rows from the config."""
    rows = config.get(key, [])
    if not isinstance(rows, list):
        raise ValueError(f"{key} must be a list.")
    clean_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{key} rows must be mappings.")
        clean_rows.append(row)
    return clean_rows


def require_columns(config: dict[str, Any], key: str) -> list[str]:
    """Return configured output columns."""
    columns = config.get(key, [])
    if not isinstance(columns, list) or not all(isinstance(col, str) for col in columns):
        raise ValueError(f"{key} must be a list of column names.")
    return columns


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    """Write a deterministic UTF-8 CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def markdown_table(rows: list[dict[str, Any]], columns: list[str], limit: int | None = None) -> str:
    """Render a compact Markdown table."""
    selected = rows if limit is None else rows[:limit]
    if not selected:
        return "_No rows available._"
    body = [[str(row.get(column, "")) for column in columns] for row in selected]
    widths = [len(column) for column in columns]
    for row in body:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def render_row(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values)) + " |"

    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([render_row(columns), separator, *[render_row(row) for row in body]])


def bullet_lines(values: Iterable[str]) -> list[str]:
    """Render non-empty values as Markdown bullets."""
    return [f"- {value}" for value in values if value]


def source_paths(config: dict[str, Any]) -> list[Path]:
    """Return configured source report paths."""
    reports = config.get("source_reports", {})
    if not isinstance(reports, dict):
        raise ValueError("source_reports must be a mapping.")
    return [resolve_path(str(path)) for path in reports.values()]


def output_paths(config: dict[str, Any]) -> dict[str, Path]:
    """Build concrete output paths from config."""
    outputs = config["outputs"]
    output_dir = resolve_path(str(outputs["output_dir"]))
    return {
        "evidence_ledger": output_dir / str(outputs["evidence_ledger"]),
        "output_contract": output_dir / str(outputs["output_contract"]),
        "claim_boundary_matrix": output_dir / str(outputs["claim_boundary_matrix"]),
        "decision_matrix": output_dir / str(outputs["decision_matrix"]),
        "station_regime_caveats": output_dir / str(outputs["station_regime_caveats"]),
        "next_gate_recommendations": output_dir / str(outputs["next_gate_recommendations"]),
        "report": output_dir / str(outputs["report"]),
        "status": output_dir / str(outputs["status"]),
        "chinese_doc": resolve_path(str(outputs["chinese_doc"])),
    }


def write_report(
    path: Path,
    config: dict[str, Any],
    result: IntegrationResult,
    evidence_rows: list[dict[str, Any]],
    contract_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
    decision_rows: list[dict[str, Any]],
    caveat_rows: list[dict[str, Any]],
    gate_rows: list[dict[str, Any]],
) -> None:
    """Write the concise evidence-rich English integration report."""
    companion = config["companion"]
    status_line = result.status if not result.missing_sources else "BLOCKED"
    missing = ", ".join(rel(path) for path in result.missing_sources) or "none"
    lines = [
        "# System A A-L1H.2b Level 1 High-Tail Integration Report",
        "",
        f"Generated: {config.get('generated_date', date.today().isoformat())}",
        f"Status: `{status_line}`",
        f"Decision: `{result.decision_status}`",
        f"Branch: `{git_branch()}`",
        f"Missing configured source reports: `{missing}`",
        "",
        "## 1. What changed after A-L1H.0 to A-L1H.2",
        "",
        "A-L1H.0 established the main failure mode: deterministic System A WBGT_A scores remain useful for retrospective temporal severity, but the high tail is compressed around the ge31 threshold and station bias is visible. A-L1H.0b added partial weather-regime evidence, then A-L1H.0c replaced that partial coverage with full-period regime diagnostics. A-L1H.1 found that raw formula/proxy candidates were weak or negative and should not replace WBGT_A. A-L1H.2 then selected a score-to-event probability companion without retraining the base WBGT models.",
        "",
        markdown_table(
            evidence_rows,
            ["evidence_id", "status", "key_result", "safe_claim", "forbidden_claim"],
            limit=None,
        ),
        "",
        "## 2. Current companion",
        "",
        f"`P_ge31` is defined as: {companion['definition']}",
        "",
        f"Current companion definition: {result.current_companion_definition}",
        "",
        f"Headline metrics: Brier about {companion['brier']}, PR-AUC about {companion['pr_auc']}, selected threshold about {companion['threshold']}, precision {companion['precision']}, recall {companion['recall']}, F1 {companion['f1']}, CSI {companion['csi']}.",
        "",
        "The deterministic WBGT_A score remains the primary temporal severity diagnostic. P_ge31 is a retrospective diagnostic companion, not an official warning probability.",
        "",
        "## 3. What is reliable",
        "",
        result.reliability_assessment,
        "",
        "Reliable wording is limited to internal retrospective diagnostics: calibrated hourly WBGT_A temporal severity, station-held-out P_ge31 companion diagnostics, and evidence that ge31 capture improves relative to fixed score 31 behavior.",
        "",
        "## 4. What remains not solved",
        "",
        result.high_tail_assessment,
        "",
        "S142, S139, radiation-hot periods, very-high shortwave / shortwave_3h, low-support bins, and ge33 all remain caveats. These caveats are diagnostic review items, not causal corrections.",
        "",
        "## 5. Why A-L2 is deferred",
        "",
        result.a_l2_decision,
        "",
        "A-L2 would be station-context residual work. A-L1H.2b only records the current Level 1 contract and does not implement station-context correction.",
        "",
        "## 6. Whether to try other models now",
        "",
        result.a_l1h3_decision,
        "",
        "No broad model search is recommended inside this lane. A-L1H.3 high-tail regression can be opened later as a separate review gate if the user wants further high-tail improvement.",
        "",
        "## 7. Output contract",
        "",
        markdown_table(
            contract_rows,
            ["output_name", "current_role", "allowed_use", "forbidden_use", "contract_decision"],
            limit=None,
        ),
        "",
        "## 8. Claim boundaries",
        "",
        markdown_table(
            claim_rows,
            ["claim", "status", "allowed_wording", "forbidden_wording", "next_gate"],
            limit=None,
        ),
        "",
        "## 9. Decision matrix",
        "",
        markdown_table(
            decision_rows,
            ["question", "answer", "decision", "caveat"],
            limit=None,
        ),
        "",
        "## 10. Station and regime caveats",
        "",
        markdown_table(
            caveat_rows,
            ["topic", "interpretation", "safe_claim", "forbidden_claim"],
            limit=None,
        ),
        "",
        "## 11. Recommended next gates",
        "",
        markdown_table(
            gate_rows,
            ["recommendation", "decision", "rationale"],
            limit=None,
        ),
        "",
        "## Claim boundary reminder",
        "",
        "This package does not claim validated local 100m WBGT, official warning probability, prospective forecast skill, public-facing alerts, completed risk maps, or System A/B coupled risk.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_chinese_doc(path: Path, config: dict[str, Any], result: IntegrationResult) -> None:
    """Write the UTF-8 Chinese model-card note."""
    companion = config["companion"]
    lines = [
        "# OpenHeat System A Level 1 高尾部整合说明",
        "",
        "## 对应任务",
        "",
        "本文档对应 `A-L1H.2b — System A Level 1 high-tail integration / output contract`。",
        "本任务只做整合、模型卡和输出契约，不训练模型，不重新运行基础 WBGT 模型，不实现 formula-v2，不重新做概率校准，也不启动 A-L2。",
        "",
        "## 1. 从 A-L1H.0 到 A-L1H.2 的变化",
        "",
        "- A-L1H.0 发现了全局高尾部压缩和站点偏差：固定 31 分数阈值漏掉了较多观测 ge31 事件。",
        "- A-L1H.0b 做了部分天气情景合并，保留率只有 40.3%，因此只能作为部分时期诊断证据。",
        "- A-L1H.0c 恢复了全时期天气情景覆盖，6696/6696 行匹配成功；radiation-hot 情景包含了大部分 ge31 事件和漏报，但这仍然不是因果证明。",
        "- A-L1H.1 审计了公式和物理代理路线，结论是 `WEAK_OR_NEGATIVE`；原始公式或代理候选没有产生 fixed_31 crossing。",
        "- A-L1H.2 接受了一个概率伴随诊断量：`M4_inertia_ridge + isotonic_score_only`，验证方式为 `station_grouped_loso`。",
        "",
        "## 2. 当前伴随量是什么",
        "",
        f"`P_ge31` 的当前定义是：{companion['definition']}",
        "",
        f"当前推荐候选：`{companion['selected_candidate']}`；验证方式：`{companion['validation']}`。",
        f"主要指标：Brier 约 {companion['brier']}，PR-AUC 约 {companion['pr_auc']}，诊断阈值约 {companion['threshold']}，precision {companion['precision']}，recall {companion['recall']}，F1 {companion['f1']}，CSI {companion['csi']}。",
        "",
        "确定性 `WBGT_A_score` 或 `model_score` 仍然是主要的回顾性时间严重度分数。`P_ge31` 只是伴随诊断量，不是官方预警概率。",
        "",
        "## 3. 目前可靠的内容",
        "",
        result.reliability_assessment,
        "",
        "可以安全表述为：System A Level 1 提供回顾性 WBGT_A 时间严重度诊断；`P_ge31` 可作为站点留一验证下的内部回顾性 ge31 伴随诊断量。",
        "",
        "## 4. 仍未解决的内容",
        "",
        result.high_tail_assessment,
        "",
        "不能声称 ge31 已完全解决，不能声称 ge33 概率已经可靠，也不能把 radiation-hot 或 very-high shortwave 解释为已证明的因果机制。",
        "",
        "## 5. 为什么暂缓 A-L2",
        "",
        result.a_l2_decision,
        "",
        "A-L2 属于站点上下文残差工作，需要单独评审和单独任务。本整合包只记录 Level 1 当前契约。",
        "",
        "## 6. 现在是否尝试其他模型",
        "",
        result.a_l1h3_decision,
        "",
        "当前不建议在本任务内继续搜索其他模型。若用户希望进一步改善高尾部，可单独开启 A-L1H.3 high-tail regression review gate。",
        "",
        "## 7. 推荐下一关口",
        "",
        "- 接受 A-L1H.2 的 `P_ge31` 作为诊断伴随量。",
        "- 暂缓 A-L2。",
        "- A-L1H.3 仅作为可选的独立评审关口。",
        "- 任何运行性或对外预警表述之前，都必须先做 prospective metadata / lead-time evaluation。",
        "- 本整合报告作为 System A Level 1 当前输出契约。",
        "",
        "## 明确禁止的表述",
        "",
        "- 不得称为 validated local 100m WBGT prediction。",
        "- 不得称为 official warning probability。",
        "- 不得称为 real-time heat risk forecast。",
        "- 不得称为 public-facing alert。",
        "- 不得称为已完成 System A/B coupled risk 或风险地图。",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status(path: Path, config_path: Path, result: IntegrationResult) -> None:
    """Write the A-L1H.2b status file."""
    files = "\n".join(f"- `{rel(path_)}`" for path_ in result.output_paths)
    missing = "\n".join(f"- `{rel(path_)}`" for path_ in result.missing_sources) or "- none"
    lines = [
        "# A-L1H.2b Status",
        "",
        f"Status: {result.status}",
        f"Decision: {result.decision_status}",
        f"Generated: {date.today().isoformat()}",
        f"Branch: {git_branch()}",
        "",
        "## Scope",
        "",
        "System A Level 1 high-tail integration, model-card note, evidence ledger, and output contract. No model training, no recalibration, no formula-v2, no high-tail regression, no A-L2, no System B or SOLWEIG changes, and no archive collector changes.",
        "",
        "## Command",
        "",
        f"- `{Path(sys.executable)} scripts/v11_l1h_run_level1_integration_report.py --config {rel(config_path)}`",
        "",
        "## Files Created / Modified",
        "",
        files,
        "",
        "## Key Results",
        "",
        f"- Current companion definition: {result.current_companion_definition}",
        f"- Reliability assessment: {result.reliability_assessment}",
        f"- High-tail assessment: {result.high_tail_assessment}",
        f"- A-L2 decision: {result.a_l2_decision}",
        f"- A-L1H.3 decision: {result.a_l1h3_decision}",
        "",
        "## Caveats",
        "",
        "- P_ge31 is retrospective and diagnostic only.",
        "- P_ge31 is not official warning probability and not prospective forecast skill.",
        "- WBGT_A score remains primary but is not local 100m WBGT.",
        "- ge33 remains exploratory.",
        "",
        "## Source Report Check",
        "",
        missing,
        "",
        "## Safe To Commit",
        "",
        "- Config, scripts, docs, and compact level1_integration CSV/Markdown outputs after review.",
        "",
        "## Not Safe To Commit",
        "",
        "- Raw archives, rasters, SOLWEIG outputs, tif/tiff files, svfs.zip, patch zip packages, or large hourly forecast CSVs.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_integration(config_path: Path) -> IntegrationResult:
    """Generate all A-L1H.2b integration artifacts."""
    config = load_config(config_path)
    paths = output_paths(config)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    missing_sources = [path for path in source_paths(config) if not path.exists()]
    status = "BLOCKED" if missing_sources else str(config.get("acceptance_status", "PASS"))
    companion = config["companion"]
    result = IntegrationResult(
        status=status,
        decision_status=str(config.get("decision_status", "")),
        current_companion_definition=str(companion["current_companion_definition"]),
        reliability_assessment=str(companion["reliability_assessment"]),
        high_tail_assessment=str(companion["high_tail_assessment"]),
        a_l2_decision=str(companion["a_l2_decision"]),
        a_l1h3_decision=str(companion["a_l1h3_decision"]),
        output_paths=[
            paths["evidence_ledger"],
            paths["output_contract"],
            paths["claim_boundary_matrix"],
            paths["decision_matrix"],
            paths["station_regime_caveats"],
            paths["next_gate_recommendations"],
            paths["report"],
            paths["status"],
            paths["chinese_doc"],
        ],
        missing_sources=missing_sources,
    )

    evidence_rows = require_rows(config, "evidence_ledger")
    contract_rows = require_rows(config, "output_contract")
    claim_rows = require_rows(config, "claim_boundary_matrix")
    decision_rows = require_rows(config, "decision_matrix")
    caveat_rows = require_rows(config, "station_regime_caveats")
    gate_rows = require_rows(config, "next_gate_recommendations")

    write_csv(paths["evidence_ledger"], require_columns(config, "evidence_ledger_columns"), evidence_rows)
    write_csv(paths["output_contract"], require_columns(config, "output_contract_columns"), contract_rows)
    write_csv(paths["claim_boundary_matrix"], require_columns(config, "claim_boundary_columns"), claim_rows)
    write_csv(paths["decision_matrix"], require_columns(config, "decision_matrix_columns"), decision_rows)
    write_csv(paths["station_regime_caveats"], require_columns(config, "station_regime_caveat_columns"), caveat_rows)
    write_csv(paths["next_gate_recommendations"], require_columns(config, "next_gate_columns"), gate_rows)
    write_report(
        paths["report"],
        config,
        result,
        evidence_rows,
        contract_rows,
        claim_rows,
        decision_rows,
        caveat_rows,
        gate_rows,
    )
    write_chinese_doc(paths["chinese_doc"], config, result)
    write_status(paths["status"], config_path, result)
    return result


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Create the A-L1H.2b System A Level 1 high-tail integration package."
    )
    parser.add_argument("--config", default="configs/v11/systema_l1h_level1_integration.yaml")
    args = parser.parse_args()

    result = run_integration(resolve_path(args.config))
    print(f"[status] {result.status}")
    print(f"[decision_status] {result.decision_status}")
    print(f"[current_companion_definition] {result.current_companion_definition}")
    print(f"[reliability_assessment] {result.reliability_assessment}")
    print(f"[high_tail_assessment] {result.high_tail_assessment}")
    print(f"[a_l2_decision] {result.a_l2_decision}")
    print(f"[a_l1h3_decision] {result.a_l1h3_decision}")
    print("[files_created]")
    for path in result.output_paths:
        print(f"- {rel(path)}")
    if result.missing_sources:
        print("[missing_sources]")
        for path in result.missing_sources:
            print(f"- {rel(path)}")
    return 0 if result.status in {"PASS", "BLOCKED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
