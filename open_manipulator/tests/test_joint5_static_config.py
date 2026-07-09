from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _arm_group_joints() -> list[str]:
    srdf_path = ROOT / "open_manipulator_x_moveit_config" / "config" / "open_manipulator_x.srdf"
    root = ET.fromstring(srdf_path.read_text())
    arm_group = next(group for group in root.findall("group") if group.attrib["name"] == "arm")
    return [joint.attrib["name"] for joint in arm_group.findall("joint")]


def _group_state_joint_names(state_name: str) -> list[str]:
    srdf_path = ROOT / "open_manipulator_x_moveit_config" / "config" / "open_manipulator_x.srdf"
    root = ET.fromstring(srdf_path.read_text())
    state = next(
        state
        for state in root.findall("group_state")
        if state.attrib["name"] == state_name and state.attrib["group"] == "arm"
    )
    return [joint.attrib["name"] for joint in state.findall("joint")]


def test_joint5_is_not_part_of_moveit_arm_group() -> None:
    assert _arm_group_joints() == ["virtual_joint", "joint1", "joint2", "joint3", "joint4", "end_effector_joint"]


def test_joint5_is_not_part_of_named_arm_states() -> None:
    assert _group_state_joint_names("init") == ["joint1", "joint2", "joint3", "joint4"]
    assert _group_state_joint_names("home") == ["joint1", "joint2", "joint3", "joint4"]


def test_joint5_is_not_commanded_by_moveit_controller_config() -> None:
    config_path = ROOT / "open_manipulator_x_moveit_config" / "config" / "moveit_controllers.yaml"
    config = yaml.safe_load(config_path.read_text())

    assert config["arm_controller"]["joints"] == ["joint1", "joint2", "joint3", "joint4"]


def test_joint5_is_not_commanded_by_trajectory_controllers() -> None:
    for config_path in [
        ROOT / "open_manipulator_x_bringup" / "config" / "hardware_controller_manager.yaml",
        ROOT / "open_manipulator_x_bringup" / "config" / "gazebo_controller_manager.yaml",
    ]:
        config = yaml.safe_load(config_path.read_text())
        assert config["arm_controller"]["ros__parameters"]["joints"] == ["joint1", "joint2", "joint3", "joint4"]
