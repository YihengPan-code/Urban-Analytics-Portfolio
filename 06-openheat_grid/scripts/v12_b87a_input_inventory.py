"""Inventory B8.7a N300 design-QA patch inputs and shared helpers.

Inputs:
    configs/v12/systemb_b87a_n300_design_qa_patch.yaml plus compact B8.7,
    B8.6f/B8.6g, N150, and candidate-universe CSV inputs declared there.
Outputs:
    outputs/v12_surrogate/b8_7a_n300_design_qa_patch/b87a_input_inventory.csv.
Saved metrics:
    Input existence, row/column counts, required-schema checks, manual-input
    presence, current N150 cell count, and guardrail safety status. This script
    reads compact CSV/Markdown metadata only and performs no raster I/O, QGIS,
    SOLWEIG, N300 execution manifest, AOI-wide prediction, B9 output, local
    WBGT, hazard/risk/exposure/vulnerability scoring, observed-truth claim,
    causal feature-importance claim, Tmrt-to-WBGT conversion, or System A/B
    coupling.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "v12" / "systemb_b87a_n300_design_qa_patch.yaml"
CLAIM_BOUNDARY = (
    "B8.7a N300 design QA patch only; not B9, not AOI-wide prediction, not "
    "local WBGT, not hazard_score or risk_score, not exposure/vulnerability "
    "score, not observed truth, not causal feature importance, no raster, no "
    "QGIS/SOLWEIG, no N300 execution manifest, no Tmrt-to-WBGT conversion, and "
    "no System A/B coupling."
)
SAMPLING_BOUNDARY = "candidate_design_only_not_N300_run_ready"
VALID_MANUAL_DECISIONS = {"keep", "exclude", "replace", "source_review", "unsure", "not_reviewed"}
FORBIDDEN_EXTENSIONS = {".tif", ".tiff", ".vrt", ".asc", ".img", ".nc", ".grib"}
FORBIDDEN_PATH_TOKENS = {
    "data/solweig/",
    "data/rasters/",
    "data/archive/",
    "data/raw/buildings_v10/",
    "svfs.zip",
    "hourly_grid_heatstress_forecast",
}

REQUIRED_INPUT_KEYS = [
    "b87_candidate_path",
    "b87_manual_qa_checklist_path",
    "b87_role_audit_path",
    "b87_spatial_audit_path",
    "b87_typology_audit_path",
    "b87_anchor_audit_path",
    "b87_neutral_audit_path",
    "b87_sparse_audit_path",
    "b87_feature_coverage_path",
    "b86f_n300_design_v2_path",
    "b86g_n300_feature_dataset_path",
    "n150_feature_matrix_path",
    "candidate_universe_path",
]
OPTIONAL_INPUT_KEYS = [
    "manual_review_input_path",
    "b87_control_audit_path",
    "n150_selected_cells_path",
    "b86g_n150_feature_dataset_path",
]

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "b87_candidate_path": [
        "cell_id",
        "selected_priority_rank",
        "primary_role",
        "spatial_bin",
        "typology",
        "nearest_anchor_cell",
        "nearest_neutral_cell",
        "nearest_n150_distance_percentile",
    ],
    "b87_manual_qa_checklist_path": ["cell_id", "recommended_action"],
    "b87_role_audit_path": ["primary_role", "observed_count", "quota", "status"],
    "b87_spatial_audit_path": ["spatial_bin", "observed_count", "status"],
    "b87_typology_audit_path": ["typology", "observed_count", "status"],
    "b87_anchor_audit_path": ["nearest_anchor_cell", "observed_count", "preferred_minimum", "status"],
    "b87_neutral_audit_path": ["nearest_neutral_cell", "neutral_boundary_role_count", "status"],
    "b87_sparse_audit_path": ["audit_item", "observed_count", "status"],
    "b87_feature_coverage_path": ["feature_family", "feature_coverage_status", "status"],
    "b87_control_audit_path": ["audit_item", "observed_value", "status"],
    "b86f_n300_design_v2_path": ["cell_id", "primary_role", "spatial_bin", "typology"],
    "b86g_n300_feature_dataset_path": ["cell_id", "feature_version"],
    "n150_feature_matrix_path": ["cell_id"],
    "candidate_universe_path": ["cell_id", "typology_label"],
    "manual_review_input_path": ["cell_id", "manual_decision"],
    "n150_selected_cells_path": ["cell_id"],
    "b86g_n150_feature_dataset_path": ["cell_id", "feature_version"],
}

SAFE_UNIVERSE_COLUMNS = [
    "cell_id",
    "centroid_x",
    "centroid_y",
    "geometry_available",
    "human_qa_exclusion_reason",
    "typology_label",
    "svf",
    "shade_fraction_base_v10",
    "shade_fraction_overhead_sens",
    "building_density",
    "mean_building_height",
    "building_height_p90",
    "open_pixel_fraction",
    "road_fraction",
    "tree_canopy_fraction",
    "gvi_percent",
    "ndvi_mean",
    "grass_fraction",
    "water_fraction",
    "dynamic_world_water_fraction",
    "built_up_fraction",
    "impervious_fraction",
    "overhead_fraction_total",
    "overhead_area_covered_walkway_m2",
    "n_overhead_features",
    "pedestrian_shelter_fraction",
    "transport_deck_fraction",
    "distance_to_water",
    "distance_to_park",
    "land_use_hint",
    "land_use_raw",
    "land_use_fraction",
    "eligible",
    "exclusion_reason",
]

SAFE_FEATURE_COLUMNS = [
    "cell_id",
    "ped_access_shade_frac",
    "ped_access_shade_frac_proxy",
    "ped_access_shade_length_m_proxy",
    "ped_access_source_status",
    "shade_corridor_source_status",
    "overhead_patch_count",
    "overhead_total_area_m2",
    "overhead_mean_patch_area_m2",
    "overhead_shape_source_status",
    "sunlit_hot_pocket_proxy_frac",
    "open_high_svf_low_shade_frac",
    "water_edge_contact_frac",
    "park_edge_contact_frac",
    "hardscape_edge_contact_frac",
    "boundary_edge_source_status",
    "neighbourhood_shade_mean",
    "neighbourhood_overhead_frac",
    "neighbourhood_open_frac",
    "tree_building_overlap_proxy",
    "tree_near_tall_building_frac",
    "height_roughness_iqr_m",
    "height_asymmetry_idx",
    "typology_geometry_class",
    "typology_shade_interaction",
    "feature_version",
]


@dataclass(frozen=True)
class InputInventoryResult:
    """B8.7a input inventory result."""

    status: str
    inputs_checked: int
    missing_required_inputs: int
    schema_errors: int
    current_n150_cells: int
    manual_input_found: bool


def repo_path(path: str | Path) -> Path:
    """Resolve a path relative to the OpenHeat project directory."""
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
    """Load the explicit B8.7a YAML config without requiring PyYAML."""
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
        raise ValueError(f"B8.7a config must parse to a mapping: {resolved}")
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
    """Resolve an output path key from the B8.7a config."""
    return repo_path(str(config[key]))


def ensure_output_dir(config: dict[str, Any]) -> Path:
    """Create and return the compact B8.7a output directory."""
    out_dir = repo_path(str(config["output_dir"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def extension_key(path: str | Path) -> str:
    """Return .csv.gz for gzip CSVs, otherwise the lower-case suffix."""
    suffixes = [suffix.lower() for suffix in repo_path(path).suffixes]
    if len(suffixes) >= 2 and suffixes[-2:] == [".csv", ".gz"]:
        return ".csv.gz"
    return repo_path(path).suffix.lower()


def safety_status(path: str | Path) -> str:
    """Classify whether a file is safe for this no-raster/no-execution lane."""
    rel = safe_rel(path).replace("\\", "/").lower()
    ext = extension_key(path)
    if ext in FORBIDDEN_EXTENSIONS:
        return "FORBIDDEN_RASTER_EXTENSION"
    if any(token in rel for token in FORBIDDEN_PATH_TOKENS):
        return "FORBIDDEN_PATH_OR_PRODUCT"
    if "qgis" in rel:
        return "SKIPPED_QGIS_REFERENCE"
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


def as_float(value: Any, default: float = float("nan")) -> float:
    """Coerce a scalar to float with a stable default."""
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool:
    """Coerce common CSV boolean spellings."""
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def md_table(frame: pd.DataFrame, columns: Sequence[str], max_rows: int = 20) -> str:
    """Render a compact Markdown table."""
    if frame.empty:
        return "_No rows._"
    view = frame.loc[:, [column for column in columns if column in frame.columns]].head(max_rows).copy()
    header = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = ["| " + " | ".join(str(item) for item in row) + " |" for row in view.fillna("").to_numpy()]
    return "\n".join([header, sep, *rows])


def csv_metadata(path: Path) -> tuple[list[str], int | None, str]:
    """Read CSV header and row count for safe compact inputs."""
    if safety_status(path) != "SAFE_TO_INSPECT":
        return [], None, "NOT_READ_BY_GUARDRAIL"
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            columns = next(reader, [])
            row_count = sum(1 for _ in reader)
        return columns, row_count, "READ_OK"
    except Exception as exc:  # pragma: no cover - defensive inventory guard
        return [], None, f"READ_FAILED:{type(exc).__name__}"


def input_keys(config: dict[str, Any]) -> list[tuple[str, bool]]:
    """Return configured input keys with required/optional flags."""
    keys = [(key, True) for key in REQUIRED_INPUT_KEYS]
    for key in OPTIONAL_INPUT_KEYS:
        if key in config:
            keys.append((key, False))
    return keys


def build_input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Build the machine-readable input inventory."""
    rows: list[dict[str, Any]] = []
    for key, required in input_keys(config):
        configured = str(config.get(key, ""))
        path = repo_path(configured) if configured else PROJECT_ROOT / "__missing__"
        exists = path.exists()
        columns: list[str] = []
        row_count: int | None = None
        read_status = "MISSING"
        if exists and extension_key(path) in {".csv", ".csv.gz"}:
            columns, row_count, read_status = csv_metadata(path)
        elif exists:
            read_status = "TEXT_OR_METADATA_ONLY" if safety_status(path) == "SAFE_TO_INSPECT" else "NOT_READ_BY_GUARDRAIL"
        required_columns = REQUIRED_COLUMNS.get(key, [])
        missing_columns = [column for column in required_columns if column not in columns] if columns else ([] if not required_columns else required_columns)
        if not exists:
            missing_columns = [] if not required else missing_columns
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
                "safety_status": safety_status(path) if exists else "MISSING",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def current_n150_cells(config: dict[str, Any]) -> set[str]:
    """Resolve current N150 labelled cells from compact non-raster sources."""
    for key in ["n150_selected_cells_path", "b86g_n150_feature_dataset_path"]:
        path_text = config.get(key)
        if not path_text:
            continue
        path = repo_path(str(path_text))
        if path.exists() and safety_status(path) == "SAFE_TO_INSPECT":
            frame = read_csv(path)
            if "cell_id" in frame.columns and frame["cell_id"].nunique() > 0:
                return set(frame["cell_id"].dropna().astype(str))
    sample = read_csv(config["n150_feature_matrix_path"])
    if "selection_status" in sample.columns:
        selected = sample.loc[sample["selection_status"].astype(str).str.contains("selected|retained|new", case=False, na=False)]
        if int(selected["cell_id"].nunique()) >= int(config.get("expected_existing_n150_count", 150)):
            return set(selected["cell_id"].dropna().astype(str))
    if "primary_role" in sample.columns:
        selected = sample.loc[sample["primary_role"].astype(str).str.len().gt(0)]
        if int(selected["cell_id"].nunique()) >= int(config.get("expected_existing_n150_count", 150)):
            return set(selected["cell_id"].dropna().astype(str))
    return set(sample["cell_id"].dropna().astype(str).head(int(config.get("expected_existing_n150_count", 150))))


