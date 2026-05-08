from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from v071_build_risk_exposure_features import parse_census_age_table, robust_minmax


def test_robust_minmax_constant_returns_zero():
    s = robust_minmax(pd.Series([5, 5, 5]))
    assert s.tolist() == [0.0, 0.0, 0.0]


def test_parse_census_age_table_hierarchical_rows(tmp_path):
    p = tmp_path / 'census.csv'
    df = pd.DataFrame({
        'Number': ['Total', 'Toa Payoh - Total', 'Toa Payoh West', 'Toa Payoh Central'],
        'Total_Total': ['1000', '1000', '600', '400'],
        'Total_0_4': ['50', '50', '30', '20'],
        'Total_65_69': ['40', '40', '20', '20'],
        'Total_70_74': ['30', '30', '15', '15'],
        'Total_75_79': ['20', '20', '10', '10'],
        'Total_80_84': ['10', '10', '5', '5'],
        'Total_85_89': ['5', '5', '3', '2'],
        'Total_90_Over': ['5', '5', '2', '3'],
    })
    df.to_csv(p, index=False)
    out = parse_census_age_table(p)
    assert len(out) == 2
    assert set(out['planning_area_census']) == {'Toa Payoh'}
    west = out[out['subzone_census'] == 'Toa Payoh West'].iloc[0]
    assert abs(west['elderly_pct_65plus'] - (20+15+10+5+3+2)/600) < 1e-9
    assert abs(west['children_pct_under5'] - 30/600) < 1e-9
