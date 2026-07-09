from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
ARM_XACRO = ROOT / "open_manipulator_x_description" / "urdf" / "open_manipulator_x.urdf.xacro"
GAZEBO_XACRO = ROOT / "open_manipulator_x_description" / "gazebo" / "open_manipulator_x.gazebo.xacro"
ROS2_CONTROL_XACRO = ROOT / "open_manipulator_x_description" / "ros2_control" / "open_manipulator_x_system.ros2_control.xacro"


def render_robot_xml() -> ET.Element:
    wrapper = f"""<?xml version=\"1.0\"?>
<robot name=\"open_manipulator_x_test\" xmlns:xacro=\"http://www.ros.org/wiki/xacro\">
  <xacro:include filename=\"{ARM_XACRO}\"/>
  <xacro:open_manipulator_x/>
</robot>
"""
    with tempfile.NamedTemporaryFile("w", suffix=".urdf.xacro", delete=False) as wrapper_file:
        wrapper_file.write(wrapper)
        wrapper_path = Path(wrapper_file.name)

    command = f"source /opt/ros/humble/setup.bash && xacro '{wrapper_path}'"
    rendered = subprocess.run(
        ["bash", "-lc", command],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    wrapper_path.unlink(missing_ok=True)
    return ET.fromstring(rendered.stdout)


def test_rendered_robot_contains_five_arm_joints_and_no_hand_or_gripper() -> None:
    robot = render_robot_xml()
    joint_names = {joint.attrib["name"] for joint in robot.findall("joint")}
    link_names = {link.attrib["name"] for link in robot.findall("link")}

    assert {"joint1", "joint2", "joint3", "joint4", "joint5"} <= joint_names
    assert "gripper_left_joint" not in joint_names
    assert "gripper_right_joint" not in joint_names
    assert "palm_lower" not in link_names
    assert "end_effector_link" in link_names


def test_rendered_robot_has_no_gripper_control_artifacts() -> None:
    gazebo_text = GAZEBO_XACRO.read_text()
    ros2_control_text = ROS2_CONTROL_XACRO.read_text()

    assert "gripper_left_joint" not in gazebo_text
    assert "gripper_right_joint" not in gazebo_text
    assert "gripper_left_joint" not in ros2_control_text
    assert "gripper_right_joint" not in ros2_control_text
    assert "joint5" in gazebo_text
    assert "joint5" in ros2_control_text
