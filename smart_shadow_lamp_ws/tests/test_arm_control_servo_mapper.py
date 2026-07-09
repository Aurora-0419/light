from __future__ import annotations

from arm_control.servo_mapper import ArmCommandPayload, arm_command_to_joint_jog_spec


def test_arm_command_to_joint_jog_spec_returns_none_when_follow_disabled():
    command = ArmCommandPayload(mode="idle", follow_enabled=False, yaw=0.4, pitch=0.2)

    assert arm_command_to_joint_jog_spec(command) is None


def test_arm_command_to_joint_jog_spec_maps_yaw_and_pitch_to_joint_velocities():
    command = ArmCommandPayload(mode="shadow_follow", follow_enabled=True, yaw=0.5, pitch=-0.25)

    jog = arm_command_to_joint_jog_spec(command, yaw_sign=1.0, pitch_sign=1.0, velocity_scale=0.6)

    assert jog is not None
    assert jog.joint_names == ["joint1", "joint2"]
    assert jog.velocities == [0.3, -0.15]


def test_arm_command_to_joint_jog_spec_applies_threshold():
    command = ArmCommandPayload(mode="shadow_follow", follow_enabled=True, yaw=0.01, pitch=0.02)

    assert arm_command_to_joint_jog_spec(command, min_threshold=0.05) is None