def load_b87_candidates(config: dict[str, Any]) -> pd.DataFrame:
    """Load B8.7 candidate rows with stable strings."""
    frame = read_csv(config["b87_candidate_path"])
    frame["cell_id"] = frame["cell_id"].astype(str)
    return frame


def load_candidate_universe(config: dict[str, Any]) -> pd.DataFrame:
    """Load one safe row per candidate-universe cell."""
    frame = read_csv(config["candidate_universe_path"])
    keep = [column for column in SAFE_UNIVERSE_COLUMNS if column in frame.columns]
    out = frame.loc[:, keep].drop_duplicates("cell_id").copy()
    return out


def load_n300_features(config: dict[str, Any]) -> pd.DataFrame:
    """Load safe B8.6g feature columns for B8.7 N300 candidates."""
    frame = read_csv(config["b86g_n300_feature_dataset_path"])
    keep = [column for column in SAFE_FEATURE_COLUMNS if column in frame.columns]
    return frame.loc[:, keep].drop_duplicates("cell_id").copy()


def add_spatial_bin(frame: pd.DataFrame, reference: pd.DataFrame | None = None) -> pd.DataFrame:
    """Attach deterministic east/west and north/south spatial bins."""
    out = frame.copy()
    if "spatial_bin" in out.columns and out["spatial_bin"].notna().any():
        return out
    if "centroid_x" not in out.columns or "centroid_y" not in out.columns:
        out["spatial_bin"] = "unknown"
        return out
    ref = reference if reference is not None else out
    x_mid = float(pd.to_numeric(ref["centroid_x"], errors="coerce").median())
    y_mid = float(pd.to_numeric(ref["centroid_y"], errors="coerce").median())
    x_values = pd.to_numeric(out["centroid_x"], errors="coerce")
    y_values = pd.to_numeric(out["centroid_y"], errors="coerce")
    out["spatial_bin"] = np.where(x_values <= x_mid, "west", "east") + "_" + np.where(y_values <= y_mid, "south", "north")
    return out


