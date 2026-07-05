from __future__ import annotations

import rclpy
from rclpy.node import Node


class LightController(Node):
    """Placeholder node for future light hardware integration."""

    def __init__(self) -> None:
        super().__init__("light_controller")


def main() -> None:
    rclpy.init()
    node = LightController()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
