# Posture Reminder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add coarse posture detection and throttled study-posture reminders to the existing smart shadow lamp ROS workspace without interfering with shadow-follow control.

**Architecture:** Extend the vision bridge with optional pose-based posture evaluation, publish the result in `VisionState`, and let `system_coordinator` handle persistence and cooldown before triggering feedback. Reuse the existing external `voice_control` feedback function for reminder playback or text output instead of building a second reminder stack.

**Tech Stack:** Python 3.10, pytest, optional MediaPipe Pose, OpenCV, ROS2 message bridge code

---

### Task 1: Extend VisionState with posture fields

**Files:**
- Modify: `/home/yzy/workspace/smart_shadow_lamp_ws/src/common_interfaces/msg/VisionState.msg`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_vision_posture_payload.py`

- [ ] **Step 1: Write the failing test**

```python
def test_posture_payload_defaults_to_ok():
    payload = VisionStatePayload(...)
    assert payload.posture_ok is True
    assert payload.posture_issue == ""
    assert payload.posture_score == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_vision_posture_payload.py -q`
Expected: FAIL because the posture fields do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```text
Add `posture_ok`, `posture_issue`, and `posture_score` to `VisionState.msg`, and extend the vision payload dataclass with matching fields.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_vision_posture_payload.py -q`
Expected: PASS

### Task 2: Add posture detector logic to vision_perception

**Files:**
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/vision_perception/vision_perception/posture_detector.py`
- Modify: `/home/yzy/workspace/smart_shadow_lamp_ws/src/vision_perception/vision_perception/adapter.py`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_posture_detector.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_rule_detector_flags_shoulder_tilt():
    result = evaluate_landmarks({...})
    assert result.posture_ok is False
    assert result.posture_issue == "shoulder_tilt"
```

```python
def test_rule_detector_flags_head_too_close():
    result = evaluate_landmarks({...})
    assert result.posture_issue == "head_too_close"
```

```python
def test_detection_result_to_payload_carries_posture_fields():
    payload = detection_result_to_payload(result, source_frame="camera", posture_result=posture)
    assert payload.posture_issue == "body_lean_left_right"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_posture_detector.py tests/test_vision_posture_payload.py -q`
Expected: FAIL because the detector and payload mapping do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```text
Create a small posture detector that accepts mocked landmarks and optionally runs MediaPipe Pose when available. Update the vision adapter so `capture_once()` runs posture detection on the same frame and injects posture state into the returned payload.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_posture_detector.py tests/test_vision_posture_payload.py -q`
Expected: PASS

### Task 3: Add reminder state machine to system_coordinator

**Files:**
- Modify: `/home/yzy/workspace/smart_shadow_lamp_ws/src/system_coordinator/system_coordinator/coordinator_node.py`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/system_coordinator/system_coordinator/posture_reminder.py`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_posture_reminder.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_reminder_requires_persistence_before_trigger():
    state = reminder_state.update(issue="shoulder_tilt", now=10.0)
    assert state.should_remind is False
```

```python
def test_reminder_respects_cooldown():
    ...
    assert second.should_remind is False
```

```python
def test_reminder_generates_expected_message_text():
    assert reminder_text_for_issue("head_too_close") == "请不要离桌面太近"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_posture_reminder.py -q`
Expected: FAIL because the reminder state machine does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```text
Add a coordinator-local posture reminder helper that tracks active issue start time and last reminder time per issue. When a reminder is due, generate a fixed Chinese text string and keep shadow-follow control untouched.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_posture_reminder.py -q`
Expected: PASS

### Task 4: Connect coordinator reminders to existing feedback output

**Files:**
- Modify: `/home/yzy/workspace/smart_shadow_lamp_ws/src/system_coordinator/system_coordinator/coordinator_node.py`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/system_coordinator/system_coordinator/feedback_adapter.py`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_feedback_adapter.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_feedback_adapter_uses_external_voice_feedback_loader():
    adapter = make_feedback_runtime(loader=fake_loader)
    payload = adapter.speak_or_print("请坐正一点")
    assert payload["text"] == "请坐正一点"
```

```python
def test_coordinator_skips_feedback_when_no_posture_issue():
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_feedback_adapter.py -q`
Expected: FAIL because the adapter does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```text
Reuse `voice_control/app/feedback/feedback.py` through a thin loader so coordinator can call `speak_or_print()` when a reminder is due. If the external module is unavailable, fall back to `print`.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_feedback_adapter.py -q`
Expected: PASS

### Task 5: Verify the full increment

**Files:**
- Test: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/*.py`

- [ ] **Step 1: Run focused posture tests**

Run: `pytest tests/test_vision_posture_payload.py tests/test_posture_detector.py tests/test_posture_reminder.py tests/test_feedback_adapter.py -q`
Expected: PASS

- [ ] **Step 2: Run full smart workspace tests**

Run: `pytest tests -q`
Expected: PASS

- [ ] **Step 3: Rebuild workspace with system Python**

Run: `rm -rf build install log && source /opt/ros/humble/setup.bash && export PATH="/usr/bin:/bin:$PATH" && colcon build`
Expected: build succeeds.
