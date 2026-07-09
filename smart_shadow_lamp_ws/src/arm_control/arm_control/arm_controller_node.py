from __future__ import annotations

try:
    import rclpy
    from rclpy.node import Node
except Exception:  # pragma: no cover - depends on ROS runtime
    rclpy = None
    Node = object

try:
    from control_msgs.msg import JointJog
    from sensor_msgs.msg import JointState
    from shadow_lamp_interfaces.msg import ArmCommand
    from std_srvs.srv import Trigger
except Exception:  # pragma: no cover - messages exist after ROS build
    JointJog = None
    JointState = None
    ArmCommand = None
    Trigger = None

from arm_control.servo_mapper import ArmCommandPayload, JointJogSpec, arm_command_to_joint_jog_spec


def update_baseline_yaw(current_baseline_yaw, current_joint1_yaw):
    if current_baseline_yaw is not None:
        return current_baseline_yaw
    return current_joint1_yaw


def compute_bounded_yaw_velocity(
    baseline_yaw_rad,
    current_joint1_yaw,
    requested_yaw_norm,
    yaw_limit_rad,
    yaw_error_deadband_rad,
    yaw_velocity_scale,
    max_velocity,
):
    requested_offset = max(-yaw_limit_rad, min(requested_yaw_norm * yaw_limit_rad, yaw_limit_rad))
    target_yaw = baseline_yaw_rad + requested_offset
    error = target_yaw - current_joint1_yaw
    if abs(error) <= yaw_error_deadband_rad:
        return 0.0
    normalized_error = error / max(yaw_limit_rad, 1e-9)
    velocity = normalized_error * yaw_velocity_scale * max_velocity
    return round(max(-max_velocity, min(velocity, max_velocity)), 6)


def arm_message_to_payload(msg) -> ArmCommandPayload:
    return ArmCommandPayload(
        mode=msg.mode,
        follow_enabled=msg.follow_enabled,
        yaw=msg.yaw,
        pitch=msg.pitch,
    )


def joint_jog_spec_to_message(spec, message_factory, clock=None):
    msg = message_factory()
    if hasattr(msg, "header") and clock is not None:
        msg.header.stamp = clock.now().to_msg()
        msg.header.frame_id = "link1"
    msg.joint_names = spec.joint_names
    msg.velocities = spec.velocities
    return msg


class ArmController(Node):
    """Maps arm follow commands into MoveIt Servo joint jog messages."""

    def __init__(self) -> None:
        if JointJog is None or JointState is None or ArmCommand is None or Trigger is None:
            raise RuntimeError("ROS message dependencies are unavailable; build the ROS workspace first")
        super().__init__("shadow_lamp_arm_controller")
        self.yaw_sign = float(self.declare_parameter("yaw_sign", 1.0).value)
        self.pitch_sign = float(self.declare_parameter("pitch_sign", 1.0).value)
        self.velocity_scale = float(self.declare_parameter("velocity_scale", 0.6).value)
        self.min_threshold = float(self.declare_parameter("min_threshold", 0.05).value)
        self.full_joint_jog = bool(self.declare_parameter("full_joint_jog", False).value)
        self.hand_yaw_limit_rad = float(self.declare_parameter("hand_yaw_limit_rad", 0.785398).value)
        self.hand_yaw_error_deadband_rad = float(
            self.declare_parameter("hand_yaw_error_deadband_rad", 0.01).value
        )
        self.hand_yaw_velocity_scale = float(self.declare_parameter("hand_yaw_velocity_scale", 1.0).value)
        self.max_velocity = float(self.declare_parameter("max_velocity", 0.8).value)
        self.servo_started = False
        self.start_requested = False
        self.current_joint1_yaw = None
        self.baseline_joint1_yaw = None

        self.publisher = self.create_publisher(JointJog, "/servo_node/delta_joint_cmds", 10)
        self.create_subscription(ArmCommand, "/arm/command", self._on_arm_command, 10)
        self.create_subscription(JointState, "/joint_states", self._on_joint_states, 10)
        self.start_servo_client = self.create_client(Trigger, "/servo_node/start_servo")
        self.start_timer = self.create_timer(1.0, self._ensure_servo_started)

    def _on_joint_states(self, msg) -> None:
        try:
            joint_index = msg.name.index("joint1")
        except ValueError:
            return
        if joint_index >= len(msg.position):
            return
        self.current_joint1_yaw = float(msg.position[joint_index])

    def _ensure_servo_started(self) -> None:
        if self.servo_started or self.start_requested:
            return
        if not self.start_servo_client.wait_for_service(timeout_sec=0.0):
            return
        self.start_requested = True
        future = self.start_servo_client.call_async(Trigger.Request())
        future.add_done_callback(self._handle_start_servo_result)

    def _handle_start_servo_result(self, future) -> None:
        self.start_requested = False
        try:
            result = future.result()
        except Exception as exc:  # pragma: no cover - depends on ROS runtime
            self.get_logger().warning(f"failed to start servo node: {exc}")
            return
        if result is not None and getattr(result, "success", False):
            self.servo_started = True

    def _on_arm_command(self, msg) -> None:
        payload = arm_message_to_payload(msg)
        bounded_yaw_session_active = self.baseline_joint1_yaw is not None

        if not payload.follow_enabled:
            if bounded_yaw_session_active:
                self.baseline_joint1_yaw = None
                jog = joint_jog_spec_to_message(
                    JointJogSpec(joint_names=["joint1", "joint2"], velocities=[0.0, 0.0]),
                    JointJog,
                    clock=self.get_clock(),
                )
                self.publisher.publish(jog)
            elif payload.mode == "hand_yaw_limited":
                self.baseline_joint1_yaw = None
            return

        if payload.mode != "hand_yaw_limited":
            self.baseline_joint1_yaw = None

        if payload.mode == "hand_yaw_limited" and payload.follow_enabled:
            self.baseline_joint1_yaw = update_baseline_yaw(self.baseline_joint1_yaw, self.current_joint1_yaw)
            if self.current_joint1_yaw is None or self.baseline_joint1_yaw is None:
                return

            yaw_velocity = compute_bounded_yaw_velocity(
                baseline_yaw_rad=self.baseline_joint1_yaw,
                current_joint1_yaw=self.current_joint1_yaw,
                requested_yaw_norm=payload.yaw,
                yaw_limit_rad=self.hand_yaw_limit_rad,
                yaw_error_deadband_rad=self.hand_yaw_error_deadband_rad,
                yaw_velocity_scale=self.hand_yaw_velocity_scale,
                max_velocity=self.max_velocity,
            )
            if yaw_velocity == 0.0:
                return

            jog = joint_jog_spec_to_message(
                JointJogSpec(joint_names=["joint1", "joint2"], velocities=[yaw_velocity * self.yaw_sign, 0.0]),
                JointJog,
                clock=self.get_clock(),
            )
            self.publisher.publish(jog)
            return

        spec = arm_command_to_joint_jog_spec(
            payload,
            yaw_sign=self.yaw_sign,
            pitch_sign=self.pitch_sign,
            velocity_scale=self.velocity_scale,
            min_threshold=self.min_threshold,
            default_full_chain=self.full_joint_jog,
        )
        if spec is None:
            return
        jog = joint_jog_spec_to_message(spec, JointJog, clock=self.get_clock())
        self.publisher.publish(jog)


def main() -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is unavailable in the current Python environment")
    rclpy.init()
    node = ArmController()
    try:
        rclpy.spin(node)
    finally:
        if hasattr(node, "destroy_node"):
            node.destroy_node()
        rclpy.shutdown()
