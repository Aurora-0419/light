from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    yaw_sign = LaunchConfiguration("yaw_sign")
    pitch_sign = LaunchConfiguration("pitch_sign")
    velocity_scale = LaunchConfiguration("velocity_scale")
    min_threshold = LaunchConfiguration("min_threshold")
    hand_yaw_limit_rad = LaunchConfiguration("hand_yaw_limit_rad")
    hand_yaw_error_deadband_rad = LaunchConfiguration("hand_yaw_error_deadband_rad")
    hand_yaw_velocity_scale = LaunchConfiguration("hand_yaw_velocity_scale")
    max_velocity = LaunchConfiguration("max_velocity")

    return LaunchDescription(
        [
            DeclareLaunchArgument("yaw_sign", default_value="1.0"),
            DeclareLaunchArgument("pitch_sign", default_value="1.0"),
            DeclareLaunchArgument("velocity_scale", default_value="0.6"),
            DeclareLaunchArgument("min_threshold", default_value="0.05"),
            DeclareLaunchArgument("hand_yaw_limit_rad", default_value="0.785398"),
            DeclareLaunchArgument("hand_yaw_error_deadband_rad", default_value="0.01"),
            DeclareLaunchArgument("hand_yaw_velocity_scale", default_value="1.0"),
            DeclareLaunchArgument("max_velocity", default_value="0.8"),
            Node(
                package="arm_control",
                executable="arm_controller",
                name="arm_controller",
                output="screen",
                parameters=[
                    {
                        "yaw_sign": yaw_sign,
                        "pitch_sign": pitch_sign,
                        "velocity_scale": velocity_scale,
                        "min_threshold": min_threshold,
                        "hand_yaw_limit_rad": hand_yaw_limit_rad,
                        "hand_yaw_error_deadband_rad": hand_yaw_error_deadband_rad,
                        "hand_yaw_velocity_scale": hand_yaw_velocity_scale,
                        "max_velocity": max_velocity,
                    }
                ],
            )
        ]
    )
