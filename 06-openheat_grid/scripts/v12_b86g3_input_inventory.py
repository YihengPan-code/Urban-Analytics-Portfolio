"""Inventory B8.6g3 compact inputs and shared no-raster helpers.

Inputs:
    configs/v12/systemb_b86g3_true_vector_source_review.yaml plus compact CSV,
    JSON, GeoJSON, GPKG/SHP metadata, and Markdown paths declared or discovered
    there.
Outputs:
    b86g3_input_inventory.csv.
Saved metrics:
    Required input existence, row counts, column counts, schema checks, current
    N150 cell count, and guardrail safety status. This script reads compact
    tabular/vector metadata only. It does not read raster-like files, run QGIS
    or SOLWEIG, create an N300 execution manifest, create AOI-wide prediction,
    create B9 outputs, produce local WBGT, hazard/risk/exposure/vulnerability
    scores, claim observed truth, claim causal feature importance, convert Tmrt
    to WBGT, or couple System A and System B.
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
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "v12" / "systemb_b86g3_true_vector_source_review.yaml"
CLAIM_BOUNDARY = (
    "B8.6g3 true-vector source review and B8.7a closeout only; not B9, "
    "not AOI-wide prediction, not local WBGT, not hazard_score or risk_score, "
    "not exposure/vulnerability scoring, not observed truth, not causal feature "
    "importance, no raster, no QGIS/SOLWEIG, no N300 execution manifest, no "
    "Tmrt-to-WBGT conversion, and no System A/B coupling."
)
FORBIDDEN_EXTENSIONS = {".tif", ".tiff", ".vrt", ".asc", ".img", ".nc", ".grib"}
ALLOWED_EXTENSIONS = {".csv", ".csv.gz", ".parquet", ".geojson", ".gpkg", ".shp", ".json", ".md"}
FORBIDDEN_PATH_TOKENS = {
    "data/solweig/",
    "data/rasters/",
    "data/archive/",
    "data/raw/buildings_v10/",
    "svfs.zip",
    "hourly_grid_heatstress_forecast",
}
EXECUTION_TOKENS = {"qgis", "runner", "execution_package", "execution_manifest"}
MAX_METADATA_BYTES_DEFAULT = 30_000_000

REQUIRED_INPUT_KEYS = [
    "b87a_v3_design_path",
    "b87a_patch_log_path",
    "b87a_freeze_readiness_path",
    "b87a_manual_input_path",
    "b87_true_vector_source_inventory_path",
    "b87_true_vector_gap_register_path",
    "b86g_source_inventory_path",
    "b86g_vector_source_readiness_path",
    "b86g_feature_gap_closure_matrix_path",
    "n150_feature_matrix_path",
    "candidate_universe_path",
]
OPTIONAL_INPUT_KEYS = ["b86g_n150_feature_dataset_path"]

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "b87a_v3_design_path": ["cell_id", "primary_role", "spatial_bin", "typology", "design_status"],
    "b87a_patch_log_path": ["cell_id", "patch_action", "manual_decision"],
    "b87a_freeze_readiness_path": ["decision_item", "status", "evidence"],
    "b87a_manual_input_path": ["cell_id", "manual_decision", "manual_notes"],
    "b87_true_vector_source_inventory_path": ["source_category", "path", "support_level", "can_support_B86G3"],
    "b87_true_vector_gap_register_path": ["source_category", "source_status", "recommended_action"],
    "b86g_source_inventory_path": ["path", "extension", "likely_role", "read_status", "safety_status"],
    "b86g_vector_source_readiness_path": ["likely_role", "readiness_status"],
    "b86g_feature_gap_closure_matrix_path": ["gap_family", "closure_status"],
    "n150_feature_matrix_path": ["cell_id"],
    "candidate_universe_path": ["cell_id", "typology_label"],
    "b86g_n150_feature_dataset_path": ["cell_id", "feature_version"],
}


@dataclass(frozen=True)
class InputInventoryResult:
    """B8.6g3 input inventory result."""

    status: str
    inputs_checked: int
    missing_required_inputs: int
    schema_errors: int
    current_n150_cells: int


def repo_path(path: str | Path) -> Path:
    """Resolve a path relative to the OpenHeat project subdirectory."""
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
    """Parse a small YAML scalar subset used by the B8.6g3 config."""
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
    """Load the explicit B8.6g3 YAML config without requiring PyYAML."""
    resolved = repo_path(config_path)
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
                config[key] = []
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
        raise ValueError(f"B8.6g3 config did not parse as a mapping: {resolved}")
    return config


def config_list(config: dict[str, Any], key: str, default: Sequence[str] | None = None) -> list[str]:
    """Return a config value as a list of strings."""
    value = config.get(key, default or [])
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [part.strip() for part in str(value).split("|") if part.strip()]


def output_path(config: dict[str, Any], key: str) -> Path:
    """Resolve an output path key from the B8.6g3 config."""
    return repo_path(str(config[key]))


def ensure_output_dir(config: dict[str, Any]) -> Path:
    """Create and return the compact B8.6g3 output directory."""
    out_dir = repo_path(str(config["output_dir"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def extension_key(path: str | Path) -> str:
    """Return .csv.gz for gzip CSVs, otherwise the lower-case suffix."""
    suffixes = [suffix.lower() for suffix in repo_path(path).suffixes]
    if len(suffixes) >= 2 and suffixes[-2:] == [".csv", ".gz"]:
        return ".csv.gz"
    return repo_path(path).suffix.lower()


def is_under_forbidden_root(path: str | Path, config: dict[str, Any] | None = None) -> bool:
    """Return true when a path falls under a configured forbidden root."""
    rel = safe_rel(path).replace("\\", "/").strip("/").lower()
    roots = [token.lower().strip("/").replace("\\", "/") for token in (config or {}).get("forbidden_roots", [])]
    roots.extend(["data/solweig", "data/rasters", "data/archive", "data/raw/buildings_v10"])
    return any(rel == root or rel.startswith(f"{root}/") for root in roots)


def safety_status(path: str | Path, config: dict[str, Any] | None = None) -> str:
    """Classify whether a path can be inspected under B8.6g3 guardrails."""
    rel = safe_rel(path).replace("\\", "/").lower()
    name = repo_path(path).name.lower()
    ext = extension_key(path)
    if ext in FORBIDDEN_EXTENSIONS:
        return "FORBIDDEN_RASTER_EXTENSION"
    if name == "svfs.zip" or any(token in rel for token in FORBIDDEN_PATH_TOKENS):
        return "FORBIDDEN_PATH_OR_PRODUCT"
    if is_under_forbidden_root(path, config):
        return "FORBIDDEN_ROOT"
    if "solweig" in rel and not (rel.startswith("docs/") or rel.startswith("configs/")):
        return "SKIPPED_SOLWEIG_OUTPUT_OR_ROOT"
    if "manifest" in name and ("solweig" in rel or "qgis" in rel or rel.startswith("configs/")):
        return "SKIPPED_EXECUTION_MANIFEST_REFERENCE"
    if any(token in rel for token in EXECUTION_TOKENS) and "outputs/v12_surrogate/b8_6g3_true_vector_source_review/" not in rel:
        if rel.startswith("docs/"):
            return "TEXT_METADATA_ONLY_EXECUTION_DOC"
        return "SKIPPED_EXECUTION_REFERENCE"
    if ext not in ALLOWED_EXTENSIONS:
        return "SKIPPED_EXTENSION_NOT_ALLOWED"
    return "SAFE_TO_INSPECT"


def read_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read a compact CSV while preserving cell IDs as strings."""
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


