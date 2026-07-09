from __future__ import annotations

from difflib import SequenceMatcher

from app.command.schema import ParsedCommand


COMMAND_PATTERNS = {
    "enable_tracking": ["开启跟踪模式", "打开跟踪模式", "开始跟踪"],
    "disable_tracking": ["关闭跟踪模式", "停止跟踪"],
    "confirm": ["确认"],
    "light_on": ["开灯"],
    "light_off": ["关灯"],
    "brightness_up": ["增加亮度"],
    "brightness_down": ["减小亮度"],
    "max_brightness": ["最大亮度"],
    "min_brightness": ["最小亮度"],
    "medium_brightness": ["中等亮度"],
    "warm_light_mode": ["切换暖光模式", "暖光模式", "反光模式"],
    "cool_light_mode": ["切换冷光模式", "冷光模式"],
}

WAKE_PREFIXES = {"你好", "您好"}
WAKE_SUFFIXES = {"小灯", "小东", "小登", "小邓", "小的", "扫荡"}

FUZZY_COMMAND_THRESHOLD = 0.75
FUZZY_COMMAND_MARGIN = 0.08


def _compact_for_match(text: str) -> str:
    return "".join(text.strip().split())


def _wake_variants(wake_phrase: str) -> set[str]:
    variants = {_compact_for_match(wake_phrase)}
    variants.update({_compact_for_match(prefix + suffix) for prefix in WAKE_PREFIXES for suffix in WAKE_SUFFIXES})
    return variants


def _strip_wake_prefix(compact_text: str, wake_phrase: str) -> str:
    for variant in sorted(_wake_variants(wake_phrase), key=len, reverse=True):
        if compact_text.startswith(variant):
            return compact_text[len(variant) :]
    return compact_text


def detect_command_name(text: str, wake_phrase: str = "你好小灯") -> str | None:
    compact = _compact_for_match(text)
    compact_without_wake = _strip_wake_prefix(compact, wake_phrase)
    for command_name, patterns in COMMAND_PATTERNS.items():
        for pattern in patterns:
            compact_pattern = _compact_for_match(pattern)
            if compact_pattern in compact or compact_pattern in compact_without_wake:
                return command_name

    scored_matches: list[tuple[float, str]] = []
    for command_name, patterns in COMMAND_PATTERNS.items():
        best_score = max(
            SequenceMatcher(None, compact_without_wake or compact, _compact_for_match(pattern)).ratio()
            for pattern in patterns
        )
        scored_matches.append((best_score, command_name))

    scored_matches.sort(reverse=True)
    best_score, best_command = scored_matches[0]
    second_score = scored_matches[1][0] if len(scored_matches) > 1 else 0.0
    if best_score >= FUZZY_COMMAND_THRESHOLD and (best_score - second_score) >= FUZZY_COMMAND_MARGIN:
        return best_command
    return None


def parse_command_text(text: str, wake_phrase: str) -> ParsedCommand:
    normalized = " ".join(text.strip().split())
    compact = _compact_for_match(normalized)
    wake_variants = _wake_variants(wake_phrase)
    if not any(variant in compact for variant in wake_variants):
        return ParsedCommand(normalized, False, None, "未检测到唤醒词")

    command_name = detect_command_name(normalized, wake_phrase=wake_phrase)
    if command_name is not None:
        first_pattern = COMMAND_PATTERNS[command_name][0]
        return ParsedCommand(
            raw_text=normalized,
            wake_detected=True,
            command_name=command_name,
            feedback_text=f"好的，已执行指令：{first_pattern}",
        )

    return ParsedCommand(normalized, True, None, "已唤醒，但未识别到有效指令")
