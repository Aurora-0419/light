from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(eq=True)
class PostureResult:
    posture_ok: bool
    posture_issue: str
    posture_score: float
    available: bool = True


def _neutral(available: bool = True) -> PostureResult:
    return PostureResult(posture_ok=True, posture_issue="", posture_score=0.0, available=available)


def evaluate_landmarks(
    landmarks: dict[str, tuple[float, float]],
    *,
    shoulder_tilt_threshold: float = 0.08,
    lean_threshold: float = 0.12,
    head_close_threshold: float = 0.04,
) -> PostureResult:
    required = {"left_shoulder", "right_shoulder", "left_hip", "right_hip", "nose"}
    if not required <= landmarks.keys():
        return _neutral(available=False)

    left_shoulder = landmarks["left_shoulder"]
    right_shoulder = landmarks["right_shoulder"]
    left_hip = landmarks["left_hip"]
    right_hip = landmarks["right_hip"]
    nose = landmarks["nose"]

    shoulder_tilt = abs(left_shoulder[1] - right_shoulder[1])
    if shoulder_tilt > shoulder_tilt_threshold:
        score = min(1.0, (shoulder_tilt - shoulder_tilt_threshold) / shoulder_tilt_threshold)
        return PostureResult(False, "shoulder_tilt", score)

    shoulder_center_x = (left_shoulder[0] + right_shoulder[0]) / 2.0
    hip_center_x = (left_hip[0] + right_hip[0]) / 2.0
    body_lean = abs(shoulder_center_x - hip_center_x)
    if body_lean > lean_threshold:
        score = min(1.0, (body_lean - lean_threshold) / lean_threshold)
        return PostureResult(False, "body_lean_left_right", score)

    shoulder_center_y = (left_shoulder[1] + right_shoulder[1]) / 2.0
    head_gap = shoulder_center_y - nose[1]
    if head_gap <= head_close_threshold + 1e-6:
        score = min(1.0, max(0.0, (head_close_threshold - head_gap) / max(head_close_threshold, 1e-6)))
        return PostureResult(False, "head_too_close", score)

    return _neutral(available=True)


class _MediaPipePoseBackend:
    def __init__(self) -> None:
        import mediapipe as mp

        self._pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._pose_landmark = mp.solutions.pose.PoseLandmark

    def detect(self, frame: np.ndarray) -> PostureResult:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._pose.process(rgb)
        if not results.pose_landmarks:
            return _neutral(available=False)

        landmarks = results.pose_landmarks.landmark
        mapping = {
            "nose": self._pose_landmark.NOSE,
            "left_shoulder": self._pose_landmark.LEFT_SHOULDER,
            "right_shoulder": self._pose_landmark.RIGHT_SHOULDER,
            "left_hip": self._pose_landmark.LEFT_HIP,
            "right_hip": self._pose_landmark.RIGHT_HIP,
        }
        normalized = {
            name: (float(landmarks[index].x), float(landmarks[index].y))
            for name, index in mapping.items()
        }
        return evaluate_landmarks(normalized)


class OptionalPosePostureDetector:
    def __init__(self, backend: Any | None = None):
        self.backend = backend
        if self.backend is None:
            try:
                self.backend = _MediaPipePoseBackend()
            except Exception:
                self.backend = None

    def detect(self, frame: np.ndarray) -> PostureResult:
        if self.backend is None:
            return _neutral(available=False)
        return self.backend.detect(frame)
