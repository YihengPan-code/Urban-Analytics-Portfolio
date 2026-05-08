"""Validation design notes and utility skeletons."""
from __future__ import annotations
import pandas as pd


def station_skill_table(pred_df: pd.DataFrame, obs_df: pd.DataFrame) -> pd.DataFrame:
    """Placeholder for forecast-vs-observed station validation.

    Expected future use:
    pred_df columns: station_id, time, predicted_wbgt_c / predicted_tair_c
    obs_df columns: station_id, time, observed_wbgt_c / observed_tair_c
    """
    merged = pred_df.merge(obs_df, on=['station_id', 'time'], how='inner')
    out = []
    for sid, g in merged.groupby('station_id'):
        if 'predicted_wbgt_c' in g and 'observed_wbgt_c' in g:
            err = g['predicted_wbgt_c'] - g['observed_wbgt_c']
            out.append({
                'station_id': sid,
                'n': len(g),
                'mae_wbgt': err.abs().mean(),
                'bias_wbgt': err.mean(),
                'rmse_wbgt': (err.pow(2).mean()) ** 0.5,
            })
    return pd.DataFrame(out)
