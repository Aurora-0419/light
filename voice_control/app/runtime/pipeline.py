from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Thread
from typing import Callable

from app.audio.capture import AudioCaptureConfig, AudioStreamReader, compute_pcm16_stats
from app.feedback.feedback import speak_or_print
from app.speech.vosk_bridge import VoskStreamingRecognizer


COMMAND_FEEDBACK_BY_NAME = {
    "enable_tracking": "已开启跟踪模式",
    "disable_tracking": "已关闭跟踪模式",
    "warm_light_mode": "已切换暖光模式",
    "cool_light_mode": "已切换冷光模式",
    "brightness_up": "好的 已执行",
    "brightness_down": "好的 已执行",
    "max_brightness": "好的 已执行",
    "min_brightness": "好的 已执行",
    "medium_brightness": "好的 已执行",
    "light_on": "好的 已执行",
    "light_off": "好的 已执行",
}


PLAYBACK_ECHO_TRANSCRIPTS = {
    "我在": {"我在", "我在请说"},
    "请再说一遍": {"请再说一遍"},
}


def _normalize_transcript(text: str) -> str:
    return "".join(ch for ch in text if not ch.isspace() and ch not in "，,。！？!?")


@dataclass
class ChunkRecognitionEvent:
    kind: str
    text: str
    audio_peak: int = 0
    audio_avg_abs: float = 0.0


class AudioChunkPipeline:
    def __init__(
        self,
        capture_config: AudioCaptureConfig,
        recognizer: VoskStreamingRecognizer,
        *,
        stream_reader: AudioStreamReader | None = None,
        no_speech_every_chunks: int = 25,
    ) -> None:
        self.capture_config = capture_config
        self.recognizer = recognizer
        self.stream_reader = stream_reader or AudioStreamReader(capture_config)
        self.no_speech_every_chunks = max(1, no_speech_every_chunks)
        self._chunks_since_no_speech_event = 0
        self._events: Queue[ChunkRecognitionEvent] = Queue()
        self._stop_event = Event()
        self._threads: list[Thread] = []

    def start(self) -> None:
        if self._threads:
            return
        self._stop_event.clear()
        worker = Thread(target=self._stream_loop, daemon=True)
        self._threads = [worker]
        for thread in self._threads:
            thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        for thread in self._threads:
            thread.join(timeout=1.0)
        self._threads = []
        self.stream_reader.stop()
        self.recognizer.reset()

    def poll_event(self, timeout_seconds: float | None = None) -> ChunkRecognitionEvent | None:
        try:
            return self._events.get(timeout=timeout_seconds)
        except Empty:
            return None

    def _stream_loop(self) -> None:
        self.stream_reader.start()
        while not self._stop_event.is_set():
            data = self.stream_reader.read_chunk()
            if not data:
                continue
            stats = compute_pcm16_stats(data)
            event = self.recognizer.feed_audio(data)
            if event and event.get("text"):
                self._chunks_since_no_speech_event = 0
                self._events.put(
                    ChunkRecognitionEvent(
                        kind=str(event.get("kind", "final")),
                        text=str(event["text"]),
                        audio_peak=int(stats["peak"]),
                        audio_avg_abs=float(stats["avg_abs"]),
                    )
                )
                continue
            self._chunks_since_no_speech_event += 1
            if self._chunks_since_no_speech_event >= self.no_speech_every_chunks:
                self._chunks_since_no_speech_event = 0
                self._events.put(
                    ChunkRecognitionEvent(
                        kind="no_speech",
                        text="",
                        audio_peak=int(stats["peak"]),
                        audio_avg_abs=float(stats["avg_abs"]),
                    )
                )
class StreamingVoiceRuntime:
    def __init__(
        self,
        pipeline: AudioChunkPipeline,
        interaction_session,
        *,
        speaker: Callable[[str], dict[str, str]] = speak_or_print,
        playback_command_window_seconds: float = 5.0,
    ) -> None:
        self.pipeline = pipeline
        self.interaction_session = interaction_session
        self.speaker = speaker
        self.playback_command_window_seconds = max(0.0, playback_command_window_seconds)
        self.started = False
        self._last_transcript = ""
        self._ignored_playback_transcripts: set[str] = set()

    def _arm_playback_gate(self, feedback_text: str) -> None:
        echoes = PLAYBACK_ECHO_TRANSCRIPTS.get(feedback_text, set())
        self._ignored_playback_transcripts = {_normalize_transcript(text) for text in echoes}

    def _finish_playback_gate(self) -> None:
        reopen = getattr(self.interaction_session, "reopen_command_window", None)
        if callable(reopen):
            reopen(command_window_seconds=self.playback_command_window_seconds)

    def _speak_feedback(self, feedback_text: str, debug_reason: str) -> None:
        playback_gated = debug_reason in {"wake_only", "retry_prompt", "retry_command"}
        if playback_gated:
            self._arm_playback_gate(feedback_text)
        payload = self.speaker(feedback_text)
        if playback_gated and payload.get("mode") == "wav":
            self._finish_playback_gate()
            return
        if playback_gated:
            self._ignored_playback_transcripts.clear()

    def start(self) -> None:
        if not self.started:
            self.pipeline.start()
            self.started = True

    def stop(self) -> None:
        if self.started:
            self.pipeline.stop()
            self.started = False
        self._last_transcript = ""

    def poll_once(self, timeout_seconds: float | None = 0.0) -> dict[str, str] | None:
        self.start()
        event = self.pipeline.poll_event(timeout_seconds=timeout_seconds)
        if event is None:
            return None
        transcript = str(getattr(event, "text", "") or "")
        if not transcript:
            self._last_transcript = ""
            retry_prompt = getattr(self.interaction_session, "retry_command_prompt", lambda: None)()
            if retry_prompt and retry_prompt.feedback_text:
                self._speak_feedback(retry_prompt.feedback_text, retry_prompt.debug_reason)
            return None
        if transcript == self._last_transcript:
            return None
        normalized_transcript = _normalize_transcript(transcript)
        if normalized_transcript in self._ignored_playback_transcripts:
            self._last_transcript = transcript
            return None
        self._ignored_playback_transcripts.clear()
        self._last_transcript = transcript
        print(transcript)
        result = self.interaction_session.process_text(transcript)
        state_getter = getattr(self.interaction_session, "debug_state", None)
        state = state_getter() if callable(state_getter) else {}
        feedback_text = result.feedback_text
        if result.command_name:
            feedback_text = COMMAND_FEEDBACK_BY_NAME.get(result.command_name)
        if feedback_text:
            self._speak_feedback(feedback_text, result.debug_reason)
        return {
            "transcript": result.transcript,
            "wake_detected": str(result.wake_detected),
            "command_name": result.command_name or "",
            "feedback_text": feedback_text or "",
            "debug_reason": result.debug_reason,
            "audio_peak": str(getattr(event, "audio_peak", 0)),
            "audio_avg_abs": str(round(float(getattr(event, "audio_avg_abs", 0.0)), 2)),
            "window_state": str(state.get("window_state", "unknown")),
            "pending_command": str(state.get("pending_command") or "-"),
        }
