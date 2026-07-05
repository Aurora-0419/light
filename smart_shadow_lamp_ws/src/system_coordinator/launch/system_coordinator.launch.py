from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="system_coordinator",
                executable="system_coordinator",
                name="system_coordinator",
                output="screen",
            )
        ]
    )
