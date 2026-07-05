from __future__ import annotations

import importlib
from pathlib import Path
from subprocess import CalledProcessError

from voice_control.adapter import (
    make_default_runtime,
    payload_to_message,
    resolve_workspace_root,
    run_once_result_to_payload,
)
from voice_control.voice_command_bridge import capture_payload_safely


class _FakeMessage:
    pass


def test_convert_run_once_output_to_payload():
    payload = run_once_result_to_payload(
        {
            "transcript": "你好小灯 开启跟踪模式",
            "wake_detected": "True",
            "command_name": "enable_tracking",
        }
    )

    assert payload.command == "enable_tracking"
    assert payload.confirmed is True
    assert payload.raw_text == "你好小灯 开启跟踪模式"


def test_payload_marks_missing_command_unconfirmed():
    payload = run_once_result_to_payload(
        {
            "transcript": "你好小灯",
            "wake_detected": "True",
            "command_name": "",
        }
    )

    assert payload.command == ""
    assert payload.confirmed is False


def test_make_default_runtime_uses_external_voice_module():
    fake_run_once = object()

    def loader(external_root: Path):
        assert external_root == Path("/tmp/project")
        return {"run_once": fake_run_once}

    runtime = make_default_runtime(external_root=Path("/tmp/project"), loader=loader)

    assert runtime.run_once_callable is fake_run_once


def test_payload_to_message_populates_message_factory():
    payload = run_once_result_to_payload(
        {
            "transcript": "你好小灯 开启跟踪模式",
            "wake_detected": "True",
            "command_name": "enable_tracking",
        }
    )

    message = payload_to_message(payload, message_factory=_FakeMessage)

    assert message.command == "enable_tracking"
    assert message.confirmed is True
    assert message.raw_text == "你好小灯 开启跟踪模式"


def test_bridge_module_imports_without_generated_message_package():
    module = importlib.import_module("voice_control.voice_command_bridge")

    assert hasattr(module, "VoiceCommandBridge")


def test_resolve_workspace_root_supports_installed_package_layout():
    adapter_file = Path(
        "/home/yzy/workspace/smart_shadow_lamp_ws/install/voice_control/lib/python3.10/site-packages/voice_control/adapter.py"
    )

    assert resolve_workspace_root(adapter_file) == Path("/home/yzy/workspace/smart_shadow_lamp_ws")


def test_capture_payload_safely_returns_none_on_runtime_error():
    class _FakeRuntime:
        def capture_once(self):
            raise CalledProcessError(1, ["arecord"])

    warnings = []

    class _FakeLogger:
        def warning(self, message):
            warnings.append(message)

    payload = capture_payload_safely(_FakeRuntime(), logger=_FakeLogger())

    assert payload is None
    assert warnings
