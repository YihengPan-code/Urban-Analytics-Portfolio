#!/usr/bin/env python
"""System A A-L2.1b station buffer feature QA and residual-readiness screen.

Inputs:
    - configs/v11/systema_l2_station_feature_qa.yaml
    - outputs/v11_systema_l2_residual/station_buffer_features_s1/
      station_buffer_feature_wide_s1.csv
    - outputs/v11_systema_l2_residual/station_buffer_features_s1/
      station_buffer_feature_schema_s1.csv
    - outputs/v11_systema_l2_residual/station_buffer_features_s1/
      station_buffer_feature_qa_s1.csv
    - outputs/v11_systema_l2_residual/identifiability_preflight/
      station_level_residual_summary.csv
    - outputs/v11_systema_l2_residual/identifiability_preflight/
      station_level_probability_error_summary.csv
    - outputs/v11_systema_l2_residual/identifiability_preflight/
      station_residual_stability_bootstrap.csv

Outputs:
    - station_feature_qa_summary.csv
    - station_feature_distribution_summary.csv
    - station_feature_collinearity_pairs.csv
    - station_feature_correlation_clusters.csv
    - station_feature_buffer_redundancy.csv
    - station_residual_association_screen.csv
    - station_context_profiles_key_stations.csv
    - station_feature_candidate_set.csv
    - station_feature_manual_review_table.csv
    - station_feature_qa_report.md
    - A_L2_1B_STATUS.md
    - docs/v11/OpenHeat_SystemA_L2_station_feature_QA_CN.md

Saved metrics:
    - Feature missingness, quantiles, zero fraction, constant/near-constant
      flags, and robust-z outlier station lists.
    - Pairwise Spearman collinearity among numeric station buffer features,
      high-collinearity/near-duplicate flags, and correlation clusters.
    - Same-base-feature buffer-scale redundancy across 50/100/250/500 m.
    - Descriptive feature association screens against station-level residual
      targets, plus clearly secondary probability-error targets when present.
    - Key station context profiles and a small future A-L2.1c candidate set.

Scope guard:
    This is a QA/screening gate only. It does not stage, commit, train residual
    ML models, start A-L2.1c modelling, create station-adjusted WBGT, create
    local 100 m WBGT, touch System B or SOLWEIG outputs, modify archive
    collectors, use station_id as a predictive feature, or claim
    station-context causal correction.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

try:  # Optional only; the lane remains valid when scipy is unavailable.
    from scipy.stats import spearmanr as scipy_spearmanr

    SCIPY_AVAILABLE = True
except Exception:  # pragma: no cover - depends on local runtime.
    scipy_spearmanr = None
    SCIPY_AVAILABLE = False


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_OUTPUT_PREFIX = "outputs/v11_systema_l2_residual/station_feature_qa"
CN_DOC_NAME = "docs/v11/OpenHeat_SystemA_L2_station_feature_QA_CN.md"
PRIMARY_TARGETS = {
    "mean_context_adjusted_score_residual_c",
    "mean_context_adjusted_high_tail_residual_c",
}


@dataclass(frozen=True)
class FeatureQaResult:
    """Headline result returned to the runner."""

    decision_status: str
    primary_candidate_count: int
    top_residual_features: str
    excluded_high_collinearity_groups: str
    key_station_caveats: str
    a_l2_1c_recommendation: str
    files_created: list[Path]
    git_status_short: str


def rel(path: Path) -> str:
    """Return a project-relative path when possible."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(raw_path: str) -> Path:
    """Resolve an absolute or project-relative path."""
    path = Path(raw_path)
    return path if path.is_absolute() else ROOT / path


def load_config(path: Path) -> dict[str, Any]:
    """Load the explicit JSON-formatted YAML config."""
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Config is not a mapping: {rel(path)}")
    return loaded


def output_paths(config: dict[str, Any]) -> dict[str, Path]:
    """Resolve all configured output paths and enforce lane write scope."""
    output_dir = resolve_path(str(config["outputs"]["output_dir"]))
    cn_doc = resolve_path(str(config["outputs"]["cn_doc"]))
    if not rel(output_dir).startswith(EXPECTED_OUTPUT_PREFIX):
        raise ValueError(f"Refusing to write outside {EXPECTED_OUTPUT_PREFIX}: {rel(output_dir)}")
    if rel(cn_doc) != CN_DOC_NAME:
        raise ValueError(f"Refusing to write unexpected CN doc path: {rel(cn_doc)}")
    return {
        "dir": output_dir,
        "qa_summary": output_dir / str(config["outputs"]["qa_summary"]),
        "distribution_summary": output_dir / str(config["outputs"]["distribution_summary"]),
        "collinearity_pairs": output_dir / str(config["outputs"]["collinearity_pairs"]),
        "correlation_clusters": output_dir / str(config["outputs"]["correlation_clusters"]),
        "buffer_redundancy": output_dir / str(config["outputs"]["buffer_redundancy"]),
        "residual_association_screen": output_dir / str(config["outputs"]["residual_association_screen"]),
        "key_station_profiles": output_dir / str(config["outputs"]["key_station_profiles"]),
        "candidate_set": output_dir / str(config["outputs"]["candidate_set"]),
        "manual_review_table": output_dir / str(config["outputs"]["manual_review_table"]),
        "qa_report": output_dir / str(config["outputs"]["qa_report"]),
        "status": output_dir / str(config["outputs"]["status"]),
        "cn_doc": cn_doc,
    }


def input_paths(config: dict[str, Any]) -> dict[str, Path]:
    """Resolve configured input paths."""
    return {key: resolve_path(str(value)) for key, value in config["inputs"].items()}


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


