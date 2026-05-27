#!/usr/bin/env python
"""Build the System A A-L1H.8 development dossier and frozen handoff package.

Inputs:
    - configs/v11/systema_l1h8_development_dossier.yaml
    - Compact Markdown/status/report evidence from A-L1H.4, A-L1H.5,
      A-L1H.6, A-L1H.7, A-L2.1c, and earlier System A diagnostics declared
      in the config.

Outputs:
    - a_l1h8_evidence_inventory.csv
    - a_l1h8_timeline.csv
    - a_l1h8_lane_status_matrix.csv
    - a_l1h8_output_contract_summary.csv
    - a_l1h8_model_evidence_summary.csv
    - a_l1h8_level2_boundary_summary.csv
    - a_l1h8_formal_snapshot_waiting_register.csv
    - a_l1h8_allowed_forbidden_claims.csv
    - a_l1h8_future_reactivation_checklist.md
    - a_l1h8_codex_reentry_prompt.md
    - a_l1h8_systema_architecture_diagram.md
    - a_l1h8_report.md
    - A_L1H8_STATUS.md
    - docs/v11/OpenHeat_SystemA_development_dossier_2026-05-27_CN.md
    - docs/handoff/OpenHeat_SystemA_FROZEN_HANDOFF_2026-05-27_CN.md

Saved metrics:
    - Evidence artifact inventory, timeline, lane status decisions, frozen
      output contract summary, model evidence summary, Level 2 boundary
      summary, formal snapshot waiting register, and allowed/forbidden claim
      matrix.

Scope guard:
    This lane is documentation/synthesis/handoff only. It does not train new
    models, modify A-L1H.5 contract decisions, modify A-L1H.6 or A-L1H.7 gates,
    modify archive collectors, touch System B or SOLWEIG outputs, create
    station-adjusted WBGT, create local 100 m WBGT, create official warning
    probability, create risk_score/hazard_score, create System A/B coupling
    output, create fake formal snapshot rows, stage, or commit.
"""
from __future__ import annotations

import csv
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - used only in lean runtimes.
    yaml = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
PASS_STATUS = "A_L1H8_DOSSIER_PASS"
PARTIAL_STATUS = "A_L1H8_DOSSIER_PARTIAL"
BLOCKED_STATUS = "A_L1H8_BLOCKED"


@dataclass(frozen=True)
class DossierResult:
    """Headline result for the A-L1H.8 dossier."""

    status: str
    evidence_artifacts_inventoried: int
    current_frozen_state: str
    formal_snapshot_waiting_status: str
    level2_boundary_status: str
    reentry_prompt_path: Path
    docs_created: list[Path]
    output_paths: list[Path]
    missing_required_contract_sources: list[Path]
    missing_prior_artifacts: list[Path]


def rel(path: Path) -> str:
    """Return a project-relative POSIX path when possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(raw_path: str | Path) -> Path:
    """Resolve an absolute or project-relative path."""
    path = Path(raw_path)
    return path if path.is_absolute() else ROOT / path


def parse_scalar(value: str) -> Any:
    """Parse the scalar subset used by explicit lane YAML configs."""
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
    """Parse the narrow YAML subset used by this lane's explicit config."""
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
    """Load the explicit A-L1H.8 YAML config."""
    text = path.read_text(encoding="utf-8")
    loaded = yaml.safe_load(text) if yaml is not None else parse_simple_yaml(text)
    if not isinstance(loaded, dict):
        raise ValueError("Config root must be a mapping.")
    return loaded


