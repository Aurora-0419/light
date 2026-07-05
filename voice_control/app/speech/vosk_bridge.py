from __future__ import annotations

import json
from pathlib import Path
import wave


class VoskRecognizer:
    def __init__(self, model_path: Path):
        self.model_path = model_path

    def available(self) -> bool:
        return self.model_path.exists()

    def transcribe_file(self, wav_path: Path) -> str:
        if not self.available():
            return ""
        try:
            from vosk import KaldiRecognizer, Model
        except Exception:
            return ""

        wf = wave.open(str(wav_path), "rb")
        try:
            model = Model(str(self.model_path))
            recognizer = KaldiRecognizer(model, wf.getframerate())
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                recognizer.AcceptWaveform(data)
            result = json.loads(recognizer.FinalResult())
            return str(result.get("text", "")).strip()
        finally:
            wf.close()
