from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import importlib

from vision_perception.adapter import (
    VisionStatePayload,
    detection_result_to_payload,
    make_default_runtime,
    payload_to_message,
    resolve_workspace_root,
)


class _FakeMessage:
    pass


def test_convert_detection_result_to_payload():
    result = SimpleNamespace(
        hand_center=(120, 90),
        shadow_center=(180, 110),
        needs_relight=True,
        suggested_target_center=(180, 110),
        shadow_area=3200,
    )

    payload = detection_result_to_payload(result, source_frame="camera")

    assert payload.hand_detected is True
    assert payload.shadow_detected is True
    assert payload.needs_relight is True
    assert payload.hand_center_x == 120.0
    assert payload.hand_center_y == 90.0
    assert payload.shadow_center_x == 180.0
    assert payload.suggested_target_x == 180.0
    assert payload.posture_ok is True
    assert payload.posture_issue == ""
    assert payload.posture_score == 0.0


def test_posture_payload_defaults_to_ok():
    payload = VisionStatePayload(
        hand_detected=False,
        hand_center_x=0.0,
        hand_center_y=0.0,
        shadow_detected=False,
        shadow_center_x=0.0,
        shadow_center_y=0.0,
        shadow_area=0.0,
        needs_relight=False,
        suggested_target_x=0.0,
        suggested_target_y=0.0,
        source_frame="camera",
    )

    assert payload.posture_ok is True
    assert payload.posture_issue == ""
    assert payload.posture_score == 0.0


def test_detection_result_to_payload_carries_posture_fields():
    result = SimpleNamespace(
        hand_center=(120, 90),
        shadow_center=(180, 110),
        needs_relight=True,
        suggested_target_center=(180, 110),
        shadow_area=3200,
    )
    posture = SimpleNamespace(posture_ok=False, posture_issue="body_lean_left_right", posture_score=0.72)

    payload = detection_result_to_payload(result, source_frame="camera", posture_result=posture)

    assert payload.posture_ok is False
    assert payload.posture_issue == "body_lean_left_right"
    assert payload.posture_score == 0.72


def test_make_default_runtime_uses_external_pc_demo_modules():
    fake_detector = object()
    fake_capture = object()
    fake_posture_detector = SimpleNamespace(detect=lambda frame: None)

    def loader(external_root: Path):
        assert external_root == Path("/tmp/project")
        return {
            "detector_factory": lambda: fake_detector,
            "capture_factory": lambda source: (fake_capture, source),
            "resolve_source": lambda args: "/dev/video6",
        }

    runtime = make_default_runtime(
        external_root=Path("/tmp/project"),
        loader=loader,
        posture_detector=fake_posture_detector,
    )

    assert runtime.source == "/dev/video6"
    assert runtime.detector is fake_detector
    assert runtime.capture[0] is fake_capture
    assert runtime.posture_detector is fake_posture_detector


def test_payload_to_message_populates_message_factory():
    payload = SimpleNamespace(
        hand_detected=True,
        hand_center_x=120.0,
        hand_center_y=90.0,
        shadow_detected=True,
        shadow_center_x=180.0,
        shadow_center_y=110.0,
        shadow_area=3200.0,
        needs_relight=True,
        suggested_target_x=180.0,
        suggested_target_y=110.0,
        source_frame="camera",
        posture_ok=False,
        posture_issue="shoulder_tilt",
        posture_score=0.8,
    )

    message = payload_to_message(payload, message_factory=_FakeMessage)

    assert message.hand_detected is True
    assert message.shadow_center_x == 180.0
    assert message.source_frame == "camera"
    assert message.posture_ok is False
    assert message.posture_issue == "shoulder_tilt"


def test_bridge_module_imports_without_generated_message_package():
    module = importlib.import_module("vision_perception.vision_state_bridge")

    assert hasattr(module, "VisionStateBridge")


def test_resolve_workspace_root_supports_installed_package_layout():
    adapter_file = Path(
        "/home/yzy/workspace/smart_shadow_lamp_ws/install/vision_perception/lib/python3.10/site-packages/vision_perception/adapter.py"
    )

    assert resolve_workspace_root(adapter_file) == Path("/home/yzy/workspace/smart_shadow_lamp_ws")
