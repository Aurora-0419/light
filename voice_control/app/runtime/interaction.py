from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Callable

from app.command.parser import detect_command_name, parse_command_text


@dataclass
class VoiceInteractionResult:
    transcript: str
    wake_detected: bool
    command_name: str | None
    feedback_text: str | None
    debug_reason: str


class VoiceInteractionSession:
    def __init__(
        self,
        wake_phrase: str,
        command_window_seconds: float,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.wake_phrase = wake_phrase
        self.command_window_seconds = command_window_seconds
        self.command_window_delay_seconds = 0.0
        self.clock = clock or monotonic
        self.awaiting_command_until = 0.0
        self.pending_command: str | None = None

    def _in_command_window(self) -> bool:
        return self.clock() <= self.awaiting_command_until

    def _open_command_window(self) -> None:
        self.awaiting_command_until = self.clock() + self.command_window_seconds

    def _close_command_window(self) -> None:
        self.awaiting_command_until = 0.0

    def _clear_pending_confirmation(self) -> None:
        self.pending_command = None

    def retry_command_prompt(self) -> VoiceInteractionResult | None:
        if not self._in_command_window():
            return None
        self._open_command_window()
        return VoiceInteractionResult(
            transcript="",
            wake_detected=True,
            command_name=None,
            feedback_text=None,
            debug_reason="retry_command",
        )

    def debug_state(self) -> dict[str, float | str | None]:
        remaining = max(0.0, self.awaiting_command_until - self.clock()) if self.awaiting_command_until > 0.0 else 0.0
        window_state = "awaiting_command" if self._in_command_window() else "idle"
        return {
            "window_state": window_state,
            "starts_in_seconds": 0.0,
            "remaining_seconds": remaining,
            "command_window_delay_seconds": self.command_window_delay_seconds,
            "pending_command": self.pending_command,
        }

    def process_text(self, text: str) -> VoiceInteractionResult:
        normalized = " ".join(text.strip().split())
        if not normalized:
            return VoiceInteractionResult(transcript="", wake_detected=False, command_name=None, feedback_text=None, debug_reason="empty")

        if self.pending_command is not None:
            command_name = detect_command_name(normalized)
            if command_name == "confirm":
                pending = self.pending_command
                self._clear_pending_confirmation()
                self._close_command_window()
                return VoiceInteractionResult(
                    transcript=normalized,
                    wake_detected=True,
                    command_name=pending,
                    feedback_text=None,
                    debug_reason="confirm_execute",
                )
            self._clear_pending_confirmation()
            self._close_command_window()
            return VoiceInteractionResult(transcript=normalized, wake_detected=False, command_name=None, feedback_text=None, debug_reason="confirm_rejected")

        parsed = parse_command_text(normalized, self.wake_phrase)
        if parsed.command_name is not None:
            if parsed.command_name == "light_off":
                self.pending_command = "light_off"
                self._open_command_window()
                return VoiceInteractionResult(
                    transcript=normalized,
                    wake_detected=parsed.wake_detected,
                    command_name=None,
                    feedback_text=None,
                    debug_reason="awaiting_confirmation",
                )
            self._close_command_window()
            return VoiceInteractionResult(
                transcript=normalized,
                wake_detected=parsed.wake_detected,
                command_name=parsed.command_name,
                feedback_text=None,
                debug_reason="publish_command",
            )

        if parsed.wake_detected:
            self._open_command_window()
            return VoiceInteractionResult(
                transcript=normalized,
                wake_detected=True,
                command_name=None,
                feedback_text=None,
                debug_reason="wake_only",
            )

        if self._in_command_window():
            command_name = detect_command_name(normalized)
            if command_name is not None:
                if command_name == "light_off":
                    self.pending_command = "light_off"
                    self._open_command_window()
                    return VoiceInteractionResult(
                        transcript=normalized,
                        wake_detected=True,
                        command_name=None,
                        feedback_text=None,
                        debug_reason="awaiting_confirmation",
                    )
                self._close_command_window()
                return VoiceInteractionResult(
                    transcript=normalized,
                    wake_detected=True,
                    command_name=command_name,
                    feedback_text=None,
                    debug_reason="publish_command",
                )
            self._open_command_window()
            return VoiceInteractionResult(
                transcript=normalized,
                wake_detected=True,
                command_name=None,
                feedback_text=None,
                debug_reason="retry_command",
            )

        if self.awaiting_command_until > 0.0 and self.clock() > self.awaiting_command_until:
            self._open_command_window()
            return VoiceInteractionResult(
                transcript=normalized,
                wake_detected=True,
                command_name=None,
                feedback_text=None,
                debug_reason="retry_prompt",
            )

        return VoiceInteractionResult(
            transcript=normalized,
            wake_detected=False,
            command_name=None,
            feedback_text=None,
            debug_reason="no_match",
        )
