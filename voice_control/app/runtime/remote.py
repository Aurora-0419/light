from __future__ import annotations

import json
from typing import Any

from app.audio.capture import compute_pcm16_stats


class RemoteRecognitionSession:
    def __init__(
        self,
        recognizer,
        interaction_session,
        *,
        no_speech_every_chunks: int = 25,
    ) -> None:
        self.recognizer = recognizer
        self.interaction_session = interaction_session
        self.no_speech_every_chunks = max(1, no_speech_every_chunks)
        self._chunks_since_no_speech_event = 0
        self._last_transcript = ""

    def _result_to_payload(self, result, *, audio_peak: int, audio_avg_abs: float) -> dict[str, str]:
        return {
            "transcript": result.transcript,
            "wake_detected": str(result.wake_detected),
            "command_name": result.command_name or "",
            "feedback_text": result.feedback_text or "",
            "debug_reason": result.debug_reason,
            "audio_peak": str(audio_peak),
            "audio_avg_abs": str(round(float(audio_avg_abs), 2)),
        }

    def process_audio_chunk(self, data: bytes) -> dict[str, str] | None:
        stats = compute_pcm16_stats(data)
        event = self.recognizer.feed_audio(data)
        if event and event.get("text"):
            if event.get("kind") != "final":
                return None
            state_getter = getattr(self.interaction_session, "debug_state", None)
            state = state_getter() if callable(state_getter) else {}
            if state.get("window_state") == "waiting_delay":
                return None
            self._chunks_since_no_speech_event = 0
            transcript = str(event["text"])
            if transcript == self._last_transcript:
                return None
            self._last_transcript = transcript
            result = self.interaction_session.process_text(transcript)
            return self._result_to_payload(
                result,
                audio_peak=int(stats["peak"]),
                audio_avg_abs=float(stats["avg_abs"]),
            )

        self._chunks_since_no_speech_event += 1
        if self._chunks_since_no_speech_event < self.no_speech_every_chunks:
            return None
        self._chunks_since_no_speech_event = 0
        self._last_transcript = ""
        retry_prompt = getattr(self.interaction_session, "retry_command_prompt", lambda: None)()
        if retry_prompt is None:
            return None
        return self._result_to_payload(
            retry_prompt,
            audio_peak=int(stats["peak"]),
            audio_avg_abs=float(stats["avg_abs"]),
        )


def format_remote_session_config(session: RemoteRecognitionSession) -> str:
    interaction = session.interaction_session
    return (
        "remote voice logic: "
        f"wake_phrase={interaction.wake_phrase!r} "
        f"command_window={interaction.command_window_seconds:.2f}s "
        f"wake_delay={interaction.command_window_delay_seconds:.2f}s "
        f"no_speech_every_chunks={session.no_speech_every_chunks}"
    )


def format_remote_result_log(payload: dict[str, str], interaction_session) -> str:
    state_getter = getattr(interaction_session, "debug_state", None)
    state = state_getter() if callable(state_getter) else {}
    transcript = payload.get("transcript") or ""
    command_name = payload.get("command_name") or "-"
    feedback_text = payload.get("feedback_text") or "-"
    pending_command = str(state.get("pending_command") or "-")
    return (
        "remote voice result: "
        f"transcript={transcript!r} "
        f"reason={payload.get('debug_reason', '')} "
        f"wake={payload.get('wake_detected', '')} "
        f"command={command_name} "
        f"feedback={feedback_text!r} "
        f"window={state.get('window_state', 'unknown')} "
        f"starts_in={float(state.get('starts_in_seconds', 0.0)):.2f}s "
        f"remaining={float(state.get('remaining_seconds', 0.0)):.2f}s "
        f"delay={float(state.get('command_window_delay_seconds', 0.0)):.2f}s "
        f"pending={pending_command} "
        f"audio_peak={payload.get('audio_peak', '')} "
        f"audio_avg_abs={payload.get('audio_avg_abs', '')}"
    )


def build_ready_message() -> str:
    return json.dumps({"type": "ready"}, ensure_ascii=False)


def build_result_message(payload: dict[str, str]) -> str:
    return json.dumps({"type": "recognition_result", **payload}, ensure_ascii=False)


def parse_client_hello(message: str) -> dict[str, Any]:
    payload = json.loads(message)
    if payload.get("type") != "hello":
        raise ValueError("expected hello message")
    return payload