#!/usr/bin/env python3
#
# Copyright 2024 ROBOTIS CO., LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Wonho Yoon, Sungho Woo

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro
import yaml


WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
COMPAT_LIB_ROOT = os.path.join(WORKSPACE_ROOT, "compat_lib")


def _ensure_geometric_shapes_compat() -> str:
    os.makedirs(COMPAT_LIB_ROOT, exist_ok=True)
    target = os.path.join(COMPAT_LIB_ROOT, "libgeometric_shapes.so.2.3.4")
    source = "/opt/ros/humble/lib/libgeometric_shapes.so.2.3.2"
    if not os.path.exists(target) and os.path.exists(source):
        os.symlink(source, target)
    return COMPAT_LIB_ROOT


def generate_launch_description():

    ld = LaunchDescription()
    compat_lib_root = _ensure_geometric_shapes_compat()
    current_ld_library_path = os.environ.get('LD_LIBRARY_PATH', '')
    ld.add_action(
        SetEnvironmentVariable(
            name='LD_LIBRARY_PATH',
            value=f"{compat_lib_root}:{current_ld_library_path}" if current_ld_library_path else compat_lib_root,
        )
    )

    use_sim = LaunchConfiguration('use_sim')
    declare_use_sim = DeclareLaunchArgument(
        'use_sim',
        default_value='true',
        description='Start robot in Gazebo simulation.')
    ld.add_action(declare_use_sim)

    # Robot description
    robot_description_config = xacro.process_file(
        os.path.join(
            get_package_share_directory('open_manipulator_x_description'),
            'urdf',
            'open_manipulator_x_robot.urdf.xacro',
        )
    )
    robot_description = {'robot_description': robot_description_config.toxml()}

    # Robot description Semantic config
    robot_description_semantic_path = os.path.join(
        get_package_share_directory('open_manipulator_x_moveit_config'),
        'config',
        'open_manipulator_x.srdf',
    )
    try:
        with open(robot_description_semantic_path, 'r') as file:
            robot_description_semantic_config = file.read()
    except EnvironmentError:  # parent of IOError, OSError *and* WindowsError where available
        return None

    robot_description_semantic = {
        'robot_description_semantic': robot_description_semantic_config
    }

    # kinematics yaml
    kinematics_yaml_path = os.path.join(
        get_package_share_directory('open_manipulator_x_moveit_config'),
        'config',
        'kinematics.yaml',
    )
    with open(kinematics_yaml_path, 'r') as file:
        kinematics_yaml = yaml.safe_load(file)

    # Get parameters for the Servo node
    servo_yaml_path = os.path.join(
        get_package_share_directory('open_manipulator_x_moveit_config'),
        'config',
        'moveit_servo.yaml',
    )
    try:
        with open(servo_yaml_path, 'r') as file:
            servo_params = {'moveit_servo': yaml.safe_load(file)}
    except EnvironmentError:  # parent of IOError, OSError *and* WindowsError where available
        return None

    # Launch as much as possible in components
    servo_node = Node(
        package='moveit_servo',
        executable='servo_node_main',
        parameters=[
            {'use_gazebo': use_sim},
            servo_params,
            robot_description,
            robot_description_semantic,
            kinematics_yaml,
        ]
    )
    ld.add_action(servo_node)

    return ld
