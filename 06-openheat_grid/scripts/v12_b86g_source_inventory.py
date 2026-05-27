"""Inventory B8.6g compact/vector inputs and safe source candidates.

Inputs:
    configs/v12/systemb_b86g_feature_acquisition.yaml plus the compact CSV,
    Markdown, JSON, and GeoJSON paths declared or discovered there.
Outputs:
    b86g_input_inventory.csv, b86g_source_inventory.csv,
    b86g_vector_source_readiness.csv, and
    b86g_compact_source_readiness.csv.
Saved metrics:
    Required input existence/schema checks, allowed compact/vector source
    discovery, safe row/column/property counts where possible, likely source
    roles, read/safety status, and vector CRS/geometry metadata when readable.
    The inventory never opens raster-like files, svfs.zip, raw archive roots,
    QGIS roots, SOLWEIG roots, or raster metadata tables.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "v12" / "systemb_b86g_feature_acquisition.yaml"
CLAIM_BOUNDARY = (
    "B8.6g compact/vector feature acquisition only; not B9, not AOI-wide prediction, "
    "not local WBGT, not hazard_score or risk_score, not observed truth, not causal "
    "feature importance, no raster, no QGIS/SOLWEIG, no Tmrt-to-WBGT conversion, "
    "and no System A/B coupling."
)

REQUIRED_INPUT_KEYS = [
    "b86f_feature_acquisition_register_path",
    "b86f_feature_acquisition_spec_path",
    "b86f_n300_v2_path",
    "b86f_failure_synthesis_path",
    "b86f_anchor_neutral_matrix_path",
    "b86d_oof_predictions_path",
    "b86d_combined_metrics_path",
    "b86d_anchor_diagnostics_path",
    "b86d_neutral_diagnostics_path",
    "n150_feature_matrix_path",
    "candidate_universe_path",
    "f5_pairwise_label_path",
]

REQUIRED_COLUMNS = {
    "b86f_feature_acquisition_register_path": ["feature_family", "priority", "minimum_output_schema"],
    "b86f_n300_v2_path": ["cell_id", "primary_role", "spatial_bin", "typology"],
    "b86f_failure_synthesis_path": ["failure_mode", "affected_bins_or_cells", "next_action"],
    "b86f_anchor_neutral_matrix_path": ["cell_id", "diagnostic_role", "failure_type", "severity"],
    "b86d_oof_predictions_path": ["cell_id", "split_family", "true_delta", "pred_combined_delta"],
    "b86d_combined_metrics_path": ["feature_set", "split_family", "MAE", "top10pct_overlap"],
    "b86d_anchor_diagnostics_path": ["cell_id", "split_family", "MAE", "failure_type"],
    "b86d_neutral_diagnostics_path": ["cell_id", "split_family", "false_promotion_rate", "failure_type"],
    "n150_feature_matrix_path": ["cell_id", "centroid_x", "centroid_y", "typology_label"],
    "candidate_universe_path": ["cell_id", "centroid_x", "centroid_y", "typology_label"],
    "f5_pairwise_label_path": ["cell_id", "forcing_day_id", "hour_sgt", "delta_tmrt_p90_c"],
}

FORBIDDEN_EXTENSIONS = {".tif", ".tiff", ".vrt", ".asc", ".img", ".nc", ".grib"}
ALLOWED_EXTENSIONS = {".csv", ".csv.gz", ".parquet", ".geojson", ".gpkg", ".shp", ".json", ".md"}
SKIP_PARTS = {"solweig", "qgis", "rasters", "archive"}
SKIP_NAME_TOKENS = {"raster", "svfs.zip", "hourly_grid_heatstress_forecast"}
MAX_METADATA_BYTES = 30_000_000


@dataclass(frozen=True)
class SourceInventoryResult:
    """B8.6g input and source inventory result."""

    status: str
    inputs_checked: int
    missing_inputs: int
    schema_errors: int
    sources_scanned: int
    usable_sources: int


def repo_path(path: str | Path) -> Path:
    """Resolve a project-relative path under the OpenHeat subdirectory."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def parse_scalar(value: str) -> Any:
    """Parse a tiny YAML scalar subset used by the B8.6g config."""
    raw = value.strip()
    if raw == "":
        return ""
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if raw.startswith("[") and raw.endswith("]"):
        body = raw[1:-1].strip()
        return [part.strip().strip("'\"") for part in body.split(",") if part.strip()]
    try:
        if "." not in raw:
            return int(raw)
        return float(raw)
    except ValueError:
        return raw.strip("'\"")


