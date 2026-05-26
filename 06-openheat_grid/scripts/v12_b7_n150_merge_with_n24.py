"""Merge completed N24 labels with B7 N126 new SOLWEIG labels into the N150 label set.

Inputs:
  - outputs/v12_solweig_n24_execution/n24_focus_tmrt_summary.csv
  - outputs/v12_solweig_n24_execution/n24_base_vs_overhead_delta.csv
  - outputs/v12_solweig_n150_execution/n150_new_focus_tmrt_summary.csv
  - outputs/v12_solweig_n150_execution/n150_new_base_vs_overhead_delta.csv
  - configs/v12/v12_solweig_n150_full_run_matrix.csv
  - outputs/v12_systemb_n150_sample_design/n150_selected_cells.csv
  - configs/v12/v12_solweig_n150_execution_config.example.json

Outputs:
  - outputs/v12_solweig_n150_execution/n150_focus_tmrt_summary_merged.csv
  - outputs/v12_solweig_n150_execution/n150_base_vs_overhead_delta_merged.csv
  - outputs/v12_solweig_n150_execution/n150_modifier_targets_b5.csv
  - outputs/v12_solweig_n150_execution/n150_reference_values_b5.csv
  - outputs/v12_solweig_n150_execution/n150_merge_validation.csv
  - outputs/v12_solweig_n150_execution/n150_merge_validation.md

Saved metrics:
  - merged focus/delta row counts and source contributions.
  - full matrix coverage, duplicate run_id, scenario/hour, retained/new-cell checks.
  - B5 reference medians, delta_tmrt_p90_c, and m_rad_pct01 rank-normalized modifier rows.

Run:
  C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\\v12_b7_n150_merge_with_n24.py
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs/v12/v12_solweig_n150_execution_config.example.json"
REPLACED_OUT = {"TP_0058", "TP_0828", "TP_0802", "TP_0675", "TP_0916"}
EXPECTED_SCENARIOS = {"base", "overhead_as_canopy"}
EXPECTED_HOURS = {10, 12, 13, 15, 16}


@dataclass
class Validation:
    check_name: str
    status: str
    expected: str
    observed: str
    detail: str = ""


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_focus(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "hour_sgt" not in out.columns and "hour" in out.columns:
        out["hour_sgt"] = out["hour"]
    out["cell_id"] = out["cell_id"].astype(str)
    out["scenario"] = out["scenario"].astype(str)
    out["hour_sgt"] = out["hour_sgt"].astype(int)
    return out


def normalize_delta(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "hour_sgt" not in out.columns and "hour" in out.columns:
        out["hour_sgt"] = out["hour"]
    out["cell_id"] = out["cell_id"].astype(str)
    out["hour_sgt"] = out["hour_sgt"].astype(int)
    return out


def normalize_matrix(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "hour_sgt" not in out.columns and "hour" in out.columns:
        out["hour_sgt"] = out["hour"]
    out["cell_id"] = out["cell_id"].astype(str)
    out["scenario"] = out["scenario"].astype(str)
    out["hour_sgt"] = out["hour_sgt"].astype(int)
    return out


def load_focus_with_full_run_ids(path: Path, source: str, full: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    focus = normalize_focus(pd.read_csv(path))
    focus["source_run_id"] = focus["run_id"].astype(str)
    full_keys = full[["run_id", "cell_id", "scenario", "hour_sgt", "selection_status", "reuse_existing_n24_label"]].copy()
    merged = focus.merge(
        full_keys,
        on=["cell_id", "scenario", "hour_sgt"],
        how="left",
        suffixes=("", "_full"),
        validate="one_to_one",
    )
    merged = merged.rename(columns={"run_id_full": "run_id_n150"}) if "run_id_full" in merged.columns else merged
    if "run_id_y" in merged.columns:
        merged = merged.rename(columns={"run_id_x": "run_id_original", "run_id_y": "run_id_n150"})
    elif "run_id_n150" not in merged.columns and "run_id" in full_keys.columns:
        # pandas keeps the left run_id and adds the matrix run_id as run_id_full under the suffix branch above.
        pass
    matrix_run = full_keys.rename(columns={"run_id": "run_id_n150"})
    if "run_id_n150" not in merged.columns:
        merged = focus.merge(matrix_run, on=["cell_id", "scenario", "hour_sgt"], how="left", validate="one_to_one")
        merged["source_run_id"] = merged["run_id"].astype(str)
    if "run_id_n150" in merged.columns:
        merged["run_id"] = merged["run_id_n150"]
    merged["source"] = source
    merged["target_version"] = cfg["target_version"]
    merged["reference_domain_version"] = cfg["reference_domain_version"]
    return merged.drop(columns=[c for c in ["run_id_n150", "run_id_original"] if c in merged.columns])


def load_delta(path: Path, source: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    delta = normalize_delta(pd.read_csv(path))
    delta["source"] = source
    return delta


def compute_b5_targets(merged_focus: pd.DataFrame, cfg: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    target_version = str(cfg.get("target_version", "systemb_target_family_v0_1_b5"))
    reference_domain_version = str(cfg.get("reference_domain_version", "n150_training_future"))
    primary_target = str(cfg.get("primary_target", "tmrt_p90_c"))
    primary_modifier_delta = str(cfg.get("primary_modifier_delta", "delta_tmrt_p90_c"))
    normalized_modifier = str(cfg.get("normalized_modifier", "m_rad_pct01"))

    ref = (
        merged_focus.groupby(["hour_sgt", "scenario"], as_index=False)
        .agg(
            tmrt_ref_p90_c=("tmrt_p90_c", "median"),
            n_reference_cells=("cell_id", "nunique"),
        )
        .sort_values(["scenario", "hour_sgt"])
    )
    ref["target_version"] = target_version
    ref["reference_domain_version"] = reference_domain_version
    ref["reference_rule"] = "same_hour_same_scenario_reference_domain_median"
    ref["primary_target"] = primary_target

    ref_metrics = ref[["hour_sgt", "scenario", "tmrt_ref_p90_c", "n_reference_cells"]].copy()
    targets = merged_focus.merge(ref_metrics, on=["hour_sgt", "scenario"], how="left", validate="many_to_one")
    targets["target_version"] = target_version
    targets["reference_domain_version"] = reference_domain_version
    targets["delta_tmrt_p90_c"] = targets["tmrt_p90_c"] - targets["tmrt_ref_p90_c"]
    targets["rank_average_delta_tmrt_p90_c"] = targets.groupby(["hour_sgt", "scenario"])["delta_tmrt_p90_c"].rank(method="average")
    denom = targets["n_reference_cells"] - 1
    targets["m_rad_pct01"] = np.where(
        denom.gt(0),
        (targets["rank_average_delta_tmrt_p90_c"] - 1) / denom,
        0.5,
    )
    targets["primary_modifier_delta"] = primary_modifier_delta
    targets["normalized_modifier"] = normalized_modifier
    targets["reference_rule"] = "same_hour_same_scenario_reference_domain_median"
    targets["rank_rule"] = "(rank_average - 1) / (n_reference_cells - 1)"
    cols_first = [
        "run_id",
        "source_run_id",
        "cell_id",
        "scenario",
        "hour_sgt",
        "source",
        "target_version",
        "reference_domain_version",
        "tmrt_p90_c",
        "tmrt_ref_p90_c",
        "delta_tmrt_p90_c",
        "rank_average_delta_tmrt_p90_c",
        "n_reference_cells",
        "m_rad_pct01",
        "primary_modifier_delta",
        "normalized_modifier",
        "reference_rule",
        "rank_rule",
    ]
    ordered_first = [c for c in cols_first if c in targets.columns]
    remaining = [c for c in targets.columns if c not in ordered_first]
    return targets[ordered_first + remaining].sort_values(["cell_id", "scenario", "hour_sgt"]), ref


def add_validation(rows: list[Validation], name: str, ok: bool, expected: Any, observed: Any, detail: str = "") -> None:
    rows.append(Validation(name, "PASS" if ok else "FAIL", str(expected), str(observed), detail))


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_None._"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in df.iterrows():
        vals = [str(row.get(col, "")).replace("\n", " ") for col in cols]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def write_validation(out_dir: Path, rows: list[Validation]) -> bool:
    df = pd.DataFrame([row.__dict__ for row in rows])
    path = out_dir / "n150_merge_validation.csv"
    df.to_csv(path, index=False)
    failed = df[df["status"].ne("PASS")].copy()
    lines = [
        "# Sprint B7 N150 Merge Validation",
        "",
        f"- checks: `{len(df)}`",
        f"- failed: `{len(failed)}`",
        "",
        "Status: **PASS**" if failed.empty else "Status: **FAILED**",
        "",
    ]
    if not failed.empty:
        lines += ["## Failed checks", "", markdown_table(failed), ""]
    lines += [
        "## All checks",
        "",
        markdown_table(df),
        "",
        "These are N150 SOLWEIG-derived Tmrt labels and B5 modifier targets only. They are not local WBGT, hazard_score, risk_score, final maps, surrogate validation, or System A/B coupling.",
    ]
    (out_dir / "n150_merge_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return failed.empty


def write_hotfix_report(
    out_dir: Path,
    ok: bool,
    merged_focus_rows: int,
    merged_delta_rows: int,
    modifier_rows: int,
    reference_rows: int,
    new_focus_rows: int,
    new_delta_rows: int,
) -> None:
    status = "PASS" if ok else "FAILED"
    lines = [
        "# Sprint B7.1 - N150 Merge Schema Hotfix",
        "",
        "## Status",
        status,
        "",
        "## Scope",
        "- repo-side merge script hotfix only",
        "- QGIS/SOLWEIG was not rerun",
        "- raw outputs were not deleted or modified",
        "- N150 selected cells and manifests were not changed",
        "- no local WBGT",
        "- no hazard_score",
        "- no risk_score",
        "- no surrogate",
        "- no System A/B coupling",
        "- no stage/commit by this script",
        "",
        "## Cause",
        "`compute_b5_targets()` merged the B5 reference table into focus rows that already carried schema fields, which could create suffixed version columns and leave no unsuffixed `target_version` / `reference_domain_version` for final column ordering.",
        "",
        "## Fix",
        "- B5 schema defaults are now explicit: `systemb_target_family_v0_1_b5` and `n150_training_future`.",
        "- `target_version` and `reference_domain_version` are written onto modifier targets after reference merge.",
        "- reference values also carry the same B5 schema columns.",
        "- output column ordering only selects columns that are present after required fields have been added.",
        "",
        "## Rerun result",
        f"- aggregation had already succeeded: new focus rows = `{new_focus_rows}`, new delta rows = `{new_delta_rows}`",
        f"- merged focus rows = `{merged_focus_rows}`",
        f"- merged delta rows = `{merged_delta_rows}`",
        f"- modifier target rows = `{modifier_rows}`",
        f"- reference rows = `{reference_rows}`",
        f"- B5 target schema columns present = `{ok}`",
        "",
        "## Claim boundaries",
        "These outputs are SOLWEIG-derived Tmrt labels and B5 modifier targets only. They are not local WBGT, hazard_score, risk_score, surrogate output, final AOI-wide maps, or System A/B coupling.",
    ]
    (out_dir / "sprint_b7_1_merge_schema_hotfix_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge completed N24 labels and B7 N126 new labels into the B5-aligned N150 target set.",
        epilog="Writes merged focus/delta CSVs, B5 reference/modifier CSVs, and validation CSV/Markdown. Does not compute local WBGT, hazard_score, risk_score, surrogate models, or System A/B coupling.",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="B7 execution config JSON.")
    args = parser.parse_args()
    cfg = read_json(repo_path(args.config))
    out_dir = repo_path(cfg["summary_output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    full = normalize_matrix(pd.read_csv(repo_path(cfg["full_matrix_path"])))
    selected = pd.read_csv(repo_path(cfg["selected_cells_path"]))
    selected["cell_id"] = selected["cell_id"].astype(str)
    retained_cells = set(selected.loc[selected["selection_status"].eq("retained_n24"), "cell_id"])
    new_cells = set(selected.loc[selected["selection_status"].eq("selected_new"), "cell_id"])

    n24_focus = load_focus_with_full_run_ids(repo_path(cfg["n24_focus_summary_path"]), "completed_n24_existing", full, cfg)
    new_focus = load_focus_with_full_run_ids(out_dir / "n150_new_focus_tmrt_summary.csv", "solweig_b7_new", full, cfg)
    merged_focus = pd.concat([n24_focus, new_focus], ignore_index=True, sort=False)
    merged_focus = merged_focus.sort_values(["cell_id", "scenario", "hour_sgt"])
    merged_focus.to_csv(out_dir / "n150_focus_tmrt_summary_merged.csv", index=False)

    n24_delta = load_delta(repo_path(cfg["n24_delta_path"]), "completed_n24_existing")
    new_delta = load_delta(out_dir / "n150_new_base_vs_overhead_delta.csv", "solweig_b7_new")
    merged_delta = pd.concat([n24_delta, new_delta], ignore_index=True, sort=False)
    merged_delta = merged_delta.sort_values(["cell_id", "hour_sgt"])
    merged_delta.to_csv(out_dir / "n150_base_vs_overhead_delta_merged.csv", index=False)

    targets, ref = compute_b5_targets(merged_focus, cfg)
    targets.to_csv(out_dir / "n150_modifier_targets_b5.csv", index=False)
    ref.to_csv(out_dir / "n150_reference_values_b5.csv", index=False)

    rows: list[Validation] = []
    full_run_ids = set(full["run_id"].astype(str))
    merged_run_ids = set(merged_focus["run_id"].astype(str))
    add_validation(rows, "merged_focus_rows", len(merged_focus) == 1500, 1500, len(merged_focus))
    add_validation(rows, "merged_unique_cells", merged_focus["cell_id"].nunique() == 150, 150, merged_focus["cell_id"].nunique())
    add_validation(rows, "n24_contribution_rows", int(merged_focus["source"].eq("completed_n24_existing").sum()) == 240, 240, int(merged_focus["source"].eq("completed_n24_existing").sum()))
    add_validation(rows, "n126_contribution_rows", int(merged_focus["source"].eq("solweig_b7_new").sum()) == 1260, 1260, int(merged_focus["source"].eq("solweig_b7_new").sum()))
    add_validation(rows, "scenarios_base_and_overhead", set(merged_focus["scenario"]) == EXPECTED_SCENARIOS, sorted(EXPECTED_SCENARIOS), sorted(set(merged_focus["scenario"])))
    add_validation(rows, "hours_10_12_13_15_16", set(merged_focus["hour_sgt"]) == EXPECTED_HOURS, sorted(EXPECTED_HOURS), sorted(set(merged_focus["hour_sgt"])))
    add_validation(rows, "no_duplicate_run_id", not merged_focus["run_id"].duplicated().any(), "none", int(merged_focus["run_id"].duplicated().sum()))
    add_validation(rows, "all_full_run_matrix_rows_represented", merged_run_ids == full_run_ids, len(full_run_ids), len(merged_run_ids), ",".join(sorted(full_run_ids - merged_run_ids)[:10]))
    add_validation(rows, "merged_delta_rows", len(merged_delta) == 750, 750, len(merged_delta))
    add_validation(rows, "replaced_out_cells_absent", set(merged_focus["cell_id"]).isdisjoint(REPLACED_OUT), "none", sorted(set(merged_focus["cell_id"]) & REPLACED_OUT))
    add_validation(rows, "retained_n24_cells_present", retained_cells.issubset(set(merged_focus["cell_id"])), len(retained_cells), len(retained_cells & set(merged_focus["cell_id"])))
    add_validation(rows, "new126_cells_present", new_cells.issubset(set(merged_focus["cell_id"])), len(new_cells), len(new_cells & set(merged_focus["cell_id"])))
    add_validation(rows, "modifier_target_rows", len(targets) == 1500, 1500, len(targets))
    add_validation(rows, "modifier_targets_include_target_version", "target_version" in targets.columns, "column present", "target_version" in targets.columns)
    add_validation(rows, "modifier_targets_include_reference_domain_version", "reference_domain_version" in targets.columns, "column present", "reference_domain_version" in targets.columns)
    target_versions = sorted(targets["target_version"].dropna().astype(str).unique()) if "target_version" in targets.columns else []
    reference_versions = sorted(targets["reference_domain_version"].dropna().astype(str).unique()) if "reference_domain_version" in targets.columns else []
    add_validation(rows, "modifier_targets_target_version_value", target_versions == ["systemb_target_family_v0_1_b5"], "systemb_target_family_v0_1_b5", target_versions)
    add_validation(rows, "modifier_targets_reference_domain_version_value", reference_versions == ["n150_training_future"], "n150_training_future", reference_versions)
    add_validation(rows, "reference_value_rows", len(ref) == 10, 10, len(ref))
    add_validation(rows, "reference_values_include_target_version", "target_version" in ref.columns, "column present", "target_version" in ref.columns)
    add_validation(rows, "reference_values_include_reference_domain_version", "reference_domain_version" in ref.columns, "column present", "reference_domain_version" in ref.columns)
    add_validation(rows, "reference_group_sizes_are_150", ref["n_reference_cells"].eq(150).all(), "all 150", sorted(ref["n_reference_cells"].unique()))

    ok = write_validation(out_dir, rows)
    write_hotfix_report(
        out_dir=out_dir,
        ok=ok,
        merged_focus_rows=len(merged_focus),
        merged_delta_rows=len(merged_delta),
        modifier_rows=len(targets),
        reference_rows=len(ref),
        new_focus_rows=len(new_focus),
        new_delta_rows=len(new_delta),
    )
    if not ok:
        raise SystemExit("FAILED: N150 merge validation failed. See outputs/v12_solweig_n150_execution/n150_merge_validation.md")
    print(f"[OK] wrote {out_dir / 'n150_focus_tmrt_summary_merged.csv'} rows={len(merged_focus)}")
    print(f"[OK] wrote {out_dir / 'n150_base_vs_overhead_delta_merged.csv'} rows={len(merged_delta)}")
    print(f"[OK] wrote {out_dir / 'n150_modifier_targets_b5.csv'} rows={len(targets)}")


if __name__ == "__main__":
    main()
