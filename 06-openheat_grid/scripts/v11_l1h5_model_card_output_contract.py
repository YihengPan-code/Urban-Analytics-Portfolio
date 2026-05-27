#!/usr/bin/env python
"""Build System A A-L1H.5 model card and hourly output contract v1.0.

Inputs:
    - configs/v11/systema_l1h5_model_card_output_contract.yaml
    - Existing A-L1H.4 compact evidence, A-L2.1c evidence if present, and
      prior A-L1H report/status files declared in the config.

Outputs:
    - a_l1h5_evidence_inventory.csv
    - a_l1h5_companion_decision_matrix.csv
    - a_l1h5_output_schema.csv
    - a_l1h5_threshold_policy_register.csv
    - a_l1h5_station_caveat_register.csv
    - a_l1h5_level2_boundary_register.csv
    - a_l1h5_prospective_evaluation_plan.md
    - a_l1h5_systema_model_card.md
    - a_l1h5_hourly_output_contract_v1.md
    - a_l1h5_report.md
    - A_L1H5_STATUS.md
    - docs/v11/OpenHeat_SystemA_L1H5_model_card_output_contract_CN.md

Saved metrics:
    - Evidence inventory with source existence, decisions, and headline metrics.
    - Companion decisions, explicit output schema, threshold-policy headlines,
      station caveats, Level 2 boundary decisions, and prospective evaluation
      criteria.

Scope guard:
    This is documentation/synthesis/output-contract finalization only. It does
    not train models, stage, commit, modify archive collectors, touch System B
    or SOLWEIG outputs, create station-adjusted WBGT, create local 100 m WBGT,
    create risk_score/hazard_score, or promote P_ge31 to an official warning
    probability.
"""
from __future__ import annotations

import csv
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - used only in lean runtimes.
    yaml = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
PASS_STATUS = "A_L1H5_CONTRACT_PASS"
PARTIAL_STATUS = "A_L1H5_CONTRACT_PARTIAL"
BLOCKED_STATUS = "A_L1H5_BLOCKED"


@dataclass(frozen=True)
class ContractResult:
    """Headline result for the A-L1H.5 contract package."""

    status: str
    primary_output_decision: str
    p_ge31_decision: str
    p_ge33_decision: str
    expected_exceedance_decision: str
    interval_decision: str
    level2_boundary_decision: str
    prospective_next_action: str
    output_paths: list[Path]
    missing_required_sources: list[Path]


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
    """Read the A-L1H.5 YAML config."""
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(text)
    else:
        loaded = parse_simple_yaml(text)
    if not isinstance(loaded, dict):
        raise ValueError("Config root must be a mapping.")
    return loaded


