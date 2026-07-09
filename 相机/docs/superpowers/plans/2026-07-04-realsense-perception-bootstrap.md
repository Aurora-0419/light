# RealSense Perception Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first-pass project under `workspace/相机/` that can open the Intel RealSense D435, display color/depth streams, run a minimal perception demo, and expose the same functionality through a ROS2 wrapper.

**Architecture:** Keep camera access and perception logic in plain Python modules so they can run directly on the RDK X5 and be tested without ROS2. Add thin ROS2 node entrypoints that reuse the same modules. Model/runtime selection must treat `RDK X5` as a `CPU/BPU` platform first and never assume CUDA.

**Tech Stack:** Python 3.10, OpenCV, pyrealsense2, NumPy, ROS2 Humble (`rclpy`), pytest

## Global Constraints

- All source code lives under `/home/sunrise/workspace/相机/`.
- The first version must run on `RDK X5` and must not assume CUDA is available.
- Runtime selection must surface when a feature should move to `BPU` later instead of silently assuming CPU is enough.
- The first perception demo should prioritize robustness over model sophistication.

---

### Task 1: Project Skeleton And Runtime Detection

**Files:**
- Create: `/home/sunrise/workspace/相机/README.md`
- Create: `/home/sunrise/workspace/相机/requirements.txt`
- Create: `/home/sunrise/workspace/相机/pytest.ini`
- Create: `/home/sunrise/workspace/相机/configs/default.yaml`
- Create: `/home/sunrise/workspace/相机/app/__init__.py`
- Create: `/home/sunrise/workspace/相机/app/runtime/__init__.py`
- Create: `/home/sunrise/workspace/相机/app/runtime/backend_selector.py`
- Create: `/home/sunrise/workspace/相机/tests/test_backend_selector.py`

**Interfaces:**
- Produces: `detect_runtime_capabilities() -> dict`
- Produces: `choose_perception_backend() -> dict`

- [ ] Step 1: Write the failing test with expected runtime keys and RDK X5 safety checks.
- [ ] Step 2: Run `pytest /home/sunrise/workspace/相机/tests/test_backend_selector.py -v` and verify failure.
- [ ] Step 3: Implement minimal project skeleton plus runtime detection that reports `cuda_available`, `horizon_bpu_available`, `recommended_backend`, and `warning`.
- [ ] Step 4: Run `pytest /home/sunrise/workspace/相机/tests/test_backend_selector.py -v` and verify pass.

### Task 2: RealSense Camera Module And Smoke Test

**Files:**
- Create: `/home/sunrise/workspace/相机/app/camera/__init__.py`
- Create: `/home/sunrise/workspace/相机/app/camera/realsense_camera.py`
- Create: `/home/sunrise/workspace/相机/tests/test_realsense_config.py`

**Interfaces:**
- Consumes: `configs/default.yaml`
- Produces: `RealSenseConfig`
- Produces: `RealSenseCamera.open() -> None`
- Produces: `RealSenseCamera.get_frames() -> dict`
- Produces: `RealSenseCamera.close() -> None`

- [ ] Step 1: Write a failing unit test for config parsing and frame dictionary shape using a mocked pipeline.
- [ ] Step 2: Run `pytest /home/sunrise/workspace/相机/tests/test_realsense_config.py -v` and verify failure.
- [ ] Step 3: Implement the RealSense wrapper with color/depth enable flags, frame conversion to NumPy, and safe cleanup.
- [ ] Step 4: Run `pytest /home/sunrise/workspace/相机/tests/test_realsense_config.py -v` and verify pass.

### Task 3: Minimal Perception Demo

**Files:**
- Create: `/home/sunrise/workspace/相机/app/perception/__init__.py`
- Create: `/home/sunrise/workspace/相机/app/perception/detector_base.py`
- Create: `/home/sunrise/workspace/相机/app/perception/hand_shadow_demo.py`
- Create: `/home/sunrise/workspace/相机/app/utils/__init__.py`
- Create: `/home/sunrise/workspace/相机/app/utils/draw.py`
- Create: `/home/sunrise/workspace/相机/tests/test_hand_shadow_demo.py`

**Interfaces:**
- Produces: `PerceptionResult`
- Produces: `HandShadowDemoDetector.process(color_frame: np.ndarray, depth_frame: np.ndarray | None) -> PerceptionResult`
- Produces: `draw_perception_overlay(frame: np.ndarray, result: PerceptionResult) -> np.ndarray`

- [ ] Step 1: Write a failing test for a synthetic foreground blob producing a non-empty detection result.
- [ ] Step 2: Run `pytest /home/sunrise/workspace/相机/tests/test_hand_shadow_demo.py -v` and verify failure.
- [ ] Step 3: Implement a lightweight perception demo using grayscale/HSV thresholding, contour filtering, and optional depth statistics.
- [ ] Step 4: Run `pytest /home/sunrise/workspace/相机/tests/test_hand_shadow_demo.py -v` and verify pass.

### Task 4: Direct Runner Script

**Files:**
- Create: `/home/sunrise/workspace/相机/scripts/run_realsense_demo.py`
- Create: `/home/sunrise/workspace/相机/tests/test_demo_cli.py`

**Interfaces:**
- Consumes: `RealSenseCamera`, `HandShadowDemoDetector`, `draw_perception_overlay`, `choose_perception_backend`
- Produces: CLI entrypoint for direct demo execution

- [ ] Step 1: Write a failing CLI test that validates argument parsing and dry-run mode.
- [ ] Step 2: Run `pytest /home/sunrise/workspace/相机/tests/test_demo_cli.py -v` and verify failure.
- [ ] Step 3: Implement the direct runner with `--dry-run`, `--no-depth`, `--save-frame`, and runtime warning output.
- [ ] Step 4: Run `pytest /home/sunrise/workspace/相机/tests/test_demo_cli.py -v` and verify pass.

### Task 5: ROS2 Wrapper Nodes

**Files:**
- Create: `/home/sunrise/workspace/相机/app/ros2_nodes/__init__.py`
- Create: `/home/sunrise/workspace/相机/app/ros2_nodes/camera_node.py`
- Create: `/home/sunrise/workspace/相机/app/ros2_nodes/perception_node.py`
- Create: `/home/sunrise/workspace/相机/scripts/run_ros2_perception_node.py`

**Interfaces:**
- Consumes: `RealSenseCamera`, `HandShadowDemoDetector`
- Produces: ROS2 node wrappers around direct modules

- [ ] Step 1: Implement thin ROS2 wrappers after the direct path works.
- [ ] Step 2: Launch the ROS2 wrapper locally to confirm import/runtime wiring.

### Task 6: End-To-End Verification On RDK X5

**Files:**
- Modify: `/home/sunrise/workspace/相机/README.md`

**Interfaces:**
- Consumes: all prior tasks
- Produces: documented verification commands and current platform caveats

- [ ] Step 1: Run the full unit test suite with `pytest /home/sunrise/workspace/相机/tests -v`.
- [ ] Step 2: Run the direct demo in dry-run mode.
- [ ] Step 3: Run the direct demo against the connected D435 for a short smoke test.
- [ ] Step 4: Run the ROS2 wrapper startup smoke test.
- [ ] Step 5: Update `README.md` with run commands, current RDK X5 caveats, and explicit note that heavier models may require conversion to `BPU` format.
