from __future__ import annotations

try:
    import rclpy
    from rclpy.node import Node
except Exception:  # pragma: no cover - import depends on local ROS runtime
    rclpy = None
    Node = object

try:
    from shadow_lamp_interfaces.msg import VoiceCommand
except Exception:  # pragma: no cover - messages exist after ROS build
    VoiceCommand = None

from voice_control.adapter import make_default_runtime, payload_to_message


def capture_payload_safely(runtime, logger):
    try:
        return runtime.capture_once()
    except Exception as exc:  # pragma: no cover - exercised by integration runtime
        logger.warning(f"voice capture failed: {exc}")
        return None


class VoiceCommandBridge(Node):
    """Publishes VoiceCommand messages from the existing speech pipeline."""

    def __init__(self) -> None:
        if VoiceCommand is None:
            raise RuntimeError("shadow_lamp_interfaces.msg.VoiceCommand is unavailable; build the ROS workspace first")
        super().__init__("voice_command_bridge")
        self.runtime = make_default_runtime()
        self.publisher = self.create_publisher(VoiceCommand, "/voice/command", 10)
        self.timer = self.create_timer(2.5, self._publish_once)

    def _publish_once(self) -> None:
        payload = capture_payload_safely(self.runtime, self.get_logger())
        if payload is None:
            return
        if not payload.confirmed or not payload.command:
            return
        msg = payload_to_message(payload, VoiceCommand)
        if hasattr(msg, "stamp"):
            msg.stamp = self.get_clock().now().to_msg()
        self.publisher.publish(msg)


def main() -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is unavailable in the current Python environment")
    rclpy.init()
    node = VoiceCommandBridge()
    try:
        rclpy.spin(node)
    finally:
        if hasattr(node, "destroy_node"):
            node.destroy_node()
        rclpy.shutdown()
