from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    start_rviz = LaunchConfiguration("start_rviz")
    start_gazebo_gui = LaunchConfiguration("start_gazebo_gui")
    start_voice = LaunchConfiguration("start_voice")
    start_vision = LaunchConfiguration("start_vision")
    vision_video = LaunchConfiguration("vision_video")

    openmanip_gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("open_manipulator_x_bringup"), "launch", "gazebo.launch.py"]
            )
        ),
        launch_arguments={
            "start_rviz": start_rviz,
            "start_gazebo_gui": start_gazebo_gui,
        }.items(),
    )

    openmanip_servo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("open_manipulator_x_moveit_config"), "launch", "servo.launch.py"]
            )
        ),
        launch_arguments={"use_sim": "true"}.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("start_rviz", default_value="false"),
            DeclareLaunchArgument("start_gazebo_gui", default_value="false"),
            DeclareLaunchArgument("start_voice", default_value="false"),
            DeclareLaunchArgument("start_vision", default_value="true"),
            DeclareLaunchArgument("vision_video", default_value=""),
            openmanip_gazebo,
            openmanip_servo,
            Node(
                condition=IfCondition(start_vision),
                package="vision_perception",
                executable="vision_state_bridge",
                name="vision_state_bridge",
                output="screen",
                parameters=[{"video_path": vision_video}],
            ),
            Node(
                package="system_coordinator",
                executable="system_coordinator",
                name="system_coordinator",
                output="screen",
                parameters=[{"tracking_enabled_default": True}],
            ),
            Node(
                package="arm_control",
                executable="arm_controller",
                name="shadow_lamp_arm_controller",
                output="screen",
                parameters=[{"full_joint_jog": True}],
            ),
            Node(
                condition=IfCondition(start_voice),
                package="voice_control",
                executable="voice_command_bridge",
                name="voice_command_bridge",
                output="screen",
            ),
        ]
    )
