from __future__ import annotations

try:
    import rclpy
    from rclpy.node import Node
except Exception:  # pragma: no cover - depends on ROS runtime
    rclpy = None
    Node = object

try:
    from control_msgs.msg import JointJog
    from shadow_lamp_interfaces.msg import ArmCommand
    from std_srvs.srv import Trigger
except Exception:  # pragma: no cover - messages exist after ROS build
    JointJog = None
    ArmCommand = None
    Trigger = None

from arm_control.servo_mapper import ArmCommandPayload, arm_command_to_joint_jog_spec


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
        if JointJog is None or ArmCommand is None or Trigger is None:
            raise RuntimeError("ROS message dependencies are unavailable; build the ROS workspace first")
        super().__init__("shadow_lamp_arm_controller")
        self.yaw_sign = float(self.declare_parameter("yaw_sign", 1.0).value)
        self.pitch_sign = float(self.declare_parameter("pitch_sign", 1.0).value)
        self.velocity_scale = float(self.declare_parameter("velocity_scale", 0.6).value)
        self.min_threshold = float(self.declare_parameter("min_threshold", 0.05).value)
        self.servo_started = False
        self.start_requested = False

        self.publisher = self.create_publisher(JointJog, "/servo_node/delta_joint_cmds", 10)
        self.create_subscription(ArmCommand, "/arm/command", self._on_arm_command, 10)
        self.start_servo_client = self.create_client(Trigger, "/servo_node/start_servo")
        self.start_timer = self.create_timer(1.0, self._ensure_servo_started)

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
        spec = arm_command_to_joint_jog_spec(
            payload,
            yaw_sign=self.yaw_sign,
            pitch_sign=self.pitch_sign,
            velocity_scale=self.velocity_scale,
            min_threshold=self.min_threshold,
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
