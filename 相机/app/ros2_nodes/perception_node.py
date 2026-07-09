from __future__ import annotations

from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from app.camera.realsense_camera import RealSenseCamera, RealSenseConfig
from app.perception.hand_shadow_demo import HandShadowDemoDetector


class PerceptionNode(Node):
    def __init__(self) -> None:
        super().__init__("perception_node")
        config_path = Path(__file__).resolve().parents[2] / "configs" / "default.yaml"
        self.camera = RealSenseCamera(RealSenseConfig.from_yaml(config_path))
        self.detector = HandShadowDemoDetector()
        self.camera.open()
        self.publisher = self.create_publisher(String, "perception/result", 10)
        self.timer = self.create_timer(0.2, self._tick)

    def _tick(self) -> None:
        try:
            frames = self.camera.get_frames()
        except RuntimeError as exc:
            self.get_logger().warning(f"failed to fetch RealSense frame: {exc}")
            return
        result = self.detector.process(frames["color"], frames["depth"])
        message = String()
        message.data = (
            f"has_detection={result.has_detection};"
            f"bbox={result.primary_bbox};"
            f"center={result.primary_center};"
            f"depth_mm={result.depth_value_mm};"
            f"label={result.label}"
        )
        self.publisher.publish(message)

    def destroy_node(self) -> bool:
        self.camera.close()
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = PerceptionNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