def git_status_short() -> str:
    """Return git status for the current project subdirectory."""
    result = subprocess.run(
        ["git", "status", "--short", "--", "."],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.rstrip()


def semicolon(values: Iterable[Any]) -> str:
    """Join unique non-empty values in first-seen order."""
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() != "nan" and text not in seen:
            seen.add(text)
            out.append(text)
    return ";".join(out)


def fmt(value: object, digits: int = 6) -> str:
    """Format numeric values for compact CSV/Markdown output."""
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        text = str(value)
        return "" if text.lower() == "nan" else text
    if not math.isfinite(number):
        return ""
    if abs(number) < 0.5 * 10 ** (-digits):
        number = 0.0
    return f"{number:.{digits}f}"


def yes_no(value: bool) -> str:
    """Return stable yes/no text."""
    return "yes" if value else "no"


def bool_value(value: object) -> bool:
    """Parse bool-like CSV/config values."""
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y"}


def markdown_table(df: pd.DataFrame, columns: list[str], limit: int = 12) -> str:
    """Render a compact Markdown table."""
    if df.empty:
        return "_No rows._"
    shown = df.loc[:, [col for col in columns if col in df.columns]].head(limit).copy()
    header_cols = shown.columns.tolist()
    header = "| " + " | ".join(header_cols) + " |"
    divider = "| " + " | ".join("---" for _ in header_cols) + " |"
    rows = []
    for _, row in shown.iterrows():
        values = [str(row[col]).replace("\n", " ").replace("|", "\\|") for col in header_cols]
        rows.append("| " + " | ".join(values) + " |")
    suffix = f"\n\n_Showing {len(shown)} of {len(df)} rows._" if len(df) > len(shown) else ""
    return "\n".join([header, divider, *rows]) + suffix


def read_csv(path: Path) -> pd.DataFrame:
    """Read a UTF-8 CSV with stable low-memory behavior."""
    return pd.read_csv(path, low_memory=False)


def write_csv(path: Path, df: pd.DataFrame) -> None:
    """Write a UTF-8 CSV and create parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def parse_feature_meta(schema: pd.DataFrame, wide: pd.DataFrame) -> pd.DataFrame:
    """Build feature metadata from the S1 schema."""
    rows: list[dict[str, Any]] = []
    for _, raw in schema.iterrows():
        column = str(raw["feature_column"])
        if column not in wide.columns:
            continue
        series = pd.to_numeric(wide[column], errors="coerce")
        non_null = int(wide[column].notna().sum())
        numeric_non_null = int(series.notna().sum())
        feature_type = "numeric" if numeric_non_null > 0 else "categorical"
        rows.append(
            {
                "feature_column": column,
                "feature_name": str(raw.get("feature_name", "")),
                "base_feature": str(raw.get("feature_name", "")),
                "buffer_m": int(raw["buffer_m"]) if pd.notna(raw.get("buffer_m")) else "",
                "feature_group": str(raw.get("feature_group", "")),
                "feature_unit": str(raw.get("feature_unit", "")),
                "source_name": str(raw.get("source_name", "")),
                "extraction_method": str(raw.get("extraction_method", "")),
                "schema_n_stations_non_null": int(raw.get("n_stations_non_null", non_null)),
                "schema_missing_fraction": float(raw.get("missing_fraction", np.nan)),
                "schema_allowed_for_future_model": bool_value(raw.get("allowed_for_future_model", False)),
                "schema_leakage_check": str(raw.get("leakage_check", "")),
                "schema_coverage_status": str(raw.get("coverage_status", "")),
                "feature_type": feature_type,
            }
        )
    meta = pd.DataFrame(rows)
    return meta.sort_values(["feature_group", "base_feature", "buffer_m", "feature_column"]).reset_index(drop=True)


def has_forbidden_token(feature: str, forbidden_tokens: list[str]) -> bool:
    """Return True when a feature name contains a forbidden predictive token."""
    lowered = feature.lower()
    return any(token.lower() in lowered for token in forbidden_tokens)


def robust_outlier_text(values: pd.Series, station_ids: pd.Series, threshold: float) -> str:
    """Return station ids with robust-z outliers."""
    clean = pd.DataFrame({"station_id": station_ids, "value": values}).dropna()
    if clean.empty:
        return ""
    median = float(clean["value"].median())
    mad = float((clean["value"] - median).abs().median())
    if mad > 0:
        z = 0.6745 * (clean["value"] - median) / mad
    else:
        q25 = float(clean["value"].quantile(0.25))
        q75 = float(clean["value"].quantile(0.75))
        iqr = q75 - q25
        if iqr <= 0:
            return ""
        z = (clean["value"] - median) / iqr
    clean = clean.assign(robust_z=z)
    outliers = clean[clean["robust_z"].abs() >= threshold].copy()
    if outliers.empty:
        return ""
    outliers["abs_z"] = outliers["robust_z"].abs()
    outliers = outliers.sort_values("abs_z", ascending=False)
    return semicolon(
        f"{row.station_id}:{fmt(row.value, 3)}(z={fmt(row.robust_z, 2)})" for row in outliers.itertuples()
    )


def build_distribution_summary(
    wide: pd.DataFrame,
    meta: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Create per-feature distribution and missingness QA rows."""
    thresholds = config["thresholds"]
    rows: list[dict[str, Any]] = []
    station_ids = wide["station_id"]
    for feature in meta.itertuples(index=False):
        column = str(feature.feature_column)
        raw = wide[column]
        values = pd.to_numeric(raw, errors="coerce")
        is_numeric = feature.feature_type == "numeric"
        observed = values if is_numeric else raw.dropna()
        n_non_null = int(raw.notna().sum())
        missing_fraction = 1.0 - (n_non_null / max(len(raw), 1))
        n_unique = int(raw.dropna().nunique())
        top_fraction = float(raw.dropna().value_counts(normalize=True).iloc[0]) if n_non_null else np.nan
        constant = n_unique <= 1
        near_constant = bool(
            constant
            or n_unique <= int(thresholds["near_constant_unique_count"])
            or (math.isfinite(top_fraction) and top_fraction >= float(thresholds["near_constant_top_fraction"]))
        )
        row: dict[str, Any] = {
            "feature_column": column,
            "feature_group": feature.feature_group,
            "base_feature": feature.base_feature,
            "buffer_m": feature.buffer_m,
            "feature_type": feature.feature_type,
            "n_non_null": n_non_null,
            "missing_fraction": fmt(missing_fraction),
            "n_unique_non_null": n_unique,
            "top_value_fraction": fmt(top_fraction),
            "constant_flag": yes_no(constant),
            "near_constant_flag": yes_no(near_constant),
            "outlier_stations_robust_z": "",
            "zero_fraction": "",
            "min": "",
            "p05": "",
            "p25": "",
            "median": "",
            "p75": "",
            "p95": "",
            "max": "",
        }
        if is_numeric:
            clean = values.dropna()
            zero_fraction = float((clean == 0).mean()) if len(clean) else np.nan
            quantiles = clean.quantile([0.05, 0.25, 0.50, 0.75, 0.95]) if len(clean) else pd.Series(dtype=float)
            iqr = float(quantiles.get(0.75, np.nan) - quantiles.get(0.25, np.nan)) if len(clean) else np.nan
            if math.isfinite(iqr) and iqr == 0:
                near_constant = True
                row["near_constant_flag"] = "yes"
            row.update(
                {
                    "zero_fraction": fmt(zero_fraction),
                    "min": fmt(clean.min() if len(clean) else np.nan),
                    "p05": fmt(quantiles.get(0.05, np.nan)),
                    "p25": fmt(quantiles.get(0.25, np.nan)),
                    "median": fmt(quantiles.get(0.50, np.nan)),
                    "p75": fmt(quantiles.get(0.75, np.nan)),
                    "p95": fmt(quantiles.get(0.95, np.nan)),
                    "max": fmt(clean.max() if len(clean) else np.nan),
                    "outlier_stations_robust_z": robust_outlier_text(
                        values, station_ids, float(thresholds["robust_z_outlier_abs"])
                    ),
                }
            )
        else:
            row["category_values"] = semicolon(observed.astype(str).head(8).tolist()) if n_non_null else ""
        rows.append(row)
    return pd.DataFrame(rows)


def spearman_rank(x: pd.Series, y: pd.Series) -> tuple[float, int]:
    """Compute pairwise Spearman rank correlation without requiring scipy."""
    pair = pd.DataFrame({"x": pd.to_numeric(x, errors="coerce"), "y": pd.to_numeric(y, errors="coerce")}).dropna()
    n_pairwise = int(len(pair))
    if n_pairwise < 3 or pair["x"].nunique() < 2 or pair["y"].nunique() < 2:
        return np.nan, n_pairwise
    rank_x = pair["x"].rank(method="average")
    rank_y = pair["y"].rank(method="average")
    return float(rank_x.corr(rank_y)), n_pairwise


def spearman_p_value(x: pd.Series, y: pd.Series) -> tuple[str, str]:
    """Return a scipy Spearman p-value when scipy is installed."""
    if not SCIPY_AVAILABLE or scipy_spearmanr is None:
        return "", "scipy_unavailable"
    pair = pd.DataFrame({"x": pd.to_numeric(x, errors="coerce"), "y": pd.to_numeric(y, errors="coerce")}).dropna()
    if len(pair) < 3 or pair["x"].nunique() < 2 or pair["y"].nunique() < 2:
        return "", "insufficient_pairwise_variation"
    result = scipy_spearmanr(pair["x"], pair["y"])
    return fmt(float(result.pvalue)), "available"


def collinearity_status(abs_r: float, high_threshold: float, near_threshold: float) -> str:
    """Classify absolute Spearman correlation."""
    if not math.isfinite(abs_r):
        return "unavailable"
    if abs_r >= near_threshold:
        return "near_duplicate"
    if abs_r >= high_threshold:
        return "high_collinearity"
    if abs_r >= 0.60:
        return "moderate_collinearity"
    return "low_collinearity"


def build_collinearity_pairs(
    wide: pd.DataFrame,
    meta: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Compute all pairwise Spearman correlations among numeric features."""
    high = float(config["thresholds"]["high_collinearity_abs_spearman"])
    near = float(config["thresholds"]["near_duplicate_abs_spearman"])
    numeric_meta = meta[meta["feature_type"] == "numeric"].copy()
    lookup = numeric_meta.set_index("feature_column").to_dict("index")
    rows: list[dict[str, Any]] = []
    columns = numeric_meta["feature_column"].tolist()
    for i, feature_a in enumerate(columns):
        for feature_b in columns[i + 1 :]:
            r, n_pairwise = spearman_rank(wide[feature_a], wide[feature_b])
            abs_r = abs(r) if math.isfinite(r) else np.nan
            meta_a = lookup[feature_a]
            meta_b = lookup[feature_b]
            rows.append(
                {
                    "feature_a": feature_a,
                    "feature_b": feature_b,
                    "feature_a_group": meta_a["feature_group"],
                    "feature_b_group": meta_b["feature_group"],
                    "feature_a_base": meta_a["base_feature"],
                    "feature_b_base": meta_b["base_feature"],
                    "feature_a_buffer_m": meta_a["buffer_m"],
                    "feature_b_buffer_m": meta_b["buffer_m"],
                    "spearman_r": fmt(r),
                    "abs_spearman_r": fmt(abs_r),
                    "n_pairwise": n_pairwise,
                    "collinearity_status": collinearity_status(abs_r, high, near),
                }
            )
    pairs = pd.DataFrame(rows)
    if pairs.empty:
        return pairs
    return pairs.sort_values(["abs_spearman_r", "feature_a", "feature_b"], ascending=[False, True, True])


def preference_rank(feature: str, config: dict[str, Any]) -> tuple[int, int, str]:
    """Rank features for cluster representation and candidate preferences."""
    primary = list(config.get("primary_candidate_preferences", []))
    secondary = list(config.get("secondary_sensitivity_preferences", []))
    if feature in primary:
        return (0, primary.index(feature), feature)
    if feature in secondary:
        return (1, secondary.index(feature), feature)
    for index, token in enumerate(["_250m", "_500m", "_100m", "_50m"]):
        if feature.endswith(token):
            return (2, index, feature)
    return (3, 0, feature)


def connected_components(features: list[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    """Return connected components for feature correlation graph."""
    adjacency: dict[str, set[str]] = {feature: set() for feature in features}
    for left, right in edges:
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)
    seen: set[str] = set()
    components: list[list[str]] = []
    for feature in features:
        if feature in seen:
            continue
        stack = [feature]
        component: list[str] = []
        seen.add(feature)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in adjacency.get(current, set()):
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))
    return components


def build_correlation_clusters(
    meta: pd.DataFrame,
    pairs: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Cluster numeric features connected by high Spearman correlation."""
    high = float(config["thresholds"]["high_collinearity_abs_spearman"])
    numeric_features = meta.loc[meta["feature_type"] == "numeric", "feature_column"].tolist()
    if pairs.empty:
        edges: list[tuple[str, str]] = []
    else:
        abs_r = pd.to_numeric(pairs["abs_spearman_r"], errors="coerce")
        edges = list(pairs.loc[abs_r >= high, ["feature_a", "feature_b"]].itertuples(index=False, name=None))
    components = connected_components(numeric_features, edges)
    components = sorted(components, key=lambda comp: preference_rank(min(comp, key=lambda f: preference_rank(f, config)), config))
    lookup = meta.set_index("feature_column").to_dict("index")
    pair_lookup: dict[frozenset[str], float] = {}
    for row in pairs.itertuples(index=False):
        pair_lookup[frozenset([row.feature_a, row.feature_b])] = float(row.abs_spearman_r)
    rows: list[dict[str, Any]] = []
    for index, component in enumerate(components, start=1):
        representative = min(component, key=lambda feature: preference_rank(feature, config))
        cluster_id = f"C{index:03d}"
        max_abs = 0.0
        for i, left in enumerate(component):
            for right in component[i + 1 :]:
                max_abs = max(max_abs, pair_lookup.get(frozenset([left, right]), 0.0))
        for feature in component:
            info = lookup[feature]
            rows.append(
                {
                    "collinearity_cluster": cluster_id,
                    "cluster_type": "high_collinearity" if len(component) > 1 else "singleton",
                    "cluster_size": len(component),
                    "feature_column": feature,
                    "feature_group": info["feature_group"],
                    "base_feature": info["base_feature"],
                    "buffer_m": info["buffer_m"],
                    "representative_feature": representative,
                    "is_representative": yes_no(feature == representative),
                    "max_abs_spearman_in_cluster": fmt(max_abs),
                    "cluster_members": semicolon(component),
                    "representative_reason": "configured preference then 250m/500m stable-scale fallback",
                }
            )
    return pd.DataFrame(rows)


def recommended_feature_for_base(features: list[str], config: dict[str, Any]) -> str:
    """Choose an interpretable/stable representative for a same-base buffer family."""
    return min(features, key=lambda feature: preference_rank(feature, config))


def build_buffer_redundancy(
    wide: pd.DataFrame,
    meta: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Compute same-base-feature buffer-scale redundancy."""
    high = float(config["thresholds"]["high_collinearity_abs_spearman"])
    near = float(config["thresholds"]["near_duplicate_abs_spearman"])
    numeric_meta = meta[meta["feature_type"] == "numeric"].copy()
    rows: list[dict[str, Any]] = []
    for (feature_group, base_feature), group in numeric_meta.groupby(["feature_group", "base_feature"], sort=True):
        features = group.sort_values("buffer_m")["feature_column"].tolist()
        if len(features) < 2:
            continue
        recommended = recommended_feature_for_base(features, config)
        recommended_buffer = group.loc[group["feature_column"] == recommended, "buffer_m"].iloc[0]
        for i, feature_a in enumerate(features):
            for feature_b in features[i + 1 :]:
                r, n_pairwise = spearman_rank(wide[feature_a], wide[feature_b])
                abs_r = abs(r) if math.isfinite(r) else np.nan
                status = collinearity_status(abs_r, high, near)
                buffer_a = group.loc[group["feature_column"] == feature_a, "buffer_m"].iloc[0]
                buffer_b = group.loc[group["feature_column"] == feature_b, "buffer_m"].iloc[0]
                rows.append(
                    {
                        "feature_group": feature_group,
                        "base_feature": base_feature,
                        "feature_a": feature_a,
                        "buffer_a_m": buffer_a,
                        "feature_b": feature_b,
                        "buffer_b_m": buffer_b,
                        "spearman_r": fmt(r),
                        "abs_spearman_r": fmt(abs_r),
                        "n_pairwise": n_pairwise,
                        "redundancy_status": status,
                        "recommended_feature": recommended,
                        "recommended_buffer_m": recommended_buffer,
                        "preference_note": "Prefer the configured interpretable full-coverage scale; do not automatically choose largest or smallest buffer.",
                    }
                )
    redundancy = pd.DataFrame(rows)
    if redundancy.empty:
        return redundancy
    return redundancy.sort_values(["abs_spearman_r", "feature_group", "base_feature"], ascending=[False, True, True])


def build_target_table(
    residual: pd.DataFrame,
    probability: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    """Merge primary residual and secondary probability-error station targets."""
    target = residual[["station_id"]].copy()
    target_specs: list[dict[str, str]] = []
    for spec in config.get("residual_targets", []):
        column = str(spec["target_column"])
        if column in residual.columns:
            target[column] = pd.to_numeric(residual[column], errors="coerce")
            target_specs.append(
                {
                    "target_id": column,
                    "source_column": column,
                    "target_label": str(spec.get("target_label", column)),
                    "target_priority": str(spec.get("target_priority", "primary")),
                    "probability_case_id": "",
                }
            )
    for spec in config.get("probability_error_cases", []):
        case_id = str(spec["probability_case_id"])
        source_column = str(spec["target_column"])
        case = probability[probability["probability_case_id"].astype(str) == case_id].copy()
        if case.empty or source_column not in case.columns:
            continue
        target_id = f"{source_column}__{case_id}"
        case = case[["station_id", source_column]].rename(columns={source_column: target_id})
        target = target.merge(case, on="station_id", how="left")
        target_specs.append(
            {
                "target_id": target_id,
                "source_column": source_column,
                "target_label": str(spec.get("target_label", target_id)),
                "target_priority": str(spec.get("target_priority", "secondary")),
                "probability_case_id": case_id,
            }
        )
    return target, target_specs


def stable_seed(base_seed: int, *parts: str) -> int:
    """Create a deterministic small integer seed from text parts."""
    offset = 0
    for part in parts:
        offset += sum((index + 1) * ord(char) for index, char in enumerate(part))
    return int((base_seed + offset) % (2**32 - 1))


def bootstrap_spearman_ci(
    x: pd.Series,
    y: pd.Series,
    iterations: int,
    seed: int,
) -> tuple[float, float, int]:
    """Bootstrap a Spearman confidence interval over station pairs."""
    pair = pd.DataFrame({"x": pd.to_numeric(x, errors="coerce"), "y": pd.to_numeric(y, errors="coerce")}).dropna()
    if len(pair) < 8 or pair["x"].nunique() < 2 or pair["y"].nunique() < 2:
        return np.nan, np.nan, 0
    rng = np.random.default_rng(seed)
    values: list[float] = []
    x_values = pair["x"].to_numpy()
    y_values = pair["y"].to_numpy()
    n = len(pair)
    for _ in range(iterations):
        idx = rng.integers(0, n, size=n)
        sample_x = pd.Series(x_values[idx])
        sample_y = pd.Series(y_values[idx])
        if sample_x.nunique() < 2 or sample_y.nunique() < 2:
            continue
        r, _ = spearman_rank(sample_x, sample_y)
        if math.isfinite(r):
            values.append(r)
    if len(values) < 20:
        return np.nan, np.nan, len(values)
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5)), len(values)


def association_status(r: float, n_pairwise: int, config: dict[str, Any]) -> str:
    """Classify a descriptive feature-target association screen."""
    if n_pairwise < int(config["thresholds"]["candidate_min_pairwise_n"]):
        return "unstable_low_support"
    if math.isfinite(r) and abs(r) >= float(config["thresholds"]["descriptive_abs_spearman"]):
        return "descriptive_candidate"
    return "weak_association"


def build_residual_association_screen(
    wide: pd.DataFrame,
    meta: pd.DataFrame,
    target: pd.DataFrame,
    target_specs: list[dict[str, str]],
    config: dict[str, Any],
) -> pd.DataFrame:
    """Screen numeric features against station-level residual targets."""
    merged = wide.merge(target, on="station_id", how="left")
    numeric_meta = meta[meta["feature_type"] == "numeric"].copy()
    meta_lookup = numeric_meta.set_index("feature_column").to_dict("index")
    iterations = int(config["thresholds"]["bootstrap_iterations"])
    base_seed = int(config["thresholds"]["bootstrap_seed"])
    rows: list[dict[str, Any]] = []
    for feature in numeric_meta["feature_column"].tolist():
        for spec in target_specs:
            target_id = spec["target_id"]
            r, n_pairwise = spearman_rank(merged[feature], merged[target_id])
            ci_low, ci_high, boot_n = bootstrap_spearman_ci(
                merged[feature],
                merged[target_id],
                iterations,
                stable_seed(base_seed, feature, target_id),
            )
            p_value, p_status = spearman_p_value(merged[feature], merged[target_id])
            info = meta_lookup[feature]
            rows.append(
                {
                    "feature_column": feature,
                    "feature_group": info["feature_group"],
                    "base_feature": info["base_feature"],
                    "buffer_m": info["buffer_m"],
                    "target_id": target_id,
                    "target_label": spec["target_label"],
                    "target_priority": spec["target_priority"],
                    "probability_case_id": spec["probability_case_id"],
                    "spearman_r": fmt(r),
                    "abs_spearman_r": fmt(abs(r) if math.isfinite(r) else np.nan),
                    "n_pairwise": n_pairwise,
                    "p_value": p_value,
                    "p_value_status": p_status,
                    "bootstrap_ci_low": fmt(ci_low),
                    "bootstrap_ci_high": fmt(ci_high),
                    "bootstrap_successful_iterations": boot_n,
                    "screen_status": association_status(r, n_pairwise, config),
                    "interpretation_boundary": "descriptive station-level screen only; no residual model and no causal correction",
                }
            )
    screen = pd.DataFrame(rows)
    if screen.empty:
        return screen
    return screen.sort_values(["target_priority", "abs_spearman_r", "feature_column"], ascending=[True, False, True])


def profile_feature_columns(wide: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    """Return configured feature columns for key-station profiles."""
    prefixes = [str(prefix) for prefix in config.get("profile_feature_prefixes", [])]
    exact = [str(column) for column in config.get("profile_exact_features", [])]
    columns: list[str] = []
    for column in wide.columns:
        if any(column.startswith(prefix) for prefix in prefixes) or column in exact:
            columns.append(column)
    return columns


def categorical_mode_text(series: pd.Series) -> tuple[str, float]:
    """Return mode and mode fraction for a categorical series."""
    clean = series.dropna().astype(str)
    if clean.empty:
        return "", np.nan
    counts = clean.value_counts(normalize=True)
    return str(counts.index[0]), float(counts.iloc[0])


def build_key_station_profiles(
    wide: pd.DataFrame,
    meta: pd.DataFrame,
    residual: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Compare key station context features against station medians/IQRs."""
    columns = profile_feature_columns(wide, config)
    meta_lookup = meta.set_index("feature_column").to_dict("index")
    residual_cols = [
        "station_id",
        "n_ge31",
        "mean_context_adjusted_score_residual_c",
        "mean_context_adjusted_high_tail_residual_c",
        "low_support_warning_flag",
    ]
    joined = wide.merge(residual[[col for col in residual_cols if col in residual.columns]], on="station_id", how="left")
    rows: list[dict[str, Any]] = []
    for station_id in config.get("key_stations", []):
        station_rows = joined[joined["station_id"].astype(str) == str(station_id)]
        if station_rows.empty:
            rows.append(
                {
                    "station_id": station_id,
                    "station_present": "no",
                    "feature_column": "",
                    "comparison_note": "configured key station is absent from station feature table",
                }
            )
            continue
        station = station_rows.iloc[0]
        for column in columns:
            info = meta_lookup.get(column, {})
            values = pd.to_numeric(wide[column], errors="coerce")
            raw_value = station[column]
            if values.notna().sum() > 0:
                clean = values.dropna()
                q25 = float(clean.quantile(0.25))
                median = float(clean.quantile(0.50))
                q75 = float(clean.quantile(0.75))
                iqr = q75 - q25
                value = float(pd.to_numeric(pd.Series([raw_value]), errors="coerce").iloc[0])
                if not math.isfinite(value):
                    comparison = "missing"
                    iqr_position = ""
                elif iqr > 0:
                    position = (value - median) / iqr
                    iqr_position = fmt(position, 3)
                    if value < q25:
                        comparison = "below_station_iqr"
                    elif value > q75:
                        comparison = "above_station_iqr"
                    else:
                        comparison = "within_station_iqr"
                else:
                    iqr_position = ""
                    comparison = "same_as_station_median" if value == median else "differs_from_zero_iqr_median"
                rows.append(
                    {
                        "station_id": station_id,
                        "station_present": "yes",
                        "station_name": station.get("station_name", ""),
                        "n_ge31": station.get("n_ge31", ""),
                        "mean_context_adjusted_score_residual_c": fmt(
                            station.get("mean_context_adjusted_score_residual_c", "")
                        ),
                        "mean_context_adjusted_high_tail_residual_c": fmt(
                            station.get("mean_context_adjusted_high_tail_residual_c", "")
                        ),
                        "low_support_warning_flag": station.get("low_support_warning_flag", ""),
                        "feature_column": column,
                        "feature_group": info.get("feature_group", ""),
                        "base_feature": info.get("base_feature", ""),
                        "buffer_m": info.get("buffer_m", ""),
                        "station_value": fmt(value),
                        "station_q25": fmt(q25),
                        "station_median": fmt(median),
                        "station_q75": fmt(q75),
                        "station_iqr": fmt(iqr),
                        "iqr_position": iqr_position,
                        "comparison_note": comparison,
                    }
                )
            else:
                mode_value, mode_fraction = categorical_mode_text(wide[column])
                rows.append(
                    {
                        "station_id": station_id,
                        "station_present": "yes",
                        "station_name": station.get("station_name", ""),
                        "n_ge31": station.get("n_ge31", ""),
                        "mean_context_adjusted_score_residual_c": fmt(
                            station.get("mean_context_adjusted_score_residual_c", "")
                        ),
                        "mean_context_adjusted_high_tail_residual_c": fmt(
                            station.get("mean_context_adjusted_high_tail_residual_c", "")
                        ),
                        "low_support_warning_flag": station.get("low_support_warning_flag", ""),
                        "feature_column": column,
                        "feature_group": info.get("feature_group", ""),
                        "base_feature": info.get("base_feature", ""),
                        "buffer_m": info.get("buffer_m", ""),
                        "station_value": "" if pd.isna(raw_value) else str(raw_value),
                        "station_q25": "",
                        "station_median": mode_value,
                        "station_q75": "",
                        "station_iqr": "",
                        "iqr_position": "",
                        "comparison_note": f"categorical; station-wide mode={mode_value}; mode_fraction={fmt(mode_fraction, 3)}",
                    }
                )
    return pd.DataFrame(rows)


def cluster_lookup(clusters: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Return cluster rows keyed by feature column."""
    if clusters.empty:
        return {}
    return clusters.set_index("feature_column").to_dict("index")


def strongest_primary_association(assoc: pd.DataFrame) -> dict[str, str]:
    """Return strongest primary target association text for each feature."""
    if assoc.empty:
        return {}
    primary = assoc[assoc["target_priority"] == "primary"].copy()
    primary["abs_value"] = pd.to_numeric(primary["abs_spearman_r"], errors="coerce")
    out: dict[str, str] = {}
    for feature, group in primary.sort_values("abs_value", ascending=False).groupby("feature_column", sort=False):
        row = group.iloc[0]
        out[str(feature)] = f"{row['target_label']} r={row['spearman_r']}"
    return out


def near_duplicate_conflict(
    feature: str,
    selected_features: set[str],
    pairs: pd.DataFrame,
    config: dict[str, Any],
) -> str:
    """Return selected primary feature that is a near duplicate, if any."""
    if pairs.empty or not selected_features:
        return ""
    near = float(config["thresholds"]["near_duplicate_abs_spearman"])
    pair_rows = pairs[(pairs["feature_a"] == feature) | (pairs["feature_b"] == feature)].copy()
    pair_rows["abs_value"] = pd.to_numeric(pair_rows["abs_spearman_r"], errors="coerce")
    pair_rows = pair_rows[pair_rows["abs_value"] >= near]
    for row in pair_rows.sort_values("abs_value", ascending=False).itertuples(index=False):
        other = row.feature_b if row.feature_a == feature else row.feature_a
        if other in selected_features:
            return str(other)
    return ""


def is_partial_landuse(feature: str) -> bool:
    """Return True for partial 50/100 m landuse majority/entropy features."""
    return feature.startswith("landuse_entropy_50m") or feature.startswith("landuse_entropy_100m") or feature.startswith(
        "landuse_majority_50m"
    ) or feature.startswith("landuse_majority_100m")


def build_candidate_set(
    meta: pd.DataFrame,
    distribution: pd.DataFrame,
    clusters: pd.DataFrame,
    pairs: pd.DataFrame,
    assoc: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Build the future A-L2.1c candidate feature table with guardrails."""
    dist_lookup = distribution.set_index("feature_column").to_dict("index")
    cl_lookup = cluster_lookup(clusters)
    primary_preferences = list(config.get("primary_candidate_preferences", []))
    secondary_preferences = set(config.get("secondary_sensitivity_preferences", []))
    forbidden = list(config.get("forbidden_feature_tokens", []))
    strongest_assoc = strongest_primary_association(assoc)
    max_primary = int(config["thresholds"]["primary_candidate_max"])
    rows: list[dict[str, Any]] = []

    ordered_features = sorted(meta["feature_column"].tolist(), key=lambda feature: preference_rank(feature, config))
    primary_selected: set[str] = set()
    for feature in ordered_features:
        info = meta.loc[meta["feature_column"] == feature].iloc[0].to_dict()
        dist = dist_lookup.get(feature, {})
        cluster = cl_lookup.get(feature, {})
        cluster_id = str(cluster.get("collinearity_cluster", ""))
        representative = str(cluster.get("representative_feature", feature))
        near_constant = str(dist.get("near_constant_flag", "no")) == "yes"
        missing_fraction = float(dist.get("missing_fraction", 0) or 0)
        feature_type = str(info.get("feature_type", ""))
        allowed_by_schema = bool(info.get("schema_allowed_for_future_model", False))
        allowed = False
        role = "secondary_sensitivity"
        reason_selected = ""
        reason_excluded = ""

        if has_forbidden_token(feature, forbidden):
            role = "metadata_only"
            reason_excluded = "contains forbidden predictive token"
        elif not allowed_by_schema or is_partial_landuse(feature) or missing_fraction > 0:
            role = "exclude_partial_coverage"
            reason_excluded = "partial station coverage or schema disallows future model use"
        elif feature_type != "numeric":
            role = "metadata_only"
            reason_excluded = "categorical context retained for review/profile only, not in small numeric primary set"
        elif near_constant:
            role = "exclude_low_variance"
            reason_excluded = "constant or near-constant across stations"
        elif feature in primary_preferences and len(primary_selected) < max_primary:
            conflict = near_duplicate_conflict(feature, primary_selected, pairs, config)
            if conflict:
                role = "exclude_near_duplicate"
                reason_excluded = f"near-duplicate with selected primary feature {conflict}"
            else:
                allowed = True
                role = "primary_candidate"
                primary_selected.add(feature)
                reason_selected = semicolon(
                    [
                        "configured small-set preference",
                        "full all-27 coverage",
                        "interpretable station-context feature",
                        strongest_assoc.get(feature, ""),
                    ]
                )
        elif near_duplicate_conflict(feature, primary_selected, pairs, config):
            conflict = near_duplicate_conflict(feature, primary_selected, pairs, config)
            role = "exclude_near_duplicate"
            reason_excluded = f"near-duplicate with selected primary feature {conflict}"
        elif feature in secondary_preferences:
            allowed = True
            role = "secondary_sensitivity"
            reason_selected = semicolon(
                [
                    "full coverage secondary sensitivity feature",
                    "not part of the small primary set",
                    strongest_assoc.get(feature, ""),
                ]
            )
        else:
            role = "secondary_sensitivity"
            allowed = True
            reason_selected = semicolon(
                [
                    "full coverage numeric context feature",
                    "secondary only to keep A-L2.1c small",
                    strongest_assoc.get(feature, ""),
                ]
            )

        rows.append(
            {
                "candidate_feature": feature,
                "feature_group": info.get("feature_group", ""),
                "base_feature": info.get("base_feature", ""),
                "buffer_m": info.get("buffer_m", ""),
                "reason_selected": reason_selected,
                "reason_excluded": reason_excluded,
                "collinearity_cluster": cluster_id,
                "cluster_representative": representative,
                "allowed_for_scoped_model": yes_no(allowed),
                "recommended_role": role,
            }
        )
    candidate = pd.DataFrame(rows)
    role_order = {
        "primary_candidate": 0,
        "secondary_sensitivity": 1,
        "exclude_near_duplicate": 2,
        "exclude_partial_coverage": 3,
        "exclude_low_variance": 4,
        "metadata_only": 5,
    }
    candidate["role_sort"] = candidate["recommended_role"].map(role_order).fillna(9)
    return candidate.sort_values(["role_sort", "feature_group", "base_feature", "buffer_m"]).drop(columns=["role_sort"])


def build_manual_review_table(
    distribution: pd.DataFrame,
    clusters: pd.DataFrame,
    assoc: pd.DataFrame,
    profiles: pd.DataFrame,
    candidate: pd.DataFrame,
) -> pd.DataFrame:
    """Create a compact manual-review checklist."""
    rows: list[dict[str, Any]] = []
    for row in distribution[distribution["outlier_stations_robust_z"].astype(str) != ""].itertuples(index=False):
        rows.append(
            {
                "review_item": "distribution_outlier",
                "feature_column": row.feature_column,
                "station_id": row.outlier_stations_robust_z,
                "review_reason": "robust-z outlier station values",
                "suggested_action": "inspect source extraction assumptions before using as primary evidence",
                "source_table": "station_feature_distribution_summary.csv",
            }
        )
    high_clusters = clusters[(clusters["cluster_type"] == "high_collinearity") & (clusters["is_representative"] == "yes")]
    for row in high_clusters.itertuples(index=False):
        rows.append(
            {
                "review_item": "high_collinearity_cluster",
                "feature_column": row.representative_feature,
                "station_id": "",
                "review_reason": f"{row.collinearity_cluster} contains {row.cluster_size} correlated features",
                "suggested_action": "use only one representative in the primary set",
                "source_table": "station_feature_correlation_clusters.csv",
            }
        )
    primary_assoc = assoc[(assoc["target_priority"] == "primary") & (assoc["screen_status"] == "descriptive_candidate")].copy()
    primary_assoc["abs_value"] = pd.to_numeric(primary_assoc["abs_spearman_r"], errors="coerce")
    for row in primary_assoc.sort_values("abs_value", ascending=False).head(12).itertuples(index=False):
        rows.append(
            {
                "review_item": "descriptive_residual_association",
                "feature_column": row.feature_column,
                "station_id": "",
                "review_reason": f"{row.target_label} association r={row.spearman_r}, CI=({row.bootstrap_ci_low},{row.bootstrap_ci_high})",
                "suggested_action": "treat as descriptive screen only; no causal correction",
                "source_table": "station_residual_association_screen.csv",
            }
        )
    for row in profiles[
        profiles["station_id"].isin(["S142", "S139", "S137", "S128"])
        & profiles["comparison_note"].isin(["above_station_iqr", "below_station_iqr"])
    ].head(20).itertuples(index=False):
        rows.append(
            {
                "review_item": "key_station_context_extreme",
                "feature_column": row.feature_column,
                "station_id": row.station_id,
                "review_reason": f"{row.comparison_note}; value={row.station_value}; median={row.station_median}",
                "suggested_action": "use as station context review, not causal explanation",
                "source_table": "station_context_profiles_key_stations.csv",
            }
        )
    excluded = candidate[candidate["recommended_role"].isin(["exclude_near_duplicate", "exclude_partial_coverage"])].head(20)
    for row in excluded.itertuples(index=False):
        rows.append(
            {
                "review_item": row.recommended_role,
                "feature_column": row.candidate_feature,
                "station_id": "",
                "review_reason": row.reason_excluded,
                "suggested_action": "keep out of primary A-L2.1c candidate set",
                "source_table": "station_feature_candidate_set.csv",
            }
        )
    return pd.DataFrame(rows)


def source_summary(schema: pd.DataFrame) -> pd.DataFrame:
    """Summarize S1 source-derived feature groups."""
    grouped = (
        schema.groupby("feature_group")
        .agg(
            feature_count=("feature_column", "count"),
            all_27_feature_count=("missing_fraction", lambda s: int((pd.to_numeric(s, errors="coerce") == 0).sum())),
            allowed_feature_count=("allowed_for_future_model", lambda s: int(s.astype(str).str.lower().eq("true").sum())),
            source_names=("source_name", lambda s: semicolon(s.astype(str))),
        )
        .reset_index()
    )
    return grouped.sort_values("feature_group")


def summarize_excluded_clusters(candidate: pd.DataFrame, clusters: pd.DataFrame) -> str:
    """Return compact text for high-collinearity exclusions."""
    excluded = candidate[candidate["recommended_role"] == "exclude_near_duplicate"].copy()
    if excluded.empty:
        return "none"
    parts: list[str] = []
    for cluster_id, group in excluded.groupby("collinearity_cluster", sort=True):
        representative = group["cluster_representative"].iloc[0]
        features = semicolon(group["candidate_feature"].head(6).tolist())
        parts.append(f"{cluster_id}:{representative} excludes {features}")
    return semicolon(parts[:8])


def summarize_top_residual_features(assoc: pd.DataFrame, limit: int = 5) -> str:
    """Return compact top primary residual association text."""
    primary = assoc[assoc["target_priority"] == "primary"].copy()
    if primary.empty:
        return "none"
    primary["abs_value"] = pd.to_numeric(primary["abs_spearman_r"], errors="coerce")
    top = primary.sort_values("abs_value", ascending=False).head(limit)
    return semicolon(f"{row.feature_column}:{row.target_label} r={row.spearman_r}" for row in top.itertuples())


def summarize_key_station_caveats(profiles: pd.DataFrame) -> str:
    """Return compact key-station caveat text."""
    if profiles.empty:
        return "key station profiles unavailable"
    parts: list[str] = []
    for station_id in ["S142", "S139", "S137", "S128", "S145"]:
        station = profiles[profiles["station_id"] == station_id]
        if station.empty:
            parts.append(f"{station_id}: absent")
            continue
        first = station.iloc[0]
        extreme_count = int(station["comparison_note"].isin(["above_station_iqr", "below_station_iqr"]).sum())
        n_ge31 = first.get("n_ge31", "")
        residual = first.get("mean_context_adjusted_score_residual_c", "")
        high_tail = first.get("mean_context_adjusted_high_tail_residual_c", "")
        parts.append(f"{station_id}:n_ge31={n_ge31},score_resid={residual},high_tail={high_tail},context_extremes={extreme_count}")
    return semicolon(parts)


def decision_status(candidate: pd.DataFrame) -> tuple[str, str]:
    """Choose the A-L2.1b decision status and recommendation."""
    primary_count = int((candidate["recommended_role"] == "primary_candidate").sum())
    if 4 <= primary_count <= 8:
        return (
            "PASS_FEATURE_QA_READY_FOR_SCOPED_MODEL",
            "A-L2.1c may proceed only as a station-level n=27 scoped preflight model using the small primary set and sensitivity checks; no station-adjusted WBGT or causal correction.",
        )
    if primary_count > 0:
        return (
            "PARTIAL_QA_MORE_SOURCE_NEEDED",
            "A-L2.1c should wait or proceed only after review because the small defensible primary set is thin.",
        )
    return (
        "BLOCKED_FEATURE_QA",
        "Do not proceed to A-L2.1c because no usable candidate set could be selected.",
    )


def build_qa_summary(
    wide: pd.DataFrame,
    meta: pd.DataFrame,
    distribution: pd.DataFrame,
    pairs: pd.DataFrame,
    clusters: pd.DataFrame,
    candidate: pd.DataFrame,
    decision: str,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Build headline QA metric rows."""
    high = float(config["thresholds"]["high_collinearity_abs_spearman"])
    near = float(config["thresholds"]["near_duplicate_abs_spearman"])
    abs_pairs = pd.to_numeric(pairs["abs_spearman_r"], errors="coerce") if not pairs.empty else pd.Series(dtype=float)
    rows = [
        {
            "qa_metric": "station_count",
            "qa_value": len(wide),
            "qa_status": "PASS" if len(wide) == int(config["expected_station_count"]) else "REVIEW",
            "notes": "Unique stations in S1 feature table.",
        },
        {
            "qa_metric": "feature_count",
            "qa_value": len(meta),
            "qa_status": "PASS",
            "notes": "Schema feature columns present in wide table.",
        },
        {
            "qa_metric": "numeric_feature_count",
            "qa_value": int((meta["feature_type"] == "numeric").sum()),
            "qa_status": "PASS",
            "notes": "Numeric features screened for collinearity and residual association.",
        },
        {
            "qa_metric": "categorical_feature_count",
            "qa_value": int((meta["feature_type"] == "categorical").sum()),
            "qa_status": "PASS",
            "notes": "Categorical landuse-majority features retained as metadata/profile context.",
        },
        {
            "qa_metric": "max_missing_fraction",
            "qa_value": fmt(distribution["missing_fraction"].astype(float).max()),
            "qa_status": "PASS" if float(distribution["missing_fraction"].astype(float).max()) <= 0.12 else "REVIEW",
            "notes": "S1 partial 50/100 m landuse fields remain excluded from the primary set.",
        },
        {
            "qa_metric": "constant_feature_count",
            "qa_value": int((distribution["constant_flag"] == "yes").sum()),
            "qa_status": "PASS",
            "notes": "Constant features are not allowed into the small primary set.",
        },
        {
            "qa_metric": "near_constant_feature_count",
            "qa_value": int((distribution["near_constant_flag"] == "yes").sum()),
            "qa_status": "PASS",
            "notes": "Near-constant features are excluded or kept only as metadata.",
        },
        {
            "qa_metric": "high_collinearity_pair_count",
            "qa_value": int((abs_pairs >= high).sum()) if len(abs_pairs) else 0,
            "qa_status": "PASS",
            "notes": "Pairs with abs(Spearman) >= 0.80.",
        },
        {
            "qa_metric": "near_duplicate_pair_count",
            "qa_value": int((abs_pairs >= near).sum()) if len(abs_pairs) else 0,
            "qa_status": "PASS",
            "notes": "Pairs with abs(Spearman) >= 0.90.",
        },
        {
            "qa_metric": "high_collinearity_cluster_count",
            "qa_value": int(clusters.loc[clusters["cluster_type"] == "high_collinearity", "collinearity_cluster"].nunique())
            if not clusters.empty
            else 0,
            "qa_status": "PASS",
            "notes": "Unique clusters with at least one abs(Spearman) >= 0.80 edge.",
        },
        {
            "qa_metric": "primary_candidate_feature_count",
            "qa_value": int((candidate["recommended_role"] == "primary_candidate").sum()),
            "qa_status": "PASS" if decision == "PASS_FEATURE_QA_READY_FOR_SCOPED_MODEL" else "REVIEW",
            "notes": "Guardrail target is a small primary set, ideally <=8.",
        },
        {
            "qa_metric": "decision_status",
            "qa_value": decision,
            "qa_status": "PASS" if decision.startswith("PASS") else "REVIEW",
            "notes": "QA gate status; no residual model was trained.",
        },
        {
            "qa_metric": "model_training",
            "qa_value": "none",
            "qa_status": "PASS",
            "notes": "Descriptive screens only.",
        },
        {
            "qa_metric": "claim_boundaries",
            "qa_value": semicolon(config.get("claim_boundaries", [])),
            "qa_status": "PASS",
            "notes": "No causal correction, station-adjusted WBGT, or local 100m WBGT.",
        },
    ]
    return pd.DataFrame(rows)


def profile_station_summary(profiles: pd.DataFrame) -> pd.DataFrame:
    """Create one-row-per-key-station highlights for reports."""
    rows: list[dict[str, Any]] = []
    for station_id, group in profiles.groupby("station_id", sort=False):
        if group["station_present"].iloc[0] != "yes":
            rows.append({"station_id": station_id, "summary": "absent from feature table"})
            continue
        extremes = group[group["comparison_note"].isin(["above_station_iqr", "below_station_iqr"])]
        highlight = semicolon(
            f"{row.feature_column}={row.station_value}({row.comparison_note})" for row in extremes.head(5).itertuples()
        )
        first = group.iloc[0]
        rows.append(
            {
                "station_id": station_id,
                "n_ge31": first.get("n_ge31", ""),
                "score_residual": first.get("mean_context_adjusted_score_residual_c", ""),
                "high_tail_residual": first.get("mean_context_adjusted_high_tail_residual_c", ""),
                "context_highlights": highlight or "no configured profile feature outside station IQR",
            }
        )
    return pd.DataFrame(rows)


def write_report(
    path: Path,
    config: dict[str, Any],
    source: pd.DataFrame,
    distribution: pd.DataFrame,
    clusters: pd.DataFrame,
    redundancy: pd.DataFrame,
    assoc: pd.DataFrame,
    profiles: pd.DataFrame,
    candidate: pd.DataFrame,
    decision: str,
    recommendation: str,
) -> None:
    """Write the English QA report."""
    high_clusters = clusters[clusters["cluster_type"] == "high_collinearity"].copy()
    high_cluster_reps = high_clusters[high_clusters["is_representative"] == "yes"].copy()
    redundancy_top = redundancy[pd.to_numeric(redundancy["abs_spearman_r"], errors="coerce") >= 0.80].copy()
    assoc_primary = assoc[assoc["target_priority"] == "primary"].copy()
    assoc_primary["abs_value"] = pd.to_numeric(assoc_primary["abs_spearman_r"], errors="coerce")
    primary_candidates = candidate[candidate["recommended_role"] == "primary_candidate"].copy()
    profile_summary = profile_station_summary(profiles[profiles["station_id"].isin(["S142", "S139", "S137", "S128"])])
    missing = distribution.copy()
    missing["missing_value"] = pd.to_numeric(missing["missing_fraction"], errors="coerce")
    missing = missing.sort_values(["missing_value", "feature_column"], ascending=[False, True])
    text = f"""# System A A-L2.1b Station Buffer Feature QA

Generated: {date.today().isoformat()}
Decision status: `{decision}`
Branch: `{git_branch()}`
Config: `configs/v11/systema_l2_station_feature_qa.yaml`

## 1. Why A-L2.1b follows A-L2.1a-S1

A-L2.0 found station-level residual structure after Level 1 controls, while A-L2.1a-S1 built all-27 station-local OSM buffer features for buildings, green, landuse, roads, and water. A-L2.1b is the QA/screening gate between those two facts: it checks whether the station-static features are complete, non-degenerate, not redundant, and defensible enough for a future station-level n=27 scoped A-L2.1c preflight model.

No residual model is trained in this lane.

## 2. Feature source summary

{markdown_table(source, ["feature_group", "feature_count", "all_27_feature_count", "allowed_feature_count", "source_names"], limit=10)}

The source feature table is the compact S1 output. Raw OSM, data.gov.sg, OneMap, raster, SOLWEIG, System B, and archive files are not copied or modified.

## 3. Distribution / missingness summary

{markdown_table(missing, ["feature_column", "feature_group", "buffer_m", "feature_type", "n_non_null", "missing_fraction", "zero_fraction", "near_constant_flag", "outlier_stations_robust_z"], limit=16)}

Partial 50/100 m landuse majority/entropy fields remain excluded from the primary candidate set. Constant or near-constant features are not allowed into the small primary set.

## 4. Collinearity clusters

{markdown_table(high_cluster_reps, ["collinearity_cluster", "cluster_size", "representative_feature", "max_abs_spearman_in_cluster", "cluster_members"], limit=12)}

High collinearity is defined as abs(Spearman) >= 0.80. Near-duplicate is defined as abs(Spearman) >= 0.90. Cluster representatives are preferences for review, not model coefficients or causal evidence.

## 5. Buffer redundancy

{markdown_table(redundancy_top, ["feature_group", "base_feature", "feature_a", "feature_b", "abs_spearman_r", "redundancy_status", "recommended_feature"], limit=16)}

For same-base 50/100/250/500 m features, the recommended scale is the configured interpretable full-coverage representative. The selection does not automatically prefer the largest or smallest buffer.

## 6. Residual association screening

{markdown_table(assoc_primary.sort_values("abs_value", ascending=False), ["feature_column", "target_label", "spearman_r", "n_pairwise", "p_value_status", "bootstrap_ci_low", "bootstrap_ci_high", "screen_status"], limit=16)}

These are descriptive station-level Spearman screens only. Probability-error screens are included in the CSV as secondary evidence because A-L2.0 found weaker station signal there.

## 7. S142 / S139 / S137 / S128 station context review

{markdown_table(profile_summary, ["station_id", "n_ge31", "score_residual", "high_tail_residual", "context_highlights"], limit=4)}

S142 remains the main high-tail underprediction caveat from A-L2.0. S139 remains low-support for station-specific probability conclusions. Key station context differences are review prompts, not causal explanations.

## 8. Recommended A-L2.1c feature candidate set

{markdown_table(primary_candidates, ["candidate_feature", "feature_group", "buffer_m", "reason_selected", "collinearity_cluster", "allowed_for_scoped_model", "recommended_role"], limit=12)}

The primary set is deliberately small and contains no `station_id`, official WBGT, residual target, event label, System B, or SOLWEIG feature. Other full-coverage numeric features are secondary sensitivity candidates or excluded as near duplicates.

## 9. Whether A-L2.1c may proceed

{recommendation}

Future modelling, if opened, should remain station-level with n=27 station rows. Station-static features must not be treated as hourly independent rows.

## 10. Claim boundaries

- No model trained.
- No station-context causal correction claimed.
- No station-adjusted WBGT created.
- No local 100 m WBGT created.
- No System B or SOLWEIG outputs touched.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_cn_doc(
    path: Path,
    source: pd.DataFrame,
    distribution: pd.DataFrame,
    clusters: pd.DataFrame,
    redundancy: pd.DataFrame,
    assoc: pd.DataFrame,
    profiles: pd.DataFrame,
    candidate: pd.DataFrame,
    decision: str,
    recommendation: str,
) -> None:
    """Write the UTF-8 Chinese documentation page."""
    high_cluster_reps = clusters[(clusters["cluster_type"] == "high_collinearity") & (clusters["is_representative"] == "yes")]
    assoc_primary = assoc[assoc["target_priority"] == "primary"].copy()
    assoc_primary["abs_value"] = pd.to_numeric(assoc_primary["abs_spearman_r"], errors="coerce")
    primary_candidates = candidate[candidate["recommended_role"] == "primary_candidate"].copy()
    profile_summary = profile_station_summary(profiles[profiles["station_id"].isin(["S142", "S139", "S137", "S128"])])
    missing = distribution.copy()
    missing["missing_value"] = pd.to_numeric(missing["missing_fraction"], errors="coerce")
    text = f"""# OpenHeat System A L2 站点缓冲区特征 QA

生成日期：{date.today().isoformat()}
决策状态：`{decision}`
配置：`configs/v11/systema_l2_station_feature_qa.yaml`

## 1. 为什么 A-L2.1b 接在 A-L2.1a-S1 之后

A-L2.0 已经发现 Level 1 控制之后仍存在站点层面的残差结构；A-L2.1a-S1 则为 27 个站点构建了建筑、绿地、土地利用、道路和水体的 OSM 缓冲区特征。A-L2.1b 的职责是做 QA、共线性检查和残差关联筛查，判断这些站点静态特征是否足以支持未来 A-L2.1c 的小范围站点层面预检模型。

本车道不训练残差模型。

## 2. 特征来源概览

{markdown_table(source, ["feature_group", "feature_count", "all_27_feature_count", "allowed_feature_count", "source_names"], limit=10)}

本次只使用 A-L2.1a-S1 已写出的紧凑 CSV 表，不复制原始 OSM、data.gov.sg、OneMap、栅格、SOLWEIG、System B 或归档数据。

## 3. 分布与缺失情况

{markdown_table(missing.sort_values(["missing_value", "feature_column"], ascending=[False, True]), ["feature_column", "feature_group", "buffer_m", "feature_type", "n_non_null", "missing_fraction", "zero_fraction", "near_constant_flag", "outlier_stations_robust_z"], limit=16)}

50/100 m 的土地利用 majority/entropy 字段覆盖不完整，因此不进入 primary candidate set。常量或近常量特征也不进入小型主候选集。

## 4. 共线性簇

{markdown_table(high_cluster_reps, ["collinearity_cluster", "cluster_size", "representative_feature", "max_abs_spearman_in_cluster", "cluster_members"], limit=12)}

abs(Spearman) >= 0.80 记为高共线性，abs(Spearman) >= 0.90 记为近重复。代表特征只是后续筛选建议，不是因果解释。

## 5. 缓冲区尺度冗余

{markdown_table(redundancy[pd.to_numeric(redundancy["abs_spearman_r"], errors="coerce") >= 0.80], ["feature_group", "base_feature", "feature_a", "feature_b", "abs_spearman_r", "redundancy_status", "recommended_feature"], limit=16)}

同一基础特征在 50/100/250/500 m 之间高度相关时，优先选择可解释且覆盖稳定的尺度；不会自动选择最大或最小缓冲区。

## 6. 残差关联筛查

{markdown_table(assoc_primary.sort_values("abs_value", ascending=False), ["feature_column", "target_label", "spearman_r", "n_pairwise", "p_value_status", "bootstrap_ci_low", "bootstrap_ci_high", "screen_status"], limit=16)}

这些结果只是站点层面的描述性 Spearman 筛查。概率误差结果只作为次要信息写入 CSV，因为 A-L2.0 显示该信号较弱。

## 7. S142 / S139 / S137 / S128 站点背景复核

{markdown_table(profile_summary, ["station_id", "n_ge31", "score_residual", "high_tail_residual", "context_highlights"], limit=4)}

S142 仍是 A-L2.0 中主要的高尾低估复核对象。S139 的事件支持很低，不应据此推广站点特异性概率结论。站点背景差异只能作为复核线索，不能解释为因果修正。

## 8. 建议的 A-L2.1c 候选特征集

{markdown_table(primary_candidates, ["candidate_feature", "feature_group", "buffer_m", "reason_selected", "collinearity_cluster", "allowed_for_scoped_model", "recommended_role"], limit=12)}

主候选集刻意保持小规模，不包含 `station_id`、官方 WBGT、残差目标、事件标签、System B 或 SOLWEIG 特征。其他完整覆盖的数值特征只作为 secondary sensitivity 或因近重复而排除。

## 9. A-L2.1c 是否可以继续

{recommendation}

如果未来开启 A-L2.1c，建模单位必须是站点层面 n=27，不能把站点静态特征当成小时级独立样本。

## 10. 声明边界

- 未训练模型。
- 不声称站点背景因果修正。
- 未创建站点调整后的 WBGT。
- 未创建本地 100 m WBGT。
- 未触碰 System B 或 SOLWEIG 输出。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_status(
    path: Path,
    result: FeatureQaResult,
    config_path: Path,
) -> None:
    """Write lane status Markdown."""
    files = "\n".join(f"- {rel(path)}" for path in result.files_created)
    text = f"""# A-L2.1b Status

Status: {result.decision_status}
Branch: {git_branch()}
Scope: station buffer feature QA / collinearity / residual-readiness gate only; no residual modelling.

Commands run:
- {sys.executable} scripts/v11_l2_run_station_feature_qa.py --config {rel(config_path)}
- CLI equivalent: python scripts/v11_l2_run_station_feature_qa.py --config {rel(config_path)}

Key results:
- Primary candidate feature count: {result.primary_candidate_count}
- Top residual-associated features: {result.top_residual_features}
- Excluded high-collinearity groups: {result.excluded_high_collinearity_groups}
- Key station caveats: {result.key_station_caveats}
- A-L2.1c recommendation: {result.a_l2_1c_recommendation}

Caveats:
- No model trained.
- No station-context causal correction claimed.
- No station-adjusted WBGT or local 100 m WBGT created.
- Probability-error screens are secondary because A-L2.0 found weaker station signal.
- Station-static features must be used only at station-level n=27 in any future scoped preflight.

Files created / modified:
{files}

Safe to commit: controlled config/script/docs and compact CSV/Markdown outputs after review.
Not safe to commit: raw spatial layers, rasters, archives, SOLWEIG/System B outputs, or large forecast/live CSVs.

Next recommended action: {result.a_l2_1c_recommendation}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_feature_qa(config_path: Path) -> FeatureQaResult:
    """Run the full A-L2.1b station feature QA gate."""
    config = load_config(config_path)
    inputs = input_paths(config)
    outputs = output_paths(config)
    outputs["dir"].mkdir(parents=True, exist_ok=True)

    wide = read_csv(inputs["feature_wide"])
    schema = read_csv(inputs["feature_schema"])
    _feature_qa_s1 = read_csv(inputs["feature_qa_s1"])
    residual = read_csv(inputs["residual_summary"])
    probability = read_csv(inputs["probability_summary"])
    _stability = read_csv(inputs["residual_stability_bootstrap"])

    meta = parse_feature_meta(schema, wide)
    source = source_summary(schema)
    distribution = build_distribution_summary(wide, meta, config)
    pairs = build_collinearity_pairs(wide, meta, config)
    clusters = build_correlation_clusters(meta, pairs, config)
    redundancy = build_buffer_redundancy(wide, meta, config)
    target, target_specs = build_target_table(residual, probability, config)
    assoc = build_residual_association_screen(wide, meta, target, target_specs, config)
    profiles = build_key_station_profiles(wide, meta, residual, config)
    candidate = build_candidate_set(meta, distribution, clusters, pairs, assoc, config)
    decision, recommendation = decision_status(candidate)
    summary = build_qa_summary(wide, meta, distribution, pairs, clusters, candidate, decision, config)
    manual_review = build_manual_review_table(distribution, clusters, assoc, profiles, candidate)

    write_csv(outputs["qa_summary"], summary)
    write_csv(outputs["distribution_summary"], distribution)
    write_csv(outputs["collinearity_pairs"], pairs)
    write_csv(outputs["correlation_clusters"], clusters)
    write_csv(outputs["buffer_redundancy"], redundancy)
    write_csv(outputs["residual_association_screen"], assoc)
    write_csv(outputs["key_station_profiles"], profiles)
    write_csv(outputs["candidate_set"], candidate)
    write_csv(outputs["manual_review_table"], manual_review)
    write_report(
        outputs["qa_report"],
        config,
        source,
        distribution,
        clusters,
        redundancy,
        assoc,
        profiles,
        candidate,
        decision,
        recommendation,
    )
    write_cn_doc(
        outputs["cn_doc"],
        source,
        distribution,
        clusters,
        redundancy,
        assoc,
        profiles,
        candidate,
        decision,
        recommendation,
    )

    files_created = [
        outputs["qa_summary"],
        outputs["distribution_summary"],
        outputs["collinearity_pairs"],
        outputs["correlation_clusters"],
        outputs["buffer_redundancy"],
        outputs["residual_association_screen"],
        outputs["key_station_profiles"],
        outputs["candidate_set"],
        outputs["manual_review_table"],
        outputs["qa_report"],
        outputs["status"],
        outputs["cn_doc"],
    ]
    result = FeatureQaResult(
        decision_status=decision,
        primary_candidate_count=int((candidate["recommended_role"] == "primary_candidate").sum()),
        top_residual_features=summarize_top_residual_features(assoc),
        excluded_high_collinearity_groups=summarize_excluded_clusters(candidate, clusters),
        key_station_caveats=summarize_key_station_caveats(profiles),
        a_l2_1c_recommendation=recommendation,
        files_created=files_created,
        git_status_short=git_status_short(),
    )
    write_status(outputs["status"], result, config_path)
    return result


def main() -> int:
    """CLI entrypoint for direct module execution."""
    parser = argparse.ArgumentParser(description="Run A-L2.1b station buffer feature QA.")
    parser.add_argument("--config", default="configs/v11/systema_l2_station_feature_qa.yaml")
    args = parser.parse_args()
    result = run_feature_qa(resolve_path(args.config))
    print(result.decision_status)
    return 0 if result.decision_status != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
