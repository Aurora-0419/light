from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

for package_name in [
    "vision_perception",
    "voice_control",
    "system_coordinator",
    "light_control",
    "arm_control",
]:
    package_root = ROOT / "src" / package_name
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
