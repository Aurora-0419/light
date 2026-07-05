from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String
import yaml

from app.audio.capture import AudioCaptureConfig, record_once
from app.command.parser import parse_command_text
from app.feedback.feedback import speak_or_print
from app.runtime.capabilities import detect_voice_capabilities
from app.speech.vosk_bridge import VoskRecognizer


class VoiceControlNode(Node):
    def __init__(self) -> None:
        super().__init__("voice_control_node")
        config_path = Path(__file__).resolve().parents[2] / "configs" / "default.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

        audio = config.get("audio", {})
        speech = config.get("speech", {})
        self.capture_config = AudioCaptureConfig(
            device=str(audio.get("device", "plughw:0,0")),
            rate=int(audio.get("rate", 16000)),
            channels=int(audio.get("channels", 1)),
            duration_seconds=int(audio.get("chunk_seconds", 2)),
        )
        self.wake_phrase = str(speech.get("wake_phrase", "你好小灯"))
        self.recognizer = VoskRecognizer(Path(__file__).resolve().parents[2] / str(speech.get("model_path", "models/vosk-model-small-cn")))
        self.publisher = self.create_publisher(String, "voice/command", 10)
        self.timer = self.create_timer(2.5, self._tick)

    def _tick(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)
        try:
            record_once(self.capture_config, wav_path)
        except subprocess.CalledProcessError as exc:
            self.get_logger().warning(f"audio capture interrupted: {exc}")
            return
        try:
            text = self.recognizer.transcribe_file(wav_path)
            parsed = parse_command_text(text, self.wake_phrase)
            if parsed.command_name is None:
                return
            msg = String()
            msg.data = parsed.command_name
            self.publisher.publish(msg)
            speak_or_print(parsed.feedback_text)
        finally:
            wav_path.unlink(missing_ok=True)


def main() -> None:
    rclpy.init()
    node = VoiceControlNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
