from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_servo_launch_sets_up_geometric_shapes_compatibility() -> None:
    launch_text = (ROOT / "open_manipulator_x_moveit_config" / "launch" / "servo.launch.py").read_text()

    assert "libgeometric_shapes.so.2.3.4" in launch_text
    assert "LD_LIBRARY_PATH" in launch_text
    assert "SetEnvironmentVariable" in launch_text
