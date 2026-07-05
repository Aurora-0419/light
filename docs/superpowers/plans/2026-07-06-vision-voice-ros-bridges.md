# Vision Voice ROS Bridges Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder ROS publishers in `smart_shadow_lamp_ws` with thin bridge code that maps the existing `相机/` and `voice_control/` projects into shared ROS message payloads.

**Architecture:** Keep the current algorithm implementations in their original projects. Add small adapter modules inside `vision_perception` and `voice_control` that load the existing code, normalize its outputs into typed payload dataclasses, and let the ROS nodes publish those payloads when ROS messages are available.

**Tech Stack:** Python 3.10, pytest, ROS2 package skeletons, existing `相机/` and `voice_control/` modules

---

### Task 1: Vision payload adapter

**Files:**
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_vision_bridge_adapter.py`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/vision_perception/vision_perception/adapter.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_convert_detection_result_to_payload():
    result = SimpleNamespace(
        hand_center=(120, 90),
        shadow_center=(180, 110),
        needs_relight=True,
        suggested_target_center=(180, 110),
        shadow_area=3200,
    )
    payload = detection_result_to_payload(result, source_frame="camera")

    assert payload.hand_detected is True
    assert payload.shadow_detected is True
    assert payload.needs_relight is True
    assert payload.hand_center_x == 120.0
```

```python
def test_make_default_runtime_uses_external_pc_demo_modules():
    runtime = make_default_runtime(external_root=Path("/tmp/project"), loader=loader)
    assert runtime.source == "/dev/video6"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_vision_bridge_adapter.py -q`
Expected: `FAIL` because the adapter module does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
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
```

```python
def detection_result_to_payload(result, source_frame: str) -> VisionStatePayload:
    ...
```

```python
def make_default_runtime(external_root: Path | None = None, loader=None) -> VisionRuntime:
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_vision_bridge_adapter.py -q`
Expected: all tests pass.

### Task 2: Voice payload adapter

**Files:**
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_voice_bridge_adapter.py`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/voice_control/voice_control/adapter.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_convert_run_once_output_to_payload():
    payload = run_once_result_to_payload(
        {"transcript": "你好小灯 开启跟踪模式", "wake_detected": "True", "command_name": "enable_tracking"}
    )
    assert payload.command == "enable_tracking"
    assert payload.confirmed is True
```

```python
def test_payload_marks_missing_command_unconfirmed():
    payload = run_once_result_to_payload(
        {"transcript": "你好小灯", "wake_detected": "True", "command_name": ""}
    )
    assert payload.confirmed is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_voice_bridge_adapter.py -q`
Expected: `FAIL` because the adapter module does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass
class VoiceCommandPayload:
    wake_word: str
    command: str
    confidence: float
    raw_text: str
    confirmed: bool
```

```python
def run_once_result_to_payload(result: dict[str, str], wake_word: str = "你好小灯") -> VoiceCommandPayload:
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_voice_bridge_adapter.py -q`
Expected: all tests pass.

### Task 3: Wire the ROS nodes to the adapters

**Files:**
- Modify: `/home/yzy/workspace/smart_shadow_lamp_ws/src/vision_perception/vision_perception/vision_state_bridge.py`
- Modify: `/home/yzy/workspace/smart_shadow_lamp_ws/src/voice_control/voice_control/voice_command_bridge.py`
- Test: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_vision_bridge_adapter.py`
- Test: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_voice_bridge_adapter.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_vision_payload_populates_message_factory():
    message = payload_to_message(payload, message_factory=FakeVisionMessage)
    assert message.hand_detected is True
```

```python
def test_voice_payload_populates_message_factory():
    message = payload_to_message(payload, message_factory=FakeVoiceMessage)
    assert message.command == "enable_tracking"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_vision_bridge_adapter.py tests/test_voice_bridge_adapter.py -q`
Expected: `FAIL` because message conversion helpers do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def payload_to_message(payload, message_factory):
    msg = message_factory()
    ...
    return msg
```

```python
class VisionStateBridge(Node):
    def _publish_state(self) -> None:
        payload = self.runtime.capture_once()
        self.publisher.publish(payload_to_message(payload, VisionState))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_vision_bridge_adapter.py tests/test_voice_bridge_adapter.py -q`
Expected: all tests pass.

### Task 4: Verify the bridge increment

**Files:**
- Test: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_workspace_layout.py`
- Test: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_vision_bridge_adapter.py`
- Test: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_voice_bridge_adapter.py`

- [ ] **Step 1: Run the focused bridge tests**

Run: `pytest tests/test_workspace_layout.py tests/test_vision_bridge_adapter.py tests/test_voice_bridge_adapter.py -q`
Expected: all tests pass.
