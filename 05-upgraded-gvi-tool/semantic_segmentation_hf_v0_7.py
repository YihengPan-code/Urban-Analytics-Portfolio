"""
Hugging Face SegFormer provider for Adaptive GVI/VVI backend v0.7.

Compared with v0.3, this provider returns soft probability maps for both
vegetation and major negative classes. The backend uses those negative maps to
suppress green signs, window glass, built surfaces and sunlit ground.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import cv2
import numpy as np

from adaptive_gvi_vvi_backend_v0_7 import SemanticPrediction


DEFAULT_VEGETATION_LABELS = {
    "tree",
    "grass",
    "plant",
    "flower",
    "vegetation",
    "palm",
    "shrub",
    "bush",
    "field",
}

GROUND_KEYWORDS = {
    "road", "sidewalk", "pavement", "street", "floor", "path", "runway",
    "earth", "sand", "dirt", "ground", "parking", "plaza",
}

STRUCTURE_KEYWORDS = {
    "fence", "railing", "gate", "grille", "bars",
}

BUILT_KEYWORDS = {
    "building", "house", "skyscraper", "wall", "window", "windowpane", "glass", "mirror",
    "door", "shop", "store", "awning",
}

ARTIFICIAL_KEYWORDS = {
    "person", "rider", "car", "truck", "bus", "train", "motorcycle", "bicycle",
    "traffic sign", "traffic light", "sign", "signboard", "billboard", "poster", "screen", "monitor",
    "pole", "sky",
} | BUILT_KEYWORDS


@dataclass
class SegmentationInfo:
    model_id: str
    device: str
    vegetation_ids: list[int]
    vegetation_labels: list[str]
    ground_ids: list[int]
    ground_labels: list[str]
    artificial_ids: list[int]
    artificial_labels: list[str]
    structure_ids: list[int]
    structure_labels: list[str]
    built_ids: list[int]
    built_labels: list[str]
    all_labels: dict[int, str]


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


class HFSegFormerVegetationSegmenter:
    """Semantic vegetation segmenter using Transformers + SegFormer.

    It reads model.config.id2label and resolves class groups by label name, so it
    is safer to switch between ADE20K and Cityscapes checkpoints.
    """

    def __init__(
        self,
        model_id: str = "nvidia/segformer-b0-finetuned-ade-512-512",
        vegetation_labels: Optional[Iterable[str]] = None,
        device: Optional[str] = None,
        morph_kernel: int = 1,
    ) -> None:
        try:
            import torch
            import torch.nn.functional as F
            from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation
        except ImportError as exc:
            raise ImportError(
                "Missing ML dependencies. Install with: "
                "pip install torch torchvision transformers pillow"
            ) from exc

        self.torch = torch
        self.F = F
        self.model_id = model_id
        if device:
            self.device = device
        elif torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"
        self.morph_kernel = int(morph_kernel)

        self.processor = AutoImageProcessor.from_pretrained(model_id)
        self.model = AutoModelForSemanticSegmentation.from_pretrained(model_id)
        self.model.to(self.device)
        self.model.eval()

        self.id2label = {int(k): normalise_label(v) for k, v in self.model.config.id2label.items()}
        self.vegetation_label_set = {normalise_label(v) for v in (vegetation_labels or DEFAULT_VEGETATION_LABELS)}

        self.vegetation_ids = self._resolve_ids(self.vegetation_label_set, exact_or_token=True)
        self.ground_ids = self._resolve_ids(GROUND_KEYWORDS)
        self.structure_ids = self._resolve_ids(STRUCTURE_KEYWORDS)
        self.built_ids = self._resolve_ids(BUILT_KEYWORDS)
        self.artificial_ids = self._resolve_ids(ARTIFICIAL_KEYWORDS)

        # Avoid treating vegetation labels as negative if a model label happens to contain both words.
        self.ground_ids = [i for i in self.ground_ids if i not in self.vegetation_ids]
        self.structure_ids = [i for i in self.structure_ids if i not in self.vegetation_ids]
        self.built_ids = [i for i in self.built_ids if i not in self.vegetation_ids]
        self.artificial_ids = [i for i in self.artificial_ids if i not in self.vegetation_ids]

        if not self.vegetation_ids:
            preview = ", ".join(f"{i}:{lbl}" for i, lbl in list(self.id2label.items())[:60])
            raise ValueError(
                "No vegetation class IDs found for this model. "
                "Pass --veg-labels with labels that exist in the model. "
                f"First labels: {preview}"
            )

    def _resolve_ids(self, keywords: Iterable[str], exact_or_token: bool = False) -> list[int]:
        keys = {normalise_label(k) for k in keywords}
        ids: list[int] = []
        for idx, label in self.id2label.items():
            if exact_or_token:
                tokens = set(label.replace("/", " ").replace(";", " ").replace(",", " ").split())
                if label in keys or tokens & keys:
                    ids.append(idx)
            else:
                if any(label_matches(label, key) for key in keys):
                    ids.append(idx)
        return sorted(set(ids))

    @property
    def info(self) -> SegmentationInfo:
        return SegmentationInfo(
            model_id=self.model_id,
            device=self.device,
            vegetation_ids=self.vegetation_ids,
            vegetation_labels=[self.id2label[i] for i in self.vegetation_ids],
            ground_ids=self.ground_ids,
            ground_labels=[self.id2label[i] for i in self.ground_ids],
            artificial_ids=self.artificial_ids,
            artificial_labels=[self.id2label[i] for i in self.artificial_ids],
            structure_ids=self.structure_ids,
            structure_labels=[self.id2label[i] for i in self.structure_ids],
            built_ids=self.built_ids,
            built_labels=[self.id2label[i] for i in self.built_ids],
            all_labels=self.id2label,
        )

    def _sum_prob(self, probs, ids: list[int], h: int, w: int) -> np.ndarray:
        if not ids:
            return np.zeros((h, w), dtype=np.float32)
        return probs[ids, :, :].sum(dim=0).detach().cpu().numpy().astype(np.float32)

    def predict(self, image_bgr: np.ndarray) -> SemanticPrediction:
        """Return vegetation and non-vegetation probability maps."""
        from PIL import Image

        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise ValueError("Expected an OpenCV BGR image with shape HxWx3.")

        h, w = image_bgr.shape[:2]
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(image_rgb)

        inputs = self.processor(images=pil_img, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with self.torch.inference_mode():
            outputs = self.model(**inputs)

        logits = outputs.logits
        upsampled = self.F.interpolate(logits, size=(h, w), mode="bilinear", align_corners=False)
        label_map = upsampled.argmax(dim=1)[0].detach().cpu().numpy().astype(np.int32)
        probs = self.torch.softmax(upsampled, dim=1)[0]

        veg_prob = self._sum_prob(probs, self.vegetation_ids, h, w)
        ground_prob = self._sum_prob(probs, self.ground_ids, h, w)
        artificial_prob = self._sum_prob(probs, self.artificial_ids, h, w)
        structure_prob = self._sum_prob(probs, self.structure_ids, h, w)
        built_prob = self._sum_prob(probs, self.built_ids, h, w)
        hard_mask = np.isin(label_map, self.vegetation_ids)

        if self.morph_kernel and self.morph_kernel > 1:
            kernel = np.ones((self.morph_kernel, self.morph_kernel), np.uint8)
            hard_u8 = hard_mask.astype(np.uint8) * 255
            hard_u8 = cv2.morphologyEx(hard_u8, cv2.MORPH_OPEN, kernel)
            hard_u8 = cv2.morphologyEx(hard_u8, cv2.MORPH_CLOSE, kernel)
            hard_mask = hard_u8 > 127

        return SemanticPrediction(
            hard_mask=hard_mask,
            vegetation_prob=veg_prob,
            label_map=label_map,
            id2label=self.id2label,
            ground_prob=ground_prob,
            artificial_prob=artificial_prob,
            structure_prob=structure_prob,
            built_prob=built_prob,
        )

    def segment(self, image_bgr: np.ndarray) -> np.ndarray:
        """Compatibility method for older backend code."""
        return self.predict(image_bgr).hard_mask
