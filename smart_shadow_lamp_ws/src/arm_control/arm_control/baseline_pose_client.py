from __future__ import annotations

import argparse
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


def build_baseline_goal_dict(joint_positions: tuple[float, float, float, float], duration_sec: float) -> dict[str, object]:
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


class BaselinePoseClient(Node):
    def __init__(self) -> None:
        super().__init__("arm_baseline_pose_client")
        self.client = ActionClient(self, FollowJointTrajectory, "/arm_controller/follow_joint_trajectory")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send a fixed baseline pose to the arm trajectory controller")
    parser.add_argument("--joint1", type=float, default=0.0)
    parser.add_argument("--joint2", type=float, default=0.0)
    parser.add_argument("--joint3", type=float, default=0.0)
    parser.add_argument("--joint4", type=float, default=0.25)
    parser.add_argument("--duration", type=float, default=4.0)
    args = parser.parse_args(argv)

    joint_positions = (args.joint1, args.joint2, args.joint3, args.joint4)

    rclpy.init(args=None)
    node = BaselinePoseClient()
    try:
        if not node.client.wait_for_server(timeout_sec=5.0):
            node.get_logger().error("trajectory action server is not available")
            return 1

        goal = _build_goal_message(joint_positions, args.duration)
        future = node.client.send_goal_async(goal)
        rclpy.spin_until_future_complete(node, future)
        goal_handle = future.result()
        if goal_handle is None or not goal_handle.accepted:
            node.get_logger().error("baseline pose goal was rejected")
            return 2

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(node, result_future)
        wrapped_result = result_future.result()
        if wrapped_result is None:
            node.get_logger().error("baseline pose result was not returned")
            return 3
        return 0 if wrapped_result.result.error_code == 0 else int(wrapped_result.result.error_code)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
