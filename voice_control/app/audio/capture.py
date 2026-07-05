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


def record_once(config: AudioCaptureConfig, output_path: Path) -> Path:
    command = build_arecord_command(config, output_path)
    subprocess.run(command, check=True)
    return output_path
