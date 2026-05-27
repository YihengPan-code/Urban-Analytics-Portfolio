"""Inventory B8.7-N300-PRE compact inputs.

Inputs:
    configs/v12/systemb_b87_n300_pre.yaml and all compact CSV/Markdown
    context paths declared there.
Outputs:
    outputs/v12_surrogate/b8_7_n300_pre/b87_input_inventory.csv.
Saved metrics:
    Input existence, size, row count, column count, required-schema checks,
    current N150 label cell source status, and guardrail flags. The inventory
    does not read raster-like files, raw SOLWEIG outputs, raw archive dumps,
    QGIS runners, AOI-wide predictions, B9 outputs, local WBGT, hazard/risk
    scores, observed-truth sources, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "v12" / "systemb_b87_n300_pre.yaml"
CLAIM_BOUNDARY = (
    "B8.7-N300-PRE design/source review only; not B9, not AOI-wide prediction, "
    "not local WBGT, not hazard_score or risk_score, not observed truth, not "
    "causal feature importance, no raster, no QGIS/SOLWEIG, no N300 execution "
    "manifest, no Tmrt-to-WBGT conversion, and no System A/B coupling."
)

REQUIRED_INPUT_KEYS = [
    "b86f_n300_v2_path",
    "b86g_n300_feature_dataset_path",
    "b86g_feature_schema_path",
    "b86g_feature_coverage_matrix_path",
    "b86g_feature_gap_closure_matrix_path",
    "b86g_failure_context_join_path",
    "b86g2_baseline_comparison_path",
    "b86g2_aoi_readiness_path",
    "n150_feature_matrix_path",
    "candidate_universe_path",
]

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "b86f_n300_v2_path": [
        "cell_id",
        "selected_priority_rank",
        "primary_role",
        "secondary_roles",
        "rationale",
        "spatial_bin",
        "typology",
        "nearest_anchor_cell",
        "nearest_neutral_cell",
        "nearest_n150_distance",
        "nearest_n150_distance_percentile",
        "coverage_gap",
        "expected_learning_value",
        "sampling_boundary",
        "claim_boundary",
    ],
    "b86g_n300_feature_dataset_path": ["cell_id", "feature_version"],
    "b86g_feature_schema_path": [
        "feature_name",
        "feature_family",
        "source_type",
        "proxy_flag",
        "claim_boundary",
    ],
    "b86g_feature_coverage_matrix_path": ["feature_family", "n300_coverage_fraction", "source_status", "proxy_status"],
    "b86g_feature_gap_closure_matrix_path": ["gap_family", "closure_status", "recommended_next_lane"],
    "b86g_failure_context_join_path": ["row_type", "cell_id", "diagnostic_role", "feature_family_coverage_fraction"],
    "b86g2_baseline_comparison_path": ["split_family", "b86g2_Spearman", "b86g2_top10pct_overlap"],
    "b86g2_aoi_readiness_path": ["readiness_item", "status", "evidence"],
    "n150_feature_matrix_path": ["cell_id"],
    "candidate_universe_path": ["cell_id", "typology_label"],
    "n150_selected_cells_path": ["cell_id"],
    "b86g_n150_feature_dataset_path": ["cell_id", "feature_version"],
}

FORBIDDEN_EXTENSIONS = {".tif", ".tiff", ".vrt", ".asc", ".img", ".nc", ".grib"}
DEFAULT_ALLOWED_EXTENSIONS = {".csv", ".csv.gz", ".parquet", ".geojson", ".gpkg", ".shp", ".json", ".md"}
SOURCE_SKIP_TOKENS = {
    "svfs.zip",
    "hourly_grid_heatstress_forecast",
    "forecast_live",
    "raster",
}


@dataclass(frozen=True)
class InputInventoryResult:
    """B8.7 input inventory result."""

    status: str
    inputs_checked: int
    missing_inputs: int
    schema_errors: int
    current_n150_label_cells: int


def repo_path(path: str | Path) -> Path:
    """Resolve a project-relative path under the OpenHeat subdirectory."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def safe_rel(path: str | Path) -> str:
    """Return a stable project-relative POSIX path when possible."""
    resolved = repo_path(path)
    try:
        return resolved.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def parse_scalar(value: str) -> Any:
    """Parse a small YAML scalar fallback value."""
    raw = value.strip()
    if raw == "":
        return ""
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        if "." not in raw:
            return int(raw)
        return float(raw)
    except ValueError:
        return raw.strip("'\"")


