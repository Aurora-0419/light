from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import cv2
import mediapipe as mp
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_pc_hand_shadow_demo import resolve_source


@dataclass
class RightHandDetection:
    label: str
    score: float
    bbox: tuple[int, int, int, int]
    pixel_landmarks: list[tuple[int, int]]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a minimal MediaPipe right-hand realtime demo")
    parser.add_argument("--webcam", action="store_true", help="Use default webcam")
    parser.add_argument("--camera", type=str, default=None, help="Use explicit camera device path or index")
    parser.add_argument("--video", type=str, default=None, help="Use video file path")
    parser.add_argument("--min-detection-confidence", type=float, default=0.5)
    parser.add_argument("--min-tracking-confidence", type=float, default=0.5)
    parser.add_argument("--mirror", action="store_true", help="Flip display horizontally before detection")
    return parser


def _normalized_landmark_xy(landmark) -> tuple[float, float]:
    if isinstance(landmark, tuple):
        return float(landmark[0]), float(landmark[1])
    return float(landmark.x), float(landmark.y)


def _iter_landmark_points(hand_landmarks) -> list[tuple[float, float]]:
    landmarks = getattr(hand_landmarks, "landmark", hand_landmarks)
    return [_normalized_landmark_xy(landmark) for landmark in landmarks]


def select_right_hand_detection(
    frame_shape: tuple[int, ...],
    multi_hand_landmarks,
    multi_handedness,
) -> RightHandDetection | None:
    if not multi_hand_landmarks or not multi_handedness:
        return None

    height, width = frame_shape[:2]
    for hand_landmarks, handedness in zip(multi_hand_landmarks, multi_handedness):
        classification = handedness.classification[0]
        label = classification.label
        if label != "Right":
            continue

        normalized_points = _iter_landmark_points(hand_landmarks)
        pixel_landmarks = [
            (min(width - 1, max(0, int(x * width))), min(height - 1, max(0, int(y * height))))
            for x, y in normalized_points
        ]
        xs = [point[0] for point in pixel_landmarks]
        ys = [point[1] for point in pixel_landmarks]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        return RightHandDetection(
            label=label,
            score=float(classification.score),
            bbox=(x0, y0, max(1, x1 - x0), max(1, y1 - y0)),
            pixel_landmarks=pixel_landmarks,
        )

    return None


def detect_right_hand(frame: np.ndarray, hands) -> RightHandDetection | None:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)
    return select_right_hand_detection(frame.shape, result.multi_hand_landmarks, result.multi_handedness)


def draw_right_hand_overlay(frame: np.ndarray, detection: RightHandDetection | None) -> np.ndarray:
    output = frame.copy()
    if detection is None:
        cv2.putText(output, "Right hand: not detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return output

    x, y, w, h = detection.bbox
    cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 2)
    for point in detection.pixel_landmarks:
        cv2.circle(output, point, 3, (0, 255, 255), -1)
    cv2.putText(
        output,
        f"{detection.label} {detection.score:.2f}",
        (x, max(20, y - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
    )
    return output


def main() -> int:
    args = build_arg_parser().parse_args()
    source = resolve_source(args)
    print(f"opening source: {source}")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"failed to open source: {source}")

    hands = mp.solutions.hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=args.min_detection_confidence,
        min_tracking_confidence=args.min_tracking_confidence,
    )
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            if args.mirror:
                frame = cv2.flip(frame, 1)
            detection = detect_right_hand(frame, hands)
            overlay = draw_right_hand_overlay(frame, detection)
            cv2.imshow("mediapipe_right_hand_demo", overlay)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
    finally:
        hands.close()
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
