from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


VOICE_ASSET_ROOT = Path(__file__).resolve().parents[3] / "语音"

FEEDBACK_AUDIO_FILES = {
    "我在": "我在请说.wav",
    "是否确认": "是否确认.wav",
    "请再说一遍": "请再说一遍.wav",
    "好的 已执行": "好的 已执行.wav",
    "已开启跟踪模式": "已开启跟踪模式.wav",
    "已关闭跟踪模式": "已关闭跟踪模式.wav",
    "已切换暖光模式": "已切换暖光模式.wav",
    "已切换冷光模式": "已切换冷光模式.wav",
    "请调整坐姿": "请调整坐姿.wav",
}


def build_feedback_payload(text: str, tts_available: bool) -> dict[str, str]:
    return {"mode": "tts" if tts_available else "text", "text": text}


def resolve_feedback_audio(text: str) -> Path | None:
    file_name = FEEDBACK_AUDIO_FILES.get(text)
    if file_name is None:
        return None
    return VOICE_ASSET_ROOT / file_name


def speak_or_print(text: str) -> dict[str, str]:
    audio_path = resolve_feedback_audio(text)
    player = shutil.which("aplay")
    if audio_path is not None and audio_path.exists() and player is not None:
        subprocess.run(
            [player, str(audio_path)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"mode": "wav", "text": text}

    engine = shutil.which("espeak-ng") or shutil.which("espeak")
    payload = build_feedback_payload(text, tts_available=engine is not None)
    if engine is not None:
        subprocess.run([engine, text], check=False)
    return payload