def load_config(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load the explicit B8.7 YAML config."""
    resolved = repo_path(config_path)
    try:
        import yaml  # type: ignore

        payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    config: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in resolved.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            if value.strip():
                config[key] = parse_scalar(value)
                current_key = None
            else:
                config[key] = {}
                current_key = key
            continue
        if current_key is None:
            continue
        if stripped.startswith("- "):
            if not isinstance(config[current_key], list):
                config[current_key] = []
            config[current_key].append(parse_scalar(stripped[2:]))
        elif ":" in stripped:
            if not isinstance(config[current_key], dict):
                config[current_key] = {}
            key, value = stripped.split(":", 1)
            config[current_key][key.strip()] = parse_scalar(value)
    if not config:
        raise ValueError(f"B8.7 config did not parse: {resolved}")
    return config


def config_list(config: dict[str, Any], key: str, default: Sequence[str] | None = None) -> list[str]:
    """Return a config value as a list of strings."""
    value = config.get(key)
    if value is None:
        return list(default or [])
    if isinstance(value, list):
        return [str(item) for item in value]
    return [part.strip() for part in str(value).split("|") if part.strip()]


def output_path(config: dict[str, Any], key: str) -> Path:
    """Resolve a configured output path."""
    return repo_path(str(config[key]))


def ensure_output_dir(config: dict[str, Any]) -> Path:
    """Create and return the B8.7 compact output directory."""
    out_dir = repo_path(str(config["output_dir"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def extension_key(path: str | Path) -> str:
    """Return .csv.gz for gzip CSVs, otherwise the normal suffix."""
    suffixes = [suffix.lower() for suffix in repo_path(path).suffixes]
    if len(suffixes) >= 2 and suffixes[-2:] == [".csv", ".gz"]:
        return ".csv.gz"
    return repo_path(path).suffix.lower()


def is_forbidden_root(path: str | Path, config: dict[str, Any] | None = None) -> bool:
    """Return true when a path belongs to a root that this lane must not read."""
    rel = safe_rel(path).lower().replace("\\", "/")
    forbidden_roots = config_list(config or {}, "forbidden_roots", ["data/solweig", "data/rasters", "data/archive"])
    return any(rel == root.lower().strip("/") or rel.startswith(f"{root.lower().strip('/')}/") for root in forbidden_roots)


def safety_status(path: str | Path, config: dict[str, Any] | None = None) -> str:
    """Classify file inspection safety under B8.7 guardrails."""
    resolved = repo_path(path)
    ext = extension_key(resolved)
    rel = safe_rel(resolved).lower()
    name = resolved.name.lower()
    if ext in FORBIDDEN_EXTENSIONS:
        return "FORBIDDEN_RASTER_EXTENSION"
    if name == "svfs.zip":
        return "FORBIDDEN_SVFS_ZIP"
    if is_forbidden_root(resolved, config):
        return "SKIPPED_FORBIDDEN_ROOT"
    if any(token in rel for token in SOURCE_SKIP_TOKENS):
        return "SKIPPED_FORBIDDEN_NAME_OR_LOCAL_OUTPUT"
    if "solweig" in rel and not rel.startswith("docs/") and not rel.startswith("configs/"):
        return "SKIPPED_SOLWEIG_OUTPUT_OR_ROOT"
    if "qgis" in rel:
        return "SKIPPED_QGIS_REFERENCE"
    allowed = set(config_list(config or {}, "allowed_extensions", sorted(DEFAULT_ALLOWED_EXTENSIONS)))
    if ext and ext not in allowed:
        return "SKIPPED_EXTENSION_NOT_ALLOWED"
    return "SAFE_TO_INSPECT"


def safe_file_size(path: str | Path) -> int | None:
    """Return file size if available."""
    try:
        return repo_path(path).stat().st_size
    except OSError:
        return None


def csv_columns_and_rows(path: str | Path) -> tuple[list[str], int | None, str]:
    """Read a compact CSV header and row count without touching raster files."""
    resolved = repo_path(path)
    try:
        opener = gzip.open if extension_key(resolved) == ".csv.gz" else open
        with opener(resolved, "rt", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            columns = next(reader, [])
            row_count = sum(1 for _ in reader)
        return columns, row_count, "READ_OK"
    except Exception as exc:  # pragma: no cover - inventory guard
        return [], None, f"READ_FAILED:{type(exc).__name__}"


def json_or_geojson_metadata(path: str | Path) -> tuple[list[str], int | None, str, str, str]:
    """Read safe JSON/GeoJSON metadata for compact/vector source review."""
    resolved = repo_path(path)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8", errors="replace"))
        if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
            features = payload.get("features") or []
            columns: set[str] = set()
            geometry_types: set[str] = set()
            for feature in features[:10_000]:
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
            columns = sorted({str(key) for row in payload[:1000] if isinstance(row, dict) for key in row.keys()})
            return columns, len(payload), "", "", "READ_OK"
        if isinstance(payload, dict):
            return sorted(str(key) for key in payload.keys()), 1, "", "", "READ_OK"
        return [], None, "", "", "READ_OK_EMPTY_OR_SCALAR"
    except Exception as exc:  # pragma: no cover - inventory guard
        return [], None, "", "", f"READ_FAILED:{type(exc).__name__}"


def vector_metadata(path: str | Path) -> tuple[list[str], int | None, str, str, str]:
    """Read vector metadata when a vector engine is available."""
    resolved = repo_path(path)
    try:
        import geopandas as gpd  # type: ignore

        frame = gpd.read_file(resolved)
        geometry_type = "|".join(sorted(str(value) for value in frame.geometry.geom_type.dropna().unique()))
        crs = str(frame.crs) if frame.crs is not None else ""
        columns = [str(column) for column in frame.columns if str(column) != "geometry"]
        return columns, int(len(frame)), geometry_type, crs, "READ_OK"
    except Exception as exc:  # pragma: no cover - optional dependency guard
        return [], None, "", "", f"METADATA_ONLY_NO_VECTOR_ENGINE:{type(exc).__name__}"


def read_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read a compact CSV preserving cell IDs as strings."""
    options: dict[str, Any] = {"dtype": {"cell_id": "string"}, "low_memory": False}
    options.update(kwargs)
    return pd.read_csv(repo_path(path), **options)


def write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    """Write a UTF-8 CSV with stable parent creation."""
    destination = repo_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, encoding="utf-8")