def load_config(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load the B8.6g YAML config without requiring PyYAML."""
    resolved = repo_path(config_path)
    config: dict[str, Any] = {}
    for line in resolved.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("- "):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.startswith(" "):
            continue
        config[key.strip()] = parse_scalar(value)
    if not config:
        raise ValueError(f"B8.6g config did not parse as a flat mapping: {resolved}")
    return config


def config_list(config: dict[str, Any], key: str, default: Sequence[str] | None = None) -> list[str]:
    """Return a pipe-delimited config value as a list."""
    value = config.get(key)
    if value is None:
        return list(default or [])
    if isinstance(value, list):
        return [str(item) for item in value]
    return [part.strip() for part in str(value).split("|") if part.strip()]


def output_path(config: dict[str, Any], key: str) -> Path:
    """Resolve an output path by flat config key."""
    return repo_path(str(config[key]))


def ensure_output_dir(config: dict[str, Any]) -> Path:
    """Create and return the B8.6g output directory."""
    out_dir = repo_path(str(config["output_dir"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def read_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read a compact CSV while preserving cell_id strings."""
    options = {"dtype": {"cell_id": "string"}, "low_memory": False}
    options.update(kwargs)
    return pd.read_csv(repo_path(path), **options)


def write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    """Write UTF-8 CSV with stable parent creation."""
    destination = repo_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, encoding="utf-8")


def write_text(text: str, path: str | Path) -> None:
    """Write UTF-8 text with LF line endings."""
    destination = repo_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="\n")


def extension_key(path: Path) -> str:
    """Return .csv.gz for gzip CSVs, otherwise the normal suffix."""
    suffixes = [suffix.lower() for suffix in path.suffixes]
    if len(suffixes) >= 2 and suffixes[-2:] == [".csv", ".gz"]:
        return ".csv.gz"
    return path.suffix.lower()


def safe_rel(path: Path) -> str:
    """Return a stable project-relative path string when possible."""
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def is_under_forbidden_root(path: Path) -> bool:
    """Return true if a path belongs to a root that must not be read."""
    rel_parts = [part.lower() for part in safe_rel(path).split("/")]
    if len(rel_parts) >= 2 and rel_parts[0] == "data" and rel_parts[1] in {"solweig", "rasters", "archive"}:
        return True
    if "raw" in rel_parts and "buildings_v10" in rel_parts:
        return True
    if any(part in {"qgis"} for part in rel_parts):
        return True
    return False


def safety_status(path: Path) -> str:
    """Classify whether a source can be inspected safely in B8.6g."""
    ext = extension_key(path)
    name = path.name.lower()
    rel = safe_rel(path).lower()
    if ext in FORBIDDEN_EXTENSIONS:
        return "FORBIDDEN_RASTER_EXTENSION"
    if name == "svfs.zip":
        return "FORBIDDEN_SVFS_ZIP"
    if is_under_forbidden_root(path):
        return "SKIPPED_FORBIDDEN_ROOT"
    if any(token in rel for token in SKIP_NAME_TOKENS):
        return "SKIPPED_FORBIDDEN_METADATA_NAME"
    if "solweig" in rel and not rel.startswith("docs/") and not rel.startswith("configs/"):
        return "SKIPPED_SOLWEIG_OUTPUT_OR_ROOT"
    if "qgis" in rel:
        return "SKIPPED_QGIS_REFERENCE"
    if ext not in ALLOWED_EXTENSIONS:
        return "SKIPPED_EXTENSION_NOT_ALLOWED"
    return "SAFE_TO_INSPECT"


def safe_file_size(path: Path) -> int | None:
    """Return file size if available."""
    try:
        return path.stat().st_size
    except OSError:
        return None


