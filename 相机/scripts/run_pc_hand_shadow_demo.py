from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
import sys

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.perception.combined_detector import CombinedHandShadowDetector


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PC-first hand shadow detection demo")
    parser.add_argument("--webcam", action="store_true", help="Use default webcam")
    parser.add_argument("--camera", type=str, default=None, help="Use explicit camera device path or index")
    parser.add_argument("--video", type=str, default=None, help="Use video file path")
    parser.add_argument("--save-frame", type=str, default=None, help="Save current processed frame")
    return parser


def _video_device_sort_key(device: str) -> tuple[int, str]:
    suffix = Path(device).name.removeprefix("video")
    return (int(suffix) if suffix.isdigit() else 9999, device)


def _list_video_devices() -> list[str]:
    return sorted((str(path) for path in Path("/dev").glob("video*")), key=_video_device_sort_key)


def _read_v4l2_device_info(device: str) -> str:
    try:
        completed = subprocess.run(
            ["v4l2-ctl", "-d", device, "--all"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return f"{completed.stdout}\n{completed.stderr}"


def find_realsense_color_device(
    devices: list[str] | None = None,
    device_info_reader=_read_v4l2_device_info,
) -> str | None:
    candidates = []
    for device in devices or _list_video_devices():
        info = device_info_reader(device)
        if "RealSense" not in info:
            continue
        if "Format Metadata Capture" in info or "'Z16 '" in info:
            continue
        if "'YUYV'" in info:
            return device
        if "'UYVY'" in info:
            candidates.append(device)
    return candidates[0] if candidates else None


def resolve_source(args: argparse.Namespace, camera_detector=find_realsense_color_device) -> int | str:
    if args.camera:
        return int(args.camera) if args.camera.isdigit() else args.camera
    if args.video:
        return args.video
    if not args.webcam:
        detected = camera_detector()
        if detected:
            return detected
    return 0


def _draw_overlay(frame, result):
    output = frame.copy()
    if getattr(result, "shadow_mask", None) is not None:
        mask = result.shadow_mask > 0
        blue = output[:, :, 0]
        blue[mask] = np.maximum(blue[mask], 160)
        output[:, :, 0] = blue
    if result.hand_center is not None:
        cv2.circle(output, result.hand_center, 8, (0, 255, 0), -1)
        cv2.putText(output, "hand", result.hand_center, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    if result.shadow_center is not None:
        cv2.circle(output, result.shadow_center, 8, (255, 0, 0), -1)
        cv2.putText(output, "shadow", result.shadow_center, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    if result.suggested_target_center is not None:
        cv2.circle(output, result.suggested_target_center, 10, (0, 0, 255), 2)
    cv2.putText(
        output,
        f"needs_relight={result.needs_relight}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
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

    detector = CombinedHandShadowDetector()
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            result = detector.process(frame)
            overlay = _draw_overlay(frame, result)
            if args.save_frame:
                cv2.imwrite(args.save_frame, overlay)
                args.save_frame = None
            cv2.imshow("pc_hand_shadow_demo", overlay)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
