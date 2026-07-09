from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.perception.hand_detector import MediaPipeHandDetector
from app.perception.shadow_detector import ShadowDetector


@dataclass
class CombinedDetectionResult:
    hand_center: tuple[int, int] | None
    palm_center: tuple[int, int] | None
    shadow_center: tuple[int, int] | None
    needs_relight: bool
    suggested_target_center: tuple[int, int] | None
    hand_count: int
    shadow_area: int | None
    shadow_mask: np.ndarray | None
    shadow_contour: np.ndarray | None
    shadow_vector: tuple[int, int] | None


class CombinedHandShadowDetector:
    def __init__(self, hand_detector=None, shadow_detector=None, min_relight_shadow_area: int = 800):
        self.hand_detector = hand_detector or MediaPipeHandDetector()
        self.shadow_detector = shadow_detector or ShadowDetector()
        self.min_relight_shadow_area = min_relight_shadow_area

    @staticmethod
    def _bbox_overlap_area(bbox_a, bbox_b) -> int:
        ax, ay, aw, ah = bbox_a
        bx, by, bw, bh = bbox_b
        left = max(ax, bx)
        top = max(ay, by)
        right = min(ax + aw, bx + bw)
        bottom = min(ay + ah, by + bh)
        if right <= left or bottom <= top:
            return 0
        return int((right - left) * (bottom - top))

    @classmethod
    def _overlaps_hand_too_much(cls, hand_bbox, shadow_bbox) -> bool:
        overlap_area = cls._bbox_overlap_area(hand_bbox, shadow_bbox)
        if overlap_area <= 0:
            return False
        _, _, sw, sh = shadow_bbox
        shadow_area = max(sw * sh, 1)
        return overlap_area / shadow_area >= 0.45

    @classmethod
    def _select_shadow_for_hand(cls, hand_center, hand_bbox, regions):
        if not regions:
            return None
        if hand_center is None:
            return regions[0]
        non_overlapping = [
            region for region in regions
            if hand_bbox is None or not cls._overlaps_hand_too_much(hand_bbox, region.bbox)
        ]
        candidates = non_overlapping or regions
        return min(
            candidates,
            key=lambda region: (
                (region.center[0] - hand_center[0]) ** 2 + (region.center[1] - hand_center[1]) ** 2,
                -region.area,
            ),
        )

    @classmethod
    def _select_hand_shadow_pair(cls, hands, regions):
        if not hands:
            return None, cls._select_shadow_for_hand(None, None, regions)
        best_pair = None
        best_score = None
        for hand in hands:
            shadow = cls._select_shadow_for_hand(hand.center, hand.bbox, regions)
            if shadow is None:
                score = (float("inf"), 0)
            else:
                distance = (shadow.center[0] - hand.center[0]) ** 2 + (shadow.center[1] - hand.center[1]) ** 2
                score = (distance, -shadow.area)
            if best_score is None or score < best_score:
                best_pair = (hand, shadow)
                best_score = score
        return best_pair

    @staticmethod
    def _is_significant_shadow(shadow_region, min_area: int) -> bool:
        return shadow_region is not None and shadow_region.area >= min_area

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
        hand, selected_shadow = self._select_hand_shadow_pair(hand_result.hands, shadow_result.regions)
        hand_center = hand.center if hand is not None else None
        palm_center = hand.palm_center if hand is not None else None
        shadow_center = selected_shadow.center if selected_shadow else None
        needs_relight = hand_center is not None and self._is_significant_shadow(
            selected_shadow,
            self.min_relight_shadow_area,
        )
        suggested_target_center = shadow_center or hand_center
        shadow_area = selected_shadow.area if selected_shadow else None
        shadow_mask = self._build_shadow_mask(frame, selected_shadow)
        shadow_contour = selected_shadow.contour if selected_shadow is not None else None
        shadow_vector = None
        if hand_center is not None and shadow_center is not None:
            shadow_vector = (shadow_center[0] - hand_center[0], shadow_center[1] - hand_center[1])
        return CombinedDetectionResult(
            hand_center=hand_center,
            palm_center=palm_center,
            shadow_center=shadow_center,
            needs_relight=needs_relight,
            suggested_target_center=suggested_target_center,
            hand_count=len(hand_result.hands),
            shadow_area=shadow_area,
            shadow_mask=shadow_mask,
            shadow_contour=shadow_contour,
            shadow_vector=shadow_vector,
        )
