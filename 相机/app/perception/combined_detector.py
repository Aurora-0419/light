from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.perception.hand_detector import MediaPipeHandDetector
from app.perception.shadow_detector import ShadowDetector


@dataclass
class CombinedDetectionResult:
    hand_center: tuple[int, int] | None
    shadow_center: tuple[int, int] | None
    needs_relight: bool
    suggested_target_center: tuple[int, int] | None
    hand_count: int
    shadow_area: int | None
    shadow_mask: np.ndarray | None
    shadow_vector: tuple[int, int] | None


class CombinedHandShadowDetector:
    def __init__(self, hand_detector=None, shadow_detector=None):
        self.hand_detector = hand_detector or MediaPipeHandDetector()
        self.shadow_detector = shadow_detector or ShadowDetector()

    @staticmethod
    def _select_shadow_for_hand(hand_center, regions):
        if not regions:
            return None
        if hand_center is None:
            return regions[0]
        return min(
            regions,
            key=lambda region: (
                (region.center[0] - hand_center[0]) ** 2 + (region.center[1] - hand_center[1]) ** 2,
                -region.area,
            ),
        )

    @staticmethod
    def _build_shadow_mask(frame: np.ndarray, shadow_region) -> np.ndarray | None:
        if shadow_region is None:
            return None
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.drawContours(mask, [shadow_region.contour], -1, 255, thickness=cv2.FILLED)
        return mask

    def process(self, frame: np.ndarray) -> CombinedDetectionResult:
        hand_result = self.hand_detector.detect(frame)
        shadow_result = self.shadow_detector.detect(frame)
        hand_center = hand_result.hands[0].center if hand_result.hands else None
        selected_shadow = self._select_shadow_for_hand(hand_center, shadow_result.regions)
        shadow_center = selected_shadow.center if selected_shadow else None
        needs_relight = hand_center is not None and selected_shadow is not None
        suggested_target_center = shadow_center or hand_center
        shadow_area = selected_shadow.area if selected_shadow else None
        shadow_mask = self._build_shadow_mask(frame, selected_shadow)
        shadow_vector = None
        if hand_center is not None and shadow_center is not None:
            shadow_vector = (shadow_center[0] - hand_center[0], shadow_center[1] - hand_center[1])
        return CombinedDetectionResult(
            hand_center=hand_center,
            shadow_center=shadow_center,
            needs_relight=needs_relight,
            suggested_target_center=suggested_target_center,
            hand_count=len(hand_result.hands),
            shadow_area=shadow_area,
            shadow_mask=shadow_mask,
            shadow_vector=shadow_vector,
        )
