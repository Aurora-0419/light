from pathlib import Path

import numpy as np

from scripts.run_realsense_demo import build_arg_parser, run_demo


def test_build_arg_parser_supports_dry_run_and_save_frame():
    parser = build_arg_parser()
    args = parser.parse_args(["--dry-run", "--save-frame", "out.png", "--no-depth"])

    assert args.dry_run is True
    assert args.save_frame == "out.png"
    assert args.no_depth is True


def test_run_demo_dry_run_returns_runtime_summary(tmp_path: Path):
    save_path = tmp_path / "frame.png"

    result = run_demo(dry_run=True, save_frame=save_path)

    assert result["mode"] == "dry_run"
    assert "backend" in result
    assert result["save_frame"] == str(save_path)


class _FakeCamera:
    def open(self):
        return None

    def get_frames(self):
        return {
            "color": np.zeros((32, 32, 3), dtype=np.uint8),
            "depth": np.zeros((32, 32), dtype=np.uint16),
        }

    def close(self):
        return None


class _FakeDetector:
    def process(self, color_frame, depth_frame):
        class Result:
            has_detection = False
            primary_bbox = None
            primary_center = None
            depth_value_mm = None
            label = "fake"

        return Result()


def test_run_demo_processes_one_frame_with_injected_camera_and_detector():
    result = run_demo(camera_factory=_FakeCamera, detector_factory=_FakeDetector)

    assert result["mode"] == "run"
    assert result["frame_shape"] == "32x32"
    assert result["label"] == "fake"
