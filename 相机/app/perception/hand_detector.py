from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class HandDetection:
    bbox: tuple[int, int, int, int]
    center: tuple[int, int]
    confidence: float
    landmarks: list[tuple[int, int]]


@dataclass
class HandDetectorResult:
    available: bool
    hands: list[HandDetection]
    warning: str = ""


class _MediaPipeBackend:
    def __init__(self) -> None:
        import mediapipe as mp

        self._mp = mp
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def detect(self, frame: np.ndarray) -> list[HandDetection]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)
        detections: list[HandDetection] = []
        if not results.multi_hand_landmarks:
            return detections

        height, width = frame.shape[:2]
        for hand_landmarks in results.multi_hand_landmarks:
            points = []
            xs = []
            ys = []
            for lm in hand_landmarks.landmark:
                x = int(lm.x * width)
                y = int(lm.y * height)
                points.append((x, y))
                xs.append(x)
                ys.append(y)
            x0, x1 = max(0, min(xs)), min(width, max(xs))
            y0, y1 = max(0, min(ys)), min(height, max(ys))
            bbox = (x0, y0, max(1, x1 - x0), max(1, y1 - y0))
            center = (x0 + bbox[2] // 2, y0 + bbox[3] // 2)
            detections.append(
                HandDetection(
                    bbox=bbox,
                    center=center,
                    confidence=0.8,
                    landmarks=points,
                )
            )
        return detections


class MediaPipeHandDetector:
    def __init__(self, backend=None):
        self.backend = backend
        self._warning = ""
        if self.backend is None:
            try:
                self.backend = _MediaPipeBackend()
            except Exception as exc:
                self.backend = None
                self._warning = f"MediaPipe unavailable: {exc}"

    def detect(self, frame: np.ndarray) -> HandDetectorResult:
        if self.backend is None:
            return HandDetectorResult(False, [], warning=self._warning)
        return HandDetectorResult(True, self.backend.detect(frame), warning=self._warning)
