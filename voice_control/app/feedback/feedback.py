from __future__ import annotations

import shutil
import subprocess


def build_feedback_payload(text: str, tts_available: bool) -> dict[str, str]:
    return {"mode": "tts" if tts_available else "text", "text": text}


def speak_or_print(text: str) -> dict[str, str]:
    engine = shutil.which("espeak-ng") or shutil.which("espeak")
    payload = build_feedback_payload(text, tts_available=engine is not None)
    if engine is not None:
        subprocess.run([engine, text], check=False)
    else:
        print(text)
    return payload
