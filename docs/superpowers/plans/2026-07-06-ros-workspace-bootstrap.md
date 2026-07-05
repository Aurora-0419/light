# ROS Workspace Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a ROS2 workspace skeleton that can later absorb the existing perception and speech projects without changing their current development flow.

**Architecture:** Use one top-level ROS2 workspace with a dedicated shared interface package and five focused Python packages. Keep the first increment light by creating stable package boundaries and placeholder nodes instead of migrating existing algorithms immediately. The source directory stays `src/common_interfaces`, but the ROS package name must be unique: `shadow_lamp_interfaces`.

**Tech Stack:** Python 3.10, ROS2 package skeletons, custom ROS messages, pytest

---

### Task 1: Add a failing workspace-structure test

**Files:**
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_workspace_layout.py`

- [ ] **Step 1: Write the failing test**

```python
def test_system_workspace_contains_expected_top_level_entries():
    expected = [
        ROOT / "README.md",
        ROOT / "src" / "common_interfaces",
        ROOT / "src" / "vision_perception",
        ROOT / "src" / "voice_control",
        ROOT / "src" / "system_coordinator",
        ROOT / "src" / "light_control",
        ROOT / "src" / "arm_control",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_workspace_layout.py -q`
Expected: `FAIL` because the workspace has not been scaffolded yet.

- [ ] **Step 3: Write minimal implementation**

```text
Create the top-level workspace directory, the README, and the package folders under src/.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_workspace_layout.py::test_system_workspace_contains_expected_top_level_entries -q`
Expected: `1 passed`

### Task 2: Add the shared interface package

**Files:**
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/common_interfaces/package.xml`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/common_interfaces/CMakeLists.txt`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/common_interfaces/msg/VisionState.msg`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/common_interfaces/msg/VoiceCommand.msg`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/common_interfaces/msg/SystemMode.msg`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/common_interfaces/msg/LightCommand.msg`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/common_interfaces/msg/ArmCommand.msg`

- [ ] **Step 1: Write the failing test**

```python
def test_common_interfaces_defines_core_messages():
    expected = {
        "VisionState.msg",
        "VoiceCommand.msg",
        "SystemMode.msg",
        "LightCommand.msg",
        "ArmCommand.msg",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_workspace_layout.py::test_common_interfaces_defines_core_messages -q`
Expected: `FAIL` because the message files do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```text
Create common_interfaces as an ament_cmake package and define the five shared message files.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_workspace_layout.py::test_common_interfaces_defines_core_messages -q`
Expected: `1 passed`

### Task 3: Add Python package skeletons for the five functional layers

**Files:**
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/vision_perception/*`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/voice_control/*`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/system_coordinator/*`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/light_control/*`
- Create: `/home/yzy/workspace/smart_shadow_lamp_ws/src/arm_control/*`

- [ ] **Step 1: Write the failing test**

```python
def test_python_packages_expose_minimal_ros_entrypoints():
    package_files = {
        "vision_perception": ["package.xml", "setup.py", "setup.cfg", "vision_perception/__init__.py"],
        "voice_control": ["package.xml", "setup.py", "setup.cfg", "voice_control/__init__.py"],
        "system_coordinator": ["package.xml", "setup.py", "setup.cfg", "system_coordinator/__init__.py"],
        "light_control": ["package.xml", "setup.py", "setup.cfg", "light_control/__init__.py"],
        "arm_control": ["package.xml", "setup.py", "setup.cfg", "arm_control/__init__.py"],
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_workspace_layout.py::test_python_packages_expose_minimal_ros_entrypoints -q`
Expected: `FAIL` because the package skeletons do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```text
Create each package as an ament_python skeleton with package.xml, setup.py, setup.cfg, resource marker, Python package directory, placeholder node, and launch file.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_workspace_layout.py::test_python_packages_expose_minimal_ros_entrypoints -q`
Expected: `1 passed`

### Task 4: Verify the full bootstrap

**Files:**
- Test: `/home/yzy/workspace/smart_shadow_lamp_ws/tests/test_workspace_layout.py`

- [ ] **Step 1: Run full workspace-structure verification**

Run: `pytest tests/test_workspace_layout.py -q`
Expected: all tests pass.

- [ ] **Step 2: Review the root README**

Run: `Read /home/yzy/workspace/smart_shadow_lamp_ws/README.md`
Expected: the file explains package roles, current migration status, and how the new workspace relates to `相机/` and `voice_control/`.
