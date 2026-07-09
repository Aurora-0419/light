from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_moveit_config_uses_five_joint_arm_and_no_gripper_group() -> None:
    srdf = (ROOT / "open_manipulator_x_moveit_config" / "config" / "open_manipulator_x.srdf").read_text()
    moveit_controllers = (ROOT / "open_manipulator_x_moveit_config" / "config" / "moveit_controllers.yaml").read_text()
    initial_positions = (ROOT / "open_manipulator_x_moveit_config" / "config" / "initial_positions.yaml").read_text()

    assert '<joint name="joint5"' in srdf
    assert '<group name="gripper">' not in srdf
    assert 'gripper_controller' not in moveit_controllers
    assert 'gripper_left_joint' not in initial_positions
    assert 'joint5:' in initial_positions
