from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EXTERNAL_VOICE_ROOT = WORKSPACE_ROOT.parent / "voice_control"


def _load_module_from_path(module_name: str, file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class FeedbackRuntime:
    feedback_module: Any | None = None

    def speak_or_print(self, text: str) -> dict[str, str]:
        if self.feedback_module is None:
            print(text)
            return {"mode": "text", "text": text}
        return self.feedback_module.speak_or_print(text)


def _load_external_feedback_module(external_root: Path) -> dict[str, Any]:
    if str(external_root) not in sys.path:
        sys.path.insert(0, str(external_root))
    module = _load_module_from_path(
        "external_voice_feedback",
        external_root / "app" / "feedback" / "feedback.py",
    )
    return {"feedback_module": module}


def make_feedback_runtime(
    external_root: Path | None = None,
    loader: Callable[[Path], dict[str, Any]] | None = None,
) -> FeedbackRuntime:
    external_root = external_root or DEFAULT_EXTERNAL_VOICE_ROOT
    loader = loader or _load_external_feedback_module
    try:
        modules = loader(external_root)
    except Exception:
        modules = {}
    return FeedbackRuntime(feedback_module=modules.get("feedback_module"))
