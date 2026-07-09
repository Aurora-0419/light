from __future__ import annotations

import math
import select
import sys
import termios
import tty

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from control_msgs.action import FollowJointTrajectory
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectoryPoint


def clamp_joint1(target_joint1: float, joint1_limit_rad: float) -> float:
    return max(-joint1_limit_rad, min(joint1_limit_rad, target_joint1))


def compute_next_joint_positions(
    *,
    key: str,
    current_positions: tuple[float, float, float, float],
    baseline_positions: tuple[float, float, float, float],
    step_rad: float,
    joint1_limit_rad: float,
) -> tuple[float, float, float, float] | None:
    if key == "0":
        return baseline_positions
    if key not in {"1", "2", "3", "4"}:
        return None

    if key in {"1", "2"}:
        delta = step_rad if key == "1" else -step_rad
        target_joint1 = clamp_joint1(current_positions[0] + delta, joint1_limit_rad)
        return (target_joint1, current_positions[1], current_positions[2], current_positions[3])

    joint2_delta = step_rad if key == "3" else -step_rad
    return (
        current_positions[0],
        round(current_positions[1] + joint2_delta, 6),
        current_positions[2],
        current_positions[3],
    )


def build_keyboard_goal_dict(joint_positions: tuple[float, float, float, float], duration_sec: float) -> dict[str, object]:
    return {
        "joint_names": ["joint1", "joint2", "joint3", "joint4"],
        "positions": list(joint_positions),
        "duration_sec": duration_sec,
    }


def _build_goal_message(joint_positions: tuple[float, float, float, float], duration_sec: float):
    goal = FollowJointTrajectory.Goal()
    goal.trajectory.joint_names = ["joint1", "joint2", "joint3", "joint4"]
    point = JointTrajectoryPoint()
    point.positions = list(joint_positions)
    point.velocities = [0.0, 0.0, 0.0, 0.0]
    point.time_from_start.sec = int(duration_sec)
    point.time_from_start.nanosec = int((duration_sec - int(duration_sec)) * 1e9)
    goal.trajectory.points = [point]
    return goal


class Joint1KeyboardTeleop(Node):
    def __init__(self) -> None:
        super().__init__("joint1_keyboard_teleop")
        self.baseline_positions = (
            float(self.declare_parameter("baseline_joint1", 0.0).value),
            float(self.declare_parameter("baseline_joint2", 0.0).value),
            float(self.declare_parameter("baseline_joint3", 0.0).value),
            float(self.declare_parameter("baseline_joint4", 0.45).value),
        )
        self.step_rad = float(self.declare_parameter("step_rad", 0.04).value)
        self.joint1_limit_rad = float(self.declare_parameter("joint1_limit_rad", math.radians(45.0)).value)
        self.duration_sec = float(self.declare_parameter("duration_sec", 1.0).value)
        self.current_positions: dict[str, float] = {}
        self.client = ActionClient(self, FollowJointTrajectory, "/arm_controller/follow_joint_trajectory")
        self.create_subscription(JointState, "/joint_states", self._on_joint_states, 10)

    def _on_joint_states(self, msg: JointState) -> None:
        for name, position in zip(msg.name, msg.position):
            if name in {"joint1", "joint2", "joint3", "joint4"}:
                self.current_positions[name] = float(position)

    def get_current_joint_positions(self) -> tuple[float, float, float, float] | None:
        names = ("joint1", "joint2", "joint3", "joint4")
        if any(name not in self.current_positions for name in names):
            return None
        return tuple(self.current_positions[name] for name in names)

    def send_joint_positions(self, joint_positions: tuple[float, float, float, float]) -> int:
        if not self.client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("trajectory action server is not available")
            return 1

        goal = _build_goal_message(joint_positions, self.duration_sec)
        future = self.client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)
        goal_handle = future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error("keyboard teleop goal was rejected")
            return 2

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        wrapped_result = result_future.result()
        if wrapped_result is None:
            self.get_logger().error("keyboard teleop result was not returned")
            return 3
        return 0 if wrapped_result.result.error_code == 0 else int(wrapped_result.result.error_code)

    def handle_key(self, key: str) -> int:
        current_positions = self.get_current_joint_positions()
        if key in {"1", "2", "3", "4"} and current_positions is None:
            self.get_logger().warning("joint_states are not ready yet")
            return 4

        target_positions = compute_next_joint_positions(
            key=key,
            current_positions=current_positions or self.baseline_positions,
            baseline_positions=self.baseline_positions,
            step_rad=self.step_rad,
            joint1_limit_rad=self.joint1_limit_rad,
        )
        if target_positions is None:
            return 0
        return self.send_joint_positions(target_positions)


def _read_key() -> str:
    dr, _, _ = select.select([sys.stdin], [], [], 0.1)
    if not dr:
        return ""
    return sys.stdin.read(1)


def main(argv: list[str] | None = None) -> int:
    rclpy.init(args=argv)
    node = Joint1KeyboardTeleop()
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
    node.get_logger().info(
        "Keyboard control: 0=baseline, 1=joint1 left, 2=joint1 right, 3=joint2 up, 4=joint2 down, q=quit"
    )
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)
            key = _read_key()
            if key == "q":
                return 0
            if key:
                result = node.handle_key(key)
                if result != 0 and key in {"0", "1", "2", "3", "4"}:
                    node.get_logger().warning(f"command for key {key} failed with code {result}")
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
