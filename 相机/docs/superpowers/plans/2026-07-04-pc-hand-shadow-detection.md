# PC Hand Shadow Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a PC-first hand and shadow detection path that can run on a laptop first, show visual results, and later be moved to RDK X5 through BPU conversion or Wi-Fi result relay.

**Architecture:** Keep the PC detector independent from the existing lightweight RDK demo. Use MediaPipe Hands when available for high-quality hand landmarks, OpenCV rules for shadow detection, and a combined result schema that can be consumed by later light/arm control packages. Preserve a fallback path when MediaPipe is not installed so tests and board-side scaffolding still run.

**Tech Stack:** Python 3.10, OpenCV, NumPy, optional MediaPipe, pytest

## Global Constraints

- All code for this increment lives under `/home/sunrise/workspace/相机/`.
- PC-first quality and speed are prioritized over pure RDK X5 local execution.
- RDK X5 deployment remains supported later through either BPU conversion or Wi-Fi result relay.
- Do not mix this with `voice_control/`; keep packages independent and communicate later through ROS topics or network messages.

---

### Task 1: Detection Result Schemas

- Create hand, shadow, and combined result dataclasses.
- Tests verify these schemas expose centers, boxes, confidence, area, and recommended control hints.

### Task 2: MediaPipe Hand Detector Wrapper

- Implement optional MediaPipe wrapper.
- If MediaPipe is unavailable, return a clear unavailable result instead of crashing.
- Tests use an injected fake backend so PC behavior is testable on RDK X5.

### Task 3: OpenCV Shadow Detector

- Implement ROI-based brightness drop detection.
- Tests use synthetic bright work surface with dark region.

### Task 4: Combined Hand + Shadow Detector

- Combine hand and shadow outputs into one control-oriented result.
- Produce suggested target center and `needs_relight` flag.

### Task 5: PC Demo Script

- Add `scripts/run_pc_hand_shadow_demo.py` with webcam/video input, overlay, and optional frame save.
- README documents PC install path: `pip install mediapipe opencv-python numpy`.

### Task 6: Migration Notes

- Document how this can later be deployed as BPU model output or Wi-Fi relay result.
