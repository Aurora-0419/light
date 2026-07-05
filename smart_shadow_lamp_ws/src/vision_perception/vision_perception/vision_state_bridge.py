from __future__ import annotations

try:
    import rclpy
    from rclpy.node import Node
except Exception:  # pragma: no cover - import depends on local ROS runtime
    rclpy = None
    Node = object

try:
    from shadow_lamp_interfaces.msg import VisionState
except Exception:  # pragma: no cover - messages exist after ROS build
    VisionState = None

from vision_perception.adapter import make_default_runtime, payload_to_message


class VisionStateBridge(Node):
    """Publishes VisionState messages from the existing PC-first perception pipeline."""

    def __init__(self) -> None:
        if VisionState is None:
            raise RuntimeError("shadow_lamp_interfaces.msg.VisionState is unavailable; build the ROS workspace first")
        super().__init__("vision_state_bridge")
        self.runtime = make_default_runtime()
        self.publisher = self.create_publisher(VisionState, "/vision/state", 10)
        self.timer = self.create_timer(0.5, self._publish_state)

    def _publish_state(self) -> None:
        payload = self.runtime.capture_once()
        msg = payload_to_message(payload, VisionState)
        if hasattr(msg, "stamp"):
            msg.stamp = self.get_clock().now().to_msg()
        self.publisher.publish(msg)

    def destroy_node(self) -> bool:
        self.runtime.close()
        return super().destroy_node()


def main() -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is unavailable in the current Python environment")
    rclpy.init()
    node = VisionStateBridge()
    try:
        rclpy.spin(node)
    finally:
        if hasattr(node, "destroy_node"):
            node.destroy_node()
        rclpy.shutdown()
