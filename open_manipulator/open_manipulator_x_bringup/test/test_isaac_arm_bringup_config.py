from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_bringup_config_spawns_only_arm_controller_for_five_joint_arm() -> None:
    gazebo_cfg = (ROOT / "open_manipulator_x_bringup" / "config" / "gazebo_controller_manager.yaml").read_text()
    hardware_cfg = (ROOT / "open_manipulator_x_bringup" / "config" / "hardware_controller_manager.yaml").read_text()
    launch_text = (ROOT / "open_manipulator_x_bringup" / "launch" / "base.launch.py").read_text()

    assert 'joint5' in gazebo_cfg
    assert 'joint5' in hardware_cfg
    assert 'gripper_controller' not in gazebo_cfg
    assert 'gripper_controller' not in hardware_cfg
    assert 'gripper_controller_spawner' not in launch_text