def write_text(text: str, path: str | Path) -> None:
    """Write UTF-8 text with LF line endings."""
    destination = repo_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="\n")


def md_table(frame: pd.DataFrame, columns: list[str] | None = None, max_rows: int = 25) -> str:
    """Render a compact Markdown table."""
    if frame.empty:
        return "_No rows._"
    view = frame.copy()
    if columns:
        view = view[[column for column in columns if column in view.columns]]
    view = view.head(max_rows)
    headers = [str(column) for column in view.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in view.iterrows():
        values = [str(row[column]).replace("\n", " ") for column in view.columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def as_float(value: Any, default: float = float("nan")) -> float:
    """Coerce a value to float with a stable default."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def status_from_checks(statuses: Iterable[str]) -> str:
    """Return FAIL/WARN/PASS from a sequence of audit statuses."""
    values = {str(status).upper() for status in statuses}
    if "FAIL" in values or "BLOCKED_SCHEMA" in values or "BLOCKED_INPUT" in values:
        return "FAIL"
    if "WARN" in values:
        return "WARN"
    return "PASS"


def current_n150_label_cells(config: dict[str, Any]) -> set[str]:
    """Resolve the current N150 labelled cell set from compact sources."""
    for key in ["n150_selected_cells_path", "b86g_n150_feature_dataset_path"]:
        path_text = config.get(key)
        if not path_text:
            continue
        path = repo_path(str(path_text))
        if path.exists() and safety_status(path, config) == "SAFE_TO_INSPECT":
            frame = read_csv(path)
            if "cell_id" in frame.columns:
                cells = {str(cell_id) for cell_id in frame["cell_id"].dropna().astype(str)}
                if cells:
                    return cells
    sample = read_csv(config["n150_feature_matrix_path"])
    if "selection_status" in sample.columns:
        selected = sample.loc[sample["selection_status"].astype(str).str.contains("selected|retained|new", case=False, na=False)]
        if len(selected) >= int(config.get("expected_existing_n150_cell_count", 150)):
            return {str(cell_id) for cell_id in selected["cell_id"].dropna().astype(str)}
    non_empty_role = sample.loc[sample.get("primary_role", pd.Series("", index=sample.index)).astype(str).str.len().gt(0)]
    return {str(cell_id) for cell_id in non_empty_role["cell_id"].dropna().astype(str)}


def input_rows_for(config: dict[str, Any]) -> list[tuple[str, str, list[str], bool]]:
    """Return configured input rows with required columns and optionality."""
    rows = [(key, str(config.get(key, "")), REQUIRED_COLUMNS.get(key, []), False) for key in REQUIRED_INPUT_KEYS]
    for key in ["n150_selected_cells_path", "b86g_n150_feature_dataset_path"]:
        if config.get(key):
            rows.append((key, str(config.get(key)), REQUIRED_COLUMNS.get(key, []), True))
    for context_path in config_list(config, "context_paths"):
        rows.append((f"context_path:{Path(context_path).name}", context_path, [], True))
    return rows


def build_input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Create the B8.7 required input inventory frame."""
    rows: list[dict[str, Any]] = []
    for key, configured_path, required_columns, optional in input_rows_for(config):
        path = repo_path(configured_path) if configured_path else PROJECT_ROOT / "__missing__"
        exists = path.exists()
        ext = extension_key(path)
        safety = safety_status(path, config) if exists else "MISSING"
        columns: list[str] = []
        row_count: int | None = None
        read_status = "MISSING"
        if exists and safety == "SAFE_TO_INSPECT" and ext in {".csv", ".csv.gz"}:
            columns, row_count, read_status = csv_columns_and_rows(path)
        elif exists and safety == "SAFE_TO_INSPECT" and ext in {".json", ".geojson"}:
            columns, row_count, _, _, read_status = json_or_geojson_metadata(path)
        elif exists and safety == "SAFE_TO_INSPECT" and ext == ".md":
            read_status = "TEXT_METADATA_ONLY"
        elif exists:
            read_status = "NOT_READ_BY_GUARDRAIL"
        missing_columns = [column for column in required_columns if column not in columns] if required_columns else []
        rows.append(
            {
                "input_key": key,
                "path": safe_rel(path),
                "optional": optional,
                "exists": exists,
                "extension": ext,
                "file_size_bytes": safe_file_size(path) if exists else None,
                "row_count": row_count,
                "column_count": len(columns) if columns else None,
                "required_columns": "|".join(required_columns),
                "missing_required_columns": "|".join(missing_columns),
                "read_status": read_status,
                "safety_status": safety,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def discover_candidate_paths(config: dict[str, Any]) -> list[Path]:
    """Discover compact/vector source candidates while skipping forbidden products."""
    roots = [repo_path(root) for root in config_list(config, "source_discovery_roots")]
    allowed = set(config_list(config, "allowed_extensions", sorted(DEFAULT_ALLOWED_EXTENSIONS)))
    output_dir_rel = str(config.get("output_dir", "")).replace("\\", "/").strip("/")
    paths: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
        for path in candidates:
            ext = extension_key(path)
            if ext in FORBIDDEN_EXTENSIONS or path.name.lower() == "svfs.zip":
                continue
            rel = safe_rel(path).replace("\\", "/")
            if output_dir_rel and (rel == output_dir_rel or rel.startswith(f"{output_dir_rel}/")):
                continue
            if ext in allowed and safety_status(path, config) == "SAFE_TO_INSPECT":
                paths[rel] = path
    return [paths[key] for key in sorted(paths)]


def likely_role(path: str | Path, columns: Sequence[str], geometry_type: str = "") -> str:
    """Assign a broad source role from path, columns, and geometry hints."""
    text = f"{safe_rel(path)} {' '.join(columns)} {geometry_type}".lower()
    if "shade_corridor" in text or "continuity" in text or "shade_gap" in text:
        return "connected_shade_corridor_or_continuity"
    if "covered_walkway" in text or "walkway" in text or "footpath" in text or "pedestrian" in text or "shelter" in text:
        return "pedestrian_network_or_covered_walkway"
    if "overhead" in text or "pedestrian_bridge" in text or "viaduct" in text or "elevated_rail" in text or "elevated_road" in text:
        return "overhead_geometry"
    if "building" in text or "height" in text or "canyon" in text or "dsm" in text:
        return "building_footprint_height_canyon"
    if "tree" in text or "canopy" in text or "gvi" in text or "ndvi" in text:
        return "tree_canopy_or_tree_building"
    if "water" in text or "park" in text or "road" in text or "hardscape" in text or "impervious" in text:
        return "water_park_road_hardscape_edge"
    if "feature" in text and "cell_id" in text:
        return "compact_existing_feature_table"
    if "grid" in text and ("cell_id" in text or "polygon" in text or "centroid" in text):
        return "cell_grid_geometry"
    return "unclassified_compact_or_vector"


def inspect_source(path: str | Path, config: dict[str, Any]) -> dict[str, Any]:
    """Inspect one compact/vector candidate source without raster I/O."""
    resolved = repo_path(path)
    ext = extension_key(resolved)
    size = safe_file_size(resolved)
    max_bytes = int(config.get("source_inventory_max_metadata_bytes", 30_000_000))
    columns: list[str] = []
    row_count: int | None = None
    geometry_type = ""
    crs = ""
    read_status = "NOT_READ"
    safety = safety_status(resolved, config)
    if safety == "SAFE_TO_INSPECT" and size is not None and size <= max_bytes:
        if ext in {".csv", ".csv.gz"}:
            columns, row_count, read_status = csv_columns_and_rows(resolved)
        elif ext in {".json", ".geojson"}:
            columns, row_count, geometry_type, crs, read_status = json_or_geojson_metadata(resolved)
        elif ext in {".gpkg", ".shp"}:
            columns, row_count, geometry_type, crs, read_status = vector_metadata(resolved)
        elif ext == ".md":
            read_status = "TEXT_METADATA_ONLY"
    elif safety == "SAFE_TO_INSPECT":
        read_status = "METADATA_ONLY_LARGE_FILE"
    return {
        "path": safe_rel(resolved),
        "extension": ext,
        "file_size_bytes": size,
        "row_count": row_count,
        "column_count": len(columns) if columns else None,
        "geometry_type": geometry_type,
        "crs": crs,
        "useful_columns": "|".join(columns[:80]),
        "likely_role": likely_role(resolved, columns, geometry_type),
        "read_status": read_status,
        "safety_status": safety,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run(config_path: Path = DEFAULT_CONFIG) -> InputInventoryResult:
    """Run B8.7 input inventory."""
    config = load_config(config_path)
    ensure_output_dir(config)
    inventory = build_input_inventory(config)
    write_csv(inventory, output_path(config, "input_inventory_path"))
    required = inventory.loc[~inventory["optional"].astype(bool)].copy()
    missing = int((~required["exists"].astype(bool)).sum()) if not required.empty else len(REQUIRED_INPUT_KEYS)
    schema_errors = int(required["missing_required_columns"].fillna("").astype(str).str.len().gt(0).sum())
    current_cells = current_n150_label_cells(config)
    expected = int(config.get("expected_existing_n150_cell_count", 150))
    status = "B87_INPUT_READY" if missing == 0 and schema_errors == 0 and len(current_cells) == expected else "B87_BLOCKED_INPUT"
    return InputInventoryResult(
        status=status,
        inputs_checked=len(inventory),
        missing_inputs=missing,
        schema_errors=schema_errors,
        current_n150_label_cells=len(current_cells),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory B8.7-N300-PRE compact inputs and schema checks. "
            "Writes b87_input_inventory.csv only; no raster, QGIS, SOLWEIG, "
            "AOI/B9, WBGT, hazard/risk, manifest, or execution outputs."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
