#!/usr/bin/env python
"""OpenHeat v1.1 archive health check.

Run this any time to get a one-page health report on the long-running archive
collector. Designed to be runnable while the loop is still collecting in
another window — no locks, read-only access.

Usage (from project root, in openheat env):
    python scripts/v11_archive_health_check.py

What it shows:
- Archive size and growth (total rows, days covered, expected vs actual rate)
- Recent loop runs (success/failure pattern from loop_runs.log)
- Station coverage (any missing stations? any silently dead?)
- Per-day WBGT row counts (last 7 days, spot gaps)
- Latest run QA snippet (errors/warnings from most recent collect)
- Health verdict: GREEN / YELLOW / RED
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WBGT_PATH = PROJECT_ROOT / "data/archive/v11_longterm/normalized/nea_wbgt_v11_longterm_normalized.csv"
PAIRS_PATH = PROJECT_ROOT / "data/calibration/v11/v11_station_weather_pairs.csv"
LOOP_LOG = PROJECT_ROOT / "outputs/v11_archive_longterm/loop_runs.log"
LATEST_QA = PROJECT_ROOT / "outputs/v11_archive_longterm/v11_archive_latest_QA_report.md"

EXPECTED_STATIONS = 27
EXPECTED_ROWS_PER_DAY = 27 * 96  # 27 stations × 96 timestamps (15 min cadence)


def header(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def section(title: str) -> None:
    print()
    print(f"--- {title} ---")


def check_wbgt_archive() -> dict:
    """Read WBGT normalized table; return key stats."""
    if not WBGT_PATH.exists():
        return {"error": f"WBGT archive not found: {WBGT_PATH}"}
    df = pd.read_csv(WBGT_PATH, low_memory=False)
    if df.empty:
        return {"error": "WBGT archive is empty"}

    df["ts"] = pd.to_datetime(df["timestamp_sgt"], errors="coerce", utc=False)
    df = df[df["ts"].notna()].copy()

    nat_count = len(pd.read_csv(WBGT_PATH, low_memory=False)) - len(df)

    stats = {
        "rows": len(df),
        "stations": df["station_id"].nunique(),
        "unique_timestamps": df["ts"].dt.floor("15min").nunique(),
        "first_obs": df["ts"].min(),
        "last_obs": df["ts"].max(),
        "nat_count": nat_count,
        "df": df,
    }
    stats["span_hours"] = (stats["last_obs"] - stats["first_obs"]).total_seconds() / 3600.0
    stats["span_days"] = stats["span_hours"] / 24.0

    # Row counts in last 24h, last 7d.
    now_local = df["ts"].max()  # use latest obs as "now" reference (avoids tz mess)
    stats["rows_last_24h"] = int((df["ts"] >= now_local - pd.Timedelta(hours=24)).sum())
    stats["rows_last_7d"] = int((df["ts"] >= now_local - pd.Timedelta(days=7)).sum())

    return stats


def check_loop_log() -> dict:
    """Parse loop_runs.log for recent run pattern."""
    if not LOOP_LOG.exists():
        return {"error": f"loop log not found: {LOOP_LOG}"}
    lines = [ln.strip() for ln in LOOP_LOG.read_text(errors="ignore").splitlines() if ln.strip()]
    if not lines:
        return {"error": "loop log is empty"}

    last_n = lines[-50:]  # focus on recent
    successes = sum(1 for ln in last_n if "exit_code=0" in ln)
    failures = sum(1 for ln in last_n if "exit_code=" in ln and "exit_code=0" not in ln)

    return {
        "total_runs_logged": len(lines),
        "last_50_runs": len(last_n),
        "last_50_success": successes,
        "last_50_fail": failures,
        "last_3_lines": last_n[-3:],
    }


def check_per_day(df: pd.DataFrame, n_days: int = 7) -> pd.DataFrame:
    """Per-day WBGT row counts for the last n days."""
    df = df.copy()
    df["date"] = df["ts"].dt.date
    counts = (
        df.groupby("date")
        .agg(rows=("station_id", "size"),
             stations=("station_id", "nunique"),
             max_wbgt=("official_wbgt_c", "max"),
             ge31=("official_wbgt_c", lambda s: (s >= 31).sum()),
             ge33=("official_wbgt_c", lambda s: (s >= 33).sum()))
        .reset_index()
        .sort_values("date", ascending=False)
        .head(n_days)
    )
    return counts


def check_station_coverage(df: pd.DataFrame) -> dict:
    """Station-level coverage in last 24h."""
    df = df.copy()
    last24 = df[df["ts"] >= df["ts"].max() - pd.Timedelta(hours=24)]
    by_station = last24.groupby("station_id").size().sort_values(ascending=True)
    silent_stations = list(by_station[by_station < 50].index)  # <50 rows in 24h = suspicious (expect ~96)
    return {
        "stations_seen_last_24h": len(by_station),
        "min_rows_per_station": int(by_station.min()) if len(by_station) > 0 else 0,
        "max_rows_per_station": int(by_station.max()) if len(by_station) > 0 else 0,
        "silent_stations": silent_stations,
    }


def health_verdict(wbgt: dict, loop: dict, station: dict) -> tuple[str, list[str]]:
    """GREEN/YELLOW/RED with reasoning."""
    issues = []

    # Loop failures
    if "error" not in loop:
        if loop["last_50_fail"] >= 5:
            issues.append(f"RED: {loop['last_50_fail']}/50 recent loop runs failed")
        elif loop["last_50_fail"] >= 2:
            issues.append(f"YELLOW: {loop['last_50_fail']}/50 recent loop runs failed")
    else:
        issues.append(f"YELLOW: {loop['error']}")

    # NaT rows (should be 0 after rebuild; growing again = NEA schema issue)
    if wbgt.get("nat_count", 0) > 0:
        issues.append(f"YELLOW: {wbgt['nat_count']} NaT rows in WBGT archive (re-run rebuild_normalized)")

    # Station count
    if wbgt.get("stations", 0) < EXPECTED_STATIONS:
        issues.append(f"YELLOW: only {wbgt['stations']} stations seen ({EXPECTED_STATIONS} expected)")

    # Silent stations (collecting <50% of expected rows in 24h)
    if station.get("silent_stations"):
        issues.append(f"YELLOW: stations under-reporting last 24h: {station['silent_stations']}")

    # Last obs lag (if last_obs > 90 min ago, loop probably stopped)
    if "last_obs" in wbgt:
        last_obs = wbgt["last_obs"]
        # Strip tz for comparison; we treat both as naive SGT.
        try:
            now_sgt = datetime.utcnow() + timedelta(hours=8)
            if last_obs.tzinfo is not None:
                last_obs = last_obs.tz_localize(None) if hasattr(last_obs, "tz_localize") else last_obs.replace(tzinfo=None)
            lag_min = (now_sgt - last_obs).total_seconds() / 60.0
            if lag_min > 90:
                issues.append(f"RED: latest WBGT obs is {lag_min:.0f} min ago (loop may be stopped)")
            elif lag_min > 30:
                issues.append(f"YELLOW: latest WBGT obs is {lag_min:.0f} min ago")
        except Exception:
            pass  # Best-effort; don't crash on tz weirdness.

    if not issues:
        return "GREEN", ["All core checks passed."]
    if any(s.startswith("RED:") for s in issues):
        return "RED", issues
    return "YELLOW", issues


def main() -> int:
    header(f"OpenHeat v1.1 archive health check  -  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    section("Archive size & growth")
    wbgt = check_wbgt_archive()
    if "error" in wbgt:
        print(f"  ERROR: {wbgt['error']}")
        return 1
    print(f"  WBGT total rows:        {wbgt['rows']:>10,}")
    print(f"  Unique stations:        {wbgt['stations']:>10}")
    print(f"  Unique timestamps:      {wbgt['unique_timestamps']:>10,}")
    print(f"  Time span:              {wbgt['span_days']:>10.2f} days  ({wbgt['span_hours']:.1f} h)")
    print(f"  First obs:              {wbgt['first_obs']}")
    print(f"  Last obs:               {wbgt['last_obs']}")
    print(f"  Rows in last 24h:       {wbgt['rows_last_24h']:>10,}  (expected ~{EXPECTED_ROWS_PER_DAY:,})")
    print(f"  Rows in last 7d:        {wbgt['rows_last_7d']:>10,}  (expected ~{EXPECTED_ROWS_PER_DAY*7:,})")
    print(f"  NaT timestamp rows:     {wbgt['nat_count']:>10}")

    section("Per-day WBGT row counts (last 7 days)")
    daily = check_per_day(wbgt["df"], n_days=7)
    if not daily.empty:
        print(daily.to_string(index=False))
    else:
        print("  No daily data.")

    section("Station coverage in last 24h")
    station = check_station_coverage(wbgt["df"])
    print(f"  Stations seen:          {station['stations_seen_last_24h']}")
    print(f"  Rows/station range:     {station['min_rows_per_station']} to {station['max_rows_per_station']}  (expect ~96)")
    if station["silent_stations"]:
        print(f"  ⚠️  Silent stations:     {station['silent_stations']}")
    else:
        print(f"  All stations active.")

    section("Loop runs (last 50)")
    loop = check_loop_log()
    if "error" in loop:
        print(f"  {loop['error']}")
    else:
        print(f"  Total runs logged:      {loop['total_runs_logged']}")
        print(f"  Last 50: {loop['last_50_success']} success, {loop['last_50_fail']} fail")
        print(f"  Last 3 log lines:")
        for ln in loop["last_3_lines"]:
            print(f"    {ln}")

    section("Latest run errors/warnings")
    if LATEST_QA.exists():
        text = LATEST_QA.read_text(errors="ignore")
        # Extract the "Fetch warnings / errors" section if present
        if "## Fetch warnings / errors" in text:
            start = text.index("## Fetch warnings / errors")
            end_candidates = [text.find(s, start + 1) for s in ["\n## ", "\n# "]]
            end_candidates = [e for e in end_candidates if e > 0]
            end = min(end_candidates) if end_candidates else len(text)
            print(text[start:end].strip())
        else:
            print("  (no Fetch warnings/errors section found in latest QA)")
    else:
        print(f"  Latest QA report not found: {LATEST_QA}")

    # Verdict
    section("Health verdict")
    verdict, issues = health_verdict(wbgt, loop, station)
    icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}[verdict]
    print(f"  {icon}  {verdict}")
    for s in issues:
        print(f"     - {s}")

    print()
    print("=" * 70)
    return 0 if verdict == "GREEN" else (1 if verdict == "RED" else 0)


if __name__ == "__main__":
    sys.exit(main())
