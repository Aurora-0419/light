from __future__ import annotations

from time import monotonic

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


def format_runtime_debug_line(result: dict[str, str]) -> str:
    transcript = str(result.get("transcript", "") or "")
    wake_detected = str(result.get("wake_detected", "False") or "False")
    command_name = str(result.get("command_name", "") or "")
    debug_reason = str(result.get("debug_reason", "unknown") or "unknown")
    window_state = str(result.get("window_state", "unknown") or "unknown")
    pending_command = str(result.get("pending_command", "-") or "-")
    line = f'[voice] transcript="{transcript}" wake={wake_detected} command="{command_name}" reason={debug_reason} window={window_state} pending={pending_command}'
    audio_peak = str(result.get("audio_peak", "") or "")
    audio_avg_abs = str(result.get("audio_avg_abs", "") or "")
    if audio_peak:
        line += f" audio_peak={audio_peak}"
    if audio_avg_abs:
        line += f" audio_avg_abs={audio_avg_abs}"
    return line


def should_log_runtime_debug(
    payload: dict[str, str],
    *,
    previous_payload: dict[str, str] | None,
    now_seconds: float,
    previous_no_speech_log_at: float,
    no_speech_interval_seconds: float = 1.0,
) -> bool:
    debug_reason = str(payload.get("debug_reason", "") or "")
    if debug_reason != "no_speech":
        return previous_payload != payload
    if previous_payload != payload:
        return True
    return (now_seconds - previous_no_speech_log_at) >= no_speech_interval_seconds


class VoiceCommandBridge(Node):
    """Publishes VoiceCommand messages from the existing speech pipeline."""

    def __init__(self) -> None:
        if VoiceCommand is None:
            raise RuntimeError("shadow_lamp_interfaces.msg.VoiceCommand is unavailable; build the ROS workspace first")
        super().__init__("voice_command_bridge")
        self.runtime = make_default_runtime()
        self.publisher = self.create_publisher(VoiceCommand, "/voice/command", 10)
        self.timer = self.create_timer(0.1, self._publish_once)
        self._last_debug_payload: dict[str, str] | None = None
        self._last_no_speech_log_at = 0.0

    def _publish_once(self) -> None:
        payload = capture_payload_safely(self.runtime, self.get_logger())
        if payload is None:
            return
        debug_payload = {
            "transcript": str(getattr(payload, "raw_text", "") or ""),
            "wake_detected": str(getattr(payload, "wake_word", "") != ""),
            "command_name": str(getattr(payload, "command", "") or ""),
            "debug_reason": str(getattr(payload, "debug_reason", "unknown") or "unknown"),
            "window_state": str(getattr(payload, "window_state", "unknown") or "unknown"),
            "pending_command": str(getattr(payload, "pending_command", "-") or "-"),
            "audio_peak": str(getattr(payload, "audio_peak", "") or ""),
            "audio_avg_abs": str(getattr(payload, "audio_avg_abs", "") or ""),
        }
        now_seconds = monotonic()
        if should_log_runtime_debug(
            debug_payload,
            previous_payload=self._last_debug_payload,
            now_seconds=now_seconds,
            previous_no_speech_log_at=self._last_no_speech_log_at,
        ):
            self.get_logger().info(format_runtime_debug_line(debug_payload))
            if debug_payload.get("debug_reason") == "no_speech":
                self._last_no_speech_log_at = now_seconds
        self._last_debug_payload = debug_payload
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
        close = getattr(getattr(node, "runtime", None), "close", None)
        if callable(close):
            close()
        if hasattr(node, "destroy_node"):
            node.destroy_node()
        rclpy.shutdown()
