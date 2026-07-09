from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_workspace_contains_required_dynamixel_source_packages():
    expected = [
        ROOT / "dynamixel_hardware_interface",
        ROOT / "dynamixel_interfaces",
        ROOT / "dynamixel_sdk",
        ROOT / "dynamixel_sdk_custom_interfaces",
    ]
    missing = [str(path.relative_to(ROOT)) for path in expected if not path.exists()]
    assert not missing, f"missing dynamixel packages: {missing}"
