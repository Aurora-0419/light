from __future__ import annotations

from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from app.camera.realsense_camera import RealSenseCamera, RealSenseConfig


class RealSenseCameraNode(Node):
    def __init__(self) -> None:
        super().__init__("realsense_camera_node")
        config_path = Path(__file__).resolve().parents[2] / "configs" / "default.yaml"
        self.camera = RealSenseCamera(RealSenseConfig.from_yaml(config_path))
        self.camera.open()
        self.publisher = self.create_publisher(String, "camera/status", 10)
        self.timer = self.create_timer(0.2, self._tick)

    def _tick(self) -> None:
        try:
            frames = self.camera.get_frames()
        except RuntimeError as exc:
            self.get_logger().warning(f"failed to fetch RealSense frame: {exc}")
            return
        color = frames["color"]
        depth = frames["depth"]
        message = String()
        message.data = (
            f"color={color.shape if color is not None else None};"
            f"depth={depth.shape if depth is not None else None}"
        )
        self.publisher.publish(message)

    def destroy_node(self) -> bool:
        self.camera.close()
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = RealSenseCameraNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