def read_text(path: Path) -> str:
    """Read text evidence with replacement for legacy mojibake inputs."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a compact UTF-8 CSV as dictionaries."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_text(path: Path, text: str) -> Path:
    """Write UTF-8 text, creating parent directories."""
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


def to_float(value: Any) -> float | None:
    """Convert a value to float when possible."""
    if value in {None, "", "NA", "nan"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt(value: Any, digits: int = 3) -> str:
    """Format compact numeric values for reports."""
    number = to_float(value)
    if number is None:
        return "NA" if value in {None, ""} else str(value)
    return f"{number:.{digits}f}"


def find_first(rows: Iterable[dict[str, str]], predicate: Callable[[dict[str, str]], bool]) -> dict[str, str]:
    """Return the first matching row or an empty row."""
    for row in rows:
        if predicate(row):
            return row
    return {}


def has_values(row: dict[str, str], **criteria: str) -> bool:
    """Check exact string criteria on a CSV row."""
    return all(str(row.get(key, "")) == str(value) for key, value in criteria.items())


def metric(row: dict[str, str], key: str) -> str:
    """Return a compact metric value from a row."""
    return fmt(row.get(key, ""))


def threshold_headline(row: dict[str, str]) -> str:
    """Summarize a threshold policy row."""
    if not row:
        return "metric unavailable"
    return (
        f"threshold={metric(row, 'threshold')}; recall={metric(row, 'recall')}; "
        f"precision={metric(row, 'precision')}; miss_rate={metric(row, 'miss_rate')}; "
        f"false_alarm_ratio={metric(row, 'false_alarm_ratio')}"
    )


def probability_headline(row: dict[str, str]) -> str:
    """Summarize a probability metric row."""
    if not row:
        return "metric unavailable"
    return (
        f"n={metric(row, 'n',)}; events={metric(row, 'event_count')}; "
        f"Brier={metric(row, 'Brier')}; ECE_fixed={metric(row, 'ECE_fixed')}; "
        f"PR-AUC={metric(row, 'PR_AUC')}; ROC-AUC={metric(row, 'ROC_AUC')}"
    )


def expected_headline(row: dict[str, str]) -> str:
    """Summarize expected exceedance metrics."""
    if not row:
        return "metric unavailable"
    return (
        f"exceedance_MAE={metric(row, 'exceedance_MAE')} C; "
        f"positive_exceedance_MAE={metric(row, 'positive_exceedance_MAE')} C; "
        f"bias={metric(row, 'bias_expected_minus_observed')} C"
    )


def interval_headline(row: dict[str, str]) -> str:
    """Summarize interval metrics."""
    if not row:
        return "metric unavailable"
    return (
        f"nominal={metric(row, 'nominal_coverage')}; coverage={metric(row, 'empirical_coverage')}; "
        f"mean_width={metric(row, 'mean_interval_width_c')} C"
    )


def station_headline(row: dict[str, str]) -> str:
    """Summarize focus-station threshold diagnostics."""
    if not row:
        return "metric unavailable"
    return (
        f"{row.get('station_id', 'station')}: n_ge31={metric(row, 'event_count_ge31')}; "
        f"recall={metric(row, 'recall')}; miss_rate={metric(row, 'miss_rate')}; "
        f"false_alarm_ratio={metric(row, 'false_alarm_ratio')}"
    )


def extract_decision(text: str) -> str:
    """Extract the first declared status/decision from a Markdown source."""
    patterns = [
        r"Decision status:\s*`?([^`\n]+)`?",
        r"Diagnostic decision:\s*`?([^`\n]+)`?",
        r"Decision:\s*`?([^`\n]+)`?",
        r"Status:\s*`?([^`\n]+)`?",
        r"Acceptance status:\s*`?([^`\n]+)`?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return "not_declared"


def markdown_cell(value: Any) -> str:
    """Escape a compact Markdown table cell."""
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def markdown_table(rows: list[dict[str, Any]], columns: list[str], limit: int | None = None) -> str:
    """Render a compact Markdown table."""
    display_rows = rows if limit is None else rows[:limit]
    if not display_rows:
        return "_No rows available._"
    headers = columns
    body = [[markdown_cell(row.get(col, "")) for col in columns] for row in display_rows]
    widths = [len(header) for header in headers]
    for row in body:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def render(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values)) + " |"

    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([render(headers), separator, *(render(row) for row in body)])


def metric_context(config: dict[str, Any]) -> dict[str, Any]:
    """Load compact A-L1H.4 metric rows used by the contract."""
    inputs = config["inputs"]
    analysis = config["analysis"]
    threshold_rows = read_csv_rows(resolve_path(inputs["l1h4_threshold_policy_metrics"]))
    probability_rows = read_csv_rows(resolve_path(inputs["l1h4_probability_model_metrics"]))
    expected_rows = read_csv_rows(resolve_path(inputs["l1h4_expected_exceedance_metrics"]))
    interval_rows = read_csv_rows(resolve_path(inputs["l1h4_quantile_interval_metrics"]))
    deterministic_rows = read_csv_rows(resolve_path(inputs["l1h4_deterministic_baseline_metrics"]))
    station_rows = read_csv_rows(resolve_path(inputs["l1h4_station_threshold_diagnostics"]))

    primary_validation = str(analysis["primary_validation_method"])
    primary_probability = str(analysis["primary_probability_companion"])
    deterministic_score = str(analysis["deterministic_primary_score"])

    fixed31 = find_first(
        threshold_rows,
        lambda row: has_values(
            row,
            sensitivity_id="all",
            validation_method=primary_validation,
            event_target="ge31",
            companion_id=deterministic_score,
            operating_point="fixed_31",
        ),
    )
    best_f1 = find_first(
        threshold_rows,
        lambda row: has_values(
            row,
            sensitivity_id="all",
            validation_method=primary_validation,
            event_target="ge31",
            companion_id=primary_probability,
            operating_point="best_F1",
        ),
    )
    recall90 = find_first(
        threshold_rows,
        lambda row: has_values(
            row,
            sensitivity_id="all",
            validation_method=primary_validation,
            event_target="ge31",
            companion_id=primary_probability,
            operating_point="recall90",
        ),
    )
    precision70 = find_first(
        threshold_rows,
        lambda row: has_values(
            row,
            sensitivity_id="all",
            validation_method=primary_validation,
            event_target="ge31",
            companion_id=primary_probability,
            operating_point="precision70",
        ),
    )
    p_ge31 = find_first(
        probability_rows,
        lambda row: has_values(
            row,
            sensitivity_id="all",
            validation_method=primary_validation,
            event_target="ge31",
            companion_id=primary_probability,
        ),
    )
    p_ge33 = find_first(
        probability_rows,
        lambda row: has_values(row, sensitivity_id="all", validation_method=primary_validation, event_target="ge33"),
    )
    expected = find_first(
        expected_rows,
        lambda row: has_values(
            row,
            sensitivity_id="all",
            validation_method=primary_validation,
            event_target="ge31",
            companion_id="deterministic_score_gap_m4_ge31",
        ),
    )
    interval90 = find_first(
        interval_rows,
        lambda row: has_values(
            row,
            sensitivity_id="all",
            validation_method=primary_validation,
            interval_id="conformal_m4_residual",
        )
        and abs((to_float(row.get("nominal_coverage")) or -1.0) - 0.9) < 1e-9,
    )
    deterministic = find_first(
        deterministic_rows,
        lambda row: has_values(
            row,
            sensitivity_id="all",
            validation_method=primary_validation,
            output_id="wbgt_a_m4",
        ),
    )
    focus = {}
    for station_id in analysis.get("focus_stations", []):
        focus[station_id] = find_first(
            station_rows,
            lambda row, station_id=station_id: has_values(
                row,
                companion_id=primary_probability,
                operating_point="best_F1",
                station_id=str(station_id),
            ),
        )
    return {
        "threshold_rows": threshold_rows,
        "probability_rows": probability_rows,
        "expected_rows": expected_rows,
        "interval_rows": interval_rows,
        "deterministic_rows": deterministic_rows,
        "station_rows": station_rows,
        "fixed31": fixed31,
        "best_f1": best_f1,
        "recall90": recall90,
        "precision70": precision70,
        "p_ge31": p_ge31,
        "p_ge33": p_ge33,
        "expected": expected,
        "interval90": interval90,
        "deterministic": deterministic,
        "focus": focus,
    }


def make_evidence_inventory(config: dict[str, Any], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Create the evidence inventory rows."""
    inputs = config["inputs"]
    sources = [
        ("active_dev_board", "lane scope and claim boundaries", inputs["active_board"], False),
        ("a_l1h4_status", "A-L1H.4 status and headline", inputs["l1h4_status"], True),
        ("a_l1h4_model_card", "A-L1H.4 model card", inputs["l1h4_model_card"], True),
        ("a_l1h4_report", "A-L1H.4 report", inputs["l1h4_report"], True),
        ("a_l1h4_output_contract_draft", "A-L1H.4 draft output contract", inputs["l1h4_output_contract_draft"], True),
        ("a_l1h4_decision_matrix", "A-L1H.4 decision matrix", inputs["l1h4_decision_matrix"], True),
        ("a_l1h4_station_caveats", "A-L1H.4 station caveats", inputs["l1h4_station_threshold_diagnostics"], True),
        ("a_l2_1c_status", "A-L2.1c status", inputs["l2_status"], False),
        ("a_l2_1c_report", "A-L2.1c report", inputs["l2_report"], False),
        ("a_l2_1c_cn_doc", "A-L2.1c Chinese note", inputs["l2_cn_doc"], False),
    ]
    rows: list[dict[str, Any]] = []
    for evidence_id, role, raw_path, required in sources:
        path = resolve_path(raw_path)
        text = read_text(path)
        if evidence_id == "a_l1h4_decision_matrix":
            decision = "matrix_available" if path.exists() else "missing"
            key_metrics = "; ".join(
                f"{row.get('criterion')}={row.get('status')}"
                for row in read_csv_rows(path)
                if row.get("criterion") in {"primary_threshold_recall_miss", "probability_calibration", "ge33_support", "claim_boundary"}
            )
        elif evidence_id == "a_l1h4_station_caveats":
            decision = "station_caveats_available" if path.exists() else "missing"
            key_metrics = "; ".join(station_headline(row) for row in ctx["focus"].values() if row)
        elif evidence_id in {"a_l2_1c_status", "a_l2_1c_report"}:
            decision = extract_decision(text) if text else "optional_missing"
            key_metrics = "weak high-tail explanatory signal; score residual not identifiable; no station correction" if text else ""
        elif evidence_id in {"a_l1h4_status", "a_l1h4_model_card", "a_l1h4_report"}:
            decision = extract_decision(text) if text else "missing"
            key_metrics = (
                f"{probability_headline(ctx['p_ge31'])}; "
                f"best_F1 {threshold_headline(ctx['best_f1'])}; "
                f"P_ge33={ctx['p_ge33'].get('status', 'NA')}"
            )
        else:
            decision = extract_decision(text) if text else ("missing_required" if required else "optional_missing")
            key_metrics = "source reviewed for scope and claim boundaries" if text else ""
        rows.append(
            {
                "evidence_id": evidence_id,
                "evidence_role": role,
                "exists": int(path.exists()),
                "path": rel(path),
                "decision": decision,
                "key_metrics": key_metrics,
                "used_for_contract": "yes" if path.exists() else ("blocked_if_missing" if required else "no_optional_missing"),
            }
        )

    for idx, raw_path in enumerate(inputs.get("prior_reports", []), start=1):
        path = resolve_path(raw_path)
        text = read_text(path)
        rows.append(
            {
                "evidence_id": f"prior_l1_high_tail_{idx:02d}",
                "evidence_role": "prior A-L1H report/status",
                "exists": int(path.exists()),
                "path": rel(path),
                "decision": extract_decision(text) if text else "missing",
                "key_metrics": summarize_prior_report(path, text),
                "used_for_contract": "yes_context" if path.exists() else "no_optional_missing",
            }
        )
    return rows


