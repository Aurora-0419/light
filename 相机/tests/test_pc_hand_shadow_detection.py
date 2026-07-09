import numpy as np

from app.perception.combined_detector import CombinedHandShadowDetector
from app.perception.hand_detector import HandDetection, MediaPipeHandDetector
from app.perception.shadow_detector import ShadowDetector


class _FakeHandBackend:
    def detect(self, frame):
        return [
            HandDetection(
                bbox=(100, 80, 60, 80),
                center=(130, 120),
                confidence=0.9,
                landmarks=[(130, 120), (135, 125)],
            )
        ]


def test_hand_detector_uses_injected_backend():
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    detector = MediaPipeHandDetector(backend=_FakeHandBackend())

    result = detector.detect(frame)

    assert result.available is True
    assert result.hands[0].center == (130, 120)
    assert result.hands[0].confidence == 0.9


def test_shadow_detector_finds_dark_region_on_bright_surface():
    frame = np.full((240, 320, 3), 220, dtype=np.uint8)
    frame[90:150, 140:220] = 70

    result = ShadowDetector(min_area=1000).detect(frame)

    assert result.has_shadow is True
    assert result.primary_shadow is not None
    assert result.primary_shadow.area >= 4000


def test_shadow_detector_ignores_black_object_on_bright_surface():
    frame = np.full((240, 320, 3), 220, dtype=np.uint8)
    frame[90:150, 140:220] = 5

    result = ShadowDetector(min_area=1000).detect(frame)

    assert result.has_shadow is False


def test_combined_detector_outputs_relight_hint():
    frame = np.full((240, 320, 3), 220, dtype=np.uint8)
    frame[90:150, 140:220] = 70
    detector = CombinedHandShadowDetector(
        hand_detector=MediaPipeHandDetector(backend=_FakeHandBackend()),
        shadow_detector=ShadowDetector(min_area=1000),
    )

    result = detector.process(frame)

    assert result.needs_relight is True
    assert result.hand_center == (130, 120)
    assert result.shadow_center is not None
    assert result.suggested_target_center is not None
    assert result.shadow_mask is not None
    assert result.shadow_mask.sum() > 0


def test_combined_detector_prefers_shadow_near_hand_over_far_dark_region():
    frame = np.full((240, 320, 3), 220, dtype=np.uint8)
    frame[95:155, 145:205] = 80
    frame[20:110, 235:315] = 80
    detector = CombinedHandShadowDetector(
        hand_detector=MediaPipeHandDetector(backend=_FakeHandBackend()),
        shadow_detector=ShadowDetector(min_area=1000),
    )

    result = detector.process(frame)

    assert result.shadow_center is not None
    assert abs(result.shadow_center[0] - 175) <= 10
    assert abs(result.shadow_center[1] - 125) <= 10
    assert result.shadow_mask is not None
    assert result.shadow_mask[125, 175] > 0
    assert result.shadow_mask[60, 275] == 0


def test_combined_detector_outputs_shadow_vector_and_selected_mask():
    frame = np.full((240, 320, 3), 220, dtype=np.uint8)
    frame[95:155, 145:205] = 80
    detector = CombinedHandShadowDetector(
        hand_detector=MediaPipeHandDetector(backend=_FakeHandBackend()),
        shadow_detector=ShadowDetector(min_area=1000),
    )

    result = detector.process(frame)

    assert result.shadow_mask is not None
    assert result.shadow_mask.sum() > 0
    assert result.shadow_vector is not None
    assert result.shadow_vector[0] > 0
