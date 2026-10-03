#!/usr/bin/env python3
"""Strict H10 identity check for OpenHeat v1.1-beta-formal.

Checks that M5/M6/M7 metrics, and optionally OOF predictions, are identical to
6 decimal places. This script intentionally does **not** accept "near identity"
as a pass condition.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

MODELS = (
    "M5_v10_morphology_ridge",
    "M6_v10_overhead_ridge",
    "M7_compact_weather_ridge",
)
METRIC_CANDIDATES = (
    "mae", "MAE", "rmse", "RMSE", "bias", "Bias", "r2", "R2",
    "f1", "F1", "precision", "Precision", "recall", "Recall",
    "tp", "TP", "fp", "FP", "fn", "FN",
)
PRED_CANDIDATES = ("prediction", "predicted", "predicted_wbgt_c", "y_pred", "oof_pred")
ID_CANDIDATES = ("station_id", "timestamp", "valid_time", "hour", "fold", "target", "aggregation", "framing")

@dataclass(frozen=True)
class H10Result:
    metrics_pass: bool
    predictions_pass: bool | None
    checked_metric_columns: list[str]
    checked_prediction_column: str | None
    n_metric_groups_checked: int
    n_prediction_rows_compared: int | None
    failures: list[str]


def model_col(df: pd.DataFrame) -> str:
    for c in ("model", "model_name", "baseline", "estimator"):
        if c in df.columns:
            return c
    raise ValueError("Could not find model column")


def present(cols: list[str], candidates: tuple[str, ...]) -> list[str]:
    lower = {c.lower(): c for c in cols}
    out = []
    for cand in candidates:
        if cand in cols:
            out.append(cand)
        elif cand.lower() in lower:
            out.append(lower[cand.lower()])
    return sorted(set(out), key=out.index)


def check_metrics(path: Path, decimals: int) -> tuple[bool, list[str], int, list[str]]:
    df = pd.read_csv(path, low_memory=False)
    mcol = model_col(df)
    metric_cols = present(list(df.columns), METRIC_CANDIDATES)
    if not metric_cols:
        raise ValueError("No metric columns found")
    group_cols = [c for c in df.columns if c not in metric_cols and c != mcol]
    failures: list[str] = []
    checked = 0
    for keys, group in df[df[mcol].isin(MODELS)].groupby(group_cols, dropna=False) if group_cols else [((), df[df[mcol].isin(MODELS)])]:
        sub = group.set_index(mcol)
        if not set(MODELS).issubset(set(sub.index)):
            continue
        checked += 1
        ref = sub.loc[MODELS[0], metric_cols].astype(float).round(decimals)
        for model in MODELS[1:]:
            other = sub.loc[model, metric_cols].astype(float).round(decimals)
            unequal = ref.ne(other)
            if unequal.any():
                bad_cols = list(ref.index[unequal])
                failures.append(f"metrics mismatch group={keys}: {MODELS[0]} vs {model}: {bad_cols}")
    return not failures and checked > 0, metric_cols, checked, failures


def check_predictions(path: Path, decimals: int) -> tuple[bool, str | None, int, list[str]]:
    df = pd.read_csv(path, low_memory=False)
    mcol = model_col(df)
    pred_cols = present(list(df.columns), PRED_CANDIDATES)
    if not pred_cols:
        return False, None, 0, ["No prediction column found"]
    pred_col = pred_cols[0]
    id_cols = [c for c in ID_CANDIDATES if c in df.columns]
    if not id_cols:
        id_cols = [c for c in df.columns if c not in {mcol, pred_col}]
    sub = df[df[mcol].isin(MODELS)].copy()
    piv = sub.pivot_table(index=id_cols, columns=mcol, values=pred_col, aggfunc="first")
    failures: list[str] = []
    if not set(MODELS).issubset(set(piv.columns)):
        failures.append("OOF predictions do not contain all M5/M6/M7 models")
        return False, pred_col, len(piv), failures
    rounded = piv[list(MODELS)].astype(float).round(decimals)
    mismatch = (rounded[MODELS[0]] != rounded[MODELS[1]]) | (rounded[MODELS[0]] != rounded[MODELS[2]])
    if mismatch.any():
        failures.append(f"OOF prediction mismatch rows={int(mismatch.sum())} / {len(mismatch)}")
    return not failures, pred_col, len(piv), failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--oof", type=Path, default=None)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--decimals", type=int, default=6)
    args = parser.parse_args()

    metrics_pass, metric_cols, n_groups, failures = check_metrics(args.metrics, args.decimals)
    predictions_pass = None
    pred_col = None
    pred_rows = None
    if args.oof and args.oof.exists():
        predictions_pass, pred_col, pred_rows, pred_failures = check_predictions(args.oof, args.decimals)
        failures.extend(pred_failures)

    result = H10Result(
        metrics_pass=metrics_pass,
        predictions_pass=predictions_pass,
        checked_metric_columns=metric_cols,
        checked_prediction_column=pred_col,
        n_metric_groups_checked=n_groups,
        n_prediction_rows_compared=pred_rows,
        failures=failures,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    status = "PASS" if metrics_pass and (predictions_pass is not False) else "FAIL"
    text = f"""
# H10 strict identity check

Status: **{status}**

```json
{json.dumps(asdict(result), ensure_ascii=False, indent=2)}
```

Required interpretation:

- PASS means M5/M6/M7 are identical to {args.decimals} decimal places for checked artifacts.
- FAIL does not mean morphology suddenly works. Audit schema, aggregator forwarding, imputer/scaler behavior, and station-to-cell mapping first.
""".strip() + "\n"
    args.out_md.write_text(text, encoding="utf-8")
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
