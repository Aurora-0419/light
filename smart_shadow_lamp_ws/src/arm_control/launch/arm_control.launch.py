from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="arm_control",
                executable="arm_controller",
                name="arm_controller",
                output="screen",
            )
        ]
    )
