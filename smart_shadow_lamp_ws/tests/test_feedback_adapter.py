from __future__ import annotations

from pathlib import Path

from system_coordinator.feedback_adapter import make_feedback_runtime


def test_feedback_adapter_uses_external_voice_feedback_loader():
    called = []

    class _FakeFeedbackModule:
        @staticmethod
        def speak_or_print(text: str):
            called.append(text)
            return {"mode": "text", "text": text}

    runtime = make_feedback_runtime(
        external_root=Path("/tmp/project"),
        loader=lambda path: {"feedback_module": _FakeFeedbackModule},
    )

    payload = runtime.speak_or_print("请坐正一点")

    assert called == ["请坐正一点"]
    assert payload["text"] == "请坐正一点"


def test_feedback_adapter_falls_back_to_print_style_payload():
    runtime = make_feedback_runtime(
        external_root=Path("/tmp/project"),
        loader=lambda path: {},
    )

    payload = runtime.speak_or_print("请不要离桌面太近")

    assert payload == {"mode": "text", "text": "请不要离桌面太近"}
