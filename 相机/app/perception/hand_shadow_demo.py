from __future__ import annotations

import cv2
import numpy as np

from app.perception.detector_base import PerceptionResult


class HandShadowDemoDetector:
    def __init__(self, min_area: int = 1200, threshold: int = 20):
        self.min_area = min_area
        self.threshold = threshold

    def process(
        self, color_frame: np.ndarray, depth_frame: np.ndarray | None
    ) -> PerceptionResult:
        gray = cv2.cvtColor(color_frame, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, self.threshold, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        valid = [c for c in contours if cv2.contourArea(c) >= self.min_area]
        if not valid:
            return PerceptionResult(False, None, None, None, label="none")

        contour = max(valid, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(contour)
        center = (x + w // 2, y + h // 2)

        depth_value_mm = None
        if depth_frame is not None:
            depth_value_mm = int(depth_frame[center[1], center[0]])

        return PerceptionResult(
            has_detection=True,
            primary_bbox=(x, y, w, h),
            primary_center=center,
            depth_value_mm=depth_value_mm,
            label="foreground_candidate",
        )
