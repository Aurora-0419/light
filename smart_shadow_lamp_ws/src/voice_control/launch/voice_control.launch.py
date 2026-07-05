from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="voice_control",
                executable="voice_command_bridge",
                name="voice_command_bridge",
                output="screen",
            )
        ]
    )
