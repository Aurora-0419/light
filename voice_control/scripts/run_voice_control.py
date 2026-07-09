from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.audio.capture import AudioCaptureConfig, record_once
from app.feedback.feedback import speak_or_print
from app.runtime.interaction import VoiceInteractionSession
from app.runtime.pipeline import AudioChunkPipeline, StreamingVoiceRuntime
from app.runtime.capabilities import detect_voice_capabilities
from app.speech.vosk_bridge import VoskRecognizer, VoskStreamingRecognizer


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run voice control package")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--stream", action="store_true")
    return parser


def run_once() -> dict[str, str]:
    config = yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8")) or {}
    audio = config.get("audio", {})
    speech = config.get("speech", {})
    capture = AudioCaptureConfig(
        device=str(audio.get("device", "plughw:0,0")),
        rate=int(audio.get("rate", 16000)),
        channels=int(audio.get("channels", 1)),
        duration_seconds=int(audio.get("chunk_seconds", 2)),
    )
    wake_phrase = str(speech.get("wake_phrase", "你好小灯"))
    command_window_delay_seconds = float(speech.get("command_window_delay_seconds", 2.0))
    recognizer = VoskRecognizer(ROOT / str(speech.get("model_path", "models/vosk-model-small-cn")))
    session = VoiceInteractionSession(
        wake_phrase=wake_phrase,
        command_window_seconds=4.0,
        command_window_delay_seconds=command_window_delay_seconds,
    )
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)
    try:
        record_once(capture, wav_path)
        text = recognizer.transcribe_file(wav_path)
        result = session.process_text(text)
        if result.feedback_text:
            speak_or_print(result.feedback_text)
        return {
            "transcript": text,
            "wake_detected": str(result.wake_detected),
            "command_name": result.command_name or "",
        }
    finally:
        wav_path.unlink(missing_ok=True)


def make_stream_runtime() -> StreamingVoiceRuntime:
    config = yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8")) or {}
    audio = config.get("audio", {})
    speech = config.get("speech", {})
    capture = AudioCaptureConfig(
        device=str(audio.get("device", "plughw:0,0")),
        rate=int(audio.get("rate", 16000)),
        channels=int(audio.get("channels", 1)),
        duration_seconds=int(audio.get("chunk_seconds", 2)),
    )
    wake_phrase = str(speech.get("wake_phrase", "你好小灯"))
    recognizer = VoskStreamingRecognizer(ROOT / str(speech.get("model_path", "models/vosk-model-small-cn")), sample_rate=capture.rate)
    session = VoiceInteractionSession(
        wake_phrase=wake_phrase,
        command_window_seconds=4.0,
    )
    return StreamingVoiceRuntime(
        pipeline=AudioChunkPipeline(capture, recognizer),
        interaction_session=session,
    )


def run_stream() -> None:
    runtime = make_stream_runtime()
    try:
        while True:
            runtime.poll_once(timeout_seconds=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        runtime.stop()


def main() -> int:
    args = build_arg_parser().parse_args()
    if args.dry_run:
        print(detect_voice_capabilities())
        return 0
    if args.once:
        print(run_once())
        return 0
    if args.stream:
        run_stream()
        return 0
    from app.ros2_nodes.voice_control_node import main as ros_main
    ros_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
