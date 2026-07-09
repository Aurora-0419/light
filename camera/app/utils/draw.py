from __future__ import annotations

import cv2
import numpy as np

from app.perception.detector_base import PerceptionResult


def draw_perception_overlay(frame: np.ndarray, result: PerceptionResult) -> np.ndarray:
    output = frame.copy()
    if result.primary_bbox is not None:
        x, y, w, h = result.primary_bbox
        cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 2)
    if result.primary_center is not None:
        cv2.circle(output, result.primary_center, 4, (0, 0, 255), -1)
    return output