def csv_columns_and_rows(path: Path) -> tuple[list[str], int | None, str]:
    """Read CSV header and count rows when safe."""
    try:
        opener = gzip.open if extension_key(path) == ".csv.gz" else open
        mode = "rt"
        with opener(path, mode, encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            columns = next(reader, [])
            row_count = sum(1 for _ in reader)
        return columns, row_count, "READ_OK"
    except Exception as exc:  # pragma: no cover - defensive inventory guard
        return [], None, f"READ_FAILED:{type(exc).__name__}"


def json_metadata(path: Path) -> tuple[list[str], int | None, str, str, str]:
    """Read safe JSON/GeoJSON property and geometry metadata."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
            features = payload.get("features") or []
            columns: set[str] = set()
            geometry_types: set[str] = set()
            for feature in features[:5000]:
                if not isinstance(feature, dict):
                    continue
                properties = feature.get("properties") or {}
                if isinstance(properties, dict):
                    columns.update(str(key) for key in properties.keys())
                geometry = feature.get("geometry") or {}
                if isinstance(geometry, dict) and geometry.get("type"):
                    geometry_types.add(str(geometry["type"]))
            crs = ""
            if isinstance(payload.get("crs"), dict):
                crs = json.dumps(payload["crs"], ensure_ascii=False)
            return sorted(columns), len(features), "|".join(sorted(geometry_types)), crs, "READ_OK"
        if isinstance(payload, list):
            columns = sorted({str(key) for row in payload[:500] if isinstance(row, dict) for key in row.keys()})
            return columns, len(payload), "", "", "READ_OK"
        if isinstance(payload, dict):
            return sorted(str(key) for key in payload.keys()), 1, "", "", "READ_OK"
        return [], None, "", "", "READ_OK_EMPTY_OR_SCALAR"
    except Exception as exc:  # pragma: no cover - defensive inventory guard
        return [], None, "", "", f"READ_FAILED:{type(exc).__name__}"


def inspect_source(path: Path) -> dict[str, Any]:
    """Inspect one source candidate without violating B8.6g guardrails."""
    ext = extension_key(path)
    size = safe_file_size(path)
    safety = safety_status(path)
    columns: list[str] = []
    row_count: int | None = None
    geometry_type = ""
    crs = ""
    read_status = "NOT_READ"
    if safety == "SAFE_TO_INSPECT" and size is not None and size <= MAX_METADATA_BYTES:
        if ext in {".csv", ".csv.gz"}:
            columns, row_count, read_status = csv_columns_and_rows(path)
        elif ext in {".json", ".geojson"}:
            columns, row_count, geometry_type, crs, read_status = json_metadata(path)
        elif ext == ".md":
            read_status = "TEXT_METADATA_ONLY"
        elif ext in {".parquet", ".gpkg", ".shp"}:
            read_status = "METADATA_ONLY_NO_VECTOR_ENGINE"
    elif safety == "SAFE_TO_INSPECT":
        read_status = "METADATA_ONLY_LARGE_FILE"
    return {
        "path": safe_rel(path),
        "extension": ext,
        "file_size_bytes": size,
        "row_count": row_count,
        "column_count": len(columns) if columns else None,
        "geometry_type": geometry_type,
        "crs": crs,
        "columns": "|".join(columns),
        "likely_role": likely_role(path, columns, geometry_type),
        "read_status": read_status,
        "safety_status": safety,
    }


def likely_role(path: Path, columns: Sequence[str], geometry_type: str = "") -> str:
    """Assign a broad B8.6g source role from path and column hints."""
    text = f"{safe_rel(path)} {' '.join(columns)} {geometry_type}".lower()
    if "anchor_neutral" in text or "failure" in text or "diagnostic" in text:
        return "failure_context"
    if "grid" in text and ("cell_id" in text or "polygon" in text or "centroid" in text):
        return "cell_grid_geometry"
    if "overhead" in text or "covered_walkway" in text or "pedestrian_bridge" in text or "viaduct" in text:
        return "overhead_vector"
    if "walkway" in text or "footpath" in text or "pedestrian" in text:
        return "walkway_or_pedestrian_network"
    if "shelter" in text or "covered" in text:
        return "covered_walkway"
    if "building" in text or "height" in text or "dsm" in text:
        return "building_footprint_height"
    if "tree" in text or "canopy" in text or "gvi" in text or "ndvi" in text:
        return "tree_canopy"
    if "water" in text or "river" in text:
        return "water_edge"
    if "road" in text or "hardscape" in text or "impervious" in text:
        return "road_or_hardscape"
    if "park" in text or "grass" in text or "green" in text:
        return "park_green"
    if "feature" in text and "cell_id" in text:
        return "compact_existing_feature_table"
    return "unusable_or_unknown"


def discover_candidate_paths(config: dict[str, Any]) -> list[Path]:
    """Discover allowed-extension source paths under configured roots."""
    roots = config_list(config, "source_discovery_roots")
    allowed = set(config_list(config, "allowed_extensions", sorted(ALLOWED_EXTENSIONS)))
    output_dir_rel = str(config.get("output_dir", "")).replace("\\", "/").strip("/")
    paths: dict[str, Path] = {}
    for root_text in roots:
        root = repo_path(root_text)
        if not root.exists():
            continue
        if root.is_file():
            candidates = [root]
        else:
            candidates = [path for path in root.rglob("*") if path.is_file()]
        for path in candidates:
            rel = safe_rel(path).replace("\\", "/")
            if output_dir_rel and (rel == output_dir_rel or rel.startswith(f"{output_dir_rel}/")):
                continue
            ext = extension_key(path)
            if ext in allowed or ext in FORBIDDEN_EXTENSIONS or path.name.lower() == "svfs.zip":
                paths[safe_rel(path)] = path
    return [paths[key] for key in sorted(paths)]


def input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Create the required compact input inventory."""
    rows: list[dict[str, Any]] = []
    for key in REQUIRED_INPUT_KEYS:
        configured = config.get(key, "")
        path = repo_path(str(configured)) if configured else PROJECT_ROOT / "__missing__"
        exists = path.exists()
        ext = extension_key(path)
        safety = safety_status(path) if exists else "MISSING"
        columns: list[str] = []
        row_count: int | None = None
        read_status = "MISSING"
        if exists and safety == "SAFE_TO_INSPECT" and ext in {".csv", ".csv.gz"}:
            columns, row_count, read_status = csv_columns_and_rows(path)
        elif exists and safety == "SAFE_TO_INSPECT" and ext == ".md":
            read_status = "TEXT_METADATA_ONLY"
        elif exists:
            read_status = "METADATA_ONLY"
        required = REQUIRED_COLUMNS.get(key, [])
        missing_cols = [column for column in required if column not in columns] if columns else ([] if ext == ".md" else required)
        rows.append(
            {
                "input_key": key,
                "path": safe_rel(path),
                "exists": exists,
                "extension": ext,
                "file_size_bytes": safe_file_size(path) if exists else None,
                "row_count": row_count,
                "column_count": len(columns) if columns else None,
                "required_columns": "|".join(required),
                "missing_required_columns": "|".join(missing_cols),
                "read_status": read_status,
                "safety_status": safety,
            }
        )
    return pd.DataFrame(rows)


def summarize_readiness(source_inventory: pd.DataFrame, roles: Iterable[str]) -> pd.DataFrame:
    """Summarize source readiness by broad role."""
    rows: list[dict[str, Any]] = []
    for role in roles:
        subset = source_inventory.loc[source_inventory["likely_role"].astype(str).eq(role)]
        safe_subset = subset.loc[subset["safety_status"].astype(str).eq("SAFE_TO_INSPECT")]
        readable = safe_subset.loc[safe_subset["read_status"].astype(str).str.contains("READ_OK|TEXT_METADATA_ONLY|METADATA_ONLY", regex=True)]
        rows.append(
            {
                "likely_role": role,
                "candidate_sources": len(subset),
                "safe_sources": len(safe_subset),
                "readable_sources": len(readable),
                "best_source_path": readable["path"].iloc[0] if not readable.empty else "",
                "readiness_status": "AVAILABLE" if not readable.empty else "NOT_AVAILABLE",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> SourceInventoryResult:
    """Run B8.6g input and source inventory."""
    config = load_config(config_path)
    ensure_output_dir(config)
    inputs = input_inventory(config)
    source_rows = [inspect_source(path) for path in discover_candidate_paths(config)]
    sources = pd.DataFrame(source_rows)
    if sources.empty:
        sources = pd.DataFrame(
            columns=[
                "path",
                "extension",
                "file_size_bytes",
                "row_count",
                "column_count",
                "geometry_type",
                "crs",
                "columns",
                "likely_role",
                "read_status",
                "safety_status",
            ]
        )
    vector_roles = [
        "cell_grid_geometry",
        "overhead_vector",
        "walkway_or_pedestrian_network",
        "covered_walkway",
        "building_footprint_height",
        "tree_canopy",
        "water_edge",
        "road_or_hardscape",
        "park_green",
    ]
    compact_roles = ["compact_existing_feature_table", "failure_context", "unusable_or_unknown"]
    write_csv(inputs, output_path(config, "input_inventory_path"))
    write_csv(sources, output_path(config, "source_inventory_path"))
    write_csv(summarize_readiness(sources, vector_roles), output_path(config, "vector_source_readiness_path"))
    write_csv(summarize_readiness(sources, compact_roles), output_path(config, "compact_source_readiness_path"))
    missing_inputs = int((~inputs["exists"].astype(bool)).sum()) if not inputs.empty else len(REQUIRED_INPUT_KEYS)
    schema_errors = int(inputs["missing_required_columns"].fillna("").astype(str).str.len().gt(0).sum())
    usable_sources = int(
        sources["safety_status"].astype(str).eq("SAFE_TO_INSPECT").astype(int).sum()
        if not sources.empty
        else 0
    )
    status = "B86G_INPUT_READY" if missing_inputs == 0 and schema_errors == 0 else "B86G_BLOCKED_INPUT"
    return SourceInventoryResult(
        status=status,
        inputs_checked=len(inputs),
        missing_inputs=missing_inputs,
        schema_errors=schema_errors,
        sources_scanned=len(sources),
        usable_sources=usable_sources,
    )


def as_float(value: Any) -> float:
    """Coerce values to float while preserving NaN on failure."""
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Inventory B8.6g compact/vector feature sources.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
