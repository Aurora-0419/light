from __future__ import annotations

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
except Exception:  # pragma: no cover - import depends on local ROS runtime
    rclpy = None
    Node = object
    String = None

from system_coordinator.feedback_adapter import make_feedback_runtime


def play_feedback_safely(runtime, text: str, logger):
    try:
        return runtime.speak_or_print(text)
    except Exception as exc:  # pragma: no cover - exercised by integration runtime
        logger.warning(f"voice feedback failed: {exc}")
        return None


class VoiceFeedbackBridge(Node):
    def __init__(self) -> None:
        if String is None:
            raise RuntimeError("std_msgs.msg.String is unavailable; build the ROS workspace first")
        super().__init__("voice_feedback_bridge")
        self.runtime = make_feedback_runtime()
        self.create_subscription(String, "/voice/feedback", self._on_feedback, 10)

    def _on_feedback(self, msg) -> None:
        text = str(getattr(msg, "data", "") or "")
        if not text:
            return
        play_feedback_safely(self.runtime, text, logger=self.get_logger())


def main() -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is unavailable in the current Python environment")
    rclpy.init()
    node = VoiceFeedbackBridge()
    try:
        rclpy.spin(node)
    finally:
        if hasattr(node, "destroy_node"):
            node.destroy_node()
        rclpy.shutdown()