def candidate_context(config: dict[str, Any], candidates: pd.DataFrame | None = None) -> pd.DataFrame:
    """Join B8.7 candidates to safe compact QA features."""
    base = load_b87_candidates(config) if candidates is None else candidates.copy()
    features = load_n300_features(config)
    universe = load_candidate_universe(config)
    out = base.merge(features, on="cell_id", how="left")
    out = out.merge(universe, on="cell_id", how="left", suffixes=("", "_universe"))
    if "typology" not in out.columns and "typology_label" in out.columns:
        out["typology"] = out["typology_label"]
    return out


def normalize_manual_decision(value: Any) -> str:
    """Normalize manual-decision text to the allowed vocabulary."""
    decision = "not_reviewed" if value is None or pd.isna(value) else str(value).strip().lower()
    return decision if decision in VALID_MANUAL_DECISIONS else "unsure"


def load_manual_review(config: dict[str, Any]) -> pd.DataFrame:
    """Load optional manual review input if present, otherwise return empty rows."""
    path = repo_path(str(config["manual_review_input_path"]))
    if not path.exists():
        return pd.DataFrame(columns=["cell_id", "manual_decision"])
    frame = read_csv(path)
    if "cell_id" not in frame.columns:
        raise ValueError(f"Manual review input is missing cell_id: {safe_rel(path)}")
    if "manual_decision" not in frame.columns:
        frame["manual_decision"] = "not_reviewed"
    frame["cell_id"] = frame["cell_id"].astype(str)
    frame["manual_decision"] = frame["manual_decision"].map(normalize_manual_decision)
    return frame


