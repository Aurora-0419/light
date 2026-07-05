from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class ShadowRegion:
    bbox: tuple[int, int, int, int]
    center: tuple[int, int]
    area: int
    contour: np.ndarray


@dataclass
class ShadowDetectionResult:
    has_shadow: bool
    primary_shadow: ShadowRegion | None
    mask: np.ndarray | None
    regions: list[ShadowRegion]


class ShadowDetector:
    def __init__(
        self,
        min_area: int = 1200,
        darkness_threshold: int = 60,
        paper_threshold: int = 140,
        min_shadow_intensity: int = 35,
    ):
        self.min_area = min_area
        self.darkness_threshold = darkness_threshold
        self.paper_threshold = paper_threshold
        self.min_shadow_intensity = min_shadow_intensity

    def detect(self, frame: np.ndarray) -> ShadowDetectionResult:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        bright_mask = cv2.inRange(gray, self.paper_threshold, 255)
        if cv2.countNonZero(bright_mask) < self.min_area:
            empty = np.zeros_like(gray, dtype=np.uint8)
            return ShadowDetectionResult(False, None, empty, [])

        paper_region = np.zeros_like(gray, dtype=np.uint8)
        contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            empty = np.zeros_like(gray, dtype=np.uint8)
            return ShadowDetectionResult(False, None, empty, [])
        largest_bright = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_bright)
        paper_region[y : y + h, x : x + w] = 255

        paper_values = gray[bright_mask > 0]
        reference_intensity = float(np.percentile(paper_values, 75))
        threshold_value = max(
            self.min_shadow_intensity,
            int(reference_intensity - self.darkness_threshold),
        )
        mask = cv2.inRange(gray, self.min_shadow_intensity, threshold_value)
        mask = cv2.bitwise_and(mask, paper_region)
        kernel = np.ones((5, 5), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid = [c for c in contours if cv2.contourArea(c) >= self.min_area]
        if not valid:
            return ShadowDetectionResult(False, None, mask, [])

        regions: list[ShadowRegion] = []
        for contour in sorted(valid, key=cv2.contourArea, reverse=True):
            x, y, w, h = cv2.boundingRect(contour)
            area = int(cv2.contourArea(contour))
            regions.append(
                ShadowRegion(
                    bbox=(x, y, w, h),
                    center=(x + w // 2, y + h // 2),
                    area=area,
                    contour=contour,
                )
            )

        return ShadowDetectionResult(True, regions[0], mask, regions)
