from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def test_system_workspace_contains_expected_top_level_entries():
    expected = [
        ROOT / "README.md",
        ROOT / "src" / "common_interfaces",
        ROOT / "src" / "vision_perception",
        ROOT / "src" / "voice_control",
        ROOT / "src" / "system_coordinator",
        ROOT / "src" / "light_control",
        ROOT / "src" / "arm_control",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected if not path.exists()]

    assert not missing, f"missing workspace entries: {missing}"


def test_common_interfaces_defines_core_messages():
    msg_dir = ROOT / "src" / "common_interfaces" / "msg"
    expected = {
        "VisionState.msg",
        "VoiceCommand.msg",
        "SystemMode.msg",
        "LightCommand.msg",
        "ArmCommand.msg",
    }

    existing = {path.name for path in msg_dir.glob("*.msg")}

    assert expected <= existing


def test_shared_interface_package_uses_unique_ros_package_name():
    package_xml = ROOT / "src" / "common_interfaces" / "package.xml"
    tree = ET.parse(package_xml)
    package_name = tree.getroot().findtext("name")

    assert package_name == "shadow_lamp_interfaces"


def test_python_packages_expose_minimal_ros_entrypoints():
    package_files = {
        "vision_perception": ["package.xml", "setup.py", "setup.cfg", "vision_perception/__init__.py"],
        "voice_control": ["package.xml", "setup.py", "setup.cfg", "voice_control/__init__.py"],
        "system_coordinator": ["package.xml", "setup.py", "setup.cfg", "system_coordinator/__init__.py"],
        "light_control": ["package.xml", "setup.py", "setup.cfg", "light_control/__init__.py"],
        "arm_control": ["package.xml", "setup.py", "setup.cfg", "arm_control/__init__.py"],
    }

    for package_name, relative_paths in package_files.items():
        package_root = ROOT / "src" / package_name
        missing = [relative for relative in relative_paths if not (package_root / relative).exists()]
        assert not missing, f"{package_name} missing files: {missing}"


def test_workspace_contains_sim_startup_chain_files():
    expected = [
        ROOT / "scripts" / "run_shadow_lamp_sim.sh",
        ROOT / "src" / "system_coordinator" / "launch" / "shadow_lamp_sim.launch.py",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected if not path.exists()]

    assert not missing, f"missing startup chain files: {missing}"