def manual_input_found(config: dict[str, Any]) -> bool:
    """Return whether the optional manual review input exists."""
    return repo_path(str(config["manual_review_input_path"])).exists()


def manual_decision_map(config: dict[str, Any]) -> dict[str, str]:
    """Return cell_id -> normalized manual decision."""
    manual = load_manual_review(config)
    if manual.empty:
        return {}
    return dict(zip(manual["cell_id"].astype(str), manual["manual_decision"].astype(str)))


def pipe_join(items: Iterable[str]) -> str:
    """Join non-empty unique flag strings with pipes."""
    seen: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.append(text)
    return "|".join(seen) if seen else "none"


def safe_numeric_features(frame: pd.DataFrame, min_non_null: int = 20) -> list[str]:
    """Return safe numeric feature columns for candidate replacement ranking."""
    forbidden_tokens = {
        "tmrt",
        "wbgt",
        "hazard",
        "risk",
        "exposure",
        "vulnerability",
        "elderly",
        "children",
        "demographic",
        "score_v071",
        "rank",
        "target",
        "output_path",
        "source",
        "notes",
        "lon",
        "lat",
    }
    allowed = []
    for column in frame.columns:
        lower = column.lower()
        if column == "cell_id" or any(token in lower for token in forbidden_tokens):
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        if int(values.notna().sum()) >= min_non_null:
            allowed.append(column)
    return allowed


