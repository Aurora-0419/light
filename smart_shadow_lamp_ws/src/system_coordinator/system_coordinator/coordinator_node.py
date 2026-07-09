from __future__ import annotations

from dataclasses import dataclass

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
except Exception:  # pragma: no cover - depends on ROS runtime
    rclpy = None
    Node = object
    String = None

try:
    from shadow_lamp_interfaces.msg import ArmCommand, LightCommand, SystemMode, VisionState, VoiceCommand
except Exception:  # pragma: no cover - messages exist after ROS build
    ArmCommand = None
    LightCommand = None
    SystemMode = None
    VisionState = None
    VoiceCommand = None

from system_coordinator.decision import ArmCommandPayload, compute_arm_command_from_vision
from system_coordinator.feedback_adapter import make_feedback_runtime
from system_coordinator.posture_reminder import PostureReminderStateMachine


@dataclass
class LightState:
    enabled: bool
    mode: str
    brightness: float
    color_temperature: float


def _clamp_brightness(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_light_command_from_voice(command: str, previous_state: LightState | None) -> LightState | None:
    state = previous_state or LightState(enabled=True, mode="warm_light_mode", brightness=0.2, color_temperature=3200.0)
    if command == "light_on":
        return LightState(enabled=True, mode=state.mode, brightness=state.brightness, color_temperature=state.color_temperature)
    if command == "light_off":
        return LightState(enabled=False, mode=state.mode, brightness=state.brightness, color_temperature=state.color_temperature)
    if command == "warm_light_mode":
        return LightState(enabled=True, mode="warm_light_mode", brightness=state.brightness, color_temperature=3200.0)
    if command == "cool_light_mode":
        return LightState(enabled=True, mode="cool_light_mode", brightness=state.brightness, color_temperature=6500.0)
    if command == "brightness_up":
        return LightState(enabled=True, mode=state.mode, brightness=_clamp_brightness(state.brightness + 0.1), color_temperature=state.color_temperature)
    if command == "brightness_down":
        return LightState(enabled=True, mode=state.mode, brightness=_clamp_brightness(state.brightness - 0.1), color_temperature=state.color_temperature)
    if command == "max_brightness":
        return LightState(enabled=True, mode=state.mode, brightness=1.0, color_temperature=state.color_temperature)
    if command == "min_brightness":
        return LightState(enabled=True, mode=state.mode, brightness=0.1, color_temperature=state.color_temperature)
    if command == "medium_brightness":
        return LightState(enabled=True, mode=state.mode, brightness=0.5, color_temperature=state.color_temperature)
    return None


def arm_payload_to_message(payload: ArmCommandPayload, message_factory):
    msg = message_factory()
    msg.mode = payload.mode
    msg.follow_enabled = payload.follow_enabled
    msg.target_x = payload.target_x
    msg.target_y = payload.target_y
    msg.target_z = payload.target_z
    msg.yaw = payload.yaw
    msg.pitch = payload.pitch
    return msg


def mode_to_message(mode: str, reason: str, tracking_enabled: bool, message_factory):
    msg = message_factory()
    msg.mode = mode
    msg.reason = reason
    msg.tracking_enabled = tracking_enabled
    return msg


def feedback_text_to_message(text: str, message_factory):
    msg = message_factory()
    msg.data = text
    return msg


def light_state_to_message(state: LightState, message_factory):
    msg = message_factory()
    msg.mode = state.mode
    msg.brightness = state.brightness
    msg.color_temperature = state.color_temperature
    msg.enabled = state.enabled
    msg.target_x = 0.0
    msg.target_y = 0.0
    return msg


class SystemCoordinator(Node):
    """Turns perception and voice state into high-level arm follow commands."""

    def __init__(self) -> None:
        if SystemMode is None or ArmCommand is None or LightCommand is None or VisionState is None or VoiceCommand is None:
            raise RuntimeError("shadow_lamp_interfaces messages are unavailable; build the ROS workspace first")
        super().__init__("system_coordinator")
        self.tracking_enabled = bool(self.declare_parameter("tracking_enabled_default", True).value)
        self.posture_reminder_enabled = bool(self.declare_parameter("posture_reminder_enabled", True).value)
        self.last_reason = "startup"
        self.light_state = LightState(enabled=True, mode="warm_light_mode", brightness=0.2, color_temperature=3200.0)
        self.feedback_runtime = make_feedback_runtime()
        self.posture_reminder = PostureReminderStateMachine(
            persistence_seconds=float(self.declare_parameter("posture_persistence_seconds", 4.0).value),
            cooldown_seconds=float(self.declare_parameter("posture_cooldown_seconds", 45.0).value),
        )
        self.mode_publisher = self.create_publisher(SystemMode, "/system/mode", 10)
        self.arm_publisher = self.create_publisher(ArmCommand, "/arm/command", 10)
        self.light_publisher = self.create_publisher(LightCommand, "/light/command", 10)
        self.feedback_publisher = self.create_publisher(String, "/voice/feedback", 10)
        self.create_subscription(VisionState, "/vision/state", self._on_vision_state, 10)
        self.create_subscription(VoiceCommand, "/voice/command", self._on_voice_command, 10)
        self.timer = self.create_timer(1.0, self._publish_mode)

    def _on_voice_command(self, msg) -> None:
        if msg.command == "enable_tracking":
            self.tracking_enabled = True
            self.last_reason = "voice_enable_tracking"
        elif msg.command == "disable_tracking":
            self.tracking_enabled = False
            self.last_reason = "voice_disable_tracking"
        light_state = compute_light_command_from_voice(msg.command, previous_state=self.light_state)
        if light_state is not None:
            self.light_state = light_state
            self.last_reason = f"voice_{msg.command}"
            light_msg = light_state_to_message(light_state, LightCommand)
            if hasattr(light_msg, "stamp"):
                light_msg.stamp = self.get_clock().now().to_msg()
            self.light_publisher.publish(light_msg)

    def _on_vision_state(self, msg) -> None:
        self._handle_posture_state(msg)
        payload = compute_arm_command_from_vision(
            tracking_enabled=self.tracking_enabled,
            hand_detected=msg.hand_detected,
            hand_center_x=msg.hand_center_x,
            hand_center_y=msg.hand_center_y,
            shadow_detected=msg.shadow_detected,
            shadow_center_x=msg.shadow_center_x,
            shadow_center_y=msg.shadow_center_y,
            needs_relight=msg.needs_relight,
        )
        self.last_reason = payload.mode
        if not payload.follow_enabled:
            return
        arm_msg = arm_payload_to_message(payload, ArmCommand)
        if hasattr(arm_msg, "stamp"):
            arm_msg.stamp = self.get_clock().now().to_msg()
        self.arm_publisher.publish(arm_msg)

    def _handle_posture_state(self, msg) -> None:
        if not self.posture_reminder_enabled:
            return
        issue = "" if getattr(msg, "posture_ok", True) else getattr(msg, "posture_issue", "")
        if issue != "shoulder_tilt":
            issue = ""
        decision = self.posture_reminder.update(
            issue=issue,
            now=self.get_clock().now().nanoseconds / 1e9,
        )
        if decision.should_remind and decision.message:
            self.feedback_publisher.publish(feedback_text_to_message(decision.message, String))

    def _publish_mode(self) -> None:
        mode = "tracking" if self.tracking_enabled else "idle"
        msg = mode_to_message(mode, self.last_reason, self.tracking_enabled, SystemMode)
        if hasattr(msg, "stamp"):
            msg.stamp = self.get_clock().now().to_msg()
        self.mode_publisher.publish(msg)


def main() -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is unavailable in the current Python environment")
    rclpy.init()
    node = SystemCoordinator()
    try:
        rclpy.spin(node)
    finally:
        if hasattr(node, "destroy_node"):
            node.destroy_node()
        rclpy.shutdown()