def read_text(path: Path) -> str:
    """Read UTF-8 text evidence with replacement for legacy artifacts."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> Path:
    """Write UTF-8 text with LF newlines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> Path:
    """Write a UTF-8 CSV with stable column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
    return path


def git_branch() -> str:
    """Return the active git branch."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def extract_status(text: str) -> str:
    """Extract the first declared status or decision from Markdown evidence."""
    patterns = [
        r"Status:\s*`?([^`\n]+)`?",
        r"Decision status:\s*`?([^`\n]+)`?",
        r"决策状态：`?([^`\n]+)`?",
        r"Status:\s*([A-Z0-9_]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return "not_declared" if text else "missing"


def markdown_cell(value: Any) -> str:
    """Escape a compact Markdown table cell."""
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def markdown_table(rows: list[dict[str, Any]], columns: list[str], limit: int | None = None) -> str:
    """Render a compact Markdown table."""
    display_rows = rows if limit is None else rows[:limit]
    if not display_rows:
        return "_No rows available._"
    widths = [len(column) for column in columns]
    body = [[markdown_cell(row.get(column, "")) for column in columns] for row in display_rows]
    for row in body:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    def render(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(values)) + " |"

    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([render(columns), separator, *(render(row) for row in body)])


def build_evidence_inventory(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Scan compact docs/reports/status files declared as evidence."""
    rows: list[dict[str, Any]] = []
    for item in config["inputs"]["evidence_sources"]:
        path = resolve_path(str(item["artifact_path"]))
        text = read_text(path)
        rows.append(
            {
                "lane_id": item["lane_id"],
                "artifact_path": rel(path),
                "exists": "yes" if path.exists() else "no",
                "status": extract_status(text),
                "key_result": item.get("key_result", ""),
                "claim_boundary": item.get("claim_boundary", ""),
                "next_action": item.get("next_action", ""),
            }
        )
    return rows


def build_timeline() -> list[dict[str, Any]]:
    """Create the ordered System A development timeline."""
    return [
        {
            "sequence": 1,
            "stage": "L1 residual decomposition / high-tail diagnostics",
            "lane": "A-L1H.0",
            "decision": "High-tail residual and ge31 miss behavior justified a focused Level 1 diagnostic lane.",
            "evidence": "Residual decomposition, station/regime/bin/hour diagnostics, ge31 miss/hit/false-alarm inventories.",
            "next_state": "Use as historical diagnostic context only.",
        },
        {
            "sequence": 2,
            "stage": "formula/proxy audit",
            "lane": "A-L1H.1",
            "decision": "Formula/proxy work stayed as companion audit, not retroactive recalibration.",
            "evidence": "Formula candidate and threshold metrics.",
            "next_state": "No contract change.",
        },
        {
            "sequence": 3,
            "stage": "probability / threshold calibration",
            "lane": "A-L1H.2",
            "decision": "Probability threshold behavior was useful as diagnostic evidence.",
            "evidence": "Calibration metrics, threshold operating points, station/regime checks.",
            "next_state": "Feed L1H4 companion suite.",
        },
        {
            "sequence": 4,
            "stage": "high-tail benchmark",
            "lane": "A-L1H.3",
            "decision": "High-tail challenger benchmark informed but did not replace WBGT_A.",
            "evidence": "Challenger overall, station, regime, threshold, reliability metrics.",
            "next_state": "No new production model in this handoff.",
        },
        {
            "sequence": 5,
            "stage": "Level 2 identifiability",
            "lane": "A-L2.0",
            "decision": "Station-context residual explanation warranted scoped preflight only.",
            "evidence": "Station residual stability and identifiability matrix.",
            "next_state": "Do not create correction layer.",
        },
        {
            "sequence": 6,
            "stage": "station feature QA",
            "lane": "A-L2.1a/b",
            "decision": "Station-local features are explanatory covariates with QA caveats.",
            "evidence": "Station buffer features and station feature QA summaries.",
            "next_state": "Use only in Level 2 explanatory sidecar.",
        },
        {
            "sequence": 7,
            "stage": "scoped residual preflight",
            "lane": "A-L2.1c",
            "decision": "Weak high-tail station-context signal; score residual not identifiable.",
            "evidence": "High-tail residual improvement about 6.5%; score residual about 1.7%; S142/S139 caveats.",
            "next_state": "Level 2 remains explanatory only.",
        },
        {
            "sequence": 8,
            "stage": "L1H4 probability companion",
            "lane": "A-L1H.4",
            "decision": "P_ge31 promising companion; P_ge33 exploratory; expected exceedance and intervals optional diagnostics.",
            "evidence": "LOSO n=1674, ge31=204, ge33=15; P_ge31 Brier 0.052, ECE 0.018, PR-AUC 0.610.",
            "next_state": "Keep P_ge31 optional pending formal prospective snapshot.",
        },
        {
            "sequence": 9,
            "stage": "L1H5 contract",
            "lane": "A-L1H.5",
            "decision": "Hourly output contract frozen with wbgt_a_c as primary.",
            "evidence": "Model card and output contract v1.0.",
            "next_state": "Do not modify in L1H8.",
        },
        {
            "sequence": 10,
            "stage": "L1H6 prospective harness",
            "lane": "A-L1H.6",
            "decision": "Harness ready but waiting for formal snapshot.",
            "evidence": "A_L1H6_WAITING_FOR_FORMAL_SNAPSHOT; no valid snapshot found.",
            "next_state": "Rerun after formal snapshot freeze.",
        },
        {
            "sequence": 11,
            "stage": "L1H7 snapshot freezer",
            "lane": "A-L1H.7",
            "decision": "Freezer waits for real formal input.",
            "evidence": "A_L1H7_WAITING_FOR_FORMAL_INPUT; dry-run only; no plausible formal candidate.",
            "next_state": "Use write_snapshot only after reviewed real candidate passes checks.",
        },
        {
            "sequence": 12,
            "stage": "current state",
            "lane": "A-L1H.8",
            "decision": "System A frozen/waiting; dossier and handoff package complete.",
            "evidence": "This development dossier consolidates evidence, contract, boundaries, waiting register, and re-entry prompt.",
            "next_state": "Future re-entry starts with formal snapshot, then A-L1H.6 evaluation.",
        },
    ]


def build_lane_status_matrix() -> list[dict[str, Any]]:
    """Build the lane status matrix requested for frozen handoff."""
    return [
        {
            "lane_item": "Level 1 deterministic baseline",
            "current_decision": "PRIMARY_FROZEN",
            "evidence": "A-L1H.5 output contract: wbgt_a_c is primary; A-L1H.4 deterministic evidence retained.",
            "blocker": "None for current frozen contract; prospective validation still pending for stronger claims.",
            "allowed_next_action": "Evaluate wbgt_a_c on a future formal snapshot.",
            "forbidden_action": "Replace primary output without a new explicit lane.",
        },
        {
            "lane_item": "P_ge31 companion",
            "current_decision": "OPTIONAL_DIAGNOSTIC_COMPANION",
            "evidence": "A-L1H.4 P_ge31 Brier=0.052, ECE=0.018, PR-AUC=0.610; best_F1 recall=0.765.",
            "blocker": "No formal prospective snapshot yet.",
            "allowed_next_action": "Evaluate promotion gates in A-L1H.6 after snapshot.",
            "forbidden_action": "Call it official warning probability.",
        },
        {
            "lane_item": "expected exceedance",
            "current_decision": "OPTIONAL_DIAGNOSTIC",
            "evidence": "A-L1H.4 expected exceedance MAE=0.100 C; positive-event MAE=0.779 C.",
            "blocker": "Prospective evaluation absent.",
            "allowed_next_action": "Report as internal diagnostic if populated by contract.",
            "forbidden_action": "Treat as corrected WBGT forecast.",
        },
        {
            "lane_item": "conformal interval",
            "current_decision": "OPTIONAL_DIAGNOSTIC",
            "evidence": "A-L1H.4 conformal 90% coverage=0.898, mean width=2.869 C.",
            "blocker": "Near-ge33 support weak; prospective validation absent.",
            "allowed_next_action": "Retain interval diagnostics in formal evaluation.",
            "forbidden_action": "Claim guaranteed operational interval.",
        },
        {
            "lane_item": "P_ge33",
            "current_decision": "EXPLORATORY_LOW_SUPPORT",
            "evidence": "A-L1H.4 ge33 events=15.",
            "blocker": "Insufficient ge33 event support.",
            "allowed_next_action": "Report support count; revisit only with at least 30 real events and calibration evidence.",
            "forbidden_action": "Promote severe warning probability.",
        },
        {
            "lane_item": "Level 2 residual explanation",
            "current_decision": "EXPLANATORY_ONLY",
            "evidence": "A-L2.1c weak high-tail signal; score residual not identifiable.",
            "blocker": "n=27 station constraints, S142/S139 caveats, limited station metadata.",
            "allowed_next_action": "Future explanatory protocol with longer archive and better station metadata/SVF/LCZ/siting.",
            "forbidden_action": "Create station correction or System B modifier.",
        },
        {
            "lane_item": "station-adjusted WBGT",
            "current_decision": "FORBIDDEN",
            "evidence": "A-L1H.5 and A-L2.1c explicitly forbid station_adjusted_wbgt_c.",
            "blocker": "No identifiable score residual correction and no validated station correction model.",
            "allowed_next_action": "None in current lane.",
            "forbidden_action": "Output station_adjusted_wbgt_c.",
        },
        {
            "lane_item": "local 100m WBGT",
            "current_decision": "FORBIDDEN",
            "evidence": "A-L1H.5 contract and project claim boundaries.",
            "blocker": "System A does not convert SOLWEIG/Tmrt or station context into local WBGT.",
            "allowed_next_action": "None in current lane.",
            "forbidden_action": "Output local_wbgt_c or delta_wbgt_cell.",
        },
        {
            "lane_item": "formal snapshot",
            "current_decision": "WAITING_FOR_REAL_INPUT",
            "evidence": "A-L1H.7 waits for formal input; A-L1H.6 waits for formal snapshot.",
            "blocker": "No real compact candidate with required schema and support.",
            "allowed_next_action": "Run A-L1H.7 write_snapshot after reviewed input exists.",
            "forbidden_action": "Use live-growing archive as formal pass or create fake rows.",
        },
        {
            "lane_item": "prospective evaluation",
            "current_decision": "HARNESS_READY_WAITING",
            "evidence": "A-L1H.6 harness and gates exist.",
            "blocker": "Formal snapshot missing.",
            "allowed_next_action": "Run A-L1H.6 after formal snapshot freeze.",
            "forbidden_action": "Claim final prospective pass before snapshot.",
        },
        {
            "lane_item": "System B coupling",
            "current_decision": "OUT_OF_SCOPE_FORBIDDEN",
            "evidence": "A-L1H.5 contract excludes System B/SOLWEIG/Tmrt/cell_id features.",
            "blocker": "No scoped coupling lane and no validated coupling contract.",
            "allowed_next_action": "Open a separate future lane only if explicitly requested.",
            "forbidden_action": "Create System A/B coupling output in this lane.",
        },
        {
            "lane_item": "risk/hazard",
            "current_decision": "FORBIDDEN",
            "evidence": "Project claim boundaries and A-L1H.5 contract forbid risk_score and hazard_score.",
            "blocker": "Exposure and vulnerability are not explicit and no risk model is complete.",
            "allowed_next_action": "Discuss future risk overlay only after separate explicit scope.",
            "forbidden_action": "Output risk_score or hazard_score.",
        },
    ]


def build_output_contract_summary(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Summarize the frozen A-L1H.5 hourly output contract."""
    rows: list[dict[str, Any]] = []
    descriptions = {
        "timestamp_sgt": "SGT timestamp for each hourly row.",
        "timestamp_utc": "UTC timestamp matching timestamp_sgt.",
        "wbgt_a_c": "Primary deterministic calibrated hourly WBGT_A value.",
        "wbgt_a_model_id": "Deterministic model identifier.",
        "wbgt_a_version": "Contract/model version string.",
        "s_wbgt_ge31": "Deterministic ge31 severity derived from wbgt_a_c.",
        "s_wbgt_band_31_33": "Deterministic band below_31, ge31_lt33, or ge33_plus derived from wbgt_a_c.",
        "source_forcing": "Forcing/source family used for the row.",
        "is_retrospective_or_prospective": "Retrospective/prospective row label.",
        "quality_flag": "Compact quality/provenance flag.",
        "p_ge31_optional": "Optional diagnostic P(WBGT >=31 C).",
        "p_ge33_optional": "Exploratory optional P(WBGT >=33 C).",
        "expected_exceedance_ge31_optional": "Optional expected exceedance above 31 C.",
        "prediction_interval_low_optional": "Optional lower diagnostic interval bound.",
        "prediction_interval_high_optional": "Optional upper diagnostic interval bound.",
        "station_adjusted_wbgt_c": "Forbidden station correction output.",
        "local_wbgt_c": "Forbidden local cell WBGT output.",
        "delta_wbgt_cell": "Forbidden cell-level WBGT delta.",
        "risk_score": "Forbidden risk score.",
        "hazard_score": "Forbidden hazard score.",
    }
    for column in config["schema"]["required_columns"]:
        rows.append(
            {
                "column_name": column,
                "column_group": "required",
                "decision": "REQUIRED",
                "description": descriptions[column],
                "allowed_use": "Frozen A-L1H.5 System A Level 1 hourly output contract.",
                "forbidden_use": "Public warning, risk score, hazard score, or local 100 m WBGT claim.",
            }
        )
    for column in config["schema"]["optional_columns"]:
        forbidden = "Official warning probability." if column == "p_ge31_optional" else "Promoted operational claim without prospective validation."
        if column == "p_ge33_optional":
            forbidden = "Promoted severe warning probability under low event support."
        if column == "expected_exceedance_ge31_optional":
            forbidden = "Corrected WBGT forecast."
        rows.append(
            {
                "column_name": column,
                "column_group": "optional_companion",
                "decision": "OPTIONAL_DIAGNOSTIC",
                "description": descriptions[column],
                "allowed_use": "Internal retrospective/prospective diagnostic when metadata and gates are satisfied.",
                "forbidden_use": forbidden,
            }
        )
    for column in config["schema"]["forbidden_columns"]:
        rows.append(
            {
                "column_name": column,
                "column_group": "forbidden",
                "decision": "FORBIDDEN",
                "description": descriptions[column],
                "allowed_use": "None in System A Level 1 contract.",
                "forbidden_use": "Must not appear in System A L1H8 outputs or future formal snapshot contract.",
            }
        )
    return rows


def build_model_evidence_summary() -> list[dict[str, Any]]:
    """Summarize model evidence and caveats without training new models."""
    return [
        {
            "evidence_item": "P_ge31 optional companion",
            "current_decision": "PROMISING_BUT_OPTIONAL",
            "evidence": "LOSO retrospective n=1674; ge31=204; Brier=0.052; ECE=0.018; PR-AUC=0.610; best_F1 recall=0.765.",
            "caveat": "Not an official warning probability and not prospectively promoted.",
            "next_action": "Evaluate against fixed_31 in future A-L1H.6 formal snapshot run.",
        },
        {
            "evidence_item": "P_ge33",
            "current_decision": "LOW_SUPPORT_EXPLORATORY",
            "evidence": "A-L1H.4 reports only 15 ge33 events.",
            "caveat": "Below promotion support threshold; station support uncertain.",
            "next_action": "Keep exploratory until at least 30 real ge33 events plus calibration evidence exist.",
        },
        {
            "evidence_item": "Expected exceedance ge31",
            "current_decision": "OPTIONAL_DIAGNOSTIC",
            "evidence": "A-L1H.4 deterministic score-gap expected exceedance MAE=0.100 C; positive-event MAE=0.779 C.",
            "caveat": "Magnitude diagnostic only; not corrected WBGT.",
            "next_action": "Report if contract column is populated in formal snapshot.",
        },
        {
            "evidence_item": "Prediction intervals",
            "current_decision": "OPTIONAL_DIAGNOSTIC",
            "evidence": "A-L1H.4 conformal 90% empirical coverage=0.898; mean width=2.869 C.",
            "caveat": "Retrospective coverage only; near-ge33 behavior weak.",
            "next_action": "Refresh coverage on formal snapshot when interval columns exist.",
        },
        {
            "evidence_item": "S142 caveat",
            "current_decision": "MONITORING_CAVEAT",
            "evidence": "S142 ge31 support=15; recall=0.533; miss_rate=0.467 under key companion diagnostics.",
            "caveat": "Station diagnostic, not station correction.",
            "next_action": "Refresh caveat in prospective evaluation.",
        },
        {
            "evidence_item": "S139 caveat",
            "current_decision": "LOW_SUPPORT_MONITORING_CAVEAT",
            "evidence": "S139 ge31 support=1 and false-alarm-sensitive diagnostics.",
            "caveat": "Too little event support for station-specific reliability claim.",
            "next_action": "Refresh caveat with formal snapshot support counts.",
        },
        {
            "evidence_item": "Level 2 high-tail residual",
            "current_decision": "WEAK_EXPLANATORY_SIGNAL",
            "evidence": "A-L2.1c high-tail residual improvement about 6.5%; permutation p_mae about 0.053; p_spearman about 0.025.",
            "caveat": "Explanatory only; n=26/27 station constraints.",
            "next_action": "Do not promote to correction layer.",
        },
        {
            "evidence_item": "Level 2 score residual",
            "current_decision": "NOT_IDENTIFIABLE",
            "evidence": "A-L2.1c score residual improvement about 1.7%; p_mae about 0.142; p_spearman about 0.309.",
            "caveat": "Does not support station correction.",
            "next_action": "Keep score residual correction out of System A contract.",
        },
        {
            "evidence_item": "Station correction",
            "current_decision": "NO_STATION_CORRECTION",
            "evidence": "A-L1H.5 Level 2 boundary and A-L2.1c preflight both reject correction output.",
            "caveat": "No station-adjusted WBGT.",
            "next_action": "Longer archive and station metadata may be future explanatory options only.",
        },
    ]


def build_level2_boundary_summary() -> list[dict[str, Any]]:
    """Summarize the Level 2 boundary explicitly."""
    return [
        {
            "boundary_item": "Level 2 role",
            "current_status": "EXPLANATORY_ONLY",
            "statement": "Level 2 is explanatory only.",
            "forbidden_output": "Operational correction model.",
            "future_option": "Protocol review after longer archive and better metadata.",
        },
        {
            "boundary_item": "station-adjusted WBGT",
            "current_status": "FORBIDDEN",
            "statement": "Level 2 does not produce station-adjusted WBGT.",
            "forbidden_output": "station_adjusted_wbgt_c",
            "future_option": "None in current v1.1 frozen handoff.",
        },
        {
            "boundary_item": "local 100 m WBGT",
            "current_status": "FORBIDDEN",
            "statement": "Level 2 does not produce local 100 m WBGT.",
            "forbidden_output": "local_wbgt_c",
            "future_option": "Requires a future explicitly scoped and validated lane.",
        },
        {
            "boundary_item": "System B modifier",
            "current_status": "FORBIDDEN",
            "statement": "Level 2 does not produce a System B modifier.",
            "forbidden_output": "System A/B coupling output or delta_wbgt_cell",
            "future_option": "Separate future coupling protocol only if explicitly opened.",
        },
        {
            "boundary_item": "future explanatory options",
            "current_status": "FUTURE_OPTION_ONLY",
            "statement": "Longer archive and better station metadata/SVF/LCZ/siting data are future options.",
            "forbidden_output": "Current correction or causal claim.",
            "future_option": "Use as explanatory evidence after formal scope review.",
        },
    ]


def build_formal_snapshot_waiting_register(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the formal snapshot waiting register."""
    formal = config["formal_snapshot"]
    schema = ", ".join(config["schema"]["required_columns"])
    candidate_paths = "; ".join(formal["candidate_paths"])
    return [
        {
            "register_item": "why_formal_snapshot_is_needed",
            "current_status": "WAITING",
            "detail": formal["why_needed"],
            "required_action": "Freeze reviewed compact prospective rows before any prospective pass or P_ge31 promotion review.",
            "forbidden_action": "Do not use a live-growing archive as the formal pass.",
        },
        {
            "register_item": "required_schema",
            "current_status": "DEFINED_BY_A_L1H5_A_L1H6_A_L1H7",
            "detail": schema,
            "required_action": "Candidate must include all required columns with unambiguous timestamp semantics and model/version metadata.",
            "forbidden_action": "Do not silently bridge ambiguous timestamp or contract columns.",
        },
        {
            "register_item": "minimum_row_event_support",
            "current_status": "DEFINED",
            "detail": f"minimum prospective rows={formal['minimum_prospective_rows']}; minimum ge31 events={formal['minimum_ge31_events']}; minimum ge33 events for promotion review={formal['minimum_ge33_events_for_promotion']}",
            "required_action": "Report support counts before interpreting metrics.",
            "forbidden_action": "Do not fabricate rows or events.",
        },
        {
            "register_item": "candidate_paths",
            "current_status": "CONFIGURED",
            "detail": candidate_paths,
            "required_action": "Place a real compact CSV/CSV.GZ/Parquet snapshot in one configured path.",
            "forbidden_action": "Do not scan raw archive dumps as formal proof.",
        },
        {
            "register_item": "A-L1H.7 current status",
            "current_status": formal["l1h7_status"],
            "detail": "Current freezer dry-run found no plausible formal candidate.",
            "required_action": "Rerun freezer with real candidate; use write_snapshot only after checks pass.",
            "forbidden_action": "Do not weaken required schema or forbidden-column checks.",
        },
        {
            "register_item": "A-L1H.6 rerun command",
            "current_status": "READY_AFTER_SNAPSHOT",
            "detail": formal["l1h6_rerun_command"],
            "required_action": "Run after frozen snapshot is written and reviewed.",
            "forbidden_action": "Do not claim prospective pass before running on snapshot.",
        },
        {
            "register_item": "write_snapshot procedure",
            "current_status": "DOCUMENTED_NOT_EXECUTED",
            "detail": formal["l1h7_write_snapshot_command"],
            "required_action": "Set A-L1H.7 config to write_snapshot only for a real candidate that passes schema, support, numeric, and forbidden-column checks.",
            "forbidden_action": "Do not write fake formal snapshot rows.",
        },
        {
            "register_item": "live-growing archive",
            "current_status": "NOT_FORMAL_PASS",
            "detail": "Formal comparisons must use a frozen snapshot, never a live-growing archive.",
            "required_action": "Version and review the frozen snapshot manifest.",
            "forbidden_action": "Do not interpret live archive rows as final formal evidence.",
        },
    ]


def build_allowed_forbidden_claims() -> list[dict[str, Any]]:
    """Build the allowed/forbidden claim matrix."""
    return [
        {
            "claim": "WBGT_A deterministic temporal baseline",
            "decision": "ALLOWED",
            "allowed_wording": "WBGT_A deterministic temporal baseline.",
            "forbidden_upgrade": "Validated local WBGT prediction.",
            "rationale": "A-L1H.5 freezes wbgt_a_c as primary calibrated hourly temporal baseline.",
        },
        {
            "claim": "P_ge31 optional diagnostic companion",
            "decision": "ALLOWED_WITH_BOUNDARY",
            "allowed_wording": "P_ge31 optional diagnostic companion.",
            "forbidden_upgrade": "Official warning probability.",
            "rationale": "A-L1H.4 retrospective evidence is promising but awaits formal prospective evaluation.",
        },
        {
            "claim": "retrospective LOSO evidence",
            "decision": "ALLOWED",
            "allowed_wording": "Retrospective station-held-out LOSO evidence.",
            "forbidden_upgrade": "Final prospective pass.",
            "rationale": "LOSO is retrospective validation, not future frozen snapshot evidence.",
        },
        {
            "claim": "prospective harness ready",
            "decision": "ALLOWED",
            "allowed_wording": "Prospective evaluation harness ready and waiting for formal snapshot.",
            "forbidden_upgrade": "Prospective evaluation complete.",
            "rationale": "A-L1H.6 status is waiting because no formal snapshot exists.",
        },
        {
            "claim": "Level 2 explanatory weak signal",
            "decision": "ALLOWED_WITH_BOUNDARY",
            "allowed_wording": "Level 2 shows weak high-tail explanatory signal.",
            "forbidden_upgrade": "Station correction or causal driver proof.",
            "rationale": "A-L2.1c is explanatory only; score residual not identifiable.",
        },
        {
            "claim": "official warning probability",
            "decision": "FORBIDDEN",
            "allowed_wording": "None.",
            "forbidden_upgrade": "Official warning probability.",
            "rationale": "No operational governance or prospective promotion exists.",
        },
        {
            "claim": "station-adjusted WBGT",
            "decision": "FORBIDDEN",
            "allowed_wording": "None.",
            "forbidden_upgrade": "station_adjusted_wbgt_c.",
            "rationale": "A-L1H.5 and A-L2.1c explicitly forbid station correction.",
        },
        {
            "claim": "local 100m WBGT",
            "decision": "FORBIDDEN",
            "allowed_wording": "None.",
            "forbidden_upgrade": "local_wbgt_c or validated 100 m local WBGT.",
            "rationale": "System A Level 1 does not produce local cell WBGT.",
        },
        {
            "claim": "risk/hazard score",
            "decision": "FORBIDDEN",
            "allowed_wording": "None.",
            "forbidden_upgrade": "risk_score or hazard_score.",
            "rationale": "Risk requires explicit exposure/vulnerability; hazard score is out of current scope.",
        },
        {
            "claim": "System A/B coupling claim",
            "decision": "FORBIDDEN",
            "allowed_wording": "None.",
            "forbidden_upgrade": "System A/B coupling output.",
            "rationale": "A-L1H.5 excludes System B/SOLWEIG/Tmrt/cell-level fields.",
        },
        {
            "claim": "final prospective pass before formal snapshot",
            "decision": "FORBIDDEN",
            "allowed_wording": "Waiting for formal snapshot.",
            "forbidden_upgrade": "Final prospective pass.",
            "rationale": "A-L1H.6 and A-L1H.7 both wait for real frozen input.",
        },
    ]


def build_reactivation_checklist(config: dict[str, Any]) -> str:
    """Build the future reactivation checklist Markdown."""
    today = config.get("generated_date", date.today().isoformat())
    l1h6_command = config["formal_snapshot"]["l1h6_rerun_command"]
    l1h7_command = config["formal_snapshot"]["l1h7_write_snapshot_command"]
    return f"""# A-L1H.8 Future Reactivation Checklist

Generated: {today}
Status: System A frozen/waiting.

- [ ] Confirm current branch and worktree status before changing anything.
- [ ] Verify A-L1H.5 contract files still exist and have not been modified.
- [ ] Confirm a real compact formal snapshot candidate exists under a configured candidate path.
- [ ] Review candidate schema for required fields, forbidden fields, row support, ge31/ge33 support, numeric WBGT fields, model/version metadata, quality flags, and retrospective/prospective labels.
- [ ] Run A-L1H.7 freezer in dry-run mode first if the candidate is new.
- [ ] If dry-run checks pass, switch A-L1H.7 config to write_snapshot through a reviewed change and run:

```bash
{l1h7_command}
```

- [ ] Review frozen snapshot manifest and validation outputs.
- [ ] Rerun A-L1H.6 prospective evaluation:

```bash
{l1h6_command}
```

- [ ] Evaluate P_ge31 promotion gates against fixed_31, calibration, precision/false-alarm behavior, and station caveats.
- [ ] Keep P_ge33 exploratory unless support and calibration thresholds are explicit.
- [ ] Update the model card only after reviewed prospective evidence exists.
- [ ] Do not train new models unless promotion gates fail and the user explicitly opens a new lane.
- [ ] Do not create station-adjusted WBGT, local 100 m WBGT, official warning probability, System A/B coupling output, risk_score, or hazard_score.
"""


def build_codex_reentry_prompt(config: dict[str, Any]) -> str:
    """Build the future Codex re-entry prompt."""
    l1h6_command = config["formal_snapshot"]["l1h6_rerun_command"]
    l1h7_command = config["formal_snapshot"]["l1h7_write_snapshot_command"]
    return f"""# Codex Re-entry Prompt: Resume System A After Formal Snapshot Exists

You are working inside the OpenHeat-ToaPayoh project subdirectory.

Current lane: System A formal snapshot re-entry after A-L1H.8 frozen handoff.

Before starting:
- Check current directory, git root, branch, `git status -sb -uno`, and `git status --short -- .`.
- Read `outputs/v11_systema_l1_high_tail/systema_development_dossier/A_L1H8_STATUS.md`.
- Read `outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_report.md`.
- Read `outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_formal_snapshot_waiting_register.csv`.
- Read the frozen A-L1H.5 model card and output contract.
- Confirm the new formal snapshot candidate is real, compact, reviewed, and not a live-growing archive.

Rules:
- Do not train new models unless promotion gates fail and the user explicitly opens a new lane.
- Do not modify A-L1H.5 contract decisions before evaluation.
- Do not modify A-L1H.6 or A-L1H.7 gates without explicit user scope.
- Do not modify archive collector.
- Do not touch System B or SOLWEIG outputs.
- Do not create station-adjusted WBGT, local 100 m WBGT, official warning probability, risk_score, hazard_score, or System A/B coupling output.
- Do not create fake formal snapshot rows.

Re-entry path:
1. If A-L1H.7 has not yet written a frozen snapshot, run a reviewed dry-run/write_snapshot procedure using:

```bash
{l1h7_command}
```

2. After the frozen snapshot manifest and validation pass, rerun:

```bash
{l1h6_command}
```

3. Evaluate P_ge31 promotion gates against fixed_31 recall/miss behavior, precision/false-alarm behavior, Brier/ECE, and station caveats.
4. Keep P_ge33 exploratory unless support and calibration thresholds are explicit.
5. Update the model card only after formal prospective evidence supports a change.
6. Report exact commands, outputs, limitations, and any generated data intentionally uncommitted.
"""


def build_architecture_diagram() -> str:
    """Build the System A architecture diagram Markdown."""
    return """# System A Frozen Architecture Diagram

```mermaid
flowchart LR
  A["Archive / forcing inputs<br/>retrospective evidence + future frozen formal snapshot"] --> B["WBGT_A deterministic baseline<br/>wbgt_a_c"]
  B --> C["Required hourly contract fields<br/>timestamps, model id/version, forcing, quality"]
  B --> D["Optional companions<br/>p_ge31_optional, expected exceedance, intervals"]
  D --> E["A-L1H.6 prospective evaluation harness<br/>promotion gates only after formal snapshot"]
  A --> F["A-L1H.7 formal snapshot freezer<br/>schema bridge + manifest + validation"]
  F --> E
  G["Level 2 explanatory sidecar<br/>weak high-tail station-context signal"] -. "no correction output" .-> B
  H["System B boundary<br/>SOLWEIG/Tmrt/radiative modifier outside this contract"] -. "no coupling output" .-> B
  I["Forbidden outputs<br/>station_adjusted_wbgt_c<br/>local_wbgt_c<br/>delta_wbgt_cell<br/>official warning probability<br/>risk_score / hazard_score"]
  B -. "must not create" .-> I
  D -. "must not claim" .-> I
  G -. "must not create" .-> I
```
"""


def build_report(
    status: str,
    config: dict[str, Any],
    evidence_rows: list[dict[str, Any]],
    timeline_rows: list[dict[str, Any]],
    lane_rows: list[dict[str, Any]],
    contract_rows: list[dict[str, Any]],
    model_rows: list[dict[str, Any]],
    level2_rows: list[dict[str, Any]],
    snapshot_rows: list[dict[str, Any]],
    claim_rows: list[dict[str, Any]],
) -> str:
    """Build the English A-L1H.8 dossier report."""
    today = config.get("generated_date", date.today().isoformat())
    return f"""# System A A-L1H.8 Development Dossier / Frozen Handoff

Generated: {today}
Decision status: `{status}`
Branch: `{git_branch()}`

## 1. Current System A State

System A is frozen/waiting. A-L1H.5 froze the Level 1 hourly output contract with `wbgt_a_c` as the deterministic primary output. A-L1H.6 built the prospective evaluation harness and is waiting for a real formal snapshot. A-L1H.7 built the formal snapshot freezer and is waiting for real formal input. A-L2.1c remains an explanatory sidecar only.

## 2. Evidence Chain

{markdown_table(evidence_rows, ["lane_id", "artifact_path", "exists", "status", "key_result"], None)}

## 3. Timeline

{markdown_table(timeline_rows, ["sequence", "stage", "lane", "decision"], None)}

## 4. Output Contract

{markdown_table(contract_rows, ["column_name", "column_group", "decision", "allowed_use", "forbidden_use"], None)}

## 5. Model Evidence

{markdown_table(model_rows, ["evidence_item", "current_decision", "evidence", "caveat"], None)}

## 6. Level 2 Boundary

{markdown_table(level2_rows, ["boundary_item", "current_status", "statement", "forbidden_output", "future_option"], None)}

## 7. Formal Snapshot Explanation

{markdown_table(snapshot_rows, ["register_item", "current_status", "detail", "required_action", "forbidden_action"], None)}

## 8. Future Reactivation Path

Start by checking branch and status, then use A-L1H.7 to write a reviewed frozen snapshot if needed. After the snapshot manifest and validation pass, run A-L1H.6 prospective evaluation and evaluate P_ge31 gates. Do not train new models unless gates fail and the user explicitly opens a new lane.

## 9. Allowed / Forbidden Claims

{markdown_table(claim_rows, ["claim", "decision", "allowed_wording", "forbidden_upgrade"], None)}

## 10. Codex Re-entry Prompt

See `outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_codex_reentry_prompt.md`.

## 11. Architecture Diagram

See `outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_systema_architecture_diagram.md`.
"""


def build_cn_doc(status: str, config: dict[str, Any], lane_rows: list[dict[str, Any]], claim_rows: list[dict[str, Any]]) -> str:
    """Build the Chinese System A development dossier in valid UTF-8."""
    today = config.get("generated_date", date.today().isoformat())
    return f"""# OpenHeat System A 开发档案与冻结交接

生成日期：{today}
决策状态：`{status}`

## 1. 当前 System A 状态

System A 当前处于冻结/等待状态。A-L1H.5 已冻结 Level 1 小时输出契约，`wbgt_a_c` 是确定性的主输出。A-L1H.6 已建立前瞻评估框架，但等待真实的正式快照。A-L1H.7 已建立正式快照冻结器，但当前等待真实正式输入。A-L2.1c 只保留为解释性侧车。

## 2. 证据链

证据链从高尾残差诊断、公式/代理审计、概率阈值校准、高尾基准、Level 2 可识别性与站点特征 QA，推进到 A-L1H.4 伴随概率套件、A-L1H.5 输出契约、A-L1H.6 前瞻框架和 A-L1H.7 快照冻结器。本轮只做归档、综合和交接，不训练新模型。

## 3. 输出契约

A-L1H.5 的冻结契约要求：`timestamp_sgt`、`timestamp_utc`、`wbgt_a_c`、`wbgt_a_model_id`、`wbgt_a_version`、`s_wbgt_ge31`、`s_wbgt_band_31_33`、`source_forcing`、`is_retrospective_or_prospective` 和 `quality_flag`。

可选诊断列包括：`p_ge31_optional`、`p_ge33_optional`、`expected_exceedance_ge31_optional`、`prediction_interval_low_optional` 和 `prediction_interval_high_optional`。

禁止列包括：`station_adjusted_wbgt_c`、`local_wbgt_c`、`delta_wbgt_cell`、`risk_score` 和 `hazard_score`。

## 4. Level 2 边界

Level 2 只是解释性侧车。它不产生站点修正 WBGT，不产生本地 100 m WBGT，不产生 System B 修饰量，也不产生 System A/B 耦合输出。更长归档、更好的站点元数据、SVF、LCZ 和站点布设数据只能作为未来解释性选项。

## 5. 正式快照说明

正式快照是未来前瞻评估和任何更强伴随列讨论的前置条件。快照必须包含冻结契约所需字段，必须区分回顾行和前瞻行，并且需要足够行数和事件支持。不能把持续增长的实时归档当作正式通过证据，也不能创建伪造快照行。

## 6. 未来重启路径

未来重启时，先检查分支和工作区状态，读取本档案和 A-L1H.5 契约。如果真实正式快照已经存在，先运行 A-L1H.7 写入冻结快照；确认 manifest 和 validation 后，再运行 A-L1H.6 前瞻评估。只有正式评估支持时，才讨论 `p_ge31_optional` 的更强内部伴随状态。除非门槛失败且用户明确开启新通道，否则不训练新模型。

## 7. 允许与禁止表述

{markdown_table(claim_rows, ["claim", "decision", "allowed_wording", "forbidden_upgrade"], None)}

## 8. Codex 重入提示

未来提示已写入：`outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_codex_reentry_prompt.md`。

## 9. 架构图

架构图已写入：`outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_systema_architecture_diagram.md`。

## 10. 车道状态矩阵

{markdown_table(lane_rows, ["lane_item", "current_decision", "blocker", "allowed_next_action", "forbidden_action"], None)}
"""


def build_handoff_doc(status: str, config: dict[str, Any], missing_prior: list[Path]) -> str:
    """Build the Chinese frozen handoff note in valid UTF-8."""
    today = config.get("generated_date", date.today().isoformat())
    missing_text = "无" if not missing_prior else "；".join(rel(path) for path in missing_prior)
    return f"""# OpenHeat System A 冻结交接说明

生成日期：{today}
决策状态：`{status}`
分支：`{git_branch()}`

## 冻结状态

System A 已冻结并等待正式快照。`wbgt_a_c` 是唯一主输出；`p_ge31_optional`、期望超阈值和区间只能作为可选诊断伴随列；`p_ge33_optional` 保持探索性。

## 交接重点

- A-L1H.5 契约不得在本交接中修改。
- A-L1H.6 和 A-L1H.7 的门槛不得在本交接中修改。
- Level 2 仅为解释性侧车，不产生站点修正或本地网格 WBGT。
- 当前等待真实正式快照；不能使用实时增长归档作为正式通过证据。
- 不创建官方预警概率、System A/B 耦合输出、risk_score 或 hazard_score。

## 未来第一步

当真实正式快照存在时，先复查 A-L1H.7 写入流程，再运行：

```bash
python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml
```

## 重入资料

- 主报告：`outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_report.md`
- 等待登记：`outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_formal_snapshot_waiting_register.csv`
- 重入提示：`outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_codex_reentry_prompt.md`
- 架构图：`outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_systema_architecture_diagram.md`

## 缺失的可选既有证据

{missing_text}
"""


def build_status(
    status: str,
    config: dict[str, Any],
    output_paths: list[Path],
    missing_required: list[Path],
    missing_prior: list[Path],
) -> str:
    """Build the A-L1H.8 status file."""
    today = config.get("generated_date", date.today().isoformat())
    files = "\n".join(f"- `{rel(path)}`" for path in output_paths)
    missing_required_text = "\n".join(f"- `{rel(path)}`" for path in missing_required) or "- none"
    missing_prior_text = "\n".join(f"- `{rel(path)}`" for path in missing_prior) or "- none"
    return f"""# A-L1H.8 Status

Status: {status}
Generated: {today}
Branch: {git_branch()}

## Scope

System A development dossier and frozen handoff only. No model training, no A-L1H.5 contract changes, no A-L1H.6/A-L1H.7 gate changes, no archive collector changes, no System B/SOLWEIG outputs, no station-adjusted WBGT, no local 100 m WBGT, no official warning probability, no risk_score/hazard_score, no System A/B coupling output, and no fake formal snapshot rows.

## Commands Run

- `python scripts/v11_l1h8_run_development_dossier.py --config configs/v11/systema_l1h8_development_dossier.yaml`

## Key Results

- Dossier status: {status}
- Evidence artifacts inventoried: {len(config["inputs"]["evidence_sources"])}
- Current System A state: frozen/waiting.
- Formal snapshot status: A-L1H.7 waiting for real formal input; A-L1H.6 waiting for formal snapshot.
- Level 2 boundary: explanatory only; no station correction, no local 100 m WBGT, no System B modifier.
- Future re-entry prompt: `outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_codex_reentry_prompt.md`

## Files Created / Modified

- `configs/v11/systema_l1h8_development_dossier.yaml`
- `scripts/v11_l1h8_systema_development_dossier.py`
- `scripts/v11_l1h8_run_development_dossier.py`
{files}

## Missing Required Contract Sources

{missing_required_text}

## Missing Optional / Prior Artifacts

{missing_prior_text}

## Caveats

- This is documentation/synthesis/handoff only.
- The dossier does not make P_ge31 an official warning probability.
- No prospective pass is claimed before a frozen formal snapshot exists.

## Safe To Commit

Controlled config, scripts, Chinese docs, handoff docs, and compact CSV/Markdown outputs from this lane after review.

## Not Safe To Commit

Raw archives, rasters, SOLWEIG/System B outputs, tif/tiff files, svfs.zip, patch zip packages, raw API dumps, large forecast/live CSVs, fake snapshot rows, or any forbidden output field.
"""


def determine_status(config: dict[str, Any], evidence_rows: list[dict[str, Any]]) -> tuple[str, list[Path], list[Path]]:
    """Determine the A-L1H.8 decision status."""
    required_contract = [resolve_path(raw) for raw in config["inputs"]["required_contract_sources"]]
    missing_required = [path for path in required_contract if not path.exists()]
    if missing_required:
        return BLOCKED_STATUS, missing_required, []
    missing_prior = [
        resolve_path(str(item["artifact_path"]))
        for item in config["inputs"]["evidence_sources"]
        if item.get("required") and not resolve_path(str(item["artifact_path"])).exists()
    ]
    if missing_prior:
        return PARTIAL_STATUS, [], missing_prior
    optional_missing = [
        resolve_path(row["artifact_path"])
        for row in evidence_rows
        if row["exists"] == "no"
    ]
    return (PARTIAL_STATUS if optional_missing else PASS_STATUS), [], optional_missing


def run_dossier(config_path: Path) -> DossierResult:
    """Run the A-L1H.8 dossier generation."""
    config = load_config(config_path)
    evidence_rows = build_evidence_inventory(config)
    status, missing_required, missing_prior = determine_status(config, evidence_rows)
    timeline_rows = build_timeline()
    lane_rows = build_lane_status_matrix()
    contract_rows = build_output_contract_summary(config)
    model_rows = build_model_evidence_summary()
    level2_rows = build_level2_boundary_summary()
    snapshot_rows = build_formal_snapshot_waiting_register(config)
    claim_rows = build_allowed_forbidden_claims()

    outputs = config["outputs"]
    output_paths = [
        write_csv(
            resolve_path(outputs["evidence_inventory"]),
            evidence_rows,
            ["lane_id", "artifact_path", "exists", "status", "key_result", "claim_boundary", "next_action"],
        ),
        write_csv(
            resolve_path(outputs["timeline"]),
            timeline_rows,
            ["sequence", "stage", "lane", "decision", "evidence", "next_state"],
        ),
        write_csv(
            resolve_path(outputs["lane_status_matrix"]),
            lane_rows,
            ["lane_item", "current_decision", "evidence", "blocker", "allowed_next_action", "forbidden_action"],
        ),
        write_csv(
            resolve_path(outputs["output_contract_summary"]),
            contract_rows,
            ["column_name", "column_group", "decision", "description", "allowed_use", "forbidden_use"],
        ),
        write_csv(
            resolve_path(outputs["model_evidence_summary"]),
            model_rows,
            ["evidence_item", "current_decision", "evidence", "caveat", "next_action"],
        ),
        write_csv(
            resolve_path(outputs["level2_boundary_summary"]),
            level2_rows,
            ["boundary_item", "current_status", "statement", "forbidden_output", "future_option"],
        ),
        write_csv(
            resolve_path(outputs["formal_snapshot_waiting_register"]),
            snapshot_rows,
            ["register_item", "current_status", "detail", "required_action", "forbidden_action"],
        ),
        write_csv(
            resolve_path(outputs["allowed_forbidden_claims"]),
            claim_rows,
            ["claim", "decision", "allowed_wording", "forbidden_upgrade", "rationale"],
        ),
    ]
    output_paths.extend(
        [
            write_text(resolve_path(outputs["future_reactivation_checklist"]), build_reactivation_checklist(config)),
            write_text(resolve_path(outputs["codex_reentry_prompt"]), build_codex_reentry_prompt(config)),
            write_text(resolve_path(outputs["architecture_diagram"]), build_architecture_diagram()),
            write_text(
                resolve_path(outputs["report"]),
                build_report(
                    status,
                    config,
                    evidence_rows,
                    timeline_rows,
                    lane_rows,
                    contract_rows,
                    model_rows,
                    level2_rows,
                    snapshot_rows,
                    claim_rows,
                ),
            ),
            write_text(resolve_path(outputs["cn_doc"]), build_cn_doc(status, config, lane_rows, claim_rows)),
            write_text(resolve_path(outputs["handoff_doc"]), build_handoff_doc(status, config, missing_prior)),
        ]
    )
    status_path = write_text(resolve_path(outputs["status"]), build_status(status, config, output_paths, missing_required, missing_prior))
    output_paths.append(status_path)
    return DossierResult(
        status=status,
        evidence_artifacts_inventoried=len(evidence_rows),
        current_frozen_state="System A frozen/waiting: A-L1H.5 contract frozen; A-L1H.6 and A-L1H.7 waiting for formal snapshot/input.",
        formal_snapshot_waiting_status="A-L1H.7 WAITING_FOR_FORMAL_INPUT; A-L1H.6 WAITING_FOR_FORMAL_SNAPSHOT.",
        level2_boundary_status="Level 2 explanatory only; no station-adjusted WBGT, local 100 m WBGT, or System B modifier.",
        reentry_prompt_path=resolve_path(outputs["codex_reentry_prompt"]),
        docs_created=[resolve_path(outputs["cn_doc"]), resolve_path(outputs["handoff_doc"])],
        output_paths=output_paths,
        missing_required_contract_sources=missing_required,
        missing_prior_artifacts=missing_prior,
    )