def summarize_prior_report(path: Path, text: str) -> str:
    """Return a short known-result summary for a prior report/status."""
    name = rel(path)
    if not text:
        return ""
    if "residual_decomposition" in name or "A_L1H_LANE_STATUS" in name:
        return "A-L1H.0 found global high-tail compression plus station-specific residual bias."
    if "weather_regime_merge_full_period" in name:
        return "A-L1H.0c recovered full-period weather-regime coverage; regime evidence is diagnostic, not causal proof."
    if "weather_regime_merge/" in name:
        return "A-L1H.0b partial weather merge showed plausible but incomplete regime structure."
    if "formula_proxy_audit" in name:
        return "A-L1H.1 formula/proxy audit was weak or negative; no canonical formula replacement."
    if "probability_threshold_calibration" in name:
        return "A-L1H.2 accepted P_ge31 as retrospective diagnostic companion only."
    if "level1_integration" in name:
        return "A-L1H.2b kept WBGT_A primary and P_ge31 diagnostic; operational claims held."
    if "high_tail_challenger" in name:
        return "A-L1H.3 challenger remained recall-first diagnostic, not a contract replacement."
    return "reviewed as prior A-L1H context."


def make_companion_decision_matrix(config: dict[str, Any], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Create companion decision matrix rows."""
    p_ge33_events = metric(ctx["p_ge33"], "event_count")
    return [
        {
            "item": "wbgt_a_c deterministic baseline",
            "decision": "PRIMARY",
            "evidence": f"WBGT_A M4 LOSO MAE={metric(ctx['deterministic'], 'MAE')} C; fixed_31 {threshold_headline(ctx['fixed31'])}.",
            "caveat": "Calibrated hourly WBGT_A temporal baseline, not local 100 m WBGT.",
            "allowed_column_name": "wbgt_a_c",
            "prohibited_interpretation": "validated local WBGT prediction or public warning.",
            "next_action": "Freeze as primary System A Level 1 output for contract v1.0.",
        },
        {
            "item": "s_wbgt_ge31 deterministic severity / band",
            "decision": "PRIMARY",
            "evidence": "Derived from wbgt_a_c against 31 C / 33 C reference bands.",
            "caveat": "Severity band is deterministic WBGT_A context, not a probability or risk score.",
            "allowed_column_name": "s_wbgt_ge31; s_wbgt_band_31_33",
            "prohibited_interpretation": "official alert threshold or completed risk classification.",
            "next_action": "Keep as required interpretability columns tied to wbgt_a_c.",
        },
        {
            "item": "p_ge31_optional",
            "decision": "OPTIONAL_COMPANION",
            "evidence": f"{probability_headline(ctx['p_ge31'])}; best_F1 {threshold_headline(ctx['best_f1'])}.",
            "caveat": "Station-held-out retrospective diagnostic only.",
            "allowed_column_name": "p_ge31_optional; p_ge31_model_id_optional; p_ge31_threshold_policy_optional",
            "prohibited_interpretation": "official warning probability or public alert probability.",
            "next_action": "Evaluate prospectively before any stronger companion status.",
        },
        {
            "item": "p_ge33_optional",
            "decision": "EXPLORATORY_ONLY",
            "evidence": f"P_ge33 support gate status={ctx['p_ge33'].get('status', 'NA')}; event_count={p_ge33_events}.",
            "caveat": "ge33 event support is below promotion threshold.",
            "allowed_column_name": "p_ge33_optional",
            "prohibited_interpretation": "validated ge33 probability or official severe-warning probability.",
            "next_action": f"Require at least {config['analysis']['min_ge33_events_for_promotion']} held-out/prospective events before promotion review.",
        },
        {
            "item": "expected_exceedance_ge31_optional",
            "decision": "OPTIONAL_COMPANION",
            "evidence": expected_headline(ctx["expected"]),
            "caveat": "Magnitude diagnostic above 31 C; not a corrected WBGT forecast.",
            "allowed_column_name": "expected_exceedance_ge31_optional",
            "prohibited_interpretation": "station-adjusted WBGT or local-cell WBGT delta.",
            "next_action": "Keep optional until prospective calibration and error behavior are reviewed.",
        },
        {
            "item": "prediction_interval_low/high_optional",
            "decision": "OPTIONAL_COMPANION",
            "evidence": interval_headline(ctx["interval90"]),
            "caveat": "Retrospective conformal interval diagnostic; near-ge33 coverage remains weak.",
            "allowed_column_name": "prediction_interval_low_optional; prediction_interval_high_optional",
            "prohibited_interpretation": "guaranteed operational forecast interval or public safety margin.",
            "next_action": "Retain as optional uncertainty diagnostic with explicit coverage metadata.",
        },
        {
            "item": "station_context_residual_explanation",
            "decision": "EXPLANATORY_ONLY",
            "evidence": "A-L2.1c found weak high-tail residual explanatory signal and score residual not identifiable.",
            "caveat": "Station context is station-level residual explanation only.",
            "allowed_column_name": "not_in_hourly_output",
            "prohibited_interpretation": "station correction model or causal urban-form correction.",
            "next_action": "Use only in caveat notes unless a future A-L2 protocol promotes it.",
        },
        {
            "item": "station_adjusted_wbgt",
            "decision": "FORBIDDEN",
            "evidence": "A-L2.1c did not identify a correction model.",
            "caveat": "Would silently upgrade claims beyond evidence.",
            "allowed_column_name": "none",
            "prohibited_interpretation": "station-adjusted WBGT_C or corrected official WBGT.",
            "next_action": "Do not create in System A Level 1 output.",
        },
        {
            "item": "local_100m_wbgt",
            "decision": "FORBIDDEN",
            "evidence": "No local cell-level WBGT validation exists in this lane.",
            "caveat": "System A Level 1 is temporal/station-hour evidence, not cell-level WBGT.",
            "allowed_column_name": "none",
            "prohibited_interpretation": "validated 100 m local WBGT prediction.",
            "next_action": "Keep out of Level 1 hourly contract.",
        },
        {
            "item": "system_b_coupling",
            "decision": "FUTURE_SCOPED",
            "evidence": "Current contract is System A only; System B/SOLWEIG coupling is outside A-L1H.5.",
            "caveat": "No System A/B coupling output is created here.",
            "allowed_column_name": "none",
            "prohibited_interpretation": "completed coupled hazard/risk product.",
            "next_action": "Open a separate scoped coupling lane only after current v1.1 evidence gates.",
        },
        {
            "item": "risk_score/hazard_score",
            "decision": "FORBIDDEN",
            "evidence": "Exposure/vulnerability and risk overlay are not explicit in this contract.",
            "caveat": "Hazard/risk score would exceed current System A evidence.",
            "allowed_column_name": "none",
            "prohibited_interpretation": "hazard map equals risk map or completed risk score.",
            "next_action": "Do not create until a separate risk-overlay design is approved.",
        },
    ]


def make_output_schema() -> list[dict[str, Any]]:
    """Create the hourly output schema register."""
    rows = [
        ("timestamp_sgt", "required", "datetime_iso8601", "SGT timestamp for the hourly row.", "hour identity", "missing or ambiguous timezone"),
        ("timestamp_utc", "required", "datetime_iso8601", "UTC timestamp matching timestamp_sgt.", "cross-system audit", "timezone-free time key"),
        ("wbgt_a_c", "required", "float_celsius", "Primary deterministic System A WBGT_A value.", "calibrated hourly WBGT temporal baseline", "local 100 m WBGT or official warning"),
        ("wbgt_a_model_id", "required", "string", "Identifier for the deterministic WBGT_A model.", "version traceability", "hidden model substitution"),
        ("wbgt_a_version", "required", "string", "Version string for the System A Level 1 contract/model artifact.", "contract traceability", "unversioned production use"),
        ("s_wbgt_ge31", "required", "float_or_integer", "Deterministic severity above the 31 C reference, derived from wbgt_a_c.", "severity context", "probability or risk score"),
        ("s_wbgt_band_31_33", "required", "categorical", "Band below_31, ge31_lt33, or ge33_plus derived from wbgt_a_c.", "threshold context", "public warning class"),
        ("source_forcing", "required", "string", "Forcing/source family used to create the row.", "provenance", "undocumented live/archive mixing"),
        ("is_retrospective_or_prospective", "required", "categorical", "Whether the row is retrospective or prospective.", "evaluation separation", "mixing retrospective and prospective rows"),
        ("quality_flag", "required", "string", "Compact quality/provenance flag.", "row quality audit", "silent quality failures"),
        ("p_ge31_optional", "optional_companion", "float_0_1", "Optional retrospective diagnostic P(WBGT >= 31 C).", "internal diagnostic companion", "official warning probability"),
        ("p_ge31_model_id_optional", "optional_companion", "string", "Model id for p_ge31_optional.", "traceability", "unversioned probability"),
        ("p_ge31_threshold_policy_optional", "optional_companion", "string", "Optional policy id used to interpret p_ge31_optional.", "diagnostic threshold review", "official public warning threshold"),
        ("p_ge33_optional", "optional_companion", "float_0_1", "Exploratory optional P(WBGT >= 33 C).", "low-support exploratory diagnostic", "promoted severe warning probability"),
        ("expected_exceedance_ge31_optional", "optional_companion", "float_celsius", "Optional expected exceedance above 31 C.", "magnitude diagnostic", "corrected WBGT value"),
        ("prediction_interval_low_optional", "optional_companion", "float_celsius", "Optional lower interval bound for wbgt_a_c diagnostic uncertainty.", "uncertainty diagnostic", "guaranteed operational interval"),
        ("prediction_interval_high_optional", "optional_companion", "float_celsius", "Optional upper interval bound for wbgt_a_c diagnostic uncertainty.", "uncertainty diagnostic", "guaranteed operational interval"),
        ("lead_time_hours_optional", "optional_companion", "integer_or_float", "Optional lead time for prospective rows when available.", "prospective evaluation audit", "claim of forecast skill without validation"),
        ("cell_id", "forbidden", "string", "Cell-level identifier is forbidden in System A Level 1 output.", "none", "local 100 m WBGT or System A/B coupling"),
        ("local_wbgt_c", "forbidden", "float_celsius", "Local cell WBGT is forbidden.", "none", "validated local WBGT prediction"),
        ("delta_wbgt_cell", "forbidden", "float_celsius", "Cell-level WBGT delta is forbidden.", "none", "SOLWEIG/Tmrt-as-WBGT conversion"),
        ("station_adjusted_wbgt_c", "forbidden", "float_celsius", "Station-adjusted WBGT is forbidden.", "none", "station correction layer"),
        ("risk_score", "forbidden", "float", "Risk score is forbidden.", "none", "completed risk model"),
        ("hazard_score", "forbidden", "float", "Hazard score is forbidden.", "none", "completed hazard map"),
    ]
    return [
        {
            "column_name": name,
            "column_group": group,
            "type": value_type,
            "description": description,
            "allowed_use": allowed,
            "forbidden_use": forbidden,
        }
        for name, group, value_type, description, allowed, forbidden in rows
    ]


def make_threshold_policy_register(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Create the threshold policy register."""
    specs = [
        (
            "fixed_31",
            "baseline_reference",
            ctx["fixed31"],
            "Reference deterministic WBGT_A score >=31 C comparison.",
            "Official public warning threshold or replacement for optional companions.",
            "Baseline only; A-L1H.4 showed lower recall and higher miss rate than optional P_ge31 best_F1.",
        ),
        (
            "best_F1",
            "retrospective_operating_point",
            ctx["best_f1"],
            "Internal retrospective operating point balancing precision and recall.",
            "Official public warning threshold or prospective deployment gate.",
            "Selected on training folds and evaluated held-out; requires prospective validation.",
        ),
        (
            "recall90",
            "screening_high_tail_sensitive",
            ctx["recall90"],
            "Internal high-tail-sensitive screening and miss inventory review.",
            "Public alert threshold without false-alarm governance.",
            "Improves recall but raises false alarms; use only as diagnostic screen.",
        ),
        (
            "precision70",
            "precision_sensitive_if_supported",
            ctx["precision70"],
            "Internal precision-sensitive diagnostic if the row is supported.",
            "Claimed precision guarantee or public threshold.",
            "A-L1H.4 isotonic row is evaluated but does not strictly reach 0.70 precision; retain as recorded diagnostic.",
        ),
    ]
    rows = []
    for policy_id, role, row, allowed, not_allowed, caveat in specs:
        rows.append(
            {
                "policy_id": policy_id,
                "policy_role": role,
                "threshold": metric(row, "threshold"),
                "allowed_use": allowed,
                "not_allowed_use": not_allowed,
                "recall": metric(row, "recall"),
                "precision": metric(row, "precision"),
                "miss_rate": metric(row, "miss_rate"),
                "false_alarm_ratio": metric(row, "false_alarm_ratio"),
                "headline": threshold_headline(row),
                "caveats": caveat,
            }
        )
    return rows


def make_station_caveat_register(config: dict[str, Any], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Create station caveat rows from A-L1H.4 station diagnostics."""
    focus_stations = set(str(value) for value in config["analysis"].get("focus_stations", []))
    primary_probability = str(config["analysis"]["primary_probability_companion"])
    rows = [
        row
        for row in ctx["station_rows"]
        if row.get("companion_id") == primary_probability and row.get("operating_point") == "best_F1"
    ]
    rows.sort(key=lambda row: (0 if row.get("station_id") in focus_stations else 1, row.get("station_id", "")))
    caveats = []
    for row in rows:
        station_id = row.get("station_id", "")
        event_count = to_float(row.get("event_count_ge31")) or 0.0
        miss_rate = to_float(row.get("miss_rate"))
        false_alarm = to_float(row.get("false_alarm_ratio"))
        if station_id == "S142":
            interpretation = "Focus caveat: high-tail misses remain material; do not treat this as solved or corrected."
            monitoring = "Track S142 recall, miss rate, high-tail residual, and any no-S142 sensitivity in prospective review."
        elif station_id == "S139":
            interpretation = "Focus caveat: very low event support and high false-alarm sensitivity."
            monitoring = "Track event support before making station-specific reliability claims."
        elif event_count == 0:
            interpretation = "No held-out ge31 events; recall is not interpretable for this station."
            monitoring = "Monitor future ge31 support before station-specific interpretation."
        elif miss_rate is not None and miss_rate >= 0.4:
            interpretation = "High miss-rate caveat under best_F1 diagnostic policy."
            monitoring = "Review misses in prospective archive snapshot before promotion."
        elif false_alarm is not None and false_alarm >= 0.6:
            interpretation = "High false-alarm caveat under best_F1 diagnostic policy."
            monitoring = "Review false alarms in prospective archive snapshot before promotion."
        else:
            interpretation = "No station correction; retain routine caveat monitoring."
            monitoring = "Continue prospective station diagnostics."
        caveats.append(
            {
                "station_id": station_id,
                "event_support": f"n={metric(row, 'n')}; n_ge31={metric(row, 'event_count_ge31')}",
                "precision": metric(row, "precision"),
                "recall": metric(row, "recall"),
                "miss_rate": metric(row, "miss_rate"),
                "false_alarm_ratio": metric(row, "false_alarm_ratio"),
                "recall_miss_false_alarm_caveat": station_headline(row),
                "interpretation": interpretation,
                "not_station_correction": "yes",
                "recommended_monitoring": monitoring,
            }
        )
    return caveats


def make_level2_boundary_register(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Create the Level 2 boundary register."""
    l2_status_path = resolve_path(config["inputs"]["l2_status"])
    l2_report_path = resolve_path(config["inputs"]["l2_report"])
    source_note = (
        f"{rel(l2_status_path)} and {rel(l2_report_path)}"
        if l2_status_path.exists() and l2_report_path.exists()
        else "A-L2.1c source missing or partial"
    )
    return [
        {
            "boundary_item": "level2_role",
            "decision": "EXPLANATORY_ONLY",
            "evidence": f"A-L2.1c scoped residual preflight reviewed: {source_note}.",
            "allowed_use": "Station-level residual explanation and caveat framing.",
            "forbidden_use": "Hourly correction layer or operational forecast model.",
            "next_action": "Only proceed under separate A-L2 protocol review.",
        },
        {
            "boundary_item": "high_tail_residual_signal",
            "decision": "WEAK_EXPLANATORY_SIGNAL_NOT_CORRECTION",
            "evidence": "High-tail residual had weak station-context explanatory signal.",
            "allowed_use": "Explain why S142/S139 caveats remain monitored.",
            "forbidden_use": "Correct wbgt_a_c or create station-adjusted WBGT.",
            "next_action": "Monitor prospectively; do not implement correction in L1H.5.",
        },
        {
            "boundary_item": "score_residual",
            "decision": "NOT_IDENTIFIABLE",
            "evidence": "A-L2.1c score residual target was not identifiable.",
            "allowed_use": "Document limitation.",
            "forbidden_use": "Claim station context fixes Level 1 score residual.",
            "next_action": "No score residual correction model.",
        },
        {
            "boundary_item": "station_adjusted_wbgt",
            "decision": "FORBIDDEN",
            "evidence": "No promoted station correction model.",
            "allowed_use": "none",
            "forbidden_use": "station_adjusted_wbgt_c output.",
            "next_action": "Keep forbidden in hourly output schema.",
        },
        {
            "boundary_item": "local_cell_level_modifier",
            "decision": "FORBIDDEN",
            "evidence": "No System B/SOLWEIG or 100 m cell features are used in System A Level 1.",
            "allowed_use": "none in this contract",
            "forbidden_use": "local 100 m WBGT or System A/B coupling output.",
            "next_action": "Future scoped lane only, not L1H.5.",
        },
    ]


def build_prospective_plan(status: str, config: dict[str, Any]) -> str:
    """Build the prospective evaluation plan Markdown."""
    min_ge33 = config["analysis"]["min_ge33_events_for_promotion"]
    today = config.get("generated_date", date.today().isoformat())
    return f"""# A-L1H.5 Prospective Evaluation Plan

Generated: {today}
Decision status: `{status}`

## Purpose

System A Level 1 v1.0 is frozen as a model card and output contract before prospective evaluation. The current evidence is retrospective station-held-out evidence; it is not a public warning system and not a validated prospective forecast.

## Required Future Snapshot

- Use a future formal archive snapshot with immutable input rows, model/card version, and extraction timestamp.
- Separate retrospective rows from prospective rows using `is_retrospective_or_prospective`.
- Keep `lead_time_hours_optional` populated for prospective rows when lead time exists.
- Do not append live-growing archive rows during formal comparison.

## Validation Design

LOSO is retrospective evidence. A prospective time validation is required before any stronger operational claim for `p_ge31_optional`, interval columns, or expected exceedance columns.

The model card, output schema, threshold-policy register, and companion decisions must be frozen before the prospective window starts.

## Metrics

- `recall_ge31`
- `precision_ge31`
- `miss_rate_ge31`
- Brier score for `p_ge31_optional`
- ECE for `p_ge31_optional`
- high-tail MAE for rows with observed WBGT >=31 C
- S142/S139 and all-station caveat register refresh

## P_ge31 Promotion Criteria

`p_ge31_optional` may be considered for stronger companion status only if a future prospective snapshot preserves materially improved ge31 recall/miss behavior relative to `wbgt_a_c` fixed_31, maintains acceptable precision/false-alarm behavior, has stable Brier/ECE, and does not fail station caveat checks.

Promotion still cannot make it an official public warning probability without separate operational governance.

## ge33 Promotion Gate

`p_ge33_optional` remains exploratory until at least {min_ge33} held-out/prospective ge33 events are available in an explicitly reviewed snapshot, with station support and calibration diagnostics reported separately.
"""


def build_model_card(status: str, config: dict[str, Any], ctx: dict[str, Any], schema_rows: list[dict[str, Any]]) -> str:
    """Build the System A model card."""
    required_columns = ", ".join(row["column_name"] for row in schema_rows if row["column_group"] == "required")
    optional_columns = ", ".join(row["column_name"] for row in schema_rows if row["column_group"] == "optional_companion")
    today = config.get("generated_date", date.today().isoformat())
    s142 = station_headline(ctx["focus"].get("S142", {}))
    s139 = station_headline(ctx["focus"].get("S139", {}))
    return f"""# System A Level 1 Model Card v1.0

Generated: {today}
Decision status: `{status}`
Branch: `{git_branch()}`

## Intended Use

System A Level 1 produces a calibrated hourly WBGT_A temporal baseline for internal retrospective and future prospective evaluation. The primary output is `wbgt_a_c`.

Optional companions may support internal diagnostics around WBGT >=31 C, expected exceedance above 31 C, and uncertainty intervals. These companions do not replace `wbgt_a_c`.

## Not Intended Use

System A Level 1 is not a validated local 100 m WBGT prediction system, not a real-time public warning system, not a station correction layer, not a System A/B coupling product, and not a risk or hazard score.

## Input Data

The model card is based on compact A-L1H.4 evidence, prior A-L1H high-tail reports, and A-L2.1c station-context preflight evidence if present. The contract uses no System B, SOLWEIG, Tmrt, raster, cell-level, exposure, vulnerability, or archive collector inputs.

## Output Columns

Required columns: {required_columns}.

Optional companion columns: {optional_columns}.

Forbidden columns are listed in `a_l1h5_output_schema.csv` and include cell-level WBGT, station-adjusted WBGT, risk score, and hazard score fields.

## Validation Evidence

- Deterministic WBGT_A baseline: MAE={metric(ctx['deterministic'], 'MAE')} C; high-tail MAE for observed ge31={metric(ctx['deterministic'], 'high_tail_mae_obs_ge31')} C.
- P_ge31 optional companion: {probability_headline(ctx['p_ge31'])}.
- P_ge31 best_F1 policy: {threshold_headline(ctx['best_f1'])}.
- Expected exceedance optional diagnostic: {expected_headline(ctx['expected'])}.
- Interval optional diagnostic: {interval_headline(ctx['interval90'])}.
- P_ge33 support: status={ctx['p_ge33'].get('status', 'NA')}; events={metric(ctx['p_ge33'], 'event_count')}.

## Known Failure Modes

- High-tail compression near and above 31 C remains a diagnostic caveat.
- ge33 support is low and cannot support promoted probability claims.
- Threshold policies are retrospective operating points, not official warning thresholds.
- Optional intervals have retrospective coverage diagnostics and weak near-ge33 coverage.
- Station diagnostics can be unstable where event support is low.

## S142/S139 Caveats

- {s142}
- {s139}

These are caveats and monitoring requirements, not station correction rules.

## Level 2 Boundary

A-L2.1c is an explanatory station-level residual preflight only. It does not create station-adjusted WBGT, a score residual correction, or a local cell-level modifier.

## System B Boundary

This Level 1 contract does not use System B, SOLWEIG, Tmrt, morphology, cell_id, or radiative modifier features. Any System A/B coupling must be a separate future-scoped lane.

## Prospective Evaluation Requirements

Before any stronger claim for optional companions, freeze this model card and output schema, then evaluate a future formal archive snapshot with prospective rows separated from retrospective rows. Required metrics include recall_ge31, precision_ge31, miss_rate_ge31, Brier, ECE, high-tail MAE, and station caveat refresh.

## Versioning

Contract version: `systema_l1h5_hourly_output_contract_v1`.

Primary model id: `{config['analysis']['deterministic_primary_model_id']}`.
"""


def build_output_contract(status: str, config: dict[str, Any], schema_rows: list[dict[str, Any]], policy_rows: list[dict[str, Any]]) -> str:
    """Build the hourly output contract Markdown."""
    today = config.get("generated_date", date.today().isoformat())
    required = [row for row in schema_rows if row["column_group"] == "required"]
    optional = [row for row in schema_rows if row["column_group"] == "optional_companion"]
    forbidden = [row for row in schema_rows if row["column_group"] == "forbidden"]
    return f"""# System A Hourly Output Contract v1.0

Generated: {today}
Decision status: `{status}`

## Contract Identity

System A Level 1 produces hourly WBGT_A rows. The primary field is `wbgt_a_c`. Optional companions remain diagnostics unless a future frozen prospective evaluation promotes them.

## Required Columns

{markdown_table(required, ["column_name", "type", "description", "forbidden_use"], None)}

## Optional Companion Columns

{markdown_table(optional, ["column_name", "type", "description", "forbidden_use"], None)}

## Forbidden Columns

{markdown_table(forbidden, ["column_name", "description", "forbidden_use"], None)}

## Threshold Policy

{markdown_table(policy_rows, ["policy_id", "policy_role", "threshold", "recall", "precision", "miss_rate", "caveats"], None)}

No policy in this contract is an official public warning threshold.

## Row Rules

- `wbgt_a_c` is required and remains the deterministic primary output.
- `s_wbgt_ge31` and `s_wbgt_band_31_33` are deterministic summaries derived from `wbgt_a_c`.
- Optional companion columns may be absent, null, or populated only when their model id / policy metadata is present.
- Prospective rows must be distinguishable from retrospective rows.
- The contract forbids station-adjusted WBGT, local 100 m WBGT, System A/B coupling fields, risk_score, and hazard_score.
"""


def build_report(
    status: str,
    config: dict[str, Any],
    ctx: dict[str, Any],
    decision_rows: list[dict[str, Any]],
    policy_rows: list[dict[str, Any]],
    station_rows: list[dict[str, Any]],
    level2_rows: list[dict[str, Any]],
) -> str:
    """Build the English A-L1H.5 report."""
    today = config.get("generated_date", date.today().isoformat())
    return f"""# System A A-L1H.5 Model Card / Output Contract Finalization

Generated: {today}
Decision status: `{status}`

## 1. Why A-L1H.5 Follows A-L1H.4 And A-L2.1c

A-L1H.4 concluded `A_L1H4_COMPANION_PROMISING`: `wbgt_a_c` remains primary, `p_ge31_optional` improves ge31 threshold behavior as a companion, `p_ge33_optional` remains low-support exploratory, and expected exceedance / intervals are optional diagnostics. A-L2.1c found weak station-context high-tail residual signal and score residual was not identifiable, so this lane finalizes a Level 1 contract without a station correction layer.

## 2. System A Primary Output

The primary output is `wbgt_a_c`: a calibrated hourly WBGT_A temporal baseline. Deterministic ge31 severity fields are derived from it and are not risk scores.

## 3. Optional Companions

{markdown_table(decision_rows[:6], ["item", "decision", "allowed_column_name", "caveat"], None)}

## 4. Threshold Policy Register

{markdown_table(policy_rows, ["policy_id", "policy_role", "threshold", "recall", "precision", "miss_rate", "not_allowed_use"], None)}

## 5. Station Caveats

{markdown_table(station_rows, ["station_id", "event_support", "recall", "miss_rate", "false_alarm_ratio", "interpretation"], 12)}

S142/S139 remain focus caveats. All station rows remain monitoring diagnostics, not station corrections.

## 6. Level 2 Boundary

{markdown_table(level2_rows, ["boundary_item", "decision", "forbidden_use"], None)}

## 7. System B / Coupling Boundary

No System B, SOLWEIG, Tmrt, morphology, cell_id, local WBGT, or radiative modifier feature is part of this System A hourly contract. Coupling is future-scoped only and produces no output here.

## 8. Prospective Evaluation Plan

A future formal archive snapshot must separate prospective rows from retrospective rows. LOSO remains retrospective evidence; prospective time validation is required with recall_ge31, precision_ge31, miss_rate_ge31, Brier, ECE, high-tail MAE, and station caveat refresh before any stronger companion claim.

## 9. Final Allowed / Forbidden Claims

Allowed: calibrated hourly WBGT_A temporal baseline; optional retrospective P_ge31 diagnostic companion; optional expected exceedance and interval diagnostics; station caveat monitoring.

Forbidden: validated local WBGT prediction, official warning probability, station-adjusted WBGT, local 100 m WBGT, System A/B coupling output, risk_score, hazard_score, and promoted ge33 probability.

## 10. Next Recommended Lane

Freeze and review this A-L1H.5 contract package. The next recommended action is a future prospective evaluation protocol using a frozen archive snapshot; do not create a station correction layer or System A/B coupling inside this lane.
"""


def build_cn_doc(
    status: str,
    config: dict[str, Any],
    ctx: dict[str, Any],
    decision_rows: list[dict[str, Any]],
    policy_rows: list[dict[str, Any]],
    level2_rows: list[dict[str, Any]],
) -> str:
    """Build the Chinese documentation note in valid UTF-8."""
    today = config.get("generated_date", date.today().isoformat())
    return f"""# OpenHeat System A A-L1H.5 模型卡与小时输出契约

生成日期：{today}
决策状态：`{status}`

## 1. 为什么 A-L1H.5 接在 A-L1H.4 和 A-L2.1c 之后

A-L1H.4 的结论是 `A_L1H4_COMPANION_PROMISING`：确定性的 `wbgt_a_c` 仍是 System A Level 1 主输出，`p_ge31_optional` 只能作为可选诊断伴随列，`p_ge33_optional` 因事件支持不足仍为探索性。A-L2.1c 显示站点环境对高尾残差只有弱解释信号，分数残差不可识别，因此本契约不建立站点修正层。

## 2. System A 主输出

System A Level 1 的主输出是 `wbgt_a_c`，含义是校准后的小时级 WBGT_A 时间基线。`s_wbgt_ge31` 和 `s_wbgt_band_31_33` 只由 `wbgt_a_c` 派生，用于确定性阈值语境，不是风险分数，也不是公共预警等级。

## 3. 可选伴随列

{markdown_table(decision_rows[:6], ["item", "decision", "allowed_column_name", "caveat"], None)}

## 4. 阈值策略登记

{markdown_table(policy_rows, ["policy_id", "policy_role", "threshold", "recall", "precision", "miss_rate", "caveats"], None)}

以上策略都不是官方公共预警阈值。

## 5. 站点注意事项

S142 仍是高尾漏报注意站点：{station_headline(ctx["focus"].get("S142", {}))}。

S139 事件支持很低且误报敏感：{station_headline(ctx["focus"].get("S139", {}))}。

这些内容是监测与解释注意事项，不是站点修正模型。

## 6. Level 2 边界

{markdown_table(level2_rows, ["boundary_item", "decision", "forbidden_use"], None)}

Level 2 当前只能作为弱解释层，不能输出 `station_adjusted_wbgt_c`，也不能生成本地网格 WBGT。

## 7. System B 与耦合边界

本契约不使用 System B、SOLWEIG、Tmrt、形态学、cell_id 或局地辐射修饰特征，也不创建 System A/B 耦合输出。

## 8. 前瞻评估计划

未来需要冻结模型卡、输出契约和阈值策略，然后在新的正式归档快照上区分回顾行与前瞻行。LOSO 仍是回顾证据；前瞻时间验证必须报告 recall_ge31、precision_ge31、miss_rate_ge31、Brier、ECE、高尾 MAE 和站点注意事项。

## 9. 最终允许与禁止表述

允许表述：校准后的小时 WBGT_A 时间基线；可选的回顾性 `P_ge31` 诊断伴随列；可选的 31 C 超阈期望值与区间诊断；站点注意事项监测。

禁止表述：已验证的本地 100 m WBGT 预测；官方预警概率；站点修正 WBGT；System A/B 耦合输出；risk_score；hazard_score；已提升的 ge33 概率。

## 10. 下一建议通道

建议冻结并审阅 A-L1H.5 契约包。下一步应是基于冻结快照的前瞻评估协议，而不是站点修正层、局地 WBGT 或 System A/B 耦合。
"""


def build_status(
    status: str,
    config: dict[str, Any],
    result_paths: list[Path],
    missing_required: list[Path],
    result: ContractResult | None = None,
) -> str:
    """Build the lane status file."""
    today = config.get("generated_date", date.today().isoformat())
    files = "\n".join(f"- `{rel(path)}`" for path in result_paths)
    missing = "\n".join(f"- `{rel(path)}`" for path in missing_required) or "- none"
    return f"""# A-L1H.5 Status

Status: {status}
Generated: {today}
Branch: {git_branch()}

## Scope

System A Level 1 model card and hourly output contract finalization only. No model training, no System B/SOLWEIG outputs, no archive collector changes, no station-adjusted WBGT, no local 100 m WBGT, no risk_score, and no hazard_score.

## Commands Run

- `python scripts/v11_l1h5_run_model_card_output_contract.py --config configs/v11/systema_l1h5_model_card_output_contract.yaml`

## Key Results

- Primary output decision: `wbgt_a_c` is PRIMARY.
- P_ge31 decision: OPTIONAL_COMPANION, not official warning probability.
- P_ge33 decision: EXPLORATORY_ONLY / LOW_SUPPORT.
- Expected exceedance decision: OPTIONAL_COMPANION.
- Interval decision: OPTIONAL_COMPANION.
- Level 2 boundary decision: EXPLANATORY_ONLY; no station correction layer.
- Prospective next action: future frozen formal archive snapshot with prospective rows separated from retrospective rows.

## Files Created / Modified

{files}

## Missing Required Sources

{missing}

## Caveats

- Current evidence is retrospective station-held-out evidence.
- Threshold policies are diagnostic operating points, not public warning thresholds.
- S142/S139 remain station caveats, not station correction rules.
- ge33 probability remains exploratory until event support is sufficient.

## Safe To Commit

Controlled config, scripts, docs, and compact CSV/Markdown outputs from this lane after review.

## Not Safe To Commit

Raw archives, rasters, SOLWEIG/System B outputs, tif/tiff files, svfs.zip, patch zip packages, raw API dumps, or large forecast/live CSVs.
"""


def determine_status(config: dict[str, Any]) -> tuple[str, list[Path]]:
    """Determine contract status from required evidence availability."""
    required_keys = [
        "l1h4_status",
        "l1h4_report",
        "l1h4_model_card",
        "l1h4_output_contract_draft",
        "l1h4_decision_matrix",
        "l1h4_threshold_policy_metrics",
        "l1h4_probability_model_metrics",
        "l1h4_expected_exceedance_metrics",
        "l1h4_quantile_interval_metrics",
        "l1h4_deterministic_baseline_metrics",
        "l1h4_station_threshold_diagnostics",
    ]
    missing = [resolve_path(config["inputs"][key]) for key in required_keys if not resolve_path(config["inputs"][key]).exists()]
    if missing:
        return BLOCKED_STATUS, missing
    optional_l2 = [resolve_path(config["inputs"][key]) for key in ("l2_status", "l2_report")]
    if any(not path.exists() for path in optional_l2):
        return PARTIAL_STATUS, []
    return PASS_STATUS, []


def run_contract(config_path: Path) -> ContractResult:
    """Run A-L1H.5 contract generation."""
    config = load_config(config_path)
    status, missing_required = determine_status(config)
    ctx = metric_context(config)

    evidence_rows = make_evidence_inventory(config, ctx)
    decision_rows = make_companion_decision_matrix(config, ctx)
    schema_rows = make_output_schema()
    policy_rows = make_threshold_policy_register(ctx)
    station_rows = make_station_caveat_register(config, ctx)
    level2_rows = make_level2_boundary_register(config)

    outputs = config["outputs"]
    output_paths = [
        write_csv(
            resolve_path(outputs["evidence_inventory"]),
            evidence_rows,
            ["evidence_id", "evidence_role", "exists", "path", "decision", "key_metrics", "used_for_contract"],
        ),
        write_csv(
            resolve_path(outputs["companion_decision_matrix"]),
            decision_rows,
            ["item", "decision", "evidence", "caveat", "allowed_column_name", "prohibited_interpretation", "next_action"],
        ),
        write_csv(
            resolve_path(outputs["output_schema"]),
            schema_rows,
            ["column_name", "column_group", "type", "description", "allowed_use", "forbidden_use"],
        ),
        write_csv(
            resolve_path(outputs["threshold_policy_register"]),
            policy_rows,
            ["policy_id", "policy_role", "threshold", "allowed_use", "not_allowed_use", "recall", "precision", "miss_rate", "false_alarm_ratio", "headline", "caveats"],
        ),
        write_csv(
            resolve_path(outputs["station_caveat_register"]),
            station_rows,
            ["station_id", "event_support", "precision", "recall", "miss_rate", "false_alarm_ratio", "recall_miss_false_alarm_caveat", "interpretation", "not_station_correction", "recommended_monitoring"],
        ),
        write_csv(
            resolve_path(outputs["level2_boundary_register"]),
            level2_rows,
            ["boundary_item", "decision", "evidence", "allowed_use", "forbidden_use", "next_action"],
        ),
    ]

    md_paths = [
        write_text(resolve_path(outputs["prospective_evaluation_plan"]), build_prospective_plan(status, config)),
        write_text(resolve_path(outputs["model_card"]), build_model_card(status, config, ctx, schema_rows)),
        write_text(resolve_path(outputs["hourly_output_contract"]), build_output_contract(status, config, schema_rows, policy_rows)),
        write_text(resolve_path(outputs["report"]), build_report(status, config, ctx, decision_rows, policy_rows, station_rows, level2_rows)),
        write_text(resolve_path(outputs["cn_doc"]), build_cn_doc(status, config, ctx, decision_rows, policy_rows, level2_rows)),
    ]
    output_paths.extend(md_paths)

    result = ContractResult(
        status=status,
        primary_output_decision="PRIMARY: wbgt_a_c deterministic WBGT_A temporal baseline",
        p_ge31_decision="OPTIONAL_COMPANION: retrospective diagnostic only, not official warning probability",
        p_ge33_decision="EXPLORATORY_ONLY: LOW_SUPPORT, not promoted",
        expected_exceedance_decision="OPTIONAL_COMPANION: diagnostic exceedance magnitude only",
        interval_decision="OPTIONAL_COMPANION: retrospective uncertainty diagnostic only",
        level2_boundary_decision="EXPLANATORY_ONLY: no station-adjusted WBGT and no local cell modifier",
        prospective_next_action="Freeze model/card and evaluate a future formal archive snapshot with prospective rows separated from retrospective rows.",
        output_paths=output_paths,
        missing_required_sources=missing_required,
    )
    status_path = write_text(resolve_path(outputs["status"]), build_status(status, config, output_paths, missing_required, result))
    result.output_paths.append(status_path)
    return result
