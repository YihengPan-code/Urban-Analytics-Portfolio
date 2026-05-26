"""Create B8.1 System B surrogate validation split manifests.

Inputs:
    outputs/v12_surrogate/b8_dataset_audit/surrogate_label_feature_matrix.csv
    outputs/v12_surrogate/b8_dataset_audit/feature_schema.csv
    configs/v12/systemb_surrogate_b8_config.yaml

Outputs:
    outputs/v12_surrogate/b8_validation_protocol/split_manifest_cell_grouped.csv
    outputs/v12_surrogate/b8_validation_protocol/split_manifest_spatial.csv
    outputs/v12_surrogate/b8_validation_protocol/split_manifest_feature_bin.csv
    outputs/v12_surrogate/b8_validation_protocol/split_manifest_hour_holdout.csv
    outputs/v12_surrogate/b8_validation_protocol/split_manifest_scenario_holdout.csv
    outputs/v12_surrogate/b8_validation_protocol/surrogate_validation_protocol.md

Saved metrics:
    Row/cell counts by split, cell_id leakage checks for grouped split
    families, selected spatial coordinate source, available/unavailable
    feature-bin families, and PASS/BLOCKED/FAILED status for B8.1.

This script defines validation manifests only. It does not create a random row
split as main evidence, train models, create AOI-wide maps, compute local WBGT,
or create hazard_score or risk_score outputs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b8_prepare_surrogate_dataset import DEFAULT_CONFIG, read_config, repo_path


COMMON_COLUMNS = ["split_family", "split_name", "fold_id", "role", "row_id", "cell_id", "scenario", "hour_sgt", "reason", "notes"]


@dataclass(frozen=True)
class SplitResult:
    status: str
    cell_grouped_rows: int
    spatial_rows: int
    feature_bin_rows: int
    feature_bin_valid_splits: list[str]
    feature_bin_blocked_splits: list[str]
    hour_holdout_rows: int
    scenario_holdout_rows: int
    spatial_status: str
    report_path: Path


def base_rows(
    frame: pd.DataFrame,
    split_family: str,
    split_name: str,
    fold_id: str,
    role: str,
    reason: str,
    notes: str,
) -> pd.DataFrame:
    """Return a manifest frame with the common split schema."""
    out = frame[["row_id", "cell_id", "scenario", "hour_sgt"]].copy()
    out.insert(0, "role", role)
    out.insert(0, "fold_id", fold_id)
    out.insert(0, "split_name", split_name)
    out.insert(0, "split_family", split_family)
    out["reason"] = reason
    out["notes"] = notes
    return out[COMMON_COLUMNS]


def make_train_test_rows(
    frame: pd.DataFrame,
    test_mask: pd.Series,
    split_family: str,
    split_name: str,
    fold_id: str,
    reason: str,
    notes: str,
) -> pd.DataFrame:
    """Create train/test manifest rows for one fold."""
    train = base_rows(frame.loc[~test_mask], split_family, split_name, fold_id, "train", reason, notes)
    test = base_rows(frame.loc[test_mask], split_family, split_name, fold_id, "test", reason, notes)
    return pd.concat([train, test], ignore_index=True)


def make_cell_grouped(frame: pd.DataFrame, random_seed: int) -> pd.DataFrame:
    """Create deterministic five-fold cell-grouped holdouts."""
    cells = np.array(sorted(frame["cell_id"].astype(str).unique()))
    rng = np.random.default_rng(random_seed)
    rng.shuffle(cells)
    n_folds = 5 if len(cells) >= 5 else max(2, len(cells))
    chunks = np.array_split(cells, n_folds)
    rows: list[pd.DataFrame] = []
    for idx, test_cells in enumerate(chunks, start=1):
        test_set = set(test_cells.tolist())
        mask = frame["cell_id"].astype(str).isin(test_set)
        rows.append(
            make_train_test_rows(
                frame,
                mask,
                "cell_grouped_holdout",
                "cell_grouped_5fold",
                str(idx),
                "Same cell_id is held out across all hours and scenarios.",
                "Group-safe by cell_id; deterministic random_state=42.",
            )
        )
    return pd.concat(rows, ignore_index=True)


def detect_coordinate_pair(frame: pd.DataFrame, config: dict[str, Any]) -> tuple[str, str] | None:
    """Find a usable coordinate pair for spatial holdouts."""
    for x_col, y_col in config["spatial_coordinate_candidates"]:
        if x_col in frame.columns and y_col in frame.columns:
            x = pd.to_numeric(frame[x_col], errors="coerce")
            y = pd.to_numeric(frame[y_col], errors="coerce")
            if x.notna().sum() and y.notna().sum() and x.nunique(dropna=True) > 1 and y.nunique(dropna=True) > 1:
                return x_col, y_col
    return None


def make_spatial(frame: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, str, str]:
    """Create spatial block holdouts from detected coordinates."""
    pair = detect_coordinate_pair(frame, config)
    if pair is None:
        return pd.DataFrame(columns=COMMON_COLUMNS), "BLOCKED", "No usable coordinate pair was available."
    x_col, y_col = pair
    cell_frame = frame.drop_duplicates("cell_id")[["cell_id", x_col, y_col]].copy()
    cell_frame[x_col] = pd.to_numeric(cell_frame[x_col], errors="coerce")
    cell_frame[y_col] = pd.to_numeric(cell_frame[y_col], errors="coerce")
    cell_frame = cell_frame.dropna(subset=[x_col, y_col])
    x_mid = float(cell_frame[x_col].median())
    y_mid = float(cell_frame[y_col].median())
    cell_frame["block"] = np.where(cell_frame[x_col] <= x_mid, "west", "east") + "_" + np.where(cell_frame[y_col] <= y_mid, "south", "north")
    blocks = sorted(cell_frame["block"].unique())
    rows: list[pd.DataFrame] = []
    for idx, block in enumerate(blocks, start=1):
        test_cells = set(cell_frame.loc[cell_frame["block"] == block, "cell_id"].astype(str))
        mask = frame["cell_id"].astype(str).isin(test_cells)
        rows.append(
            make_train_test_rows(
                frame,
                mask,
                "spatial_holdout",
                f"spatial_block_{block}",
                str(idx),
                f"Hold out spatial block `{block}` using `{x_col}` / `{y_col}` median bins.",
                "Group-safe by cell_id; cells do not cross train/test within fold.",
            )
        )
    return pd.concat(rows, ignore_index=True), "PASS", f"Used `{x_col}` / `{y_col}` median-bin spatial blocks."


def selected_feature_columns(schema: pd.DataFrame) -> list[str]:
    """Return schema-selected non-leaky feature columns."""
    return schema.loc[schema["role"] == "feature", "column_name"].astype(str).tolist()


def pick_family_column(frame: pd.DataFrame, selected: set[str], candidates: list[str]) -> str | None:
    """Pick the first usable numeric selected feature for a family."""
    for column in candidates:
        if column in selected and column in frame.columns:
            values = pd.to_numeric(frame[column], errors="coerce")
            if values.notna().sum() >= 20 and values.nunique(dropna=True) > 1:
                return column
    return None


def blocked_feature_row(
    split_name: str,
    fold_id: str,
    reason: str,
    notes: str,
    train_cells: int,
    test_cells: int,
) -> pd.DataFrame:
    """Create one machine-readable blocked/degenerate feature-bin row."""
    return pd.DataFrame(
        [
            {
                "split_family": "feature_bin_holdout",
                "split_name": split_name,
                "fold_id": fold_id,
                "role": "blocked",
                "row_id": "",
                "cell_id": "",
                "scenario": "",
                "hour_sgt": "",
                "reason": reason,
                "notes": notes,
                "split_status": "BLOCKED_DEGENERATE",
                "train_cell_count": train_cells,
                "test_cell_count": test_cells,
            }
        ]
    )


def annotate_feature_rows(manifest: pd.DataFrame, train_cells: int, test_cells: int) -> pd.DataFrame:
    """Attach feature-bin validity metadata to train/test rows."""
    out = manifest.copy()
    out["split_status"] = "VALID"
    out["train_cell_count"] = train_cells
    out["test_cell_count"] = test_cells
    return out


def make_feature_bin(
    frame: pd.DataFrame,
    schema: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, str], list[str], list[str], list[str]]:
    """Create low/high feature-bin holdouts for available feature families."""
    selected = set(selected_feature_columns(schema))
    rows: list[pd.DataFrame] = []
    available: dict[str, str] = {}
    unavailable: list[str] = []
    valid_splits: list[str] = []
    blocked_splits: list[str] = []
    fold_index = 1
    min_train_cells = int(config.get("min_feature_bin_train_cells", 30))
    min_test_cells = int(config.get("min_feature_bin_test_cells", 30))
    cell_frame = frame.drop_duplicates("cell_id").copy()
    for family, candidates in config["feature_bin_families"].items():
        column = pick_family_column(cell_frame, selected, candidates)
        if column is None:
            unavailable.append(family)
            continue
        available[family] = column
        values = pd.to_numeric(cell_frame[column], errors="coerce")
        low_cut = float(values.quantile(0.2))
        high_cut = float(values.quantile(0.8))
        bins = {
            "low": set(cell_frame.loc[values <= low_cut, "cell_id"].astype(str)),
            "high": set(cell_frame.loc[values >= high_cut, "cell_id"].astype(str)),
        }
        for bin_name, test_cells in bins.items():
            split_name = f"{family}_{bin_name}_bin"
            mask = frame["cell_id"].astype(str).isin(test_cells)
            train_cell_count = int(frame.loc[~mask, "cell_id"].nunique())
            test_cell_count = len(test_cells)
            reason = f"Hold out {bin_name} 20% bin for `{column}` ({family})."
            if train_cell_count < min_train_cells or test_cell_count < min_test_cells:
                blocked_splits.append(split_name)
                rows.append(
                    blocked_feature_row(
                        split_name,
                        str(fold_index),
                        reason,
                        f"BLOCKED/DEGENERATE: train cells={train_cell_count}, test cells={test_cell_count}; required min_train_cells={min_train_cells}, min_test_cells={min_test_cells}.",
                        train_cell_count,
                        test_cell_count,
                    )
                )
            else:
                valid_splits.append(split_name)
                rows.append(
                    annotate_feature_rows(
                        make_train_test_rows(
                            frame,
                            mask,
                            "feature_bin_holdout",
                            split_name,
                            str(fold_index),
                            reason,
                            "Group-safe by cell_id; valid feature-bin transfer diagnostic.",
                        ),
                        train_cell_count,
                        test_cell_count,
                    )
                )
            fold_index += 1
    manifest = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=[*COMMON_COLUMNS, "split_status", "train_cell_count", "test_cell_count"])
    return manifest, available, unavailable, valid_splits, blocked_splits


def make_hour_holdout(frame: pd.DataFrame) -> pd.DataFrame:
    """Create leave-one-hour-out transfer diagnostics."""
    rows: list[pd.DataFrame] = []
    for idx, hour in enumerate(sorted(pd.to_numeric(frame["hour_sgt"], errors="coerce").dropna().astype(int).unique()), start=1):
        mask = pd.to_numeric(frame["hour_sgt"], errors="coerce") == hour
        rows.append(
            make_train_test_rows(
                frame,
                mask,
                "hour_holdout",
                f"leave_hour_{hour}_out",
                str(idx),
                f"Leave hour_sgt {hour} out.",
                "Transfer diagnostic; same cells may appear in train/test across different hours by design.",
            )
        )
    return pd.concat(rows, ignore_index=True)


def make_scenario_holdout(frame: pd.DataFrame) -> pd.DataFrame:
    """Create base-to-overhead and overhead-to-base scenario transfer diagnostics."""
    scenarios = ["base", "overhead_as_canopy"]
    rows: list[pd.DataFrame] = []
    for idx, test_scenario in enumerate(scenarios, start=1):
        train_scenario = [scenario for scenario in scenarios if scenario != test_scenario][0]
        mask = frame["scenario"].astype(str) == test_scenario
        rows.append(
            make_train_test_rows(
                frame,
                mask,
                "scenario_holdout",
                f"train_{train_scenario}_test_{test_scenario}",
                str(idx),
                f"Train on `{train_scenario}` and test on `{test_scenario}`.",
                "Transfer diagnostic; same cells may appear in train/test across scenarios by design.",
            )
        )
    return pd.concat(rows, ignore_index=True)


def no_cell_leakage(manifest: pd.DataFrame) -> bool:
    """Check that no fold has a cell_id in both train and test."""
    if "role" in manifest.columns:
        manifest = manifest.loc[manifest["role"].isin(["train", "test"])].copy()
    for (_, fold_id), part in manifest.groupby(["split_family", "fold_id"]):
        train = set(part.loc[part["role"] == "train", "cell_id"].astype(str))
        test = set(part.loc[part["role"] == "test", "cell_id"].astype(str))
        if train & test:
            return False
    return True


def split_counts(manifest: pd.DataFrame) -> pd.DataFrame:
    """Compute row and cell counts by split and role."""
    if manifest.empty:
        return pd.DataFrame(columns=["split_family", "split_name", "fold_id", "role", "row_count", "cell_count"])
    valid_row_manifest = manifest.loc[manifest["role"].isin(["train", "test"])].copy() if "role" in manifest.columns else manifest
    if valid_row_manifest.empty:
        return pd.DataFrame(columns=["split_family", "split_name", "fold_id", "role", "row_count", "cell_count"])
    return (
        valid_row_manifest.groupby(["split_family", "split_name", "fold_id", "role"], dropna=False)
        .agg(row_count=("row_id", "count"), cell_count=("cell_id", "nunique"))
        .reset_index()
    )


def counts_markdown(title: str, manifest: pd.DataFrame) -> list[str]:
    """Format split counts for the protocol document."""
    counts = split_counts(manifest)
    lines = [f"## {title}", ""]
    if counts.empty:
        return [*lines, "- No manifest rows were created.", ""]
    lines.append("| split_name | fold_id | role | row_count | cell_count |")
    lines.append("|---|---:|---|---:|---:|")
    for row in counts.itertuples(index=False):
        lines.append(f"| {row.split_name} | {row.fold_id} | {row.role} | {row.row_count} | {row.cell_count} |")
    lines.append("")
    return lines


def write_protocol(
    path: Path,
    status: str,
    cell_manifest: pd.DataFrame,
    spatial_manifest: pd.DataFrame,
    feature_manifest: pd.DataFrame,
    hour_manifest: pd.DataFrame,
    scenario_manifest: pd.DataFrame,
    spatial_status: str,
    spatial_note: str,
    available_families: dict[str, str],
    unavailable_families: list[str],
    valid_feature_splits: list[str],
    blocked_feature_splits: list[str],
) -> None:
    """Write the B8.1 validation protocol Markdown."""
    cell_clean = no_cell_leakage(cell_manifest)
    spatial_clean = spatial_manifest.empty or no_cell_leakage(spatial_manifest)
    feature_clean = feature_manifest.empty or no_cell_leakage(feature_manifest)
    lines = [
        "# B8.1 Surrogate Validation Split Protocol",
        "",
        f"Status: **{status}**",
        "",
        "## Why Random Row Split Is Not Main Evidence",
        "",
        "The row unit is `cell_id x hour_sgt x scenario`. A random row split would leak static cell-level features because the same cell could appear in both train and test rows. B8.1 therefore prioritizes cell-grouped, spatial, and feature-bin holdouts for cell generalization, with hour and scenario holdouts kept as transfer diagnostics.",
        "",
        "## Split Family Definitions",
        "",
        "- `cell_grouped_holdout`: deterministic five-fold cell holdout; group-safe by `cell_id`.",
        f"- `spatial_holdout`: {spatial_note}",
        "- `feature_bin_holdout`: low/high bins of available non-leaky feature families; group-safe by `cell_id`.",
        "- `hour_holdout`: leave one `hour_sgt` out; tests hour transfer and may reuse cells across train/test by design.",
        "- `scenario_holdout`: train one scenario and test the other; tests scenario transfer and may reuse cells across train/test by design.",
        "",
        "## Leakage Checks For Grouped Splits",
        "",
        f"- cell_grouped_holdout cell leakage: {'PASS' if cell_clean else 'FAIL'}",
        f"- spatial_holdout cell leakage: {'PASS' if spatial_clean else 'FAIL'}",
        f"- feature_bin_holdout cell leakage: {'PASS' if feature_clean else 'FAIL'}",
        "",
        "## Group-Safe And Transfer Diagnostics",
        "",
        "- Group-safe by cell_id: `cell_grouped_holdout`, valid `spatial_holdout`, `feature_bin_holdout`.",
        "- Transfer diagnostics: `hour_holdout`, `scenario_holdout`.",
        "",
        "## Feature-Bin Families",
        "",
        f"- Available families: {', '.join(f'{k} -> `{v}`' for k, v in available_families.items()) if available_families else '(none)'}",
        f"- Unavailable families: {', '.join(unavailable_families) if unavailable_families else '(none)'}",
        f"- Valid feature-bin splits: {', '.join(valid_feature_splits) if valid_feature_splits else '(none)'}",
        f"- Blocked/degenerate feature-bin splits: {', '.join(blocked_feature_splits) if blocked_feature_splits else '(none)'}",
        "- A feature-bin split is valid only when both train and test have at least 30 unique cells.",
        "",
        f"## Spatial Split Status",
        "",
        f"- Spatial status: {spatial_status}",
        f"- Spatial note: {spatial_note}",
        "",
    ]
    lines.extend(counts_markdown("Cell-Grouped Counts", cell_manifest))
    lines.extend(counts_markdown("Spatial Counts", spatial_manifest))
    lines.extend(counts_markdown("Feature-Bin Counts", feature_manifest))
    lines.extend(counts_markdown("Hour-Holdout Counts", hour_manifest))
    lines.extend(counts_markdown("Scenario-Holdout Counts", scenario_manifest))
    lines.extend(
        [
            "## How B8.2 Should Consume These Manifests",
            "",
            "- Join each manifest to `surrogate_label_feature_matrix.csv` by `row_id`.",
            "- Use only `feature_schema.csv` rows with `role == feature` and `predictor_tier == physical_core` as headline candidate predictors.",
            "- Do not consume feature-bin rows where `split_status == BLOCKED_DEGENERATE` as validation folds.",
            "- Treat `delta_tmrt_p90_c` as the primary physical target and `tmrt_p90_c` as the secondary target.",
            "- Retain `m_rad_pct01` as a reference-domain modifier/label for post-prediction interpretation, not as the only regression target.",
            "- Do not use random row split as headline evidence.",
            "",
            "## Caveats",
            "",
            "- No models are trained in B8.1.",
            "- No Tmrt value is converted to WBGT.",
            "- No AOI-wide final output is created.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path = DEFAULT_CONFIG) -> SplitResult:
    """Run B8.1 split generation and write all configured outputs."""
    config = read_config(config_path)
    audit_dir = repo_path(config["outputs"]["audit_dir"])
    validation_dir = repo_path(config["outputs"]["validation_dir"])
    validation_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = audit_dir / "surrogate_label_feature_matrix.csv"
    schema_path = audit_dir / "feature_schema.csv"
    if not matrix_path.exists() or not schema_path.exists():
        for name in [
            "split_manifest_cell_grouped.csv",
            "split_manifest_spatial.csv",
            "split_manifest_feature_bin.csv",
            "split_manifest_hour_holdout.csv",
            "split_manifest_scenario_holdout.csv",
        ]:
            pd.DataFrame(columns=COMMON_COLUMNS).to_csv(validation_dir / name, index=False)
        report_path = validation_dir / "surrogate_validation_protocol.md"
        report_path.write_text("# B8.1 Surrogate Validation Split Protocol\n\nStatus: **BLOCKED**\n\nB8.0 matrix/schema outputs are missing.\n", encoding="utf-8")
        return SplitResult("BLOCKED", 0, 0, 0, [], [], 0, 0, "BLOCKED", report_path)

    frame = pd.read_csv(matrix_path, dtype={"cell_id": "string", "row_id": "string"})
    schema = pd.read_csv(schema_path)
    cell_manifest = make_cell_grouped(frame, int(config["random_seed"]))
    spatial_manifest, spatial_status, spatial_note = make_spatial(frame, config)
    feature_manifest, available_families, unavailable_families, valid_feature_splits, blocked_feature_splits = make_feature_bin(frame, schema, config)
    hour_manifest = make_hour_holdout(frame)
    scenario_manifest = make_scenario_holdout(frame)

    cell_manifest.to_csv(validation_dir / "split_manifest_cell_grouped.csv", index=False)
    spatial_manifest.to_csv(validation_dir / "split_manifest_spatial.csv", index=False)
    feature_manifest.to_csv(validation_dir / "split_manifest_feature_bin.csv", index=False)
    hour_manifest.to_csv(validation_dir / "split_manifest_hour_holdout.csv", index=False)
    scenario_manifest.to_csv(validation_dir / "split_manifest_scenario_holdout.csv", index=False)

    checks = {
        "cell_grouped_created": not cell_manifest.empty,
        "cell_grouped_no_cell_leakage": no_cell_leakage(cell_manifest),
        "spatial_valid_or_blocked": spatial_status in {"PASS", "BLOCKED"},
        "feature_bin_created": not feature_manifest.empty,
        "feature_bin_has_valid_splits": bool(valid_feature_splits),
        "hour_holdout_created": not hour_manifest.empty,
        "scenario_holdout_created": not scenario_manifest.empty,
    }
    status = "PASS" if all(checks.values()) else "FAILED"
    report_path = validation_dir / "surrogate_validation_protocol.md"
    write_protocol(
        report_path,
        status,
        cell_manifest,
        spatial_manifest,
        feature_manifest,
        hour_manifest,
        scenario_manifest,
        spatial_status,
        spatial_note,
        available_families,
        unavailable_families,
        valid_feature_splits,
        blocked_feature_splits,
    )
    return SplitResult(
        status=status,
        cell_grouped_rows=len(cell_manifest),
        spatial_rows=len(spatial_manifest),
        feature_bin_rows=len(feature_manifest),
        feature_bin_valid_splits=valid_feature_splits,
        feature_bin_blocked_splits=blocked_feature_splits,
        hour_holdout_rows=len(hour_manifest),
        scenario_holdout_rows=len(scenario_manifest),
        spatial_status=spatial_status,
        report_path=report_path,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Create B8.1 surrogate validation split manifests.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to the explicit B8 YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps({**result.__dict__, "report_path": str(result.report_path)}, indent=2, default=str))


if __name__ == "__main__":
    main()
