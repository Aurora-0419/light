from __future__ import annotations

import json
from pathlib import Path
import wave


class VoskRecognizer:
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.model_loader = self._default_model_loader
        self._model = None

    def available(self) -> bool:
        return self.model_path.exists()

    def _default_model_loader(self, model_path: Path):
        from vosk import Model

        return Model(str(model_path))

    def _load_model(self):
        if self._model is None:
            self._model = self.model_loader(self.model_path)
        return self._model

    def transcribe_file(self, wav_path: Path) -> str:
        if not self.available():
            return ""
        try:
            from vosk import KaldiRecognizer
        except Exception:
            return ""

        wf = wave.open(str(wav_path), "rb")
        try:
            model = self._load_model()
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


class VoskStreamingRecognizer:
    def __init__(self, model_path: Path, sample_rate: int, model_loader=None):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.model_loader = model_loader or self._default_model_loader
        self.recognizer_factory = self._default_recognizer_factory
        self._model = None
        self._recognizer = None

    def _default_model_loader(self, model_path: Path):
        from vosk import Model

        return Model(str(model_path))

    def _default_recognizer_factory(self, model, sample_rate: int):
        from vosk import KaldiRecognizer

        return KaldiRecognizer(model, sample_rate)

    def _ensure_recognizer(self):
        if self._model is None:
            self._model = self.model_loader(self.model_path)
        if self._recognizer is None:
            self._recognizer = self.recognizer_factory(self._model, self.sample_rate)
        return self._recognizer

    def reset(self) -> None:
        self._recognizer = None

    def feed_audio(self, data: bytes) -> dict[str, str] | None:
        if not data:
            return None
        recognizer = self._ensure_recognizer()
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = str(result.get("text", "") or "").strip()
            if text:
                return {"kind": "final", "text": text}
            return None
        partial = json.loads(recognizer.PartialResult())
        text = str(partial.get("partial", "") or "").strip()
        if text:
            return {"kind": "partial", "text": text}
        return None
