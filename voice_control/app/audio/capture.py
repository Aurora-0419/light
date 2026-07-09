from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass
class AudioCaptureConfig:
    device: str
    rate: int
    channels: int
    duration_seconds: int


def compute_poll_interval_seconds(duration_seconds: int, *, overhead_seconds: float = 0.5) -> float:
    return max(0.5, float(duration_seconds) + overhead_seconds)


def compute_pcm16_stats(data: bytes) -> dict[str, float | int]:
    usable_length = len(data) - (len(data) % 2)
    if usable_length <= 0:
        return {"bytes": len(data), "samples": 0, "peak": 0, "avg_abs": 0.0}
    samples = [
        int.from_bytes(data[index : index + 2], "little", signed=True)
        for index in range(0, usable_length, 2)
    ]
    absolute_values = [abs(sample) for sample in samples]
    peak = max(absolute_values, default=0)
    avg_abs = sum(absolute_values) / len(absolute_values) if absolute_values else 0.0
    return {"bytes": len(data), "samples": len(samples), "peak": peak, "avg_abs": avg_abs}


def build_arecord_command(config: AudioCaptureConfig, output_path: Path) -> list[str]:
    return [
        "arecord",
        "-D",
        config.device,
        "-f",
        "S16_LE",
        "-r",
        str(config.rate),
        "-c",
        str(config.channels),
        "-d",
        str(config.duration_seconds),
        str(output_path),
    ]


def build_arecord_stream_command(config: AudioCaptureConfig) -> list[str]:
    return [
        "arecord",
        "-D",
        config.device,
        "-f",
        "S16_LE",
        "-r",
        str(config.rate),
        "-c",
        str(config.channels),
        "-t",
        "raw",
    ]


def record_once(config: AudioCaptureConfig, output_path: Path) -> Path:
    command = build_arecord_command(config, output_path)
    subprocess.run(command, check=True)
    return output_path


class AudioStreamReader:
    def __init__(
        self,
        config: AudioCaptureConfig | None = None,
        *,
        process_factory=None,
        chunk_bytes: int = 3200,
    ) -> None:
        self.config = config
        self.process_factory = process_factory or self._default_process_factory
        self.chunk_bytes = chunk_bytes
        self.process = None

    def _default_process_factory(self):
        if self.config is None:
            raise RuntimeError("AudioStreamReader requires a config when no process_factory is provided")
        return subprocess.Popen(
            build_arecord_stream_command(self.config),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def start(self) -> None:
        if self.process is None:
            self.process = self.process_factory()

    def read_chunk(self) -> bytes | None:
        self.start()
        stdout = getattr(self.process, "stdout", None)
        if stdout is None:
            return None
        data = stdout.read(self.chunk_bytes)
        if not data:
            return None
        return data

    def stop(self) -> None:
        if self.process is None:
            return
        terminate = getattr(self.process, "terminate", None)
        if callable(terminate):
            terminate()
        wait = getattr(self.process, "wait", None)
        if callable(wait):
            wait(timeout=1.0)
        self.process = None
