from __future__ import annotations

import os
import platform
import shutil


def _detect_platform_name() -> str:
    machine = platform.machine().lower()
    if machine in {"aarch64", "arm64"} and os.path.exists("/dev/bpu"):
        return "rdk_x5"
    return machine or "unknown"


def detect_voice_capabilities(
    platform_name: str | None = None,
    microphone_available: bool | None = None,
    vosk_available: bool | None = None,
    tts_available: bool | None = None,
) -> dict[str, object]:
    platform_name = platform_name or _detect_platform_name()
    microphone_available = microphone_available if microphone_available is not None else shutil.which("arecord") is not None
    if vosk_available is None:
        try:
            import vosk  # noqa: F401

            vosk_available = True
        except Exception:
            vosk_available = False
    tts_available = tts_available if tts_available is not None else shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None

    recommended_mode = "local_command"
    warning = "Offline command mode is preferred on RDK X5."
    if not microphone_available:
        warning = "Offline command mode is preferred on RDK X5, but no microphone capture command is available."
    elif not vosk_available:
        warning = "Offline command mode is preferred on RDK X5. Install an offline ASR engine or model to improve recognition."

    return {
        "platform": platform_name,
        "microphone_available": microphone_available,
        "vosk_available": vosk_available,
        "tts_available": tts_available,
        "recommended_mode": recommended_mode,
        "warning": warning,
    }
