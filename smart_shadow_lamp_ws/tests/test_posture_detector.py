from __future__ import annotations

from types import SimpleNamespace

from vision_perception.posture_detector import PostureResult, evaluate_landmarks


def test_rule_detector_flags_shoulder_tilt():
    landmarks = {
        "left_shoulder": (0.40, 0.40),
        "right_shoulder": (0.60, 0.55),
        "left_hip": (0.42, 0.65),
        "right_hip": (0.58, 0.65),
        "nose": (0.50, 0.22),
    }

    result = evaluate_landmarks(landmarks)

    assert result.posture_ok is False
    assert result.posture_issue == "shoulder_tilt"
    assert result.posture_score > 0.0


def test_rule_detector_flags_head_too_close():
    landmarks = {
        "left_shoulder": (0.42, 0.40),
        "right_shoulder": (0.58, 0.40),
        "left_hip": (0.44, 0.66),
        "right_hip": (0.56, 0.66),
        "nose": (0.50, 0.36),
    }

    result = evaluate_landmarks(landmarks)

    assert result.posture_ok is False
    assert result.posture_issue == "head_too_close"


def test_rule_detector_flags_body_lean_left_right():
    landmarks = {
        "left_shoulder": (0.26, 0.40),
        "right_shoulder": (0.46, 0.40),
        "left_hip": (0.44, 0.66),
        "right_hip": (0.56, 0.66),
        "nose": (0.34, 0.20),
    }

    result = evaluate_landmarks(landmarks)

    assert result.posture_ok is False
    assert result.posture_issue == "body_lean_left_right"


def test_rule_detector_returns_neutral_for_missing_landmarks():
    result = evaluate_landmarks({"nose": (0.5, 0.3)})

    assert result == PostureResult(posture_ok=True, posture_issue="", posture_score=0.0, available=False)
