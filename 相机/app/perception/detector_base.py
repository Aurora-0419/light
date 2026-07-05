from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PerceptionResult:
    has_detection: bool
    primary_bbox: tuple[int, int, int, int] | None
    primary_center: tuple[int, int] | None
    depth_value_mm: int | None
    label: str = "candidate"
