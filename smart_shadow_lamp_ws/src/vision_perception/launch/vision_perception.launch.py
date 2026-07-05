from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="vision_perception",
                executable="vision_state_bridge",
                name="vision_state_bridge",
                output="screen",
            )
        ]
    )
