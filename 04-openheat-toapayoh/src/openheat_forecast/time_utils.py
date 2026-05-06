"""Timezone utilities for OpenHeat."""
from __future__ import annotations
from zoneinfo import ZoneInfo
from typing import Any, Iterable
import pandas as pd

SGT = ZoneInfo("Asia/Singapore")
UTC = ZoneInfo("UTC")


def to_singapore_timestamp(value: Any):
    """Parse a scalar timestamp as tz-aware Asia/Singapore time.

    Naive timestamps are interpreted as Singapore local time. Tz-aware values are
    converted to Singapore time. Invalid values become pandas.NaT.
    """
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return pd.NaT
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        return ts.tz_localize(SGT)
    return ts.tz_convert(SGT)


def to_singapore_time_series(values: Iterable[Any]) -> pd.Series:
    """Robust helper for mixed-format timestamp parsing."""
    return pd.Series([to_singapore_timestamp(v) for v in values])


def utc_now_iso() -> str:
    return pd.Timestamp.now(tz=UTC).isoformat(timespec="seconds")
