"""
Adaptive GVI/VVI backend v0.5

v0.4 is a precision-focused correction of v0.3.

Why this version exists
-----------------------
v0.3 solved most false negatives by allowing soft-semantic and colour-based
recovery, but this made the system too permissive: green signs, sunlit ground
and greenish window glass could enter both GVI and VVI.

Core change
-----------
The pipeline is now:

    semantic vegetation
    - hard negative semantic classes/probabilities
    - sunlit ground / paving guard
    - rectangular panel / window / sign guard
    + controlled contextual recovery only

Definitions
-----------
VVI = cleaned semantic vegetation + context-supported recovery vegetation
GVI = VVI ∩ calibrated green colour mask, optionally requiring semantic support

The old browser tool's tested HSV/HSL thresholds are still used as the
explainable colour layer, but colour alone is no longer allowed to create VVI
by default. This is the key anti-sign/anti-ground change.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Protocol

import cv2
import numpy as np
import pandas as pd


class Segmenter(Protocol):
    model_id: str

    def segment(self, image_bgr: np.ndarray) -> np.ndarray: ...


@dataclass
class SemanticPrediction:
    """Container returned by a semantic model provider.

    hard_mask:
        Argmax vegetation mask.
    vegetation_prob:
        Soft probability map for vegetation labels, range 0..1.
    label_map/id2label:
        Argmax class map and labels.
    ground_prob / artificial_prob / structure_prob / built_prob:
        Optional soft probabilities for non-vegetation groups used as vetoes.
    """

    hard_mask: np.ndarray
    vegetation_prob: Optional[np.ndarray] = None
    label_map: Optional[np.ndarray] = None
    id2label: Optional[dict[int, str]] = None
    ground_prob: Optional[np.ndarray] = None
    artificial_prob: Optional[np.ndarray] = None
    structure_prob: Optional[np.ndarray] = None
    built_prob: Optional[np.ndarray] = None


@dataclass
class Settings:
    # Basic identity
    preset_name: str = "standard"
    recovery_mode: str = "balanced"  # conservative | balanced | aggressive
    ground_guard: str = "strong"  # light | balanced | strong
    artifact_guard: str = "strong"  # light | balanced | strong

    # Legacy-tested GVI HSL/HLS colour layer from the old browser tool.
    # Hue is 0..360, saturation/lightness are 0..100.
    g_hue_min: float = 46
    g_hue_max: float = 109
    g_sat_min: float = 10
    g_light_min: float = 0
    g_light_max: float = 95

    # High-vis / artificial green exclusion.
    exclude_high_vis: bool = True
    hv_hue_min: float = 45
    hv_hue_max: float = 105
    hv_sat_min: float = 42
    hv_light_min: float = 45

    # Broader colour candidates used only when semantic/soft/contextual evidence supports them.
    broad_hue_min: float = 20
    broad_hue_max: float = 135
    broad_sat_min: float = 3
    broad_light_min: float = 2
    broad_light_max: float = 97

    # Muted / grey-green / olive-green support. In v0.4 muted colour can help VVI recovery,
    # but is not counted as GVI by default to reduce paving/glass false positives.
    muted_sat_min: float = 3.0
    muted_sat_max: float = 42
    muted_light_min: float = 5
    muted_light_max: float = 90
    muted_lab_a_green_min: float = 1.0
    muted_exg_norm_min: float = -0.005
    muted_green_ratio_min: float = 0.338
    count_muted_as_gvi: bool = False

    # Seasonal / woody support. These increase VVI, not GVI-green by default.
    include_autumn: bool = False
    include_woody: bool = False
    count_autumn_as_gvi: bool = False

    # Semantic thresholds. v0.4 defaults are stricter than v0.3.
    semantic_prob_min: float = 0.40
    soft_semantic_prob_min: float = 0.12
    min_safe_recovery_prob: float = 0.10

    # Contextual recovery.
    enable_recovery: bool = True
    fence_recovery: bool = True
    recovery_radius_px: int = 12
    component_min_area_px: int = 80
    component_min_area_ratio: float = 0.00016
    high_conf_exg_norm_min: float = 0.026
    high_conf_lab_a_green_min: float = 3.0
    allow_isolated_colour_recovery: bool = False

    # Ground false-positive guard.
    ground_bottom_start: float = 0.48
    ground_light_min: float = 50
    ground_sat_max: float = 36
    ground_weak_exg_norm_max: float = 0.030
    ground_weak_lab_a_green_max: float = 3.2
    ground_texture_max: float = 8.5
    remove_horizontal_ground_components: bool = True

    # v0.5 ground-quality refinement. This specifically targets sunlit/mossy paving
    # or compacted soil on the lower image being classified as grass/vegetation.
    # It does not remove all grass. Lower-image VVI must pass a grass-quality test
    # or a semantic-probability margin test. Tree/shrub/canopy labels are protected.
    enable_ground_quality_guard: bool = True
    ground_filter_mode: str = "balanced"  # off | balanced | strict
    ground_quality_bottom_start: float = 0.46
    front_ground_start: float = 0.68
    ground_quality_exg_min: float = 0.040
    ground_quality_lab_min: float = 2.6
    ground_quality_green_ratio_min: float = 0.345
    ground_quality_sat_min: float = 6.0
    front_ground_exg_min: float = 0.070
    front_ground_lab_min: float = 4.2
    front_ground_green_ratio_min: float = 0.355
    ground_negative_prob_min: float = 0.14
    ground_veg_prob_min: float = 0.52
    ground_veg_prob_margin: float = 0.10
    ground_component_min_area_px: int = 180
    ground_component_min_area_ratio: float = 0.00045
    ground_component_low_quality_ratio: float = 0.54
    ground_component_quality_ratio_max: float = 0.30
    protect_tree_canopy_on_ground: bool = True

    # Artificial sign/window/panel guard.
    hard_negative_veto: bool = True
    negative_prob_min: float = 0.30
    negative_over_veg_ratio: float = 1.05
    built_prob_min: float = 0.28
    panel_fill_ratio_min: float = 0.52
    panel_texture_max: float = 10.5
    panel_area_min_ratio: float = 0.00018
    panel_upper_y_max: float = 0.90
    remove_rectangular_panels: bool = True
    gvi_requires_semantic_support: bool = True

    # Morphology / smoothing.
    min_component_area_px: int = 18
    close_kernel_px: int = 3


# -----------------------------------------------------------------------------
# Settings / presets
# -----------------------------------------------------------------------------


def build_settings(
    preset: str = "standard",
    recovery_mode: str = "balanced",
    ground_guard: str = "strong",
    artifact_guard: str = "strong",
    overrides: Optional[Mapping[str, Any]] = None,
) -> Settings:
    """Build calibrated settings.

    The primary GVI thresholds are inherited from the user's older tested HTML/JS tool:
    - Standard: H46-109, S>=10, L0-95
    - Autumn: H20-110, S>=8, L10-95
    - Strict: H36-163, S>=49, L0-95
    - Shadow: H25-100, S>=10, L5-95
    - Anti-glare: H30-100, S>=15, L15-90
    """

    p = preset.lower().strip().replace(" ", "_").replace("-", "_")
    s = Settings(preset_name=p, recovery_mode=recovery_mode, ground_guard=ground_guard, artifact_guard=artifact_guard)

    if p in {"standard", "legacy_standard"}:
        s.g_hue_min, s.g_hue_max, s.g_sat_min, s.g_light_min, s.g_light_max = 46, 109, 10, 0, 95
        s.broad_hue_min, s.broad_hue_max = 20, 130
    elif p in {"autumn", "autumn_adjusted", "legacy_autumn"}:
        s.g_hue_min, s.g_hue_max, s.g_sat_min, s.g_light_min, s.g_light_max = 20, 110, 8, 10, 95
        s.include_autumn = True
        s.broad_hue_min, s.broad_hue_max = 14, 132
        s.muted_sat_min = 2.5
        s.soft_semantic_prob_min = 0.11
    elif p in {"strict", "strict_filter", "legacy_strict"}:
        s.g_hue_min, s.g_hue_max, s.g_sat_min, s.g_light_min, s.g_light_max = 36, 163, 49, 0, 95
        s.broad_hue_min, s.broad_hue_max = 35, 122
        s.muted_sat_min = 8
        s.count_muted_as_gvi = False
        s.recovery_radius_px = 8
        s.soft_semantic_prob_min = 0.18
        s.semantic_prob_min = 0.45
    elif p in {"shadow", "shadow_boost", "shadow_enhancement", "legacy_shadow"}:
        s.g_hue_min, s.g_hue_max, s.g_sat_min, s.g_light_min, s.g_light_max = 25, 100, 10, 5, 95
        s.broad_hue_min, s.broad_hue_max = 18, 125
        s.muted_sat_min = 2.0
        s.muted_light_min = 2
        s.soft_semantic_prob_min = 0.10
        s.recovery_radius_px = 16
    elif p in {"sunny", "sun", "high_sun"}:
        s.g_hue_min, s.g_hue_max, s.g_sat_min, s.g_light_min, s.g_light_max = 42, 115, 9, 0, 96
        s.hv_sat_min, s.hv_light_min = 45, 52
        s.ground_light_min = 48
        s.ground_sat_max = 40
        s.ground_weak_exg_norm_max = 0.038
        s.ground_weak_lab_a_green_max = 4.0
        s.remove_horizontal_ground_components = True
        s.count_muted_as_gvi = False
    elif p in {"anti_glare", "anti_glare_vest", "high_vis", "high_vis_removal", "legacy_antiglare"}:
        s.g_hue_min, s.g_hue_max, s.g_sat_min, s.g_light_min, s.g_light_max = 30, 100, 15, 15, 90
        s.hv_sat_min, s.hv_light_min = 38, 40
        s.ground_light_min = 48
        s.ground_sat_max = 38
        s.count_muted_as_gvi = False
    elif p in {"winter", "winter_woody"}:
        s.g_hue_min, s.g_hue_max, s.g_sat_min, s.g_light_min, s.g_light_max = 35, 112, 7, 0, 96
        s.include_woody = True
        s.include_autumn = True
        s.count_muted_as_gvi = False
        s.soft_semantic_prob_min = 0.10
        s.recovery_radius_px = 16
        s.broad_hue_min, s.broad_hue_max = 12, 130
    elif p in {"custom"}:
        pass
    else:
        raise ValueError(
            f"Unknown preset '{preset}'. Use standard, autumn, strict, shadow, sunny, anti_glare, winter, or custom."
        )

    apply_recovery_mode(s, recovery_mode)
    apply_ground_guard(s, ground_guard)
    apply_ground_quality_filter(s, s.ground_filter_mode)
    apply_artifact_guard(s, artifact_guard)

    if overrides:
        for key, value in overrides.items():
            if value is None or value == "":
                continue
            if not hasattr(s, key):
                continue
            current = getattr(s, key)
            if isinstance(current, bool):
                setattr(s, key, parse_bool(value))
            elif isinstance(current, int):
                setattr(s, key, int(float(value)))
            elif isinstance(current, float):
                setattr(s, key, float(value))
            else:
                setattr(s, key, str(value))

    return s


def apply_recovery_mode(s: Settings, mode: str) -> None:
    m = mode.lower().strip()
    s.recovery_mode = m
    if m == "conservative":
        s.recovery_radius_px = min(s.recovery_radius_px, 8)
        s.soft_semantic_prob_min = max(s.soft_semantic_prob_min, 0.18)
        s.min_safe_recovery_prob = max(s.min_safe_recovery_prob, 0.15)
        s.component_min_area_px = max(s.component_min_area_px, 130)
        s.muted_sat_min = max(s.muted_sat_min, 5)
        s.high_conf_exg_norm_min = max(s.high_conf_exg_norm_min, 0.034)
        s.high_conf_lab_a_green_min = max(s.high_conf_lab_a_green_min, 4.0)
        s.allow_isolated_colour_recovery = False
    elif m == "balanced":
        # balanced in v0.4 is deliberately more precise than balanced in v0.3
        s.recovery_radius_px = min(s.recovery_radius_px, 14)
        s.soft_semantic_prob_min = max(s.soft_semantic_prob_min, 0.12)
        s.min_safe_recovery_prob = max(s.min_safe_recovery_prob, 0.10)
        s.component_min_area_px = max(s.component_min_area_px, 80)
        s.allow_isolated_colour_recovery = False
    elif m == "aggressive":
        s.recovery_radius_px = max(s.recovery_radius_px, 22)
        s.soft_semantic_prob_min = min(s.soft_semantic_prob_min, 0.075)
        s.min_safe_recovery_prob = min(s.min_safe_recovery_prob, 0.075)
        s.component_min_area_px = min(s.component_min_area_px, 45)
        s.muted_sat_min = min(s.muted_sat_min, 1.8)
        s.high_conf_exg_norm_min = min(s.high_conf_exg_norm_min, 0.016)
        s.high_conf_lab_a_green_min = min(s.high_conf_lab_a_green_min, 1.8)
        # still false by default; can be enabled explicitly if the user wants recall at all costs
        s.allow_isolated_colour_recovery = False
    else:
        raise ValueError("recovery_mode must be conservative, balanced, or aggressive")


def apply_ground_guard(s: Settings, mode: str) -> None:
    m = mode.lower().strip()
    s.ground_guard = m
    if m == "light":
        s.ground_light_min = max(s.ground_light_min, 58)
        s.ground_sat_max = min(s.ground_sat_max, 30)
        s.ground_weak_exg_norm_max = min(s.ground_weak_exg_norm_max, 0.018)
        s.ground_weak_lab_a_green_max = min(s.ground_weak_lab_a_green_max, 1.8)
        s.ground_texture_max = min(s.ground_texture_max, 5.5)
    elif m == "balanced":
        s.ground_light_min = min(s.ground_light_min, 52)
        s.ground_sat_max = max(s.ground_sat_max, 34)
        s.ground_weak_exg_norm_max = max(s.ground_weak_exg_norm_max, 0.026)
        s.ground_weak_lab_a_green_max = max(s.ground_weak_lab_a_green_max, 2.8)
        s.ground_texture_max = max(s.ground_texture_max, 7.5)
    elif m == "strong":
        s.ground_light_min = min(s.ground_light_min, 46)
        s.ground_sat_max = max(s.ground_sat_max, 42)
        s.ground_weak_exg_norm_max = max(s.ground_weak_exg_norm_max, 0.040)
        s.ground_weak_lab_a_green_max = max(s.ground_weak_lab_a_green_max, 4.2)
        s.ground_texture_max = max(s.ground_texture_max, 11.0)
    else:
        raise ValueError("ground_guard must be light, balanced, or strong")


def apply_ground_quality_filter(s: Settings, mode: str) -> None:
    """Tune the new v0.5 grass-vs-mossy-paving filter.

    balanced is the recommended default for the park images you showed.
    strict is useful when lower-frame paths or compacted/mossy surfaces still enter VVI/GVI.
    """
    m = (mode or "balanced").lower().strip()
    s.ground_filter_mode = m
    if m == "off":
        s.enable_ground_quality_guard = False
    elif m == "balanced":
        s.enable_ground_quality_guard = True
        s.ground_quality_bottom_start = min(s.ground_quality_bottom_start, 0.46)
        s.front_ground_start = min(max(s.front_ground_start, 0.66), 0.72)
        s.ground_quality_exg_min = max(s.ground_quality_exg_min, 0.040)
        s.ground_quality_lab_min = max(s.ground_quality_lab_min, 2.6)
        s.ground_quality_green_ratio_min = max(s.ground_quality_green_ratio_min, 0.345)
        s.front_ground_exg_min = max(s.front_ground_exg_min, 0.070)
        s.front_ground_lab_min = max(s.front_ground_lab_min, 4.2)
        s.front_ground_green_ratio_min = max(s.front_ground_green_ratio_min, 0.355)
        s.ground_veg_prob_min = max(s.ground_veg_prob_min, 0.52)
        s.ground_veg_prob_margin = max(s.ground_veg_prob_margin, 0.10)
    elif m == "strict":
        s.enable_ground_quality_guard = True
        s.ground_quality_bottom_start = min(s.ground_quality_bottom_start, 0.42)
        s.front_ground_start = min(max(s.front_ground_start, 0.60), 0.66)
        s.ground_quality_exg_min = max(s.ground_quality_exg_min, 0.055)
        s.ground_quality_lab_min = max(s.ground_quality_lab_min, 3.6)
        s.ground_quality_green_ratio_min = max(s.ground_quality_green_ratio_min, 0.352)
        s.front_ground_exg_min = max(s.front_ground_exg_min, 0.090)
        s.front_ground_lab_min = max(s.front_ground_lab_min, 5.2)
        s.front_ground_green_ratio_min = max(s.front_ground_green_ratio_min, 0.365)
        s.ground_negative_prob_min = min(s.ground_negative_prob_min, 0.10)
        s.ground_veg_prob_min = max(s.ground_veg_prob_min, 0.60)
        s.ground_veg_prob_margin = max(s.ground_veg_prob_margin, 0.16)
        s.ground_component_low_quality_ratio = min(s.ground_component_low_quality_ratio, 0.48)
        s.ground_component_quality_ratio_max = min(s.ground_component_quality_ratio_max, 0.24)
    else:
        raise ValueError("ground_filter_mode must be off, balanced, or strict")


def apply_artifact_guard(s: Settings, mode: str) -> None:
    m = mode.lower().strip()
    s.artifact_guard = m
    if m == "light":
        s.negative_prob_min = max(s.negative_prob_min, 0.40)
        s.negative_over_veg_ratio = max(s.negative_over_veg_ratio, 1.30)
        s.built_prob_min = max(s.built_prob_min, 0.40)
        s.panel_fill_ratio_min = max(s.panel_fill_ratio_min, 0.62)
        s.panel_texture_max = min(s.panel_texture_max, 7.5)
    elif m == "balanced":
        s.negative_prob_min = min(max(s.negative_prob_min, 0.32), 0.36)
        s.negative_over_veg_ratio = min(max(s.negative_over_veg_ratio, 1.08), 1.18)
        s.built_prob_min = min(max(s.built_prob_min, 0.30), 0.36)
        s.panel_fill_ratio_min = min(max(s.panel_fill_ratio_min, 0.54), 0.58)
        s.panel_texture_max = max(s.panel_texture_max, 9.0)
    elif m == "strong":
        s.negative_prob_min = min(s.negative_prob_min, 0.26)
        s.negative_over_veg_ratio = min(s.negative_over_veg_ratio, 0.95)
        s.built_prob_min = min(s.built_prob_min, 0.24)
        s.panel_fill_ratio_min = min(s.panel_fill_ratio_min, 0.50)
        s.panel_texture_max = max(s.panel_texture_max, 12.0)
        s.gvi_requires_semantic_support = True
    else:
        raise ValueError("artifact_guard must be light, balanced, or strong")


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


# -----------------------------------------------------------------------------
# Colour feature extraction
# -----------------------------------------------------------------------------


def hue_in_range(hue_deg: np.ndarray, h_min: float, h_max: float) -> np.ndarray:
    if h_min <= h_max:
        return (hue_deg >= h_min) & (hue_deg <= h_max)
    return (hue_deg >= h_min) | (hue_deg <= h_max)


def image_features(image_bgr: np.ndarray) -> dict[str, np.ndarray]:
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    hls = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HLS).astype(np.float32)
    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)

    hue = hls[:, :, 0] * 2.0
    light = hls[:, :, 1] / 255.0 * 100.0
    sat = hls[:, :, 2] / 255.0 * 100.0

    r = image_rgb[:, :, 0].astype(np.float32)
    g = image_rgb[:, :, 1].astype(np.float32)
    b = image_rgb[:, :, 2].astype(np.float32)
    max_rgb = np.maximum.reduce([r, g, b])
    min_rgb = np.minimum.reduce([r, g, b])
    chroma = max_rgb - min_rgb
    sum_rgb = r + g + b + 1.0

    exg = 2.0 * g - r - b
    exg_norm = exg / sum_rgb
    green_ratio = g / sum_rgb
    lab_a_green = 128.0 - lab[:, :, 1]
    lab_b_yellow = lab[:, :, 2] - 128.0
    value = max_rgb / 255.0 * 100.0

    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    texture = cv2.blur(cv2.magnitude(sobel_x, sobel_y), (7, 7))

    # Local colour variance: useful for separating leafy texture from smooth panels/glass/paving.
    mean = cv2.blur(gray, (9, 9))
    mean_sq = cv2.blur(gray * gray, (9, 9))
    local_std = np.sqrt(np.maximum(mean_sq - mean * mean, 0))

    return {
        "rgb": image_rgb,
        "hue": hue,
        "sat": sat,
        "light": light,
        "r": r,
        "g": g,
        "b": b,
        "max_rgb": max_rgb,
        "min_rgb": min_rgb,
        "chroma": chroma,
        "exg": exg,
        "exg_norm": exg_norm,
        "green_ratio": green_ratio,
        "lab_a_green": lab_a_green,
        "lab_b_yellow": lab_b_yellow,
        "value": value,
        "texture": texture,
        "local_std": local_std,
    }


def colour_masks(image_bgr: np.ndarray, settings: Settings) -> dict[str, np.ndarray]:
    f = image_features(image_bgr)
    hue, sat, light = f["hue"], f["sat"], f["light"]
    r, g, b = f["r"], f["g"], f["b"]
    exg_norm = f["exg_norm"]
    lab_a_green = f["lab_a_green"]
    green_ratio = f["green_ratio"]
    chroma = f["chroma"]
    lab_b_yellow = f["lab_b_yellow"]
    value = f["value"]

    legacy_green = (
        hue_in_range(hue, settings.g_hue_min, settings.g_hue_max)
        & (sat >= settings.g_sat_min)
        & (light >= settings.g_light_min)
        & (light <= settings.g_light_max)
    )

    neon_like = (exg_norm >= 0.075) | ((sat >= 68) & (light >= 55)) | ((sat >= 75) & (value >= 70))
    high_vis = (
        settings.exclude_high_vis
        & hue_in_range(hue, settings.hv_hue_min, settings.hv_hue_max)
        & (sat >= settings.hv_sat_min)
        & (light >= settings.hv_light_min)
        & neon_like
    )

    strong_green = (
        legacy_green
        & ~high_vis
        & (
            (exg_norm >= settings.high_conf_exg_norm_min)
            | (lab_a_green >= settings.high_conf_lab_a_green_min)
            | ((g >= r * 1.03) & (g >= b * 1.03))
        )
    )

    broad_green = (
        ~high_vis
        & hue_in_range(hue, settings.broad_hue_min, settings.broad_hue_max)
        & (sat >= settings.broad_sat_min)
        & (light >= settings.broad_light_min)
        & (light <= settings.broad_light_max)
        & ((green_ratio >= 0.330) | (g >= r * 0.94) | (g >= b * 0.94) | (lab_a_green >= -0.5))
    )

    muted_green = (
        ~high_vis
        & hue_in_range(hue, 24, 122)
        & (sat >= settings.muted_sat_min)
        & (sat <= settings.muted_sat_max)
        & (light >= settings.muted_light_min)
        & (light <= settings.muted_light_max)
        & (chroma >= 4.0)
        & (
            (lab_a_green >= settings.muted_lab_a_green_min)
            | (exg_norm >= settings.muted_exg_norm_min)
            | (green_ratio >= settings.muted_green_ratio_min)
        )
        & ~((np.abs(r - g) < 3.0) & (np.abs(g - b) < 3.0))
    )

    olive_dry = (
        ~high_vis
        & hue_in_range(hue, 16, 80)
        & (sat >= 4.0)
        & (sat <= 48)
        & (light >= 7)
        & (light <= 84)
        & (chroma >= 6)
        & (g >= b * 0.82)
        & (r >= b * 0.78)
        & (lab_b_yellow >= -7)
        & (lab_a_green >= -5)
    )

    autumn = (
        settings.include_autumn
        & ~high_vis
        & hue_in_range(hue, 14, 72)
        & (sat >= 5)
        & (sat <= 68)
        & (light >= 8)
        & (light <= 92)
        & (r >= g * 0.70)
        & (g >= b * 0.68)
        & (lab_b_yellow >= -5)
    )

    woody = (
        settings.include_woody
        & ~high_vis
        & hue_in_range(hue, 10, 58)
        & (sat >= 5)
        & (sat <= 46)
        & (light >= 10)
        & (light <= 72)
        & (chroma >= 8)
        & ~((b > r * 1.12) & (b > g * 1.08))
    )

    gvi_colour = legacy_green | (muted_green if settings.count_muted_as_gvi else False)
    if settings.count_autumn_as_gvi:
        gvi_colour = gvi_colour | autumn
    gvi_colour = gvi_colour & ~high_vis

    recovery_colour = (legacy_green | broad_green | muted_green | olive_dry | autumn | woody) & ~high_vis

    return {
        **f,
        "legacy_green": legacy_green,
        "strong_green": strong_green,
        "broad_green": broad_green,
        "muted_green": muted_green,
        "olive_dry": olive_dry,
        "autumn": autumn,
        "woody": woody,
        "gvi_colour": gvi_colour,
        "recovery_colour": recovery_colour,
        "high_vis": high_vis,
    }


# -----------------------------------------------------------------------------
# Semantic metadata helpers
# -----------------------------------------------------------------------------


def normalise_label(label: str) -> str:
    return str(label).lower().replace("_", " ").replace("-", " ").strip()


def label_matches(label: str, keyword: str) -> bool:
    """Word-aware label matching.

    Avoid unsafe substring matches such as "ground" matching "background".
    Handles labels like "building;edifice" and phrases like "traffic sign".
    """
    import re

    label_n = normalise_label(label)
    key = normalise_label(keyword)
    label_tokens = re.findall(r"[a-z0-9]+", label_n)
    key_tokens = re.findall(r"[a-z0-9]+", key)
    if not key_tokens:
        return False
    if len(key_tokens) == 1:
        return key_tokens[0] in label_tokens
    # phrase match across normalized whitespace / punctuation
    label_joined = " ".join(label_tokens)
    key_joined = " ".join(key_tokens)
    return f" {key_joined} " in f" {label_joined} "


def label_keyword_mask(pred: Optional[SemanticPrediction], include_keywords: Iterable[str]) -> Optional[np.ndarray]:
    if pred is None or pred.label_map is None or pred.id2label is None:
        return None
    keywords = [normalise_label(k) for k in include_keywords]
    keep_ids = []
    for idx, label in pred.id2label.items():
        label_n = normalise_label(label)
        if any(label_matches(label_n, k) for k in keywords):
            keep_ids.append(int(idx))
    if not keep_ids:
        return np.zeros_like(pred.label_map, dtype=bool)
    return np.isin(pred.label_map, keep_ids)


GROUND_LABEL_KEYWORDS = {
    "road", "sidewalk", "pavement", "street", "floor", "path", "runway",
    "earth", "sand", "dirt", "ground", "parking", "plaza",
}

STRUCTURE_LABEL_KEYWORDS = {
    "fence", "railing", "gate", "grille", "bars",
}

HARD_ARTIFACT_LABEL_KEYWORDS = {
    "person", "car", "truck", "bus", "train", "bicycle", "motorcycle", "rider",
    "traffic sign", "signboard", "sign", "billboard", "poster", "screen", "monitor",
    "window", "windowpane", "glass", "mirror", "door", "building", "house", "skyscraper",
    "wall", "awning", "shop", "store", "pole", "traffic light", "sky",
}

BUILT_WINDOW_LABEL_KEYWORDS = {
    "window", "windowpane", "glass", "mirror", "building", "house", "skyscraper", "wall", "door", "shop", "store", "awning",
}

SIGN_LABEL_KEYWORDS = {
    "traffic sign", "signboard", "sign", "billboard", "poster", "screen", "monitor", "advertisement", "banner",
}

TREE_CANOPY_LABEL_KEYWORDS = {
    "tree", "palm", "bush", "shrub", "trunk", "branch"
}

GRASS_GROUND_LABEL_KEYWORDS = {
    "grass", "field", "meadow", "lawn", "plant", "flower", "vegetation"
}


def safe_prob(prob: Optional[np.ndarray], shape: tuple[int, int]) -> np.ndarray:
    if prob is None:
        return np.zeros(shape, dtype=np.float32)
    if prob.shape[:2] != shape:
        h, w = shape
        return cv2.resize(prob.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    return prob.astype(np.float32)


# -----------------------------------------------------------------------------
# Mask operations
# -----------------------------------------------------------------------------


def morph_close(mask: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    if kernel_size <= 1:
        return mask.astype(bool)
    k = np.ones((kernel_size, kernel_size), np.uint8)
    out = cv2.morphologyEx(mask.astype(np.uint8) * 255, cv2.MORPH_CLOSE, k)
    return out > 127


def morph_open(mask: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    if kernel_size <= 1:
        return mask.astype(bool)
    k = np.ones((kernel_size, kernel_size), np.uint8)
    out = cv2.morphologyEx(mask.astype(np.uint8) * 255, cv2.MORPH_OPEN, k)
    return out > 127


def dilate_mask(mask: np.ndarray, radius_px: int) -> np.ndarray:
    if radius_px <= 0:
        return mask.astype(bool)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius_px * 2 + 1, radius_px * 2 + 1))
    return cv2.dilate(mask.astype(np.uint8), k, iterations=1).astype(bool)


def remove_small_components(mask: np.ndarray, min_area_px: int) -> np.ndarray:
    if min_area_px <= 1:
        return mask.astype(bool)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    out = np.zeros(mask.shape, dtype=bool)
    for idx in range(1, n):
        if stats[idx, cv2.CC_STAT_AREA] >= min_area_px:
            out[labels == idx] = True
    return out


def component_context_recovery(
    candidate: np.ndarray,
    allowed_context: np.ndarray,
    high_conf_colour: np.ndarray,
    artifact_context: np.ndarray,
    image_shape: tuple[int, int],
    settings: Settings,
) -> np.ndarray:
    """Keep only colour components that have real semantic/contextual support.

    v0.3 allowed isolated strong-colour components. That recovered hidden vegetation,
    but also recovered green signboards. v0.4 disables isolated colour recovery unless
    explicitly requested.
    """

    h, w = image_shape
    min_area = max(settings.component_min_area_px, int(settings.component_min_area_ratio * h * w))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(candidate.astype(np.uint8), connectivity=8)
    out = np.zeros(candidate.shape, dtype=bool)
    for idx in range(1, n):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        comp = labels == idx
        artifact_ratio = float((comp & artifact_context).sum()) / max(1, area)
        if artifact_ratio >= 0.10:
            continue
        overlap = float((comp & allowed_context).sum()) / max(1, area)
        high_conf_ratio = float((comp & high_conf_colour).sum()) / max(1, area)
        if overlap >= 0.020:
            out[comp] = True
        elif settings.allow_isolated_colour_recovery and high_conf_ratio >= 0.55:
            out[comp] = True
    return out


def semantic_negative_veto(
    shape: tuple[int, int],
    masks: Mapping[str, np.ndarray],
    settings: Settings,
    pred: Optional[SemanticPrediction],
) -> np.ndarray:
    if pred is None:
        return np.zeros(shape, dtype=bool)

    veg_prob = safe_prob(pred.vegetation_prob, shape)
    artificial_prob = safe_prob(pred.artificial_prob, shape)
    ground_prob = safe_prob(pred.ground_prob, shape)
    built_prob = safe_prob(pred.built_prob, shape)

    hard_artifact = label_keyword_mask(pred, HARD_ARTIFACT_LABEL_KEYWORDS)
    if hard_artifact is None:
        hard_artifact = np.zeros(shape, dtype=bool)
    hard_sign = label_keyword_mask(pred, SIGN_LABEL_KEYWORDS)
    if hard_sign is None:
        hard_sign = np.zeros(shape, dtype=bool)
    hard_built = label_keyword_mask(pred, BUILT_WINDOW_LABEL_KEYWORDS)
    if hard_built is None:
        hard_built = np.zeros(shape, dtype=bool)

    # Do not let slight model uncertainty remove real vegetation; require negative classes
    # to be clearly stronger, or hard sign/window/building labels.
    prob_veto = (
        ((artificial_prob >= settings.negative_prob_min) | (built_prob >= settings.built_prob_min))
        & ((artificial_prob + built_prob) >= veg_prob * settings.negative_over_veg_ratio)
    )

    # Ground probability is only a veto if colour looks weak/smooth/ground-like.
    weak_colour = (
        (masks["exg_norm"] <= settings.ground_weak_exg_norm_max)
        & (masks["lab_a_green"] <= settings.ground_weak_lab_a_green_max)
        & (masks["sat"] <= settings.ground_sat_max)
        & ~masks["strong_green"]
    )
    ground_prob_veto = (
        (ground_prob >= settings.negative_prob_min)
        & (ground_prob >= veg_prob * settings.negative_over_veg_ratio)
        & weak_colour
    )

    hard_veto = (hard_sign | hard_built | prob_veto | ground_prob_veto) if settings.hard_negative_veto else (prob_veto | ground_prob_veto)
    return hard_veto


def ground_false_positive_mask(
    shape: tuple[int, int],
    masks: Mapping[str, np.ndarray],
    settings: Settings,
    pred: Optional[SemanticPrediction] = None,
) -> np.ndarray:
    h, w = shape
    hue = masks["hue"]
    sat = masks["sat"]
    light = masks["light"]
    exg_norm = masks["exg_norm"]
    lab_a_green = masks["lab_a_green"]
    strong_green = masks["strong_green"]
    muted_green = masks["muted_green"]
    texture = masks["texture"]

    yy = np.arange(h, dtype=np.float32)[:, None] / max(1, h - 1)
    bottom_zone = yy >= settings.ground_bottom_start

    weak_veg_colour = (
        (exg_norm <= settings.ground_weak_exg_norm_max)
        & (lab_a_green <= settings.ground_weak_lab_a_green_max)
        & ~strong_green
        & ~(muted_green & (lab_a_green >= settings.high_conf_lab_a_green_min + 0.5))
    )

    smooth_bright_ground_like = (
        bottom_zone
        & hue_in_range(hue, 18, 108)
        & (light >= settings.ground_light_min)
        & (sat <= settings.ground_sat_max)
        & (texture <= settings.ground_texture_max)
    )

    sunlit_ground_like = (
        bottom_zone
        & hue_in_range(hue, 18, 108)
        & (light >= settings.ground_light_min)
        & (sat <= settings.ground_sat_max)
        & (weak_veg_colour | smooth_bright_ground_like)
    )

    ground_label = label_keyword_mask(pred, GROUND_LABEL_KEYWORDS)
    if ground_label is None:
        ground_label = np.zeros(shape, dtype=bool)
    ground_label_weak = ground_label & (weak_veg_colour | smooth_bright_ground_like)

    negative_veto = semantic_negative_veto(shape, masks, settings, pred)

    return sunlit_ground_like | ground_label_weak | negative_veto | masks["high_vis"]


def remove_horizontal_ground_components(mask: np.ndarray, masks: Mapping[str, np.ndarray], settings: Settings) -> np.ndarray:
    """Remove large lower-frame components that look like smooth sunlit paving."""
    if not settings.remove_horizontal_ground_components:
        return mask.astype(bool)

    h, w = mask.shape
    yy = np.arange(h, dtype=np.float32)[:, None] / max(1, h - 1)
    bottom = yy >= settings.ground_bottom_start
    weak = (
        (masks["exg_norm"] <= settings.ground_weak_exg_norm_max)
        & (masks["lab_a_green"] <= settings.ground_weak_lab_a_green_max)
        & (masks["sat"] <= settings.ground_sat_max)
        & ~masks["strong_green"]
    )
    smooth = masks.get("texture", np.zeros_like(mask, dtype=np.float32)) <= settings.ground_texture_max
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    out = mask.copy().astype(bool)
    min_area = max(180, int(0.00045 * h * w))
    for idx in range(1, n):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        comp = labels == idx
        bottom_ratio = float((comp & bottom).sum()) / max(1, area)
        weak_ratio = float((comp & weak).sum()) / max(1, area)
        strong_ratio = float((comp & masks["strong_green"]).sum()) / max(1, area)
        smooth_ratio = float((comp & smooth).sum()) / max(1, area)
        comp_w = int(stats[idx, cv2.CC_STAT_WIDTH])
        comp_h = int(stats[idx, cv2.CC_STAT_HEIGHT])
        horizontal = comp_w >= comp_h * 1.45
        if bottom_ratio >= 0.62 and horizontal:
            if (weak_ratio >= 0.58 and strong_ratio <= 0.12) or (smooth_ratio >= 0.78 and strong_ratio <= 0.18):
                out[comp] = False
    return out



def ground_quality_removed_mask(
    vvi_mask: np.ndarray,
    masks: Mapping[str, np.ndarray],
    settings: Settings,
    pred: Optional[SemanticPrediction],
) -> np.ndarray:
    """Remove lower-frame VVI that looks like mossy/sunlit paving rather than grass.

    This v0.5 guard is different from the older ground guard:
    - older guard: remove obviously smooth/bright ground before VVI is built;
    - this guard: after the semantic model has labelled something as vegetation,
      retest lower-image components with a stricter grass-quality and probability-margin rule.

    The goal is to suppress false grass on paths/compacted soil while preserving real lawns.
    """
    if (not settings.enable_ground_quality_guard) or settings.ground_filter_mode == "off":
        return np.zeros(vvi_mask.shape, dtype=bool)

    h, w = vvi_mask.shape
    yy = np.arange(h, dtype=np.float32)[:, None] / max(1, h - 1)
    lower_zone = yy >= settings.ground_quality_bottom_start
    front_zone = yy >= settings.front_ground_start

    hue = masks["hue"]
    sat = masks["sat"]
    exg_norm = masks["exg_norm"]
    lab_a_green = masks["lab_a_green"]
    green_ratio = masks["green_ratio"]
    strong_green = masks["strong_green"]

    # Balanced quality: a pixel has enough green vegetation signal for mid/lower grass.
    green_hue = hue_in_range(hue, 24, 124)
    ground_quality = (
        green_hue
        & (sat >= settings.ground_quality_sat_min)
        & (
            ((exg_norm >= settings.ground_quality_exg_min) & (green_ratio >= settings.ground_quality_green_ratio_min))
            | (lab_a_green >= settings.ground_quality_lab_min)
            | (strong_green & (exg_norm >= settings.ground_quality_exg_min * 0.65))
        )
    )

    # Near-camera foreground must be more convincing; this is where paving/moss false positives dominate.
    front_quality = (
        green_hue
        & (sat >= settings.ground_quality_sat_min + 1.5)
        & (
            ((exg_norm >= settings.front_ground_exg_min) & (green_ratio >= settings.front_ground_green_ratio_min))
            | (lab_a_green >= settings.front_ground_lab_min)
            | (strong_green & (exg_norm >= settings.ground_quality_exg_min))
        )
    )

    veg_prob = safe_prob(pred.vegetation_prob if pred is not None else None, vvi_mask.shape)
    ground_prob = safe_prob(pred.ground_prob if pred is not None else None, vvi_mask.shape)
    artificial_prob = safe_prob(pred.artificial_prob if pred is not None else None, vvi_mask.shape)
    built_prob = safe_prob(pred.built_prob if pred is not None else None, vvi_mask.shape)
    neg_prob = np.maximum.reduce([ground_prob, artificial_prob, built_prob])

    tree_canopy = label_keyword_mask(pred, TREE_CANOPY_LABEL_KEYWORDS)
    if tree_canopy is None:
        tree_canopy = np.zeros(vvi_mask.shape, dtype=bool)
    grass_label = label_keyword_mask(pred, GRASS_GROUND_LABEL_KEYWORDS)
    if grass_label is None:
        grass_label = np.zeros(vvi_mask.shape, dtype=bool)
    ground_label = label_keyword_mask(pred, GROUND_LABEL_KEYWORDS)
    if ground_label is None:
        ground_label = np.zeros(vvi_mask.shape, dtype=bool)

    # Protect tree/shrub canopy/trunks even if they extend into lower frame. Ground filtering is aimed at
    # grass/paving ambiguity, not woody vegetation.
    protected = tree_canopy if settings.protect_tree_canopy_on_ground else np.zeros_like(vvi_mask, dtype=bool)

    semantic_margin_ok = (
        (veg_prob >= settings.ground_veg_prob_min)
        & ((veg_prob - neg_prob) >= settings.ground_veg_prob_margin)
        & (ground_quality | grass_label)
    )

    # Pixel-level low-quality risk. We only remove lower-zone pixels that are not tree/canopy and
    # either carry explicit ground probability/label or fail the stricter front-ground quality test.
    weak_lower = lower_zone & ~ground_quality
    weak_front = front_zone & ~front_quality
    negative_ground_risk = (ground_prob >= settings.ground_negative_prob_min) | ground_label
    colour_ground_risk = (
        (exg_norm <= settings.ground_weak_exg_norm_max)
        & (lab_a_green <= settings.ground_weak_lab_a_green_max)
        & (sat <= settings.ground_sat_max)
        & ~strong_green
    )

    pixel_remove = (
        vvi_mask
        & lower_zone
        & ~protected
        & ~semantic_margin_ok
        & (
            (weak_lower & (negative_ground_risk | colour_ground_risk))
            | weak_front
            | ((neg_prob >= settings.ground_negative_prob_min) & (neg_prob >= veg_prob - 0.03) & ~ground_quality)
        )
    )

    # Component-level reinforcement: remove connected lower-frame components where most pixels fail
    # grass quality and the component shape/location is ground-plane-like. To avoid deleting true lawns,
    # the component must have little high-quality grass evidence.
    candidate_for_components = vvi_mask & lower_zone & ~protected
    n, labels, stats, _ = cv2.connectedComponentsWithStats(candidate_for_components.astype(np.uint8), connectivity=8)
    comp_remove = np.zeros_like(vvi_mask, dtype=bool)
    min_area = max(settings.ground_component_min_area_px, int(settings.ground_component_min_area_ratio * h * w))
    for idx in range(1, n):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        comp = labels == idx
        bottom_ratio = float((comp & lower_zone).sum()) / max(1, area)
        front_ratio = float((comp & front_zone).sum()) / max(1, area)
        low_quality_ratio = float((comp & ~ground_quality).sum()) / max(1, area)
        front_low_ratio = float((comp & front_zone & ~front_quality).sum()) / max(1, (comp & front_zone).sum()) if (comp & front_zone).sum() else 0.0
        quality_ratio = float((comp & ground_quality).sum()) / max(1, area)
        strong_ratio = float((comp & strong_green).sum()) / max(1, area)
        ground_prob_mean = float(np.mean(ground_prob[comp])) if area else 0.0
        neg_prob_mean = float(np.mean(neg_prob[comp])) if area else 0.0
        veg_prob_mean = float(np.mean(veg_prob[comp])) if area else 0.0
        bw = int(stats[idx, cv2.CC_STAT_WIDTH])
        bh = int(stats[idx, cv2.CC_STAT_HEIGHT])
        horizontal = bw >= bh * 1.25

        weak_component = (
            bottom_ratio >= 0.62
            and horizontal
            and low_quality_ratio >= settings.ground_component_low_quality_ratio
            and quality_ratio <= settings.ground_component_quality_ratio_max
            and strong_ratio <= 0.22
        )
        prob_component = (
            (ground_prob_mean >= settings.ground_negative_prob_min or neg_prob_mean >= settings.ground_negative_prob_min)
            and (veg_prob_mean <= ground_prob_mean + settings.ground_veg_prob_margin or low_quality_ratio >= 0.50)
            and quality_ratio <= 0.38
        )
        front_component = front_ratio >= 0.35 and front_low_ratio >= 0.60 and quality_ratio <= 0.42 and strong_ratio <= 0.26

        if weak_component or prob_component or front_component:
            # Remove only the weak pixels unless the whole component is very low quality.
            if quality_ratio <= 0.18 or prob_component:
                comp_remove[comp] = True
            else:
                comp_remove[comp & (~ground_quality | front_zone & ~front_quality)] = True

    return pixel_remove | comp_remove

def rectangular_panel_guard(
    mask: np.ndarray,
    masks: Mapping[str, np.ndarray],
    settings: Settings,
    pred: Optional[SemanticPrediction],
    external_semantic_context: np.ndarray,
) -> np.ndarray:
    """Detect green signs/window panes/panels that survive semantic and colour filters.

    The guard is component-based. It removes mostly rectangular, smooth, panel-like
    regions in upper/middle image areas, especially where model metadata says built/sign.
    """
    if not settings.remove_rectangular_panels:
        return np.zeros(mask.shape, dtype=bool)

    h, w = mask.shape
    hard_artifact = label_keyword_mask(pred, HARD_ARTIFACT_LABEL_KEYWORDS)
    if hard_artifact is None:
        hard_artifact = np.zeros(mask.shape, dtype=bool)
    hard_sign = label_keyword_mask(pred, SIGN_LABEL_KEYWORDS)
    if hard_sign is None:
        hard_sign = np.zeros(mask.shape, dtype=bool)
    hard_built = label_keyword_mask(pred, BUILT_WINDOW_LABEL_KEYWORDS)
    if hard_built is None:
        hard_built = np.zeros(mask.shape, dtype=bool)

    artificial_prob = safe_prob(pred.artificial_prob if pred is not None else None, mask.shape)
    built_prob = safe_prob(pred.built_prob if pred is not None else None, mask.shape)

    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    removed = np.zeros(mask.shape, dtype=bool)
    min_area = max(48, int(settings.panel_area_min_ratio * h * w))

    for idx in range(1, n):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        x = int(stats[idx, cv2.CC_STAT_LEFT])
        y = int(stats[idx, cv2.CC_STAT_TOP])
        bw = int(stats[idx, cv2.CC_STAT_WIDTH])
        bh = int(stats[idx, cv2.CC_STAT_HEIGHT])
        if bw <= 2 or bh <= 2:
            continue
        comp = labels == idx
        bbox_area = max(1, bw * bh)
        fill_ratio = area / bbox_area
        y_bottom = (y + bh) / max(1, h)
        if y_bottom > settings.panel_upper_y_max:
            # Lower-frame smooth components are handled by ground guard, not panel guard.
            continue

        tex = float(np.median(masks["texture"][comp]))
        local_std = float(np.median(masks["local_std"][comp]))
        sat_median = float(np.median(masks["sat"][comp]))
        light_median = float(np.median(masks["light"][comp]))
        artifact_ratio = float((comp & hard_artifact).sum()) / max(1, area)
        sign_ratio = float((comp & hard_sign).sum()) / max(1, area)
        built_ratio = float((comp & hard_built).sum()) / max(1, area)
        prob_ratio = float(np.median((artificial_prob + built_prob)[comp]))
        context_ratio = float((comp & external_semantic_context).sum()) / max(1, area)
        aspect = max(bw / max(1, bh), bh / max(1, bw))

        rectangular = fill_ratio >= settings.panel_fill_ratio_min and aspect >= 1.15
        smooth_panel = tex <= settings.panel_texture_max and local_std <= max(10.0, settings.panel_texture_max * 1.4)
        vivid_or_glassy = (sat_median >= 18 and light_median >= 18) or (light_median >= 58)

        strong_artifact_evidence = artifact_ratio >= 0.18 or sign_ratio >= 0.08 or built_ratio >= 0.28 or prob_ratio >= settings.built_prob_min
        shape_artifact_evidence = rectangular and smooth_panel and vivid_or_glassy and context_ratio <= 0.05

        if strong_artifact_evidence and (rectangular or smooth_panel):
            removed[comp] = True
        elif shape_artifact_evidence and area >= min_area * 1.2:
            removed[comp] = True
    return removed


# -----------------------------------------------------------------------------
# IO helpers
# -----------------------------------------------------------------------------


def load_semantic_mask(mask_path: Optional[Path], image_shape: tuple[int, int]) -> Optional[np.ndarray]:
    if mask_path is None or not mask_path.exists():
        return None
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        return None
    h, w = image_shape
    if mask.shape[:2] != (h, w):
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
    return mask > 127


def save_binary_mask(mask: np.ndarray, path: Path) -> None:
    cv2.imwrite(str(path), mask.astype(np.uint8) * 255)


def overlay_masks(
    image_bgr: np.ndarray,
    gvi_mask: np.ndarray,
    raw_vvi_mask: np.ndarray,
    recovery_mask: np.ndarray,
    removed_mask: np.ndarray,
) -> np.ndarray:
    """Create diagnostic overlay.

    BGR colours:
      - green: GVI-green vegetation
      - cyan/blue: semantic VVI-only vegetation
      - orange: recovered VVI-only vegetation
      - red: removed sign/window/ground/high-vis artifacts
    """

    overlay = image_bgr.copy().astype(np.float32)
    green = np.array([60, 230, 45], dtype=np.float32)
    cyan = np.array([235, 175, 20], dtype=np.float32)
    orange = np.array([20, 130, 255], dtype=np.float32)
    red = np.array([40, 40, 255], dtype=np.float32)

    raw_vvi_only = raw_vvi_mask & ~gvi_mask
    recovery_only = recovery_mask & ~gvi_mask

    overlay[raw_vvi_only] = overlay[raw_vvi_only] * 0.42 + cyan * 0.58
    overlay[recovery_only] = overlay[recovery_only] * 0.36 + orange * 0.64
    overlay[gvi_mask] = overlay[gvi_mask] * 0.34 + green * 0.66
    overlay[removed_mask] = overlay[removed_mask] * 0.28 + red * 0.72
    return np.clip(overlay, 0, 255).astype(np.uint8)


def resolve_semantic_prediction(
    image_bgr: np.ndarray,
    semantic_mask: Optional[np.ndarray],
    segmenter: Optional[Segmenter],
) -> tuple[Optional[SemanticPrediction], str]:
    if semantic_mask is not None:
        return SemanticPrediction(hard_mask=semantic_mask.astype(bool)), "external_mask"
    if segmenter is None:
        return None, "none"

    if hasattr(segmenter, "predict"):
        pred = segmenter.predict(image_bgr)  # type: ignore[attr-defined]
        return pred, f"model:{getattr(segmenter, 'model_id', 'unknown')}"

    mask = segmenter.segment(image_bgr)
    return SemanticPrediction(hard_mask=mask.astype(bool)), f"model:{getattr(segmenter, 'model_id', 'unknown')}"


def analyse_array(
    image_bgr: np.ndarray,
    image_name: str,
    output_dir: Path,
    settings: Settings,
    semantic_mask: Optional[np.ndarray] = None,
    segmenter: Optional[Segmenter] = None,
    save_outputs: bool = True,
) -> dict[str, Any]:
    h, w = image_bgr.shape[:2]
    total = h * w
    masks = colour_masks(image_bgr, settings)
    pred, semantic_source = resolve_semantic_prediction(image_bgr, semantic_mask, segmenter)

    if pred is not None:
        raw_semantic = pred.hard_mask.astype(bool)
        if raw_semantic.shape[:2] != (h, w):
            raw_semantic = cv2.resize(raw_semantic.astype(np.uint8) * 255, (w, h), interpolation=cv2.INTER_NEAREST) > 127

        if pred.vegetation_prob is not None:
            veg_prob = safe_prob(pred.vegetation_prob, (h, w))
            # high enough probability can fix hard argmax failures, but this is vetoed by negative classes later
            raw_semantic = raw_semantic | (veg_prob >= settings.semantic_prob_min)
            soft_semantic = veg_prob >= settings.soft_semantic_prob_min
            safe_soft_semantic = veg_prob >= settings.min_safe_recovery_prob
        else:
            veg_prob = np.zeros((h, w), dtype=np.float32)
            soft_semantic = raw_semantic
            safe_soft_semantic = raw_semantic

        removed_initial = ground_false_positive_mask((h, w), masks, settings, pred)
        raw_semantic_clean = raw_semantic & ~removed_initial
        raw_semantic_clean = remove_small_components(morph_close(raw_semantic_clean, settings.close_kernel_px), settings.min_component_area_px)

        semantic_context = dilate_mask(raw_semantic_clean, settings.recovery_radius_px)
        external_context_for_panel = semantic_context & ~raw_semantic_clean

        if settings.enable_recovery:
            hard_artifact = semantic_negative_veto((h, w), masks, settings, pred)
            high_conf_colour = masks["strong_green"] | (
                masks["muted_green"]
                & ((masks["exg_norm"] >= settings.high_conf_exg_norm_min) | (masks["lab_a_green"] >= settings.high_conf_lab_a_green_min))
            )

            # Recovery must have semantic support or be next to semantic vegetation. Colour alone is not enough.
            soft_colour_recovery = safe_soft_semantic & masks["recovery_colour"] & ~hard_artifact
            near_semantic_recovery = semantic_context & masks["recovery_colour"] & soft_semantic & ~hard_artifact

            structure_mask = label_keyword_mask(pred, STRUCTURE_LABEL_KEYWORDS)
            if structure_mask is None:
                structure_mask = np.zeros((h, w), dtype=bool)
            fence_recovery = (
                settings.fence_recovery
                & structure_mask
                & masks["recovery_colour"]
                & (safe_soft_semantic | semantic_context)
                & ~hard_artifact
            )

            allowed_context = semantic_context | safe_soft_semantic
            component_recovery = component_context_recovery(
                candidate=masks["recovery_colour"],
                allowed_context=allowed_context,
                high_conf_colour=high_conf_colour,
                artifact_context=hard_artifact | removed_initial,
                image_shape=(h, w),
                settings=settings,
            )

            recovery_mask = (soft_colour_recovery | near_semantic_recovery | fence_recovery | component_recovery)
            recovery_mask = recovery_mask & ~raw_semantic_clean & ~removed_initial
            recovery_mask = remove_small_components(morph_close(recovery_mask, settings.close_kernel_px), settings.min_component_area_px)
        else:
            recovery_mask = np.zeros((h, w), dtype=bool)

        vvi_candidate = raw_semantic_clean | recovery_mask
        vvi_candidate = remove_horizontal_ground_components(vvi_candidate, masks, settings)

        # v0.5: second-pass lower-frame ground-quality check. This removes mossy/sunlit
        # paving or compacted soil that the semantic model calls grass/vegetation.
        ground_quality_removed = ground_quality_removed_mask(vvi_candidate, masks, settings, pred)
        vvi_candidate = vvi_candidate & ~ground_quality_removed

        # Component-level panel/sign/window guard after VVI candidate is built.
        panel_removed = rectangular_panel_guard(vvi_candidate, masks, settings, pred, external_context_for_panel)
        removed_mask = removed_initial | ground_quality_removed | panel_removed

        vvi_mask = vvi_candidate & ~removed_mask
        recovery_mask = recovery_mask & vvi_mask
        raw_semantic_clean = raw_semantic_clean & vvi_mask

        # GVI is stricter than VVI. If required, recovery must still be semantically supported.
        if settings.gvi_requires_semantic_support:
            gvi_semantic_support = raw_semantic_clean | (recovery_mask & (safe_soft_semantic | semantic_context))
        else:
            gvi_semantic_support = vvi_mask
        gvi_mask = gvi_semantic_support & masks["gvi_colour"] & ~removed_mask
        mode = "semantic_vvi_v0_5_ground_refined_precision"
    else:
        # Colour-only fallback: deliberately conservative in v0.4.
        removed_initial = ground_false_positive_mask((h, w), masks, settings, None)
        raw_semantic = np.zeros((h, w), dtype=bool)
        raw_semantic_clean = np.zeros((h, w), dtype=bool)
        recovery_mask = masks["strong_green"] & ~removed_initial
        recovery_mask = remove_small_components(morph_close(recovery_mask, settings.close_kernel_px), max(80, settings.min_component_area_px))
        vvi_mask = remove_horizontal_ground_components(recovery_mask, masks, settings)
        ground_quality_removed = ground_quality_removed_mask(vvi_mask, masks, settings, None)
        vvi_mask = vvi_mask & ~ground_quality_removed
        removed_mask = removed_initial | ground_quality_removed
        gvi_mask = vvi_mask & masks["gvi_colour"]
        mode = "colour_proxy_v0_5_ground_refined_conservative"

    raw_semantic_pct = float(raw_semantic.sum() / total * 100) if pred is not None else 0.0
    raw_semantic_clean_pct = float(raw_semantic_clean.sum() / total * 100)
    recovery_pct = float(recovery_mask.sum() / total * 100)
    gvi_pct = float(gvi_mask.sum() / total * 100)
    vvi_pct = float(vvi_mask.sum() / total * 100)
    high_vis_pct = float(masks["high_vis"].sum() / total * 100)
    removed_pct = float(removed_mask.sum() / total * 100)
    ground_quality_removed_pct = float(ground_quality_removed.sum() / total * 100) if "ground_quality_removed" in locals() else 0.0
    panel_removed_pct = float(panel_removed.sum() / total * 100) if "panel_removed" in locals() else 0.0
    muted_pct = float(masks["muted_green"].sum() / total * 100)
    olive_dry_pct = float(masks["olive_dry"].sum() / total * 100)
    gap_pct = max(0.0, vvi_pct - gvi_pct)
    recovery_share_of_vvi = float(recovery_mask.sum() / max(1, vvi_mask.sum()) * 100)

    if recovery_share_of_vvi > 38 or removed_pct > 26:
        confidence_label = "low"
    elif recovery_share_of_vvi > 22 or removed_pct > 14:
        confidence_label = "medium"
    else:
        confidence_label = "high"

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(image_name).stem
    overlay_path = output_dir / f"{stem}_overlay_gvi_{gvi_pct:.1f}_vvi_{vvi_pct:.1f}.png"
    vvi_mask_path = output_dir / f"{stem}_vvi_mask.png"
    gvi_mask_path = output_dir / f"{stem}_gvi_mask.png"
    raw_semantic_mask_path = output_dir / f"{stem}_semantic_raw_mask.png"
    semantic_clean_mask_path = output_dir / f"{stem}_semantic_clean_mask.png"
    recovery_mask_path = output_dir / f"{stem}_recovery_mask.png"
    removed_mask_path = output_dir / f"{stem}_removed_artifact_mask.png"

    overlay = overlay_masks(image_bgr, gvi_mask, raw_semantic_clean, recovery_mask, removed_mask)

    if save_outputs:
        cv2.imwrite(str(overlay_path), overlay)
        save_binary_mask(vvi_mask, vvi_mask_path)
        save_binary_mask(gvi_mask, gvi_mask_path)
        save_binary_mask(recovery_mask, recovery_mask_path)
        save_binary_mask(removed_mask, removed_mask_path)
        if pred is not None:
            save_binary_mask(raw_semantic, raw_semantic_mask_path)
            save_binary_mask(raw_semantic_clean, semantic_clean_mask_path)

    return {
        "image": image_name,
        "mode": mode,
        "semantic_source": semantic_source,
        "width": w,
        "height": h,
        "gvi_pct": round(gvi_pct, 4),
        "vvi_pct": round(vvi_pct, 4),
        "gap_pct": round(gap_pct, 4),
        "raw_semantic_vvi_pct": round(raw_semantic_pct, 4),
        "semantic_clean_vvi_pct": round(raw_semantic_clean_pct, 4),
        "recovery_pct": round(recovery_pct, 4),
        "recovery_share_of_vvi_pct": round(recovery_share_of_vvi, 4),
        "removed_artifact_pct": round(removed_pct, 4),
        "removed_ground_artifact_pct": round(removed_pct, 4),  # compatibility with v0.3/v0.4 frontend columns
        "ground_quality_removed_pct": round(ground_quality_removed_pct, 4),
        "component_artifact_removed_pct": round(panel_removed_pct, 4),
        "high_vis_pct": round(high_vis_pct, 4),
        "muted_candidate_pct": round(muted_pct, 4),
        "olive_dry_candidate_pct": round(olive_dry_pct, 4),
        "confidence_label": confidence_label,
        "overlay_path": str(overlay_path) if save_outputs else "",
        "vvi_mask_path": str(vvi_mask_path) if save_outputs else "",
        "gvi_mask_path": str(gvi_mask_path) if save_outputs else "",
        "semantic_raw_mask_path": str(raw_semantic_mask_path) if (save_outputs and pred is not None) else "",
        "semantic_clean_mask_path": str(semantic_clean_mask_path) if (save_outputs and pred is not None) else "",
        "recovery_mask_path": str(recovery_mask_path) if save_outputs else "",
        "removed_mask_path": str(removed_mask_path) if save_outputs else "",
        **{f"setting_{k}": v for k, v in asdict(settings).items()},
    }


def analyse_image(
    image_path: Path,
    output_dir: Path,
    settings: Settings,
    mask_path: Optional[Path] = None,
    segmenter: Optional[Segmenter] = None,
) -> dict[str, Any]:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")
    semantic_mask = load_semantic_mask(mask_path, image.shape[:2])
    return analyse_array(
        image_bgr=image,
        image_name=image_path.name,
        output_dir=output_dir,
        settings=settings,
        semantic_mask=semantic_mask,
        segmenter=segmenter if semantic_mask is None else None,
        save_outputs=True,
    )


def iter_images(input_path: Path) -> Iterable[Path]:
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
    if input_path.is_file() and input_path.suffix.lower() in extensions:
        yield input_path
    elif input_path.is_dir():
        for p in sorted(input_path.iterdir()):
            if p.suffix.lower() in extensions:
                yield p


def find_mask(mask_dir: Optional[Path], image_path: Path) -> Optional[Path]:
    if mask_dir is None:
        return None
    for ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
        candidate = mask_dir / f"{image_path.stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def build_segmenter(kind: str, model_id: str, veg_labels: Optional[str], device: Optional[str]) -> Optional[Segmenter]:
    if kind == "none":
        return None
    if kind == "hf":
        from semantic_segmentation_hf_v0_5 import HFSegFormerVegetationSegmenter

        labels = [x.strip() for x in veg_labels.split(",")] if veg_labels else None
        segmenter = HFSegFormerVegetationSegmenter(model_id=model_id, vegetation_labels=labels, device=device)
        info = segmenter.info
        print(f"Loaded {info.model_id} on {info.device}")
        print("Vegetation labels:", ", ".join(info.vegetation_labels))
        print("Ground labels:", ", ".join(info.ground_labels))
        print("Artificial/built labels:", ", ".join(info.artificial_labels[:20]))
        return segmenter
    raise ValueError(f"Unknown segmenter: {kind}")


def settings_overrides_from_args(args: argparse.Namespace) -> dict[str, Any]:
    overrides = {}
    for key in (
        "semantic_prob_min",
        "soft_semantic_prob_min",
        "min_safe_recovery_prob",
        "recovery_radius_px",
        "count_muted_as_gvi",
        "fence_recovery",
        "exclude_high_vis",
        "allow_isolated_colour_recovery",
        "gvi_requires_semantic_support",
        "hard_negative_veto",
        "remove_rectangular_panels",
        "enable_ground_quality_guard",
        "ground_filter_mode",
        "ground_quality_bottom_start",
        "front_ground_start",
        "ground_veg_prob_margin",
        "ground_negative_prob_min",
    ):
        value = getattr(args, key, None)
        if value is not None:
            overrides[key] = value
    return overrides


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch calculate precision-guarded GVI and VVI from street-level images.")
    parser.add_argument("--input", required=True, type=Path, help="Input image or folder.")
    parser.add_argument("--output", required=True, type=Path, help="Output folder.")
    parser.add_argument("--mask-dir", type=Path, default=None, help="Optional folder of semantic vegetation masks.")
    parser.add_argument(
        "--preset",
        default="standard",
        choices=["standard", "autumn", "strict", "shadow", "sunny", "anti_glare", "winter", "custom"],
        help="Colour preset. Standard/autumn/shadow are calibrated from the older HTML tool.",
    )
    parser.add_argument("--recovery-mode", default="balanced", choices=["conservative", "balanced", "aggressive"])
    parser.add_argument("--ground-guard", default="strong", choices=["light", "balanced", "strong"])
    parser.add_argument("--ground-filter-mode", default="balanced", choices=["off", "balanced", "strict"], help="v0.5 lower-frame grass-vs-paving refinement.")
    parser.add_argument("--artifact-guard", default="strong", choices=["light", "balanced", "strong"])
    parser.add_argument("--segmenter", default="none", choices=["none", "hf"], help="Run a semantic segmentation model if no mask is provided.")
    parser.add_argument("--model-id", default="nvidia/segformer-b0-finetuned-ade-512-512", help="Hugging Face semantic segmentation model id.")
    parser.add_argument("--veg-labels", default=None, help="Comma-separated vegetation labels, e.g. tree,grass,plant,flower,vegetation")
    parser.add_argument("--device", default=None, help="Override device, e.g. cpu, cuda, mps.")
    parser.add_argument("--semantic-prob-min", type=float, default=None)
    parser.add_argument("--soft-semantic-prob-min", type=float, default=None)
    parser.add_argument("--min-safe-recovery-prob", type=float, default=None)
    parser.add_argument("--recovery-radius-px", type=int, default=None)
    parser.add_argument("--count-muted-as-gvi", type=str, default=None)
    parser.add_argument("--fence-recovery", type=str, default=None)
    parser.add_argument("--exclude-high-vis", type=str, default=None)
    parser.add_argument("--allow-isolated-colour-recovery", type=str, default=None)
    parser.add_argument("--gvi-requires-semantic-support", type=str, default=None)
    parser.add_argument("--hard-negative-veto", type=str, default=None)
    parser.add_argument("--remove-rectangular-panels", type=str, default=None)
    parser.add_argument("--enable-ground-quality-guard", type=str, default=None)
    parser.add_argument("--ground-quality-bottom-start", type=float, default=None)
    parser.add_argument("--front-ground-start", type=float, default=None)
    parser.add_argument("--ground-veg-prob-margin", type=float, default=None)
    parser.add_argument("--ground-negative-prob-min", type=float, default=None)
    parser.add_argument("--settings-json", type=Path, default=None, help="Optional JSON settings overrides.")
    args = parser.parse_args()

    overrides = settings_overrides_from_args(args)
    if args.settings_json and args.settings_json.exists():
        overrides.update(json.loads(args.settings_json.read_text(encoding="utf-8")))
    settings = build_settings(args.preset, args.recovery_mode, args.ground_guard, args.artifact_guard, overrides=overrides)
    apply_ground_quality_filter(settings, args.ground_filter_mode)
    # Re-apply explicit settings-json/CLI overrides after the preset-specific mode, so user values win.
    for k, v in overrides.items():
        if v is None or v == "" or not hasattr(settings, k):
            continue
        cur = getattr(settings, k)
        if isinstance(cur, bool):
            setattr(settings, k, parse_bool(v))
        elif isinstance(cur, int):
            setattr(settings, k, int(float(v)))
        elif isinstance(cur, float):
            setattr(settings, k, float(v))
        else:
            setattr(settings, k, str(v))
    segmenter = build_segmenter(args.segmenter, args.model_id, args.veg_labels, args.device)

    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for image_path in iter_images(args.input):
        mask_path = find_mask(args.mask_dir, image_path)
        rows.append(analyse_image(image_path, args.output, settings, mask_path, segmenter))

    if not rows:
        raise SystemExit("No images found.")

    df = pd.DataFrame(rows)
    csv_path = args.output / "gvi_vvi_results_v0_5.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    (args.output / "settings_used_v0_5.json").write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {csv_path}")
    cols = [
        "image",
        "mode",
        "gvi_pct",
        "vvi_pct",
        "raw_semantic_vvi_pct",
        "recovery_pct",
        "removed_artifact_pct",
        "confidence_label",
    ]
    print(df[cols].to_string(index=False))


if __name__ == "__main__":
    main()
