from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ArmCommandPayload:
    mode: str
    follow_enabled: bool
    target_x: float = 0.0
    target_y: float = 0.0
    target_z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0


def _clip(value: float, limit: float = 1.0) -> float:
    return max(-limit, min(limit, value))


def compute_arm_command_from_vision(
    *,
    tracking_enabled: bool,
    hand_detected: bool,
    hand_center_x: float,
    hand_center_y: float,
    shadow_detected: bool,
    shadow_center_x: float,
    shadow_center_y: float,
    needs_relight: bool,
    image_width: float = 640.0,
    image_height: float = 480.0,
    deadband_px: float = 15.0,
) -> ArmCommandPayload:
    if not tracking_enabled or not hand_detected or not shadow_detected or not needs_relight:
        return ArmCommandPayload(mode="idle", follow_enabled=False)

    dx = shadow_center_x - hand_center_x
    dy = shadow_center_y - hand_center_y

    if abs(dx) < deadband_px and abs(dy) < deadband_px:
        return ArmCommandPayload(mode="hold", follow_enabled=False)

    yaw = 0.0 if abs(dx) < deadband_px else _clip(dx / max(image_width / 4.0, 1.0))
    pitch = 0.0 if abs(dy) < deadband_px else _clip(dy / max(image_height / 4.0, 1.0))

    return ArmCommandPayload(
        mode="shadow_follow",
        follow_enabled=True,
        target_x=shadow_center_x,
        target_y=shadow_center_y,
        yaw=yaw,
        pitch=pitch,
    )