def csv_columns_and_rows(path: str | Path) -> tuple[list[str], int | None, str]:
    """Read CSV header and row count when safe."""
    try:
        opener = gzip.open if extension_key(path) == ".csv.gz" else open
        with opener(repo_path(path), "rt", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            columns = next(reader, [])
            row_count = sum(1 for _ in reader)
        return columns, row_count, "READ_OK"
    except Exception as exc:  # pragma: no cover - defensive inventory guard
        return [], None, f"READ_FAILED:{type(exc).__name__}"


def json_vector_metadata(path: str | Path) -> tuple[list[str], int | None, str, str, str]:
    """Read safe JSON/GeoJSON property, geometry, and CRS metadata."""
    try:
        payload = json.loads(repo_path(path).read_text(encoding="utf-8", errors="replace"))
        if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
            features = payload.get("features") or []
            columns: set[str] = set()
            geometry_types: set[str] = set()
            for feature in features:
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


def inspect_path(path: str | Path, config: dict[str, Any]) -> dict[str, Any]:
    """Inspect one source candidate without reading unsafe products."""
    resolved = repo_path(path)
    ext = extension_key(resolved)
    status = safety_status(resolved, config)
    file_size = resolved.stat().st_size if resolved.exists() else 0
    columns: list[str] = []
    row_count: int | None = None
    geometry_type = ""
    crs = ""
    read_status = "MISSING" if not resolved.exists() else "NOT_READ_BY_GUARDRAIL"
    max_bytes = int(config.get("source_inventory_max_metadata_bytes", MAX_METADATA_BYTES_DEFAULT))
    if resolved.exists() and status == "SAFE_TO_INSPECT" and file_size <= max_bytes:
        if ext in {".csv", ".csv.gz"}:
            columns, row_count, read_status = csv_columns_and_rows(resolved)
        elif ext in {".json", ".geojson"}:
            columns, row_count, geometry_type, crs, read_status = json_vector_metadata(resolved)
        elif ext == ".md":
            read_status = "TEXT_METADATA_ONLY"
        elif ext in {".parquet", ".gpkg", ".shp"}:
            read_status = "METADATA_ONLY_NO_VECTOR_ENGINE"
    elif resolved.exists() and status == "SAFE_TO_INSPECT":
        read_status = "METADATA_ONLY_LARGE_FILE"
    return {
        "path": safe_rel(resolved),
        "extension": ext,
        "file_size_bytes": file_size,
        "row_count": row_count,
        "column_count": len(columns) if columns else None,
        "geometry_type": geometry_type,
        "CRS": crs,
        "useful_columns": "|".join(columns),
        "read_status": read_status,
        "safety_status": status,
    }


def discover_candidate_paths(config: dict[str, Any]) -> list[Path]:
    """Discover allowed-extension paths under configured source roots."""
    roots = config_list(config, "source_discovery_roots")
    allowed = set(config_list(config, "allowed_extensions", sorted(ALLOWED_EXTENSIONS)))
    output_dir_rel = str(config.get("output_dir", "")).replace("\\", "/").strip("/")
    paths: dict[str, Path] = {}
    for root_text in roots:
        root = repo_path(root_text)
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
        for path in candidates:
            rel = safe_rel(path).replace("\\", "/")
            if output_dir_rel and (rel == output_dir_rel or rel.startswith(f"{output_dir_rel}/")):
                continue
            ext = extension_key(path)
            if ext in allowed or ext in FORBIDDEN_EXTENSIONS or path.name.lower() == "svfs.zip":
                paths[rel] = path
    return [paths[key] for key in sorted(paths)]


def input_keys(config: dict[str, Any]) -> list[tuple[str, bool]]:
    """Return configured input keys with required/optional flags."""
    keys = [(key, True) for key in REQUIRED_INPUT_KEYS]
    for key in OPTIONAL_INPUT_KEYS:
        if key in config:
            keys.append((key, False))
    return keys


def build_input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Build the machine-readable B8.6g3 input inventory."""
    rows: list[dict[str, Any]] = []
    for key, required in input_keys(config):
        configured = str(config.get(key, ""))
        path = repo_path(configured) if configured else PROJECT_ROOT / "__missing__"
        exists = path.exists()
        columns: list[str] = []
        row_count: int | None = None
        read_status = "MISSING"
        if exists and extension_key(path) in {".csv", ".csv.gz"} and safety_status(path, config) == "SAFE_TO_INSPECT":
            columns, row_count, read_status = csv_columns_and_rows(path)
        elif exists:
            read_status = "TEXT_OR_METADATA_ONLY" if safety_status(path, config) == "SAFE_TO_INSPECT" else "NOT_READ_BY_GUARDRAIL"
        required_columns = REQUIRED_COLUMNS.get(key, [])
        missing_columns = [column for column in required_columns if column not in columns] if columns else ([] if not required_columns else required_columns)
        if not exists and not required:
            missing_columns = []
        rows.append(
            {
                "input_key": key,
                "path": safe_rel(path),
                "required": required,
                "exists": exists,
                "extension": extension_key(path),
                "file_size_bytes": path.stat().st_size if exists else 0,
                "row_count": row_count,
                "column_count": len(columns) if columns else 0,
                "required_columns": "|".join(required_columns),
                "missing_required_columns": "|".join(missing_columns),
                "read_status": read_status,
                "safety_status": safety_status(path, config) if exists else "MISSING",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def current_n150_cells(config: dict[str, Any]) -> set[str]:
    """Resolve current N150 cells from compact non-raster sources."""
    feature_path = config.get("b86g_n150_feature_dataset_path")
    if feature_path and repo_path(str(feature_path)).exists():
        frame = read_csv(str(feature_path))
        if "cell_id" in frame.columns:
            return set(frame["cell_id"].dropna().astype(str))
    frame = read_csv(config["n150_feature_matrix_path"])
    if "selection_status" in frame.columns:
        selected = frame.loc[frame["selection_status"].astype(str).str.contains("selected|retained|new", case=False, na=False)]
        if int(selected["cell_id"].nunique()) >= int(config.get("expected_n300_count", 150)):
            return set(selected["cell_id"].dropna().astype(str))
    if "primary_role" in frame.columns:
        selected = frame.loc[frame["primary_role"].astype(str).str.len().gt(0)]
        if int(selected["cell_id"].nunique()) >= int(config.get("expected_n300_count", 150)):
            return set(selected["cell_id"].dropna().astype(str))
    return set(frame["cell_id"].dropna().astype(str).head(int(config.get("expected_n300_count", 150))))


def pipe_join(items: Iterable[str]) -> str:
    """Join non-empty unique strings with pipes."""
    seen: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.append(text)
    return "|".join(seen) if seen else "none"


def md_table(frame: pd.DataFrame, columns: Sequence[str], max_rows: int = 20) -> str:
    """Render a compact Markdown table."""
    if frame.empty:
        return "_No rows._"
    view = frame.loc[:, [column for column in columns if column in frame.columns]].head(max_rows).copy()
    header = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = ["| " + " | ".join(str(item) for item in row) + " |" for row in view.fillna("").to_numpy()]
    return "\n".join([header, sep, *rows])


def run(config_path: Path = DEFAULT_CONFIG) -> InputInventoryResult:
    """Run B8.6g3 input inventory."""
    config = load_config(config_path)
    ensure_output_dir(config)
    inventory = build_input_inventory(config)
    write_csv(inventory, output_path(config, "input_inventory_path"))
    required = inventory.loc[inventory["required"].astype(bool)].copy()
    missing = int((~required["exists"].astype(bool)).sum())
    schema_errors = int(required["missing_required_columns"].fillna("").astype(str).str.len().gt(0).sum())
    n150_cells = current_n150_cells(config)
    expected = int(config.get("expected_n300_count", 150))
    status = "B86G3_INPUT_READY" if missing == 0 and schema_errors == 0 and len(n150_cells) == expected else "B86G3_BLOCKED_INPUT"
    return InputInventoryResult(
        status=status,
        inputs_checked=len(inventory),
        missing_required_inputs=missing,
        schema_errors=schema_errors,
        current_n150_cells=len(n150_cells),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory B8.6g3 compact/vector source-review inputs. Writes an "
            "input inventory only; no raster, QGIS/SOLWEIG, N300 manifest, "
            "AOI/B9, WBGT, hazard/risk, or System A/B coupling output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
