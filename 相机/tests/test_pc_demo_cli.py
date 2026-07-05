from types import SimpleNamespace

import numpy as np

from scripts.run_pc_hand_shadow_demo import (
    _draw_overlay,
    build_arg_parser,
    find_realsense_color_device,
    resolve_source,
)


def test_pc_demo_cli_supports_webcam_and_video_flags():
    parser = build_arg_parser()
    args = parser.parse_args(["--webcam", "--save-frame", "frame.png"])

    assert args.webcam is True
    assert args.save_frame == "frame.png"


def test_pc_demo_cli_supports_explicit_camera_source():
    parser = build_arg_parser()
    args = parser.parse_args(["--camera", "/dev/video4"])

    assert args.camera == "/dev/video4"


def test_explicit_camera_source_overrides_webcam_default():
    parser = build_arg_parser()
    args = parser.parse_args(["--webcam", "--camera", "/dev/video4"])

    assert resolve_source(args) == "/dev/video4"


def test_default_source_auto_selects_realsense_color_device():
    parser = build_arg_parser()
    args = parser.parse_args([])

    assert resolve_source(args, camera_detector=lambda: "/dev/video6") == "/dev/video6"


def test_webcam_source_skips_auto_selection():
    parser = build_arg_parser()
    args = parser.parse_args(["--webcam"])

    assert resolve_source(args, camera_detector=lambda: "/dev/video6") == 0


def test_find_realsense_color_device_skips_depth_metadata_and_bad_color_nodes():
    device_infos = {
        "/dev/video2": "Card type        : Intel(R) RealSense(TM) Depth Ca\nPixel Format      : 'Z16 '",
        "/dev/video3": "Card type        : Intel(R) RealSense(TM) Depth Ca\nFormat Metadata Capture:",
        "/dev/video4": "Card type        : Intel(R) RealSense(TM) Depth Ca\nPixel Format      : 'UYVY'",
        "/dev/video6": "Card type        : Intel(R) RealSense(TM) Depth Ca\nPixel Format      : 'YUYV'",
    }

    selected = find_realsense_color_device(
        devices=list(device_infos),
        device_info_reader=lambda device: device_infos[device],
    )

    assert selected == "/dev/video6"


def test_draw_overlay_tints_shadow_mask_region():
    frame = np.zeros((80, 80, 3), dtype=np.uint8)
    shadow_mask = np.zeros((80, 80), dtype=np.uint8)
    shadow_mask[40:60, 40:60] = 255
    result = SimpleNamespace(
        hand_center=None,
        shadow_center=None,
        needs_relight=False,
        suggested_target_center=None,
        shadow_mask=shadow_mask,
    )

    overlay = _draw_overlay(frame, result)

    assert overlay[50, 50, 0] > 0
    assert overlay[5, 5, 0] == 0
