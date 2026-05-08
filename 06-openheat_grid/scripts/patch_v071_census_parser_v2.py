"""Hotfix v0.7.1.2: patch Census age-table parser for data.gov.sg CSV schemas.

Run from the OpenHeat project root:
    python scripts/patch_v071_census_parser_v2.py

This replaces parse_census_age_table() in scripts/v071_build_risk_exposure_features.py
with a schema-flexible parser. It avoids re.sub replacement-string escape issues by
using a lambda replacement.
"""
from __future__ import annotations

from pathlib import Path
import re
import shutil

TARGET = Path("scripts/v071_build_risk_exposure_features.py")
BACKUP_SUFFIX = ".bak_v071_census_parser_v2"

NEW_FUNC = r'''def parse_census_age_table(path: str | Path) -> pd.DataFrame:
    """Parse Census 2020 subzone age table robustly.

    The data.gov.sg CSV has appeared with column names such as:
    - Number
    - Total_Total
    - Total_0_4
    - Total_65_69 ... Total_85_89
    - sometimes Total_90_Over / Total_90_and_Over / other 90+ variants

    This parser does not hard-code a single 90+ column name. Instead it:
    1. Detects the label column, usually 'Number'.
    2. Detects total population and age-band columns by normalised names.
    3. Sums all Total_* age bands with starting age >= 65.
    4. Uses Total_0_4 for children under 5 when available.
    5. Infers planning area from rows like 'Toa Payoh - Total'.

    Returns one row per subzone with:
    planning_area, subzone, total_pop, elderly_count_65plus,
    children_count_under5, elderly_pct_65plus, children_pct_under5,
    planning_area_norm, subzone_norm
    """
    import re as _re
    import numpy as _np
    import pandas as _pd

    df = _pd.read_csv(path)

    def _norm_col(x) -> str:
        s = str(x).strip().lower()
        s = s.replace("&", "and")
        s = _re.sub(r"[^a-z0-9]+", "_", s)
        return s.strip("_")

    norm_to_col = {_norm_col(c): c for c in df.columns}

    # Label column. In the current data.gov.sg CSV this is 'Number'.
    label_col = None
    for cand in ["number", "planning_area_subzone", "planning_area_subzone_of_residence", "subzone", "name"]:
        if cand in norm_to_col:
            label_col = norm_to_col[cand]
            break
    if label_col is None:
        # Fallback: first non-ID text-like column.
        non_id = [c for c in df.columns if not _norm_col(c).startswith("id") and _norm_col(c) != "_id"]
        if not non_id:
            raise KeyError(f"Could not identify census label column. Available columns: {list(df.columns)}")
        label_col = non_id[0]

    # Total population column.
    total_col = None
    for cand in ["total_total", "total", "all_total"]:
        if cand in norm_to_col:
            total_col = norm_to_col[cand]
            break
    if total_col is None:
        # Prefer a column that has both 'total' and not an age band.
        for n, c in norm_to_col.items():
            if n.startswith("total") and not _re.search(r"\d", n):
                total_col = c
                break
    if total_col is None:
        raise KeyError(f"Could not identify total population column. Available columns: {list(df.columns)}")

    def _age_start_from_norm(n: str):
        # Examples: total_65_69, total_90_over, total_90_and_over, total_0_4
        if not n.startswith("total_"):
            return None
        if n in {"total_total", "total"}:
            return None
        m = _re.search(r"total_(\d+)", n)
        if not m:
            return None
        return int(m.group(1))

    total_age_cols = []
    elderly_cols = []
    child_cols = []
    for col in df.columns:
        n = _norm_col(col)
        start = _age_start_from_norm(n)
        if start is None:
            continue
        total_age_cols.append(col)
        if start >= 65:
            elderly_cols.append(col)
        if start == 0:
            child_cols.append(col)

    if not elderly_cols:
        raise KeyError(
            "Could not identify any Total age-band columns starting at 65+. "
            f"Available columns: {list(df.columns)}"
        )
    if not child_cols:
        # Keep pipeline alive; children score can be zero if the source schema changes.
        child_cols = []

    def _to_num(s):
        return _pd.to_numeric(s.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce")

    work = df.copy()
    work["_label"] = work[label_col].astype(str).str.strip()
    work["total_pop"] = _to_num(work[total_col]).fillna(0)
    work["elderly_count_65plus"] = work[elderly_cols].apply(_to_num).fillna(0).sum(axis=1)
    if child_cols:
        work["children_count_under5"] = work[child_cols].apply(_to_num).fillna(0).sum(axis=1)
    else:
        work["children_count_under5"] = 0.0

    # Infer planning area from '<Planning Area> - Total' rows.
    rows = []
    current_pa = None
    for _, row in work.iterrows():
        label = str(row["_label"]).strip()
        if not label or label.lower() in {"nan", "total"}:
            continue
        if _re.search(r"\s*-\s*total$", label, flags=_re.I):
            current_pa = _re.sub(r"\s*-\s*total$", "", label, flags=_re.I).strip()
            continue
        # Drop obvious aggregate rows.
        if label.lower().endswith(" total") or label.lower() == "total":
            continue
        if current_pa is None:
            current_pa = "UNKNOWN"
        total = float(row["total_pop"])
        elderly = float(row["elderly_count_65plus"])
        child = float(row["children_count_under5"])
        rows.append({
            "planning_area": current_pa,
            "subzone": label,
            "total_pop": total,
            "elderly_count_65plus": elderly,
            "children_count_under5": child,
            "elderly_pct_65plus": elderly / total if total > 0 else _np.nan,
            "children_pct_under5": child / total if total > 0 else _np.nan,
        })

    out = _pd.DataFrame(rows)
    if out.empty:
        raise ValueError("Parsed Census table is empty. Check the label/planning-area row format.")

    def _norm_name(x):
        s = str(x).upper().strip()
        s = _re.sub(r"[^A-Z0-9]+", " ", s)
        return _re.sub(r"\s+", " ", s).strip()

    out["planning_area_norm"] = out["planning_area"].map(_norm_name)
    out["subzone_norm"] = out["subzone"].map(_norm_name)
    out["census_age_cols_used_65plus"] = ";".join(elderly_cols)
    out["census_child_cols_used_under5"] = ";".join(child_cols)
    return out
'''


def main() -> None:
    if not TARGET.exists():
        raise FileNotFoundError(f"Cannot find target file: {TARGET.resolve()}")

    text = TARGET.read_text(encoding="utf-8")
    pattern = r"def parse_census_age_table\(.*?\n(?=def\s+|class\s+|if\s+__name__\s*==|$)"
    if not re.search(pattern, text, flags=re.DOTALL):
        raise RuntimeError("Could not locate parse_census_age_table() block to replace.")

    backup = TARGET.with_name(TARGET.name + BACKUP_SUFFIX)
    if not backup.exists():
        shutil.copy2(TARGET, backup)

    # Use lambda replacement so backslashes inside NEW_FUNC, e.g. \d, are not treated
    # as replacement-template escapes by re.subn().
    new_text, n = re.subn(pattern, lambda m: NEW_FUNC + "\n\n", text, count=1, flags=re.DOTALL)
    if n != 1:
        raise RuntimeError(f"Expected exactly 1 replacement, got {n}")

    TARGET.write_text(new_text, encoding="utf-8")
    print("[OK] Patched", TARGET)
    print("[OK] Backup:", backup)
    print("Next run:")
    print("  python scripts\\v071_build_risk_exposure_features.py --config configs\\v071_risk_exposure_config.example.json")


if __name__ == "__main__":
    main()
