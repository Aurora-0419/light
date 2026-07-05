from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParsedCommand:
    raw_text: str
    wake_detected: bool
    command_name: str | None
    feedback_text: str
