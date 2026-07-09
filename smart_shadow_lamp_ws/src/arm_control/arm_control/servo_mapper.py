from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ArmCommandPayload:
    mode: str
    follow_enabled: bool
    yaw: float = 0.0
    pitch: float = 0.0


@dataclass
class JointJogSpec:
    joint_names: list[str]
    velocities: list[float]


def arm_command_to_joint_jog_spec(
    command: ArmCommandPayload,
    *,
    yaw_sign: float = 1.0,
    pitch_sign: float = 1.0,
    velocity_scale: float = 0.6,
    min_threshold: float = 0.05,
    include_full_chain: bool = False,
    default_full_chain: bool = False,
) -> JointJogSpec | None:
    if not command.follow_enabled or command.mode not in {
        "shadow_follow",
        "hand_follow",
        "hand_point_3d",
        "hand_point_3d_yaw_only",
        "tracking",
    }:
        return None

    yaw_velocity = yaw_sign * velocity_scale * command.yaw
    pitch_velocity = pitch_sign * velocity_scale * command.pitch

    if abs(yaw_velocity) < min_threshold and abs(pitch_velocity) < min_threshold:
        return None

    if include_full_chain or default_full_chain:
        return JointJogSpec(
            joint_names=["joint1", "joint2", "joint3", "joint4"],
            velocities=[round(yaw_velocity, 6), round(pitch_velocity, 6), 0.0, 0.0],
        )

    return JointJogSpec(
        joint_names=["joint1", "joint2"],
        velocities=[round(yaw_velocity, 6), round(pitch_velocity, 6)],
    )
