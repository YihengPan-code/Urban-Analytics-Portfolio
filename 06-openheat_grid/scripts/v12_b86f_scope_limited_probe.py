"""Compare baseline and abstention-gated scope-limited surrogate diagnostics.

Inputs:
    b86f_abstention_gate_metrics.csv plus the B8.6f config.
Outputs:
    b86f_scope_limited_surrogate_metrics.csv.
Saved metrics:
    Baseline B8.6d-style retained metrics, moderate-gate metrics, strict-gate
    metrics, deltas versus baseline, top-k screening suitability, and a
    diagnostic-only scope status. This script does not create AOI-wide
    prediction, B9, WBGT, hazard, risk, raster, QGIS/SOLWEIG, or System A/B
    coupling output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86f_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    as_float,
    load_config,
    output_path,
    read_csv,
    write_csv,
)


@dataclass(frozen=True)
class ScopeProbeResult:
    """Scope-limited surrogate probe result."""

    status: str
    rows: int
    candidate_rows: int


def row_status(row: pd.Series) -> str:
    """Assign diagnostic scope status for a comparison row."""
    gate = str(row["gate_level"])
    if gate == "baseline_no_gate":
        return "SCOPE_LIMITED_DIAGNOSTIC_ONLY"
    coverage = as_float(row.get("retained_coverage_fraction"), 0.0)
    spearman_delta = as_float(row.get("Spearman_delta_vs_baseline"), 0.0)
    top10_delta = as_float(row.get("top10_delta_vs_baseline"), 0.0)
    fp_delta = as_float(row.get("false_promotion_delta_vs_baseline"), 0.0)
    if coverage >= 0.40 and spearman_delta >= 0.20 and top10_delta >= 0.15 and fp_delta <= -0.05:
        return "SCOPE_LIMITED_PREFLIGHT_CANDIDATE"
    if coverage < 0.25 or spearman_delta < 0 or top10_delta < -0.10:
        return "NOT_READY"
    return "SCOPE_LIMITED_DIAGNOSTIC_ONLY"


def topk_suitability(row: pd.Series) -> str:
    """Classify top-k screening suitability without production claims."""
    top10 = as_float(row.get("top10pct_overlap_retained"))
    spearman = as_float(row.get("Spearman_retained"))
    fp_rate = as_float(row.get("neutral_false_promotion_rate_retained"))
    coverage = as_float(row.get("retained_coverage_fraction"))
    if top10 >= 0.60 and spearman >= 0.50 and fp_rate <= 0.15 and coverage >= 0.40:
        return "diagnostic_screening_candidate_only"
    if top10 >= 0.50 and fp_rate <= 0.20 and coverage >= 0.30:
        return "weak_diagnostic_screening_candidate"
    return "not_suitable_for_screening"


def scope_metrics(config: dict[str, Any]) -> pd.DataFrame:
    """Build baseline versus gated scope-limited comparison metrics."""
    metrics = read_csv(output_path(config, "abstention_gate_metrics"))
    baseline = metrics.loc[metrics["gate_level"].astype(str).eq("baseline_no_gate")].copy()
    rows: list[dict[str, Any]] = []
    for _, row in metrics.iterrows():
        split = str(row["split_family"])
        base = baseline.loc[baseline["split_family"].astype(str).eq(split)]
        base_row = base.iloc[0] if not base.empty else row
        out = row.to_dict()
        out["baseline_MAE"] = base_row.get("MAE_retained")
        out["baseline_Spearman"] = base_row.get("Spearman_retained")
        out["baseline_top10pct_overlap"] = base_row.get("top10pct_overlap_retained")
        out["baseline_neutral_false_promotion_rate"] = base_row.get("neutral_false_promotion_rate_retained")
        out["MAE_delta_vs_baseline"] = as_float(row.get("MAE_retained")) - as_float(base_row.get("MAE_retained"))
        out["Spearman_delta_vs_baseline"] = as_float(row.get("Spearman_retained")) - as_float(base_row.get("Spearman_retained"))
        out["top10_delta_vs_baseline"] = as_float(row.get("top10pct_overlap_retained")) - as_float(base_row.get("top10pct_overlap_retained"))
        out["false_promotion_delta_vs_baseline"] = as_float(row.get("neutral_false_promotion_rate_retained")) - as_float(
            base_row.get("neutral_false_promotion_rate_retained")
        )
        rows.append(out)
    out = pd.DataFrame(rows)
    out["topk_screening_suitability"] = out.apply(topk_suitability, axis=1)
    out["scope_status"] = out.apply(row_status, axis=1)
    out["status_boundary"] = "diagnostic_only_not_production"
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def run(config_path: Path = DEFAULT_CONFIG) -> ScopeProbeResult:
    """Write scope-limited surrogate diagnostic comparison metrics."""
    config = load_config(config_path)
    out = scope_metrics(config)
    write_csv(out, output_path(config, "scope_limited_surrogate_metrics"))
    candidate_rows = int(out["scope_status"].astype(str).eq("SCOPE_LIMITED_PREFLIGHT_CANDIDATE").sum())
    if candidate_rows:
        status = "B86F_SCOPE_LIMITED_PREFLIGHT_CANDIDATE"
    elif out["scope_status"].astype(str).eq("NOT_READY").any():
        status = "B86F_SCOPE_LIMITED_NOT_READY"
    else:
        status = "B86F_SCOPE_LIMITED_DIAGNOSTIC_ONLY"
    return ScopeProbeResult(status=status, rows=len(out), candidate_rows=candidate_rows)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Compare baseline and abstention-gated B8.6f scope-limited diagnostics.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
