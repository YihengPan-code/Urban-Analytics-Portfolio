#!/usr/bin/env python3
"""Run one GitHub Actions-safe OpenHeat v1.1 archive collection.

Inputs
------
- ``--config``: GHA wrapper config JSON. The config points to the existing
  collector config and declares controlled output directories.
- Optional API keys are read by the underlying collector from environment
  variables such as ``DATA_GOV_SG_API_KEY``.

Outputs
-------
- ``data/calibration/v11/live_chunks/wbgt_pairs_YYYY-MM-DD.csv.gz``: compact
  station-weather paired rows, deduplicated by ``station_id`` and
  ``valid_timestamp``.
- ``outputs/v11_archive_ops/gha_run_manifest_YYYYMMDD.csv`` and per-run JSON:
  scheduled/start/end timestamps, source, row counts, stations, warnings, and
  exit code.

Saved metrics
-------------
The run manifest records ``rows_fetched``, ``rows_added``, ``stations_seen``,
``warnings``, ``api_status``, ``exit_code``, and the GitHub commit SHA. GitHub
Actions is treated as best-effort archive continuity, not strict sensor-grade
15-minute cadence.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_CONFIG = Path("configs/v11/v11_archive_gha_config.example.json")


@dataclass(frozen=True)
class GhaManifest:
    run_id: str
    scheduled_at_utc: str
    started_at_utc: str
    completed_at_utc: str
    source: str
    exit_code: int
    rows_fetched: int
    rows_added: int
    stations_seen: int
    station_ids_seen: list[str]
    warnings: list[str]
    api_status: str
    commit_sha: str
    chunk_path: str | None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_id_from_started(started_at_utc: str) -> str:
    safe = started_at_utc.replace("-", "").replace(":", "").replace("+00:00", "Z")
    safe = safe.replace("Z", "").replace("T", "_")
    return f"gha_{safe}Z"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_valid_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "valid_timestamp" not in out.columns:
        if "timestamp_sgt" in out.columns:
            out["valid_timestamp"] = out["timestamp_sgt"]
        elif "timestamp_utc" in out.columns:
            out["valid_timestamp"] = out["timestamp_utc"]
        elif "valid_time_sgt" in out.columns:
            out["valid_timestamp"] = out["valid_time_sgt"]
        else:
            raise ValueError("Pair table has no timestamp_sgt/timestamp_utc/valid_time_sgt column.")
    out["station_id"] = out["station_id"].astype(str)
    out["valid_timestamp"] = out["valid_timestamp"].astype(str)
    return out


def append_live_chunk(chunk_path: Path, pairs: pd.DataFrame) -> tuple[int, int]:
    pairs = normalize_valid_timestamp(pairs)
    before_keys: set[tuple[str, str]] = set()
    if chunk_path.exists():
        old = pd.read_csv(chunk_path, low_memory=False)
        old = normalize_valid_timestamp(old)
        before_keys = set(zip(old["station_id"], old["valid_timestamp"]))
        combined = pd.concat([old, pairs], ignore_index=True, sort=False)
    else:
        combined = pairs

    combined = normalize_valid_timestamp(combined)
    combined = combined.drop_duplicates(["station_id", "valid_timestamp"], keep="last")
    after_keys = set(zip(combined["station_id"], combined["valid_timestamp"]))
    rows_added = len(after_keys - before_keys)
    chunk_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(chunk_path, index=False, compression="gzip")
    return len(pairs), rows_added


def append_manifest_csv(path: Path, manifest: GhaManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = asdict(manifest)
    row["station_ids_seen"] = json.dumps(row["station_ids_seen"], ensure_ascii=False)
    row["warnings"] = json.dumps(row["warnings"], ensure_ascii=False)
    frame = pd.DataFrame([row])
    if path.exists():
        old = pd.read_csv(path)
        frame = pd.concat([old, frame], ignore_index=True, sort=False)
        frame = frame.drop_duplicates(["run_id"], keep="last")
    frame.to_csv(path, index=False)


def build_collector_config(wrapper_cfg: dict[str, Any], tmp_root: Path) -> dict[str, Any]:
    base_path = Path(wrapper_cfg.get("base_collector_config", "configs/v11/v11_longterm_archive_config.example.json"))
    collector_cfg = read_json(base_path)

    archive_cfg = collector_cfg.setdefault("archive", {})
    archive_cfg.update(
        {
            "root_dir": str(tmp_root / "archive_root"),
            "raw_json_dir": str(tmp_root / "raw_json"),
            "outputs_dir": str(tmp_root / "collector_outputs"),
            "state_path": str(tmp_root / "archive_state.json"),
            "save_raw_json": False,
            "write_daily_partitions": False,
            "run_label_prefix": "v11_gha",
        }
    )

    collector_overrides = wrapper_cfg.get("collector_overrides", {})
    for section, values in collector_overrides.items():
        if isinstance(values, dict):
            collector_cfg.setdefault(section, {}).update(values)

    pairing_cfg = collector_cfg.setdefault("pairing", {})
    pairing_cfg["output_operational_pairs_csv"] = str(tmp_root / "paired" / "v11_operational_station_weather_pairs.csv")
    pairing_cfg["output_latest_pairs_csv"] = str(tmp_root / "latest" / "v11_station_weather_pairs.csv")
    return collector_cfg


def write_manifest_outputs(ops_dir: Path, manifest: GhaManifest) -> None:
    day = manifest.started_at_utc[:10].replace("-", "")
    write_json(ops_dir / f"gha_run_manifest_{manifest.run_id}.json", asdict(manifest))
    write_json(ops_dir / "gha_run_manifest_latest.json", asdict(manifest))
    append_manifest_csv(ops_dir / f"gha_run_manifest_{day}.csv", manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    started_at = utc_now_iso()
    scheduled_at = os.getenv("OPENHEAT_SCHEDULED_AT_UTC") or started_at
    run_id = run_id_from_started(started_at)
    wrapper_cfg = read_json(args.config)
    outputs_cfg = wrapper_cfg.get("outputs", {})
    ops_dir = Path(outputs_cfg.get("ops_dir", "outputs/v11_archive_ops"))
    live_chunk_dir = Path(outputs_cfg.get("live_chunk_dir", "data/calibration/v11/live_chunks"))
    chunk_path = live_chunk_dir / f"wbgt_pairs_{started_at[:10]}.csv.gz"

    warnings: list[str] = []
    rows_fetched = 0
    rows_added = 0
    station_ids: list[str] = []
    exit_code = 0

    try:
        with tempfile.TemporaryDirectory(prefix="openheat_v11_gha_") as tmp:
            from v11_archive_collect_once import collect_once

            collector_cfg = build_collector_config(wrapper_cfg, Path(tmp))
            result = collect_once(collector_cfg)
            warnings.extend(str(w) for w in result.get("errors", []))
            pairs_path = Path(collector_cfg["pairing"]["output_latest_pairs_csv"])
            if not pairs_path.exists():
                raise FileNotFoundError(f"Collector did not write pair table: {pairs_path}")
            pairs = pd.read_csv(pairs_path, low_memory=False)
            if pairs.empty:
                warnings.append("collector produced zero paired rows")
            else:
                pairs = normalize_valid_timestamp(pairs)
                station_ids = sorted(pairs["station_id"].dropna().astype(str).unique().tolist())
                rows_fetched, rows_added = append_live_chunk(chunk_path, pairs)
    except Exception as exc:  # Manifest still records failures for ops diagnosis.
        exit_code = 1
        warnings.append(f"{type(exc).__name__}: {exc}")
        warnings.append(traceback.format_exc(limit=5))

    completed_at = utc_now_iso()
    api_status = "ok" if exit_code == 0 and not warnings else ("error" if exit_code else "warn")
    manifest = GhaManifest(
        run_id=run_id,
        scheduled_at_utc=scheduled_at,
        started_at_utc=started_at,
        completed_at_utc=completed_at,
        source=os.getenv("OPENHEAT_RUN_SOURCE", "gha"),
        exit_code=exit_code,
        rows_fetched=int(rows_fetched),
        rows_added=int(rows_added),
        stations_seen=len(station_ids),
        station_ids_seen=station_ids,
        warnings=warnings,
        api_status=api_status,
        commit_sha=os.getenv("GITHUB_SHA", ""),
        chunk_path=str(chunk_path) if chunk_path.exists() else None,
    )
    write_manifest_outputs(ops_dir, manifest)
    print(json.dumps(asdict(manifest), ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
