from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="light_control",
                executable="light_controller",
                name="light_controller",
                output="screen",
            )
        ]
    )
