from __future__ import annotations

from pathlib import Path

try:
    import rclpy
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node
    from std_msgs.msg import String
except Exception:  # pragma: no cover - depends on ROS runtime
    rclpy = None
    ExternalShutdownException = KeyboardInterrupt
    Node = object
    String = None
import yaml

from app.audio.capture import AudioCaptureConfig, compute_poll_interval_seconds
from app.runtime.interaction import VoiceInteractionSession
from app.runtime.pipeline import AudioChunkPipeline, StreamingVoiceRuntime
from app.speech.vosk_bridge import VoskStreamingRecognizer


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
        self.command_window_delay_seconds = float(speech.get("command_window_delay_seconds", 2.0))
        self.recognizer = VoskStreamingRecognizer(
            Path(__file__).resolve().parents[2] / str(speech.get("model_path", "models/vosk-model-small-cn")),
            sample_rate=self.capture_config.rate,
        )
        self.interaction_session = VoiceInteractionSession(
            wake_phrase=self.wake_phrase,
            command_window_seconds=4.0,
            command_window_delay_seconds=self.command_window_delay_seconds,
        )
        self.runtime = StreamingVoiceRuntime(
            pipeline=AudioChunkPipeline(self.capture_config, self.recognizer),
            interaction_session=self.interaction_session,
        )
        self.publisher = self.create_publisher(String, "voice/command", 10)
        self.timer = self.create_timer(max(0.1, compute_poll_interval_seconds(self.capture_config.duration_seconds, overhead_seconds=-3.8)), self._tick)

    def _tick(self) -> None:
        result = self.runtime.poll_once(timeout_seconds=0.0)
        if result is None:
            return
        command_name = str(result.get("command_name", "") or "")
        if not command_name:
            return
        msg = String()
        msg.data = command_name
        self.publisher.publish(msg)


def main() -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is unavailable in the current Python environment")
    rclpy.init()
    node = VoiceControlNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        runtime = getattr(node, "runtime", None)
        if runtime is not None:
            runtime.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
