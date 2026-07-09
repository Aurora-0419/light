# Paper Hand Shadow Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the PC demo automatically choose the RealSense color node and detect hand-caused paper shadows strongly enough to drive later light-angle control.

**Architecture:** Keep the PC demo on the existing OpenCV plus MediaPipe path. Detect the bright paper work area first, extract darkened regions only inside that work area, then associate the most plausible shadow region with the detected hand using simple spatial scoring instead of a heavy learned model. Expose a selected shadow mask and a hand-to-shadow control vector through the combined result so the UI and later control loop can use the same data.

**Tech Stack:** Python 3.10, OpenCV, NumPy, optional MediaPipe, pytest

---

### Task 1: Keep Camera Source Selection Stable

**Files:**
- Modify: `/home/yzy/workspace/相机/scripts/run_pc_hand_shadow_demo.py`
- Test: `/home/yzy/workspace/相机/tests/test_pc_demo_cli.py`

- [ ] **Step 1: Write the failing test**

```python
def test_default_source_auto_selects_realsense_color_device():
    parser = build_arg_parser()
    args = parser.parse_args([])

    assert resolve_source(args, camera_detector=lambda: "/dev/video6") == "/dev/video6"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pc_demo_cli.py::test_default_source_auto_selects_realsense_color_device -q`
Expected: `FAIL` because default source still resolves to `0`.

- [ ] **Step 3: Write minimal implementation**

```python
def resolve_source(args: argparse.Namespace, camera_detector=find_realsense_color_device) -> int | str:
    if args.camera:
        return int(args.camera) if args.camera.isdigit() else args.camera
    if args.video:
        return args.video
    if not args.webcam:
        detected = camera_detector()
        if detected:
            return detected
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pc_demo_cli.py::test_default_source_auto_selects_realsense_color_device -q`
Expected: `1 passed`

### Task 2: Detect Paper-Only Shadow Candidates

**Files:**
- Modify: `/home/yzy/workspace/相机/app/perception/shadow_detector.py`
- Test: `/home/yzy/workspace/相机/tests/test_pc_hand_shadow_detection.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_shadow_detector_ignores_black_object_on_bright_surface():
    frame = np.full((240, 320, 3), 220, dtype=np.uint8)
    frame[90:150, 140:220] = 5

    result = ShadowDetector(min_area=1000).detect(frame)

    assert result.has_shadow is False
```

```python
def test_shadow_detector_finds_dark_region_on_bright_surface():
    frame = np.full((240, 320, 3), 220, dtype=np.uint8)
    frame[90:150, 140:220] = 70

    result = ShadowDetector(min_area=1000).detect(frame)

    assert result.has_shadow is True
    assert result.primary_shadow is not None
    assert result.primary_shadow.area >= 4000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pc_hand_shadow_detection.py::test_shadow_detector_ignores_black_object_on_bright_surface tests/test_pc_hand_shadow_detection.py::test_shadow_detector_finds_dark_region_on_bright_surface -q`
Expected: at least the black-object test fails because the old detector labels any large dark block as a shadow.

- [ ] **Step 3: Write minimal implementation**

```python
bright_mask = cv2.inRange(gray, self.paper_threshold, 255)
paper_region = np.zeros_like(gray, dtype=np.uint8)
contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
largest_bright = max(contours, key=cv2.contourArea)
x, y, w, h = cv2.boundingRect(largest_bright)
paper_region[y : y + h, x : x + w] = 255

paper_values = gray[bright_mask > 0]
reference_intensity = float(np.percentile(paper_values, 75))
threshold_value = max(self.min_shadow_intensity, int(reference_intensity - self.darkness_threshold))
mask = cv2.inRange(gray, self.min_shadow_intensity, threshold_value)
mask = cv2.bitwise_and(mask, paper_region)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pc_hand_shadow_detection.py::test_shadow_detector_ignores_black_object_on_bright_surface tests/test_pc_hand_shadow_detection.py::test_shadow_detector_finds_dark_region_on_bright_surface -q`
Expected: `2 passed`

### Task 3: Associate the Shadow With the Hand

