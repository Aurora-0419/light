from pathlib import Path

import numpy as np

from app.camera.realsense_camera import RealSenseCamera, RealSenseConfig


class _MockFrame:
    def __init__(self, data):
        self._data = data

    def get_data(self):
        return self._data


class _MockFrameset:
    def __init__(self, color, depth):
        self._color = _MockFrame(color)
        self._depth = _MockFrame(depth)

    def get_color_frame(self):
        return self._color

    def get_depth_frame(self):
        return self._depth


class _MockPipeline:
    def wait_for_frames(self):
        color = np.zeros((480, 640, 3), dtype=np.uint8)
        depth = np.zeros((480, 640), dtype=np.uint16)
        return _MockFrameset(color, depth)

    def stop(self):
        return None


def test_realsense_config_loads_from_yaml():
    config = RealSenseConfig.from_yaml(
        Path(__file__).resolve().parents[1] / "configs" / "default.yaml"
    )

    assert config.width == 640
    assert config.height == 480
    assert config.fps == 30
    assert config.enable_depth is True
    assert config.enable_color is True


def test_realsense_camera_returns_numpy_frames_from_pipeline():
    camera = RealSenseCamera(RealSenseConfig(width=640, height=480, fps=30))
    camera.pipeline = _MockPipeline()
    camera._is_open = True

    frames = camera.get_frames()

    assert frames["color"].shape == (480, 640, 3)
    assert frames["depth"].shape == (480, 640)
    assert frames["color"].dtype == np.uint8
    assert frames["depth"].dtype == np.uint16
