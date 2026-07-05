from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

try:
    import pyrealsense2 as rs
except ImportError:  # pragma: no cover - exercised on hardware path
    rs = None


@dataclass
class RealSenseConfig:
    width: int
    height: int
    fps: int
    backend: str = "auto"
    color_device: str = "/dev/video4"
    depth_device: str = "/dev/video0"
    enable_color: bool = True
    enable_depth: bool = True

    @classmethod
    def from_yaml(cls, path: Path) -> "RealSenseConfig":
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        camera = data.get("camera", {})
        return cls(
            backend=str(camera.get("backend", "auto")),
            width=int(camera.get("width", 640)),
            height=int(camera.get("height", 480)),
            fps=int(camera.get("fps", 30)),
            color_device=str(camera.get("color_device", "/dev/video4")),
            depth_device=str(camera.get("depth_device", "/dev/video0")),
            enable_color=bool(camera.get("enable_color", True)),
            enable_depth=bool(camera.get("enable_depth", True)),
        )


class RealSenseCamera:
    def __init__(self, config: RealSenseConfig):
        self.config = config
        self.pipeline: Any | None = None
        self.pipeline_config: Any | None = None
        self.color_capture: Any | None = None
        self._is_open = False
        self._backend_in_use = "unknown"

    def _choose_backend(self) -> str:
        if self.config.backend != "auto":
            return self.config.backend
        if os.path.exists(self.config.color_device):
            return "v4l2"
        if rs is not None:
            return "pyrealsense2"
        raise RuntimeError("No usable RealSense backend is available")

    def open(self) -> None:
        backend = self._choose_backend()
        if backend == "v4l2":
            self.color_capture = cv2.VideoCapture(self.config.color_device, cv2.CAP_V4L2)
            self.color_capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            self.color_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            self.color_capture.set(cv2.CAP_PROP_FPS, self.config.fps)
            if not self.color_capture.isOpened():
                raise RuntimeError(f"Failed to open V4L2 color device: {self.config.color_device}")
            self._backend_in_use = "v4l2"
        else:
            if rs is None:
                raise RuntimeError("pyrealsense2 is not available in the current environment")
            self.pipeline = rs.pipeline()
            self.pipeline_config = rs.config()
            if self.config.enable_color:
                self.pipeline_config.enable_stream(
                    rs.stream.color,
                    self.config.width,
                    self.config.height,
                    rs.format.bgr8,
                    self.config.fps,
                )
            if self.config.enable_depth:
                self.pipeline_config.enable_stream(
                    rs.stream.depth,
                    self.config.width,
                    self.config.height,
                    rs.format.z16,
                    self.config.fps,
                )
            self.pipeline.start(self.pipeline_config)
            self._backend_in_use = "pyrealsense2"
        self._is_open = True

    def get_frames(self) -> dict[str, np.ndarray | None]:
        if not self._is_open:
            raise RuntimeError("RealSense camera is not open")

        if self._backend_in_use == "v4l2":
            if self.color_capture is None:
                raise RuntimeError("V4L2 color capture is not initialized")
            ok, color = self.color_capture.read()
            if not ok or color is None:
                raise RuntimeError("Failed to read color frame from V4L2 device")
            return {"color": color, "depth": None}

        frames = self.pipeline.wait_for_frames()
        color_frame = frames.get_color_frame() if self.config.enable_color else None
        depth_frame = frames.get_depth_frame() if self.config.enable_depth else None

        color = np.asanyarray(color_frame.get_data()) if color_frame else None
        depth = np.asanyarray(depth_frame.get_data()) if depth_frame else None
        return {"color": color, "depth": depth}

    def close(self) -> None:
        if self.color_capture is not None:
            self.color_capture.release()
            self.color_capture = None
        if self.pipeline is not None and self._is_open:
            self.pipeline.stop()
            self.pipeline = None
        self._is_open = False
