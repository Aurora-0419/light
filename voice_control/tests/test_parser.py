from app.command.parser import parse_command_text


def test_parse_command_text_requires_wake_phrase():
    result = parse_command_text("开启跟踪模式", wake_phrase="你好小灯")

    assert result.wake_detected is False
    assert result.command_name is None


def test_parse_command_text_maps_tracking_command_after_wake_phrase():
    result = parse_command_text("你好小灯 开启跟踪模式", wake_phrase="你好小灯")

    assert result.wake_detected is True
    assert result.command_name == "enable_tracking"
    assert "开启跟踪模式" in result.feedback_text
