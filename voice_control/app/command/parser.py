from __future__ import annotations

from app.command.schema import ParsedCommand


COMMAND_PATTERNS = {
    "enable_tracking": ["开启跟踪模式", "打开跟踪模式", "开始跟踪"],
    "disable_tracking": ["关闭跟踪模式", "停止跟踪"],
    "warm_light_mode": ["切换暖光模式", "暖光模式"],
    "cool_light_mode": ["切换冷光模式", "冷光模式"],
}


def parse_command_text(text: str, wake_phrase: str) -> ParsedCommand:
    normalized = " ".join(text.strip().split())
    if wake_phrase not in normalized:
        return ParsedCommand(normalized, False, None, "未检测到唤醒词")

    for command_name, patterns in COMMAND_PATTERNS.items():
        for pattern in patterns:
            if pattern in normalized:
                return ParsedCommand(
                    raw_text=normalized,
                    wake_detected=True,
                    command_name=command_name,
                    feedback_text=f"好的，已执行指令：{pattern}",
                )

    return ParsedCommand(normalized, True, None, "已唤醒，但未识别到有效指令")
