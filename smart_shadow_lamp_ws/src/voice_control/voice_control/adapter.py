from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
from queue import Empty, Queue
from time import sleep
import sys
from threading import Event, Thread
from types import ModuleType
from typing import Any, Callable

import yaml
from websockets.sync.client import connect


def resolve_workspace_root(adapter_file: Path) -> Path:
    adapter_file = adapter_file.resolve()
    for parent in adapter_file.parents:
        if (parent / "src").is_dir():
            return parent
        if parent.name == "install":
            return parent.parent
    raise RuntimeError(f"failed to infer workspace root from {adapter_file}")


WORKSPACE_ROOT = resolve_workspace_root(Path(__file__))
DEFAULT_EXTERNAL_VOICE_ROOT = WORKSPACE_ROOT.parent / "voice_control"


@dataclass
class VoiceCommandPayload:
    wake_word: str
    command: str
    confidence: float
    raw_text: str
    confirmed: bool
    debug_reason: str = "unknown"
    audio_peak: str = ""
    audio_avg_abs: str = ""
    window_state: str = "unknown"
    pending_command: str = "-"


@dataclass
class VoiceRuntime:
    run_once_callable: Callable[[], dict[str, str]] | None = None
    stream_runtime: Any | None = None

    def capture_once(self, wake_word: str = "你好小灯") -> VoiceCommandPayload:
        if self.stream_runtime is not None:
            result = self.stream_runtime.poll_once(timeout_seconds=0.0)
            if result is None:
                return VoiceCommandPayload(wake_word="", command="", confidence=0.0, raw_text="", confirmed=False)
        else:
            result = self.run_once_callable()
        return run_once_result_to_payload(result, wake_word=wake_word)

    def close(self) -> None:
        if self.stream_runtime is not None:
            stop = getattr(self.stream_runtime, "stop", None)
            if callable(stop):
                stop()


@dataclass
class FallbackVoiceRuntime:
    primary: Any
    fallback: Any
    using_fallback: bool = False
    log_callable: Callable[[str], None] = print

    def capture_once(self, wake_word: str = "你好小灯") -> VoiceCommandPayload:
        if not self.using_fallback:
            try:
                return self.primary.capture_once(wake_word=wake_word)
            except Exception as exc:
                self.using_fallback = True
                self.log_callable(f"remote voice unavailable, falling back to local: {exc}")
        return self.fallback.capture_once(wake_word=wake_word)

    def close(self) -> None:
        for runtime in (self.primary, self.fallback):
            close = getattr(runtime, "close", None)
            if callable(close):
                close()


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def run_once_result_to_payload(
    result: dict[str, str],
    wake_word: str = "你好小灯",
) -> VoiceCommandPayload:
    command = str(result.get("command_name", "") or "")
    wake_detected = _is_truthy(result.get("wake_detected", False))
    return VoiceCommandPayload(
        wake_word=wake_word if wake_detected else "",
        command=command,
        confidence=1.0 if command else 0.0,
        raw_text=str(result.get("transcript", "") or ""),
        confirmed=bool(command),
        debug_reason=str(result.get("debug_reason", "unknown") or "unknown"),
        audio_peak=str(result.get("audio_peak", "") or ""),
        audio_avg_abs=str(result.get("audio_avg_abs", "") or ""),
        window_state=str(result.get("window_state", "unknown") or "unknown"),
        pending_command=str(result.get("pending_command", "-") or "-"),
    )


def payload_to_message(payload: VoiceCommandPayload, message_factory: Callable[[], Any]) -> Any:
    msg = message_factory()
    msg.wake_word = payload.wake_word
    msg.command = payload.command
    msg.confidence = payload.confidence
    msg.raw_text = payload.raw_text
    msg.confirmed = payload.confirmed
    return msg


