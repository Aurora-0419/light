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
        darkness_threshold: int = 45,
        paper_threshold: int = 140,
        min_shadow_intensity: int = 35,
        adaptive_paper_percentile: float = 65.0,
    ):
        self.min_area = min_area
        self.darkness_threshold = darkness_threshold
        self.paper_threshold = paper_threshold
        self.min_shadow_intensity = min_shadow_intensity
        self.adaptive_paper_percentile = adaptive_paper_percentile

    def _paper_mask(self, gray: np.ndarray) -> np.ndarray:
        brightest_threshold = max(self.paper_threshold, int(gray.max()) - 10)
        brightest_mask = cv2.inRange(gray, brightest_threshold, 255)
        if cv2.countNonZero(brightest_mask) >= self.min_area:
            kernel = np.ones((7, 7), dtype=np.uint8)
            brightest_mask = cv2.morphologyEx(brightest_mask, cv2.MORPH_CLOSE, kernel)
            return brightest_mask

        fixed_mask = cv2.inRange(gray, self.paper_threshold, 255)
        if cv2.countNonZero(fixed_mask) >= self.min_area:
            return fixed_mask
        adaptive_threshold = int(np.percentile(gray, self.adaptive_paper_percentile))
        threshold = max(adaptive_threshold, self.min_shadow_intensity + 20)
        bright_mask = cv2.inRange(gray, threshold, 255)
        kernel = np.ones((7, 7), dtype=np.uint8)
        bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_CLOSE, kernel)
        return bright_mask

    @staticmethod
    def _contour_center(contour: np.ndarray, bbox: tuple[int, int, int, int]) -> tuple[int, int]:
        moments = cv2.moments(contour)
        if moments["m00"]:
            return (int(moments["m10"] / moments["m00"]), int(moments["m01"] / moments["m00"]))
        x, y, w, h = bbox
        return (x + w // 2, y + h // 2)

    def detect(self, frame: np.ndarray) -> ShadowDetectionResult:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        bright_mask = self._paper_mask(gray)
        if cv2.countNonZero(bright_mask) < self.min_area:
            empty = np.zeros_like(gray, dtype=np.uint8)
            return ShadowDetectionResult(False, None, empty, [])

        paper_region = np.zeros_like(gray, dtype=np.uint8)
        contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            empty = np.zeros_like(gray, dtype=np.uint8)
            return ShadowDetectionResult(False, None, empty, [])
        largest_bright = max(contours, key=cv2.contourArea)
        cv2.drawContours(paper_region, [largest_bright], -1, 255, thickness=cv2.FILLED)

        paper_values = gray[paper_region > 0]
        reference_intensity = float(np.percentile(paper_values, 75))
        contrast = max(18, min(self.darkness_threshold, int(reference_intensity * 0.18)))
        threshold_value = max(
            self.min_shadow_intensity,
            int(reference_intensity - contrast),
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
            bbox = (x, y, w, h)
            regions.append(
                ShadowRegion(
                    bbox=bbox,
                    center=self._contour_center(contour, bbox),
                    area=area,
                    contour=contour,
                )
            )

        return ShadowDetectionResult(True, regions[0], mask, regions)
