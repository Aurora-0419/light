from __future__ import annotations

import os
import platform
from typing import Any


def _detect_platform_name() -> str:
    machine = platform.machine().lower()
    if machine in {"aarch64", "arm64"} and os.path.exists("/dev/bpu"):
        return "rdk_x5"
    return machine or "unknown"


def detect_runtime_capabilities() -> dict[str, Any]:
    horizon_bpu_available = os.path.exists("/dev/bpu")
    cuda_available = False

    platform_name = _detect_platform_name()
    if platform_name == "rdk_x5":
        recommended_backend = "bpu" if horizon_bpu_available else "cpu"
        warning = (
            "RDK X5 environment detected. Prefer BPU deployment for heavier models."
            if horizon_bpu_available
            else "RDK X5 detected without available BPU runtime path. Use CPU only for lightweight demos and convert models to BPU later."
        )
    else:
        recommended_backend = "cpu"
        warning = "CUDA is not assumed. Use CPU by default unless an explicit accelerator is configured."

    return {
        "platform": platform_name,
        "cuda_available": cuda_available,
        "horizon_bpu_available": horizon_bpu_available,
        "recommended_backend": recommended_backend,
        "warning": warning,
    }


def choose_perception_backend(capabilities: dict[str, Any] | None = None) -> dict[str, str]:
    capabilities = capabilities or detect_runtime_capabilities()

    platform_name = capabilities.get("platform", "unknown")
    if platform_name == "rdk_x5":
        if capabilities.get("horizon_bpu_available"):
            return {
                "backend": "bpu",
                "warning": "RDK X5 BPU is available. Convert heavier models to Horizon BPU format before deployment.",
            }
        return {
            "backend": "cpu",
            "warning": "RDK X5 is running CPU fallback only. Heavier models should be converted to BPU format.",
        }

    return {
        "backend": "cpu",
        "warning": "Defaulting to CPU backend. Configure another accelerator explicitly if needed.",
    }
