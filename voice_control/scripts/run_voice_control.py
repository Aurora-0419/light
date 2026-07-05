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
from app.command.parser import parse_command_text
from app.feedback.feedback import speak_or_print
from app.runtime.capabilities import detect_voice_capabilities
from app.speech.vosk_bridge import VoskRecognizer


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run voice control package")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
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
    recognizer = VoskRecognizer(ROOT / str(speech.get("model_path", "models/vosk-model-small-cn")))
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)
    try:
        record_once(capture, wav_path)
        text = recognizer.transcribe_file(wav_path)
        parsed = parse_command_text(text, wake_phrase)
        speak_or_print(parsed.feedback_text)
        return {
            "transcript": text,
            "wake_detected": str(parsed.wake_detected),
            "command_name": parsed.command_name or "",
        }
    finally:
        wav_path.unlink(missing_ok=True)


def main() -> int:
    args = build_arg_parser().parse_args()
    if args.dry_run:
        print(detect_voice_capabilities())
        return 0
    if args.once:
        print(run_once())
        return 0
    from app.ros2_nodes.voice_control_node import main as ros_main
    ros_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
