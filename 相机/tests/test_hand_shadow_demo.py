import numpy as np

from app.perception.hand_shadow_demo import HandShadowDemoDetector


def test_hand_shadow_demo_detects_synthetic_foreground_blob():
    color = np.zeros((480, 640, 3), dtype=np.uint8)
    depth = np.zeros((480, 640), dtype=np.uint16)

    color[150:280, 220:360] = (180, 170, 160)
    depth[150:280, 220:360] = 800

    detector = HandShadowDemoDetector(min_area=1000)
    result = detector.process(color, depth)

    assert result.has_detection is True
    assert result.primary_bbox is not None
    assert result.primary_center is not None
    assert result.depth_value_mm == 800
