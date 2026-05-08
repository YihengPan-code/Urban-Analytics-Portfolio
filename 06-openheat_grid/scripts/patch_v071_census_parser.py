from pathlib import Path
import re

TARGET = Path('scripts/v071_build_risk_exposure_features.py')

NEW_FUNC = '''def parse_census_age_table(path: str | Path) -> pd.DataFrame:
    """Parse SingStat Census 2020 age-by-subzone table robustly.

    The data.gov.sg CSV may expose the 90+ column as Total_90_Over,
    Total_90_and_Over, or another normalised variant.  This parser detects
    65+ Total age-band columns dynamically rather than relying on one exact
    column name.
    """
    path = Path(path)
    df = pd.read_csv(path)

    def norm_col(x: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", str(x).strip().lower()).strip("_")

    norm_to_col = {norm_col(c): c for c in df.columns}

    def find_by_norm(candidates: list[str]) -> str:
        for cand in candidates:
            key = norm_col(cand)
            if key in norm_to_col:
                return norm_to_col[key]
        raise KeyError(
            f"Could not find any of columns {candidates}. "
            f"Available normalized examples: {list(norm_to_col.keys())[:30]}..."
        )

    label_col = find_by_norm(["Number", "Subzone", "subzone", "planning_area_subzone"])
    total_col = find_by_norm(["Total_Total", "(Total) Total", "Total Total"])
    under5_col = find_by_norm(["Total_0_4", "(Total) 0 - 4", "Total 0 4"])

    elderly_cols: list[str] = []
    for col in df.columns:
        n = norm_col(col)
        if not n.startswith("total_") or n == "total_total":
            continue
        m = re.match(r"^total_(\\d+)(?:_(\\d+)|_over|_and_over|_or_over|_and_above|_plus)(?:_text)?$", n)
        if not m:
            continue
        if int(m.group(1)) >= 65:
            elderly_cols.append(col)

    if not elderly_cols:
        raise KeyError(
            "Could not identify any Total age-band columns for 65+. "
            f"Available columns: {list(df.columns)}"
        )

    out = df.copy()
    out["row_label"] = out[label_col].astype(str).str.strip()
    out = out[
        out["row_label"].notna()
        & (out["row_label"].str.lower() != "total")
        & (~out["row_label"].str.contains(r"\\s-\\sTotal$", case=False, regex=True, na=False))
    ].copy()

    def to_num(s):
        return pd.to_numeric(
            s.astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("na", "", case=False, regex=False)
            .str.strip(),
            errors="coerce",
        ).fillna(0)

    out["total_pop"] = to_num(out[total_col])
    out["children_count_under5"] = to_num(out[under5_col])
    out["elderly_count_65plus"] = sum(to_num(out[c]) for c in elderly_cols)

    out["children_pct_under5"] = np.where(
        out["total_pop"] > 0,
        out["children_count_under5"] / out["total_pop"],
        np.nan,
    )
    out["elderly_pct_65plus"] = np.where(
        out["total_pop"] > 0,
        out["elderly_count_65plus"] / out["total_pop"],
        np.nan,
    )
    out["demographic_vulnerability_raw"] = (
        0.75 * out["elderly_pct_65plus"].fillna(0)
        + 0.25 * out["children_pct_under5"].fillna(0)
    )

    out["subzone"] = out["row_label"]
    out["planning_area"] = ""

    return out[[
        "planning_area",
        "subzone",
        "total_pop",
        "children_count_under5",
        "elderly_count_65plus",
        "children_pct_under5",
        "elderly_pct_65plus",
        "demographic_vulnerability_raw",
    ]]
'''

def main():
    if not TARGET.exists():
        raise FileNotFoundError(f"Cannot find {TARGET}. Run this from the project root.")
    text = TARGET.read_text(encoding='utf-8')
    pattern = r"def parse_census_age_table\(.*?\n(?=def |# ---------------------------------------------------------------------|class |if __name__ == ['\"]__main__['\"]:)"
    new_text, n = re.subn(pattern, NEW_FUNC + "\n\n", text, count=1, flags=re.DOTALL)
    if n != 1:
        raise RuntimeError("Could not locate parse_census_age_table() block to replace. Please patch manually.")
    backup = TARGET.with_suffix('.py.bak_v071_census_parser')
    backup.write_text(text, encoding='utf-8')
    TARGET.write_text(new_text, encoding='utf-8')
    print(f"[OK] Patched {TARGET}")
    print(f"[OK] Backup written to {backup}")

if __name__ == '__main__':
    main()
