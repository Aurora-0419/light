from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.camera.realsense_camera import RealSenseCamera, RealSenseConfig
from app.perception.hand_shadow_demo import HandShadowDemoDetector
from app.utils.draw import draw_perception_overlay
from app.runtime.backend_selector import choose_perception_backend, detect_runtime_capabilities


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the RealSense perception demo")
    parser.add_argument("--dry-run", action="store_true", help="Only inspect runtime state")
    parser.add_argument("--no-depth", action="store_true", help="Disable depth stream")
    parser.add_argument("--save-frame", type=str, default=None, help="Optional frame output path")
    return parser


def _default_camera_factory(no_depth: bool) -> RealSenseCamera:
    config = RealSenseConfig.from_yaml(ROOT / "configs" / "default.yaml")
    config.enable_depth = not no_depth
    return RealSenseCamera(config)


def run_demo(
    dry_run: bool = False,
    no_depth: bool = False,
    save_frame: Path | None = None,
    camera_factory=None,
    detector_factory=None,
) -> dict[str, str]:
    capabilities = detect_runtime_capabilities()
    backend = choose_perception_backend(capabilities)

    if dry_run:
        return {
            "mode": "dry_run",
            "backend": backend["backend"],
            "warning": backend["warning"],
            "depth_enabled": str(not no_depth),
            "save_frame": str(save_frame) if save_frame is not None else "",
        }

    camera_factory = camera_factory or (lambda: _default_camera_factory(no_depth))
    detector_factory = detector_factory or HandShadowDemoDetector

    camera = camera_factory()
    detector = detector_factory()
    camera.open()
    try:
        frames = camera.get_frames()
        result = detector.process(frames["color"], frames["depth"])
        overlay = draw_perception_overlay(frames["color"], result)
        if save_frame is not None:
            cv2.imwrite(str(save_frame), overlay)

        height, width = frames["color"].shape[:2]
        return {
            "mode": "run",
            "backend": backend["backend"],
            "warning": backend["warning"],
            "depth_enabled": str(not no_depth),
            "save_frame": str(save_frame) if save_frame is not None else "",
            "frame_shape": f"{width}x{height}",
            "label": result.label,
        }
    finally:
        camera.close()


def main() -> int:
    args = build_arg_parser().parse_args()
    result = run_demo(
        dry_run=args.dry_run,
        no_depth=args.no_depth,
        save_frame=Path(args.save_frame) if args.save_frame else None,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