def _load_module_from_path(module_name: str, file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_external_voice_module(external_root: Path) -> dict[str, Any]:
    if str(external_root) not in sys.path:
        sys.path.insert(0, str(external_root))
    module = _load_module_from_path(
        "external_voice_control_demo",
        external_root / "scripts" / "run_voice_control.py",
    )
    return {
        "run_once": getattr(module, "run_once", None),
        "make_stream_runtime": getattr(module, "make_stream_runtime", None),
    }


def _load_external_config(external_root: Path) -> dict[str, Any]:
    config_path = external_root / "configs" / "default.yaml"
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _load_external_audio_support(external_root: Path) -> dict[str, Any]:
    if str(external_root) not in sys.path:
        sys.path.insert(0, str(external_root))
    capture_module = _load_module_from_path(
        "external_voice_capture",
        external_root / "app" / "audio" / "capture.py",
    )
    feedback_module = _load_module_from_path(
        "external_voice_feedback",
        external_root / "app" / "feedback" / "feedback.py",
    )
    return {
        "AudioCaptureConfig": getattr(capture_module, "AudioCaptureConfig"),
        "AudioStreamReader": getattr(capture_module, "AudioStreamReader"),
        "speak_or_print": getattr(feedback_module, "speak_or_print"),
    }


class RemoteVoiceRuntime:
    def __init__(
        self,
        *,
        server_url: str,
        audio_capture_config,
        audio_stream_reader_factory: Callable[[Any], Any],
        speaker: Callable[[str], dict[str, str]],
        connect_callable: Callable[..., Any] = connect,
        open_timeout_seconds: float = 2.0,
        wait_after_playback_seconds: float = 3.0,
        sleep_callable: Callable[[float], None] = sleep,
        log_callable: Callable[[str], None] = print,
    ) -> None:
        self.server_url = server_url
        self.audio_capture_config = audio_capture_config
        self.audio_stream_reader_factory = audio_stream_reader_factory
        self.speaker = speaker
        self.connect_callable = connect_callable
        self.open_timeout_seconds = max(0.1, float(open_timeout_seconds))
        self.wait_after_playback_seconds = max(0.0, float(wait_after_playback_seconds))
        self.sleep_callable = sleep_callable
        self.log_callable = log_callable
        self._events: Queue[dict[str, str]] = Queue()
        self._stop_event = Event()
        self._worker: Thread | None = None
        self._fatal_error: Exception | None = None
        self._ready = Event()

    def _play_feedback(self, reader, text: str) -> None:
        reader.stop()
        try:
            self.speaker(text)
            if self.wait_after_playback_seconds > 0.0:
                self.sleep_callable(self.wait_after_playback_seconds)
        finally:
            reader.start()

    def _drain_server_messages(self, websocket, reader) -> None:
        while not self._stop_event.is_set():
            try:
                message = websocket.recv(timeout=0.0)
            except TimeoutError:
                return
            if not isinstance(message, str):
                continue
            payload = json.loads(message)
            if payload.get("type") == "ready":
                self._ready.set()
                continue
            if payload.get("type") != "recognition_result":
                continue
            result = {
                "transcript": str(payload.get("transcript", "") or ""),
                "wake_detected": str(payload.get("wake_detected", "False") or "False"),
                "command_name": str(payload.get("command_name", "") or ""),
                "feedback_text": str(payload.get("feedback_text", "") or ""),
                "debug_reason": str(payload.get("debug_reason", "unknown") or "unknown"),
                "audio_peak": str(payload.get("audio_peak", "") or ""),
                "audio_avg_abs": str(payload.get("audio_avg_abs", "") or ""),
            }
            if result["feedback_text"]:
                self._play_feedback(reader, result["feedback_text"])
            self._events.put(result)

    def _worker_loop(self) -> None:
        reader = self.audio_stream_reader_factory(self.audio_capture_config)
        try:
            self.log_callable(f"remote voice connecting: {self.server_url}")
            with self.connect_callable(self.server_url, open_timeout=self.open_timeout_seconds) as websocket:
                self.log_callable(f"remote voice connected: {self.server_url}")
                websocket.send(
                    json.dumps(
                        {
                            "type": "hello",
                            "rate": int(getattr(self.audio_capture_config, "rate", 16000)),
                            "channels": int(getattr(self.audio_capture_config, "channels", 1)),
                            "format": "pcm_s16le",
                        },
                        ensure_ascii=False,
                    )
                )
                self._drain_server_messages(websocket, reader)
                reader.start()
                while not self._stop_event.is_set():
                    chunk = reader.read_chunk()
                    if not chunk:
                        continue
                    websocket.send(chunk)
                    self._drain_server_messages(websocket, reader)
        except Exception as exc:
            self._fatal_error = exc
            self.log_callable(f"remote voice disconnected: {exc}")
        finally:
            reader.stop()

    def _ensure_started(self) -> None:
        if self._worker is not None:
            return
        self._worker = Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def capture_once(self, wake_word: str = "你好小灯") -> VoiceCommandPayload:
        self._ensure_started()
        if self._fatal_error is not None:
            raise self._fatal_error
        try:
            result = self._events.get_nowait()
        except Empty:
            return VoiceCommandPayload(wake_word="", command="", confidence=0.0, raw_text="", confirmed=False)
        return run_once_result_to_payload(result, wake_word=wake_word)

    def close(self) -> None:
        self._stop_event.set()
        if self._worker is not None:
            self._worker.join(timeout=1.0)
            self._worker = None


def _make_remote_runtime(external_root: Path, config: dict[str, Any]) -> RemoteVoiceRuntime:
    audio_support = _load_external_audio_support(external_root)
    audio = config.get("audio", {})
    remote = config.get("remote", {})
    capture_config = audio_support["AudioCaptureConfig"](
        device=str(audio.get("device", "plughw:0,0")),
        rate=int(audio.get("rate", 16000)),
        channels=int(audio.get("channels", 1)),
        duration_seconds=int(audio.get("chunk_seconds", 2)),
    )
    server_url = str(remote.get("server_url", "ws://10.125.175.124:8765"))
    open_timeout_seconds = float(remote.get("open_timeout_seconds", 2.0))
    wait_after_playback_seconds = float(remote.get("wait_after_playback_seconds", 3.0))
    return RemoteVoiceRuntime(
        server_url=server_url,
        audio_capture_config=capture_config,
        audio_stream_reader_factory=audio_support["AudioStreamReader"],
        speaker=audio_support["speak_or_print"],
        open_timeout_seconds=open_timeout_seconds,
        wait_after_playback_seconds=wait_after_playback_seconds,
    )


def make_default_runtime(
    external_root: Path | None = None,
    loader: Callable[[Path], dict[str, Any]] | None = None,
    config_loader: Callable[[Path], dict[str, Any]] | None = None,
) -> VoiceRuntime:
    external_root = external_root or DEFAULT_EXTERNAL_VOICE_ROOT
    loader = loader or _load_external_voice_module
    config_loader = config_loader or _load_external_config
    modules = loader(external_root)
    config = config_loader(external_root)
    stream_factory = modules.get("make_stream_runtime")
    local_runtime = None
    if callable(stream_factory):
        local_runtime = VoiceRuntime(stream_runtime=stream_factory())
    else:
        local_runtime = VoiceRuntime(run_once_callable=modules["run_once"])
    if bool(config.get("remote", {}).get("enabled", False)):
        return FallbackVoiceRuntime(primary=_make_remote_runtime(external_root, config), fallback=local_runtime)
    return local_runtime
