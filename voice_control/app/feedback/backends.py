from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess


def _resolve_piper_player() -> str | None:
    return shutil.which("aplay")


def _load_piper_sample_rate(model_path: str) -> int | None:
    config_path = Path(model_path).with_suffix(".onnx.json")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    if not isinstance(config, dict):
        return None
    audio_config = config.get("audio")
    if not isinstance(audio_config, dict):
        return None

    sample_rate = audio_config.get("sample_rate")
    if not isinstance(sample_rate, int) or sample_rate <= 0:
        return None
    return sample_rate


def resolve_backend(config: dict[str, object]) -> tuple[str, str | None]:
    backend = str(config.get("backend", "auto"))
    model_path = str(config.get("piper_model_path", ""))

    if backend == "text" or not bool(config.get("enable_tts", True)):
        return "text", None

    if backend in {"auto", "piper"}:
        executable = shutil.which("piper")
        if executable and model_path and Path(model_path).exists() and _resolve_piper_player():
            return "piper", executable
        if backend == "piper":
            return "text", None

    if backend in {"auto", "espeak", "espeak-ng"}:
        executable = shutil.which("espeak-ng") or shutil.which("espeak")
        if executable:
            return Path(executable).name, executable
        if backend in {"espeak", "espeak-ng"}:
            return "text", None

    if backend in {"auto", "spd-say"}:
        executable = shutil.which("spd-say")
        if executable:
            return "spd-say", executable
        if backend == "spd-say":
            return "text", None

    return "text", None


def run_backend(backend: str, executable: str | None, text: str, config: dict[str, object]) -> bool:
    if backend == "piper" and executable is not None:
        player = _resolve_piper_player()
        if player is None:
            return False
        sample_rate = _load_piper_sample_rate(str(config.get("piper_model_path", "")))
        if sample_rate is None:
            return False

        cmd = [executable, "--model", str(config.get("piper_model_path", ""))]
        speaker = str(config.get("piper_speaker", ""))
        if speaker:
            cmd.extend(["--speaker", speaker])
        cmd.append("--output-raw")
        cmd.extend(["--length_scale", str(config.get("piper_length_scale", 1.0))])

        synth = None
        playback = None
        try:
            synth = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            playback = subprocess.Popen(
                [player, "-q", "-t", "raw", "-r", str(sample_rate), "-f", "S16_LE", "-c", "1"],
                stdin=synth.stdout,
            )
            if synth.stdout is not None:
                synth.stdout.close()
            if synth.stdin is not None:
                synth.stdin.write(text.encode("utf-8"))
                synth.stdin.close()
            synth_returncode = synth.wait()
            playback_returncode = playback.wait()
        except OSError:
            return False
        return synth_returncode == 0 and playback_returncode == 0

    if backend in {"espeak-ng", "espeak"} and executable is not None:
        try:
            completed = subprocess.run(
                [executable, "-v", str(config.get("espeak_voice", "zh")), text],
                check=False,
            )
        except OSError:
            return False
        return completed.returncode == 0

    if backend == "spd-say" and executable is not None:
        try:
            completed = subprocess.run([executable, text], check=False)
        except OSError:
            return False
        return completed.returncode == 0

    return False
