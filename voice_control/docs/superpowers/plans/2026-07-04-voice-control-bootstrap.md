# Voice Control Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent ROS-capable voice control package under `workspace/voice_control/` that supports microphone capture, wake phrase detection, fixed command parsing, and feedback output.

**Architecture:** Keep audio capture, speech parsing, command routing, and feedback in plain Python modules with a thin ROS2 wrapper. Prefer offline-friendly building blocks on `RDK X5`, use `arecord` for microphone input, and surface clear fallbacks when TTS or larger speech models are unavailable.

**Tech Stack:** Python 3.10, ROS2 Humble (`rclpy`), pytest, subprocess-based ALSA capture, optional `vosk`

## Global Constraints

- All source code lives under `/home/sunrise/workspace/voice_control/`.
- The package must remain independent from `/home/sunrise/workspace/相机/`.
- The first version must run on `RDK X5` and must not assume CUDA is available.
- Speech functionality should favor offline-capable components first, but may degrade gracefully when optional dependencies are missing.

---

### Task 1: Package Skeleton And Runtime Detection

**Files:**
- Create: `/home/sunrise/workspace/voice_control/README.md`
- Create: `/home/sunrise/workspace/voice_control/requirements.txt`
- Create: `/home/sunrise/workspace/voice_control/pytest.ini`
- Create: `/home/sunrise/workspace/voice_control/configs/default.yaml`
- Create: `/home/sunrise/workspace/voice_control/app/__init__.py`
- Create: `/home/sunrise/workspace/voice_control/app/runtime/__init__.py`
- Create: `/home/sunrise/workspace/voice_control/app/runtime/capabilities.py`
- Create: `/home/sunrise/workspace/voice_control/tests/test_capabilities.py`

### Task 2: Audio Capture Wrapper

**Files:**
- Create: `/home/sunrise/workspace/voice_control/app/audio/__init__.py`
- Create: `/home/sunrise/workspace/voice_control/app/audio/capture.py`
- Create: `/home/sunrise/workspace/voice_control/tests/test_capture.py`

### Task 3: Wake Phrase And Command Parsing

**Files:**
- Create: `/home/sunrise/workspace/voice_control/app/command/__init__.py`
- Create: `/home/sunrise/workspace/voice_control/app/command/schema.py`
- Create: `/home/sunrise/workspace/voice_control/app/command/parser.py`
- Create: `/home/sunrise/workspace/voice_control/tests/test_parser.py`

### Task 4: Offline Speech Bridge And Feedback

**Files:**
- Create: `/home/sunrise/workspace/voice_control/app/speech/__init__.py`
- Create: `/home/sunrise/workspace/voice_control/app/speech/vosk_bridge.py`
- Create: `/home/sunrise/workspace/voice_control/app/feedback/__init__.py`
- Create: `/home/sunrise/workspace/voice_control/app/feedback/feedback.py`
- Create: `/home/sunrise/workspace/voice_control/tests/test_feedback.py`

### Task 5: ROS2 Voice Node And CLI Entry

**Files:**
- Create: `/home/sunrise/workspace/voice_control/app/ros2_nodes/__init__.py`
- Create: `/home/sunrise/workspace/voice_control/app/ros2_nodes/voice_control_node.py`
- Create: `/home/sunrise/workspace/voice_control/scripts/__init__.py`
- Create: `/home/sunrise/workspace/voice_control/scripts/run_voice_control.py`
- Create: `/home/sunrise/workspace/voice_control/tests/test_cli.py`

### Task 6: Verification And Documentation

**Files:**
- Modify: `/home/sunrise/workspace/voice_control/README.md`

- [ ] Run `python3 -m pytest /home/sunrise/workspace/voice_control/tests -v`
- [ ] Run the CLI in dry-run mode
- [ ] Record a short microphone sample through the wrapper
- [ ] Smoke-test the ROS2 node entrypoint
- [ ] Document current dependency gaps and optional `vosk` model path setup
