from app.feedback.feedback import build_feedback_payload


def test_build_feedback_payload_marks_text_mode_without_tts():
    payload = build_feedback_payload("好的，已开启跟踪模式", tts_available=False)

    assert payload["mode"] == "text"
    assert payload["text"] == "好的，已开启跟踪模式"
