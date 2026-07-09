from __future__ import annotations

from system_coordinator.decision import compute_arm_command_from_vision


def test_compute_arm_command_from_vision_returns_no_motion_without_relight_need():
    command = compute_arm_command_from_vision(
        tracking_enabled=True,
        hand_detected=True,
        hand_center_x=100.0,
        hand_center_y=100.0,
        shadow_detected=True,
        shadow_center_x=120.0,
        shadow_center_y=120.0,
        needs_relight=False,
    )

    assert command.follow_enabled is False
    assert command.yaw == 0.0
    assert command.pitch == 0.0


def test_compute_arm_command_from_vision_outputs_normalized_shadow_direction():
    command = compute_arm_command_from_vision(
        tracking_enabled=True,
        hand_detected=True,
        hand_center_x=200.0,
        hand_center_y=160.0,
        shadow_detected=True,
        shadow_center_x=280.0,
        shadow_center_y=220.0,
        needs_relight=True,
        image_width=640.0,
        image_height=480.0,
    )

    assert command.follow_enabled is True
    assert command.mode == "shadow_follow"
    assert command.yaw > 0.0
    assert command.pitch > 0.0
    assert command.target_x == 280.0
    assert command.target_y == 220.0


def test_compute_arm_command_from_vision_respects_deadband():
    command = compute_arm_command_from_vision(
        tracking_enabled=True,
        hand_detected=True,
        hand_center_x=200.0,
        hand_center_y=160.0,
        shadow_detected=True,
        shadow_center_x=208.0,
        shadow_center_y=168.0,
        needs_relight=True,
        deadband_px=12.0,
    )

    assert command.follow_enabled is False
    assert command.yaw == 0.0
    assert command.pitch == 0.0
