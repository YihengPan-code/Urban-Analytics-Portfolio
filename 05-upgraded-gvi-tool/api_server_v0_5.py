"""
FastAPI wrapper for Adaptive GVI/VVI backend v0.5.

Run:
    pip install -r requirements-v0.5.txt
    uvicorn api_server_v0_5:app --reload --host 127.0.0.1 --port 8000

Then open:
    frontend_adaptive_gvi_vvi_v0_5.html
"""

from __future__ import annotations

import base64
import os
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from adaptive_gvi_vvi_backend_v0_5 import analyse_array, build_segmenter, build_settings, parse_bool


app = FastAPI(title="Adaptive GVI/VVI API", version="0.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "null",  # allows direct file:// frontend during local prototyping
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_SEGMENTER_CACHE = {}


def get_segmenter(segmenter: str, model_id: str, veg_labels: Optional[str], device: Optional[str]):
    if segmenter == "none":
        return None
    key = (segmenter, model_id, veg_labels or "", device or "")
    if key not in _SEGMENTER_CACHE:
        _SEGMENTER_CACHE[key] = build_segmenter(segmenter, model_id, veg_labels, device)
    return _SEGMENTER_CACHE[key]


def b64_png(path: Path) -> str:
    data = path.read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.5", "default_mode": "precision-guarded semantic GVI/VVI"}


@app.post("/analyse")
async def analyse_endpoint(
    file: UploadFile = File(...),
    preset: str = Form("standard"),
    recovery_mode: str = Form("balanced"),
    ground_guard: str = Form("strong"),
    ground_filter_mode: str = Form("balanced"),
    artifact_guard: str = Form("strong"),
    segmenter: str = Form(os.getenv("GVI_SEGMENTER", "hf")),
    model_id: str = Form(os.getenv("GVI_MODEL_ID", "nvidia/segformer-b0-finetuned-ade-512-512")),
    veg_labels: Optional[str] = Form(None),
    device: Optional[str] = Form(None),
    semantic_prob_min: Optional[float] = Form(None),
    soft_semantic_prob_min: Optional[float] = Form(None),
    min_safe_recovery_prob: Optional[float] = Form(None),
    recovery_radius_px: Optional[int] = Form(None),
    count_muted_as_gvi: str = Form("false"),
    fence_recovery: str = Form("true"),
    exclude_high_vis: str = Form("true"),
    allow_isolated_colour_recovery: str = Form("false"),
    gvi_requires_semantic_support: str = Form("true"),
    hard_negative_veto: str = Form("true"),
    remove_rectangular_panels: str = Form("true"),
    enable_ground_quality_guard: str = Form("true"),
    ground_quality_bottom_start: Optional[float] = Form(None),
    front_ground_start: Optional[float] = Form(None),
    ground_veg_prob_margin: Optional[float] = Form(None),
    ground_negative_prob_min: Optional[float] = Form(None),
):
    raw = await file.read()
    arr = np.frombuffer(raw, dtype=np.uint8)
    image_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise HTTPException(status_code=400, detail="Could not decode uploaded image.")

    overrides = {
        "semantic_prob_min": semantic_prob_min,
        "soft_semantic_prob_min": soft_semantic_prob_min,
        "min_safe_recovery_prob": min_safe_recovery_prob,
        "recovery_radius_px": recovery_radius_px,
        "count_muted_as_gvi": parse_bool(count_muted_as_gvi),
        "fence_recovery": parse_bool(fence_recovery),
        "exclude_high_vis": parse_bool(exclude_high_vis),
        "allow_isolated_colour_recovery": parse_bool(allow_isolated_colour_recovery),
        "gvi_requires_semantic_support": parse_bool(gvi_requires_semantic_support),
        "hard_negative_veto": parse_bool(hard_negative_veto),
        "remove_rectangular_panels": parse_bool(remove_rectangular_panels),
        "enable_ground_quality_guard": parse_bool(enable_ground_quality_guard),
        "ground_filter_mode": ground_filter_mode,
        "ground_quality_bottom_start": ground_quality_bottom_start,
        "front_ground_start": front_ground_start,
        "ground_veg_prob_margin": ground_veg_prob_margin,
        "ground_negative_prob_min": ground_negative_prob_min,
    }
    # Build presets/guard strength first, then apply requested ground-quality mode and explicit overrides.
    base_overrides = {k: v for k, v in overrides.items() if k != "ground_filter_mode"}
    settings = build_settings(preset, recovery_mode, ground_guard, artifact_guard, overrides=base_overrides)
    if ground_filter_mode:
        from adaptive_gvi_vvi_backend_v0_5 import apply_ground_quality_filter
        apply_ground_quality_filter(settings, ground_filter_mode)
    for k, v in overrides.items():
        if k == "ground_filter_mode" or v is None or v == "":
            continue
        if hasattr(settings, k):
            cur = getattr(settings, k)
            if isinstance(cur, bool):
                setattr(settings, k, parse_bool(v))
            elif isinstance(cur, int):
                setattr(settings, k, int(float(v)))
            elif isinstance(cur, float):
                setattr(settings, k, float(v))
            else:
                setattr(settings, k, str(v))
    model = get_segmenter(segmenter, model_id, veg_labels, device)

    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = analyse_array(
            image_bgr=image_bgr,
            image_name=file.filename or "upload.jpg",
            output_dir=out_dir,
            settings=settings,
            segmenter=model,
            save_outputs=True,
        )
        overlay_uri = b64_png(Path(result["overlay_path"]))
        vvi_uri = b64_png(Path(result["vvi_mask_path"]))
        gvi_uri = b64_png(Path(result["gvi_mask_path"]))
        recovery_uri = b64_png(Path(result["recovery_mask_path"]))
        removed_uri = b64_png(Path(result["removed_mask_path"]))

        semantic_raw_uri = ""
        semantic_clean_uri = ""
        if result.get("semantic_raw_mask_path"):
            semantic_raw_uri = b64_png(Path(result["semantic_raw_mask_path"]))
        if result.get("semantic_clean_mask_path"):
            semantic_clean_uri = b64_png(Path(result["semantic_clean_mask_path"]))

        # Path values are local temp paths, so remove them from JSON payload.
        public_result = dict(result)
        for key in list(public_result.keys()):
            if key.endswith("_path"):
                public_result[key] = ""

        return {
            "result": public_result,
            "overlay_png": overlay_uri,
            "vvi_mask_png": vvi_uri,
            "gvi_mask_png": gvi_uri,
            "semantic_raw_mask_png": semantic_raw_uri,
            "semantic_clean_mask_png": semantic_clean_uri,
            "recovery_mask_png": recovery_uri,
            "removed_mask_png": removed_uri,
        }
