from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable


def resolve_workspace_root(adapter_file: Path) -> Path:
    adapter_file = adapter_file.resolve()
    for parent in adapter_file.parents:
        if (parent / "src").is_dir() and (parent / "tests").is_dir():
            return parent
    raise RuntimeError(f"failed to infer workspace root from {adapter_file}")


WORKSPACE_ROOT = resolve_workspace_root(Path(__file__))
DEFAULT_EXTERNAL_VOICE_ROOT = WORKSPACE_ROOT.parent / "voice_control"


@dataclass
class VoiceCommandPayload:
    wake_word: str
    command: str
    confidence: float
    raw_text: str
    confirmed: bool


@dataclass
class VoiceRuntime:
    run_once_callable: Callable[[], dict[str, str]]

    def capture_once(self, wake_word: str = "你好小灯") -> VoiceCommandPayload:
        result = self.run_once_callable()
        return run_once_result_to_payload(result, wake_word=wake_word)


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def run_once_result_to_payload(
    result: dict[str, str],
    wake_word: str = "你好小灯",
) -> VoiceCommandPayload:
    command = str(result.get("command_name", "") or "")
    wake_detected = _is_truthy(result.get("wake_detected", False))
    return VoiceCommandPayload(
        wake_word=wake_word if wake_detected else "",
        command=command,
        confidence=1.0 if command else 0.0,
        raw_text=str(result.get("transcript", "") or ""),
        confirmed=bool(command),
    )


def payload_to_message(payload: VoiceCommandPayload, message_factory: Callable[[], Any]) -> Any:
    msg = message_factory()
    msg.wake_word = payload.wake_word
    msg.command = payload.command
    msg.confidence = payload.confidence
    msg.raw_text = payload.raw_text
    msg.confirmed = payload.confirmed
    return msg


def _load_module_from_path(module_name: str, file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_external_voice_module(external_root: Path) -> dict[str, Any]:
    if str(external_root) not in sys.path:
        sys.path.insert(0, str(external_root))
    module = _load_module_from_path(
        "external_voice_control_demo",
        external_root / "scripts" / "run_voice_control.py",
    )
    return {"run_once": module.run_once}


def make_default_runtime(
    external_root: Path | None = None,
    loader: Callable[[Path], dict[str, Any]] | None = None,
) -> VoiceRuntime:
    external_root = external_root or DEFAULT_EXTERNAL_VOICE_ROOT
    loader = loader or _load_external_voice_module
    modules = loader(external_root)
    return VoiceRuntime(run_once_callable=modules["run_once"])
