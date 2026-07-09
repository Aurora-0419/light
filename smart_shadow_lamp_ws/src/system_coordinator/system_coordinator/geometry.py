from __future__ import annotations

import math


def _round_point(point: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(round(value, 6) for value in point)


def camera_point_from_pixel_depth(
    *,
    u: float,
    v: float,
    depth_m: float,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
) -> tuple[float, float, float]:
    x = (u - cx) * depth_m / fx
    y = (v - cy) * depth_m / fy
    return _round_point((x, y, depth_m))


def _rotate_xyz(point: tuple[float, float, float], rotation_rpy_deg: tuple[float, float, float]) -> tuple[float, float, float]:
    roll_deg, pitch_deg, yaw_deg = rotation_rpy_deg
    roll = math.radians(roll_deg)
    pitch = math.radians(pitch_deg)
    yaw = math.radians(yaw_deg)

    x, y, z = point

    cy = math.cos(yaw)
    sy = math.sin(yaw)
    x, y = cy * x - sy * y, sy * x + cy * y

    cp = math.cos(pitch)
    sp = math.sin(pitch)
    x, z = cp * x + sp * z, -sp * x + cp * z

    cr = math.cos(roll)
    sr = math.sin(roll)
    y, z = cr * y - sr * z, sr * y + cr * z

    return (x, y, z)


def transform_point_camera_to_base(
    *,
    point_camera: tuple[float, float, float],
    translation_base_camera: tuple[float, float, float],
    rotation_rpy_deg: tuple[float, float, float],
) -> tuple[float, float, float]:
    rotated = _rotate_xyz(point_camera, rotation_rpy_deg)
    transformed = tuple(rotated[i] + translation_base_camera[i] for i in range(3))
    return _round_point(transformed)


def apply_left_offset_in_base(
    *,
    point_base: tuple[float, float, float],
    offset_base: tuple[float, float, float],
) -> tuple[float, float, float]:
    shifted = tuple(point_base[i] + offset_base[i] for i in range(3))
    return _round_point(shifted)


def clamp_min_height_in_base(
    *,
    point_base: tuple[float, float, float],
    min_target_z_m: float,
) -> tuple[float, float, float]:
    x, y, z = point_base
    return _round_point((x, y, max(z, min_target_z_m)))


def pointing_command_from_base_target(
    *,
    point_base: tuple[float, float, float],
    lamp_origin_base: tuple[float, float, float],
    max_yaw_rad: float,
    max_pitch_rad: float,
) -> tuple[float, float]:
    dx = point_base[0] - lamp_origin_base[0]
    dy = point_base[1] - lamp_origin_base[1]
    dz = point_base[2] - lamp_origin_base[2]

    yaw_angle = math.atan2(dy, max(dx, 1e-6))
    horizontal_distance = math.hypot(dx, dy)
    pitch_angle = math.atan2(dz, max(horizontal_distance, 1e-6))

    yaw = max(-1.0, min(1.0, yaw_angle / max(max_yaw_rad, 1e-6)))
    pitch = max(-1.0, min(1.0, pitch_angle / max(max_pitch_rad, 1e-6)))
    return (round(yaw, 6), round(pitch, 6))