**Files:**
- Modify: `/home/yzy/workspace/相机/app/perception/shadow_detector.py`
- Modify: `/home/yzy/workspace/相机/app/perception/combined_detector.py`
- Test: `/home/yzy/workspace/相机/tests/test_pc_hand_shadow_detection.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_combined_detector_prefers_shadow_near_hand_over_far_dark_region():
    frame = np.full((240, 320, 3), 220, dtype=np.uint8)
    frame[95:155, 145:205] = 80
    frame[20:100, 240:310] = 80
    detector = CombinedHandShadowDetector(
        hand_detector=MediaPipeHandDetector(backend=_FakeHandBackend()),
        shadow_detector=ShadowDetector(min_area=1000),
    )

    result = detector.process(frame)

    assert result.shadow_center is not None
    assert abs(result.shadow_center[0] - 175) <= 10
    assert abs(result.shadow_center[1] - 125) <= 10
```

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pc_hand_shadow_detection.py::test_combined_detector_prefers_shadow_near_hand_over_far_dark_region tests/test_pc_hand_shadow_detection.py::test_combined_detector_outputs_shadow_vector_and_selected_mask -q`
Expected: `FAIL` because the current combined detector uses only the detector’s primary region and exposes no vector.

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass
class ShadowDetectionResult:
    has_shadow: bool
    primary_shadow: ShadowRegion | None
    mask: np.ndarray | None
    regions: list[ShadowRegion]

def _select_shadow_for_hand(hand_center, regions):
    if hand_center is None or not regions:
        return regions[0] if regions else None
    return min(regions, key=lambda region: (region.center[0] - hand_center[0]) ** 2 + (region.center[1] - hand_center[1]) ** 2)
```

```python
selected_shadow = _select_shadow_for_hand(hand_center, shadow_result.regions)
shadow_center = selected_shadow.center if selected_shadow else None
shadow_vector = None if hand_center is None or shadow_center is None else (
    shadow_center[0] - hand_center[0],
    shadow_center[1] - hand_center[1],
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pc_hand_shadow_detection.py::test_combined_detector_prefers_shadow_near_hand_over_far_dark_region tests/test_pc_hand_shadow_detection.py::test_combined_detector_outputs_shadow_vector_and_selected_mask -q`
Expected: `2 passed`

### Task 4: Show the Selected Shadow Region in the PC Demo

**Files:**
- Modify: `/home/yzy/workspace/相机/scripts/run_pc_hand_shadow_demo.py`
- Test: `/home/yzy/workspace/相机/tests/test_pc_demo_cli.py`
- Doc: `/home/yzy/workspace/相机/README.md`

- [ ] **Step 1: Write the failing test**

```python
def test_draw_overlay_tints_shadow_mask_region():
    frame = np.zeros((80, 80, 3), dtype=np.uint8)
    shadow_mask = np.zeros((80, 80), dtype=np.uint8)
    shadow_mask[40:60, 40:60] = 255
    result = SimpleNamespace(
        hand_center=None,
        shadow_center=None,
        needs_relight=False,
        suggested_target_center=None,
        shadow_mask=shadow_mask,
    )

    overlay = _draw_overlay(frame, result)

    assert overlay[50, 50, 0] > 0
    assert overlay[5, 5, 0] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pc_demo_cli.py::test_draw_overlay_tints_shadow_mask_region -q`
Expected: `FAIL` because the old overlay only draws points and labels.

- [ ] **Step 3: Write minimal implementation**

```python
if getattr(result, "shadow_mask", None) is not None:
    mask = result.shadow_mask > 0
    blue = output[:, :, 0]
    blue[mask] = np.maximum(blue[mask], 160)
    output[:, :, 0] = blue
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pc_demo_cli.py::test_draw_overlay_tints_shadow_mask_region -q`
Expected: `1 passed`

### Task 5: Verify the Whole Increment

**Files:**
- Test: `/home/yzy/workspace/相机/tests/test_pc_demo_cli.py`
- Test: `/home/yzy/workspace/相机/tests/test_pc_hand_shadow_detection.py`
- Manual check: `/home/yzy/workspace/相机/scripts/run_pc_hand_shadow_demo.py`

- [ ] **Step 1: Run focused automated tests**

Run: `pytest tests/test_pc_demo_cli.py tests/test_pc_hand_shadow_detection.py -q`
Expected: all selected tests pass.

- [ ] **Step 2: Run one hardware probe**

Run: `python3 -c "import cv2; from scripts.run_pc_hand_shadow_demo import build_arg_parser, resolve_source; args=build_arg_parser().parse_args([]); source=resolve_source(args); cap=cv2.VideoCapture(source, cv2.CAP_V4L2 if isinstance(source, str) and source.startswith('/dev/video') else 0); ok, frame=cap.read() if cap.isOpened() else (False, None); print({'source': source, 'opened': cap.isOpened(), 'ok': ok, 'shape': None if frame is None else frame.shape}); cap.release()"`
Expected: source resolves to the RealSense color node and returns a color frame.