def nearest_by_features(query: pd.DataFrame, reference: pd.DataFrame, features: Sequence[str]) -> pd.DataFrame:
    """Find nearest reference cell for each query row under robust-scaled features."""
    common = [column for column in features if column in query.columns and column in reference.columns]
    if not common or query.empty or reference.empty:
        return pd.DataFrame(columns=["cell_id", "nearest_cell_id", "feature_space_distance"])
    combined = (
        pd.concat([query.loc[:, common], reference.loc[:, common]], ignore_index=True)
        .apply(pd.to_numeric, errors="coerce")
        .astype(float)
    )
    med = combined.median(axis=0, skipna=True)
    q75 = combined.quantile(0.75)
    q25 = combined.quantile(0.25)
    scale = (q75 - q25).replace(0, np.nan).fillna(combined.std(axis=0, skipna=True)).replace(0, np.nan).fillna(1.0)
    q_values = ((query.loc[:, common].apply(pd.to_numeric, errors="coerce").fillna(med) - med) / scale).to_numpy(dtype=float)
    r_values = ((reference.loc[:, common].apply(pd.to_numeric, errors="coerce").fillna(med) - med) / scale).to_numpy(dtype=float)
    ref_ids = reference["cell_id"].astype(str).to_numpy()
    rows: list[dict[str, Any]] = []
    for idx, values in enumerate(q_values):
        distances = np.sqrt(np.sum((r_values - values) ** 2, axis=1))
        ref_idx = int(np.argmin(distances))
        rows.append(
            {
                "cell_id": str(query.iloc[idx]["cell_id"]),
                "nearest_cell_id": str(ref_ids[ref_idx]),
                "feature_space_distance": float(distances[ref_idx]),
            }
        )
    return pd.DataFrame(rows)


def read_status_count(path: str | Path, status_col: str = "status") -> str:
    """Return a PASS/WARN/FAIL headline for a compact audit CSV."""
    frame = read_csv(path)
    if status_col not in frame.columns:
        return "PASS=0 WARN=0 FAIL=0"
    counts = frame[status_col].astype(str).str.upper().value_counts().to_dict()
    return f"PASS={counts.get('PASS', 0)} WARN={counts.get('WARN', 0)} FAIL={counts.get('FAIL', 0)}"


def run(config_path: Path = DEFAULT_CONFIG) -> InputInventoryResult:
    """Run B8.7a input inventory."""
    config = load_config(config_path)
    ensure_output_dir(config)
    inventory = build_input_inventory(config)
    write_csv(inventory, output_path(config, "input_inventory_path"))
    required = inventory.loc[inventory["required"].astype(bool)].copy()
    missing = int((~required["exists"].astype(bool)).sum())
    schema_errors = int(required["missing_required_columns"].fillna("").astype(str).str.len().gt(0).sum())
    n150_cells = current_n150_cells(config)
    manual_found = manual_input_found(config)
    expected_n150 = int(config.get("expected_existing_n150_count", 150))
    status = (
        "B87A_INPUT_READY"
        if missing == 0 and schema_errors == 0 and len(n150_cells) == expected_n150
        else "B87A_BLOCKED_INPUT"
    )
    return InputInventoryResult(
        status=status,
        inputs_checked=len(inventory),
        missing_required_inputs=missing,
        schema_errors=schema_errors,
        current_n150_cells=len(n150_cells),
        manual_input_found=manual_found,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory B8.7a compact design-QA inputs and guardrail status. "
            "Writes b87a_input_inventory.csv only; no raster/QGIS/SOLWEIG/"
            "manifest/AOI/B9/WBGT/hazard/risk/exposure/vulnerability output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
