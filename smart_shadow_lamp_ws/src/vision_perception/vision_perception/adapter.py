from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable


def resolve_workspace_root(adapter_file: Path) -> Path:
    adapter_file = adapter_file.resolve()
    for parent in adapter_file.parents:
        if (parent / "src").is_dir():
            return parent
        if parent.name == "install":
            return parent.parent
    raise RuntimeError(f"failed to infer workspace root from {adapter_file}")


WORKSPACE_ROOT = resolve_workspace_root(Path(__file__))
DEFAULT_EXTERNAL_VISION_ROOT = WORKSPACE_ROOT.parent / "camera"

from vision_perception.posture_detector import OptionalPosePostureDetector, PostureResult


@dataclass
class VisionStatePayload:
    hand_detected: bool
    hand_center_x: float
    hand_center_y: float
    shadow_detected: bool
    shadow_center_x: float
    shadow_center_y: float
    shadow_area: float
    needs_relight: bool
    suggested_target_x: float
    suggested_target_y: float
    source_frame: str
    posture_ok: bool = True
    posture_issue: str = ""
    posture_score: float = 0.0


@dataclass
class VisionRuntime:
    detector: Any
    capture: Any
    source: int | str
    posture_detector: Any

    def capture_once(self) -> VisionStatePayload:
        ok, frame = self.capture.read()
        if not ok or frame is None:
            return VisionStatePayload(
                hand_detected=False,
                hand_center_x=0.0,
                hand_center_y=0.0,
                shadow_detected=False,
                shadow_center_x=0.0,
                shadow_center_y=0.0,
                shadow_area=0.0,
                needs_relight=False,
                suggested_target_x=0.0,
                suggested_target_y=0.0,
                source_frame=str(self.source),
            )
        result = self.detector.process(frame)
        posture_result = self.posture_detector.detect(frame)
        return detection_result_to_payload(
            result,
            source_frame=str(self.source),
            posture_result=posture_result,
        )

    def close(self) -> None:
        release = getattr(self.capture, "release", None)
        if callable(release):
            release()


def _point_or_zero(value: tuple[int, int] | None) -> tuple[float, float]:
    if value is None:
        return 0.0, 0.0
    return float(value[0]), float(value[1])


def detection_result_to_payload(
    result: Any,
    source_frame: str,
    posture_result: PostureResult | Any | None = None,
) -> VisionStatePayload:
    hand_x, hand_y = _point_or_zero(getattr(result, "hand_center", None))
    shadow_x, shadow_y = _point_or_zero(getattr(result, "shadow_center", None))
    target_x, target_y = _point_or_zero(getattr(result, "suggested_target_center", None))
    shadow_area = getattr(result, "shadow_area", None)
    posture_result = posture_result or PostureResult(posture_ok=True, posture_issue="", posture_score=0.0)
    return VisionStatePayload(
        hand_detected=getattr(result, "hand_center", None) is not None,
        hand_center_x=hand_x,
        hand_center_y=hand_y,
        shadow_detected=getattr(result, "shadow_center", None) is not None,
        shadow_center_x=shadow_x,
        shadow_center_y=shadow_y,
        shadow_area=float(shadow_area or 0.0),
        needs_relight=bool(getattr(result, "needs_relight", False)),
        suggested_target_x=target_x,
        suggested_target_y=target_y,
        source_frame=source_frame,
        posture_ok=bool(getattr(posture_result, "posture_ok", True)),
        posture_issue=str(getattr(posture_result, "posture_issue", "") or ""),
        posture_score=float(getattr(posture_result, "posture_score", 0.0) or 0.0),
    )


def payload_to_message(payload: VisionStatePayload, message_factory: Callable[[], Any]) -> Any:
    msg = message_factory()
    msg.hand_detected = payload.hand_detected
    msg.hand_center_x = payload.hand_center_x
    msg.hand_center_y = payload.hand_center_y
    msg.shadow_detected = payload.shadow_detected
    msg.shadow_center_x = payload.shadow_center_x
    msg.shadow_center_y = payload.shadow_center_y
    msg.shadow_area = payload.shadow_area
    msg.needs_relight = payload.needs_relight
    msg.suggested_target_x = payload.suggested_target_x
    msg.suggested_target_y = payload.suggested_target_y
    msg.source_frame = payload.source_frame
    msg.posture_ok = payload.posture_ok
    msg.posture_issue = payload.posture_issue
    msg.posture_score = payload.posture_score
    return msg


def _load_module_from_path(module_name: str, file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_external_pc_demo_modules(external_root: Path) -> dict[str, Any]:
    if str(external_root) not in sys.path:
        sys.path.insert(0, str(external_root))
    module = _load_module_from_path(
        "external_pc_hand_shadow_demo",
        external_root / "scripts" / "run_pc_hand_shadow_demo.py",
    )
    return {
        "detector_factory": module.CombinedHandShadowDetector,
        "capture_factory": module.cv2.VideoCapture,
        "resolve_source": module.resolve_source,
    }


def make_default_runtime(
    external_root: Path | None = None,
    loader: Callable[[Path], dict[str, Any]] | None = None,
    posture_detector: Any | None = None,
    video_path: str | None = None,
) -> VisionRuntime:
    external_root = external_root or DEFAULT_EXTERNAL_VISION_ROOT
    loader = loader or _load_external_pc_demo_modules
    modules = loader(external_root)
    args = argparse.Namespace(webcam=False, camera=None, video=video_path, save_frame=None)
    source = modules["resolve_source"](args)
    detector = modules["detector_factory"]()
    capture = modules["capture_factory"](source)
    posture_detector = posture_detector or OptionalPosePostureDetector()
    return VisionRuntime(detector=detector, capture=capture, source=source, posture_detector=posture_detector)
