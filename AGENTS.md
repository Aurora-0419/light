# AGENTS.md — Smart Shadowless Lamp System

> **Last updated:** 2026-07-06
> **Platform:** RDK X5 (deployment target), PC (development)
> **ROS version:** Humble (system Python 3.10 required)

---

## Project Overview

A smart shadowless lamp prototype for study/work scenarios. The system uses a D435 camera for perception, a microphone for voice commands, and a 6-axis OpenMANIPULATOR-X robotic arm to adjust lamp direction based on detected hand shadows. Additional features include posture reminders during study.

**Competition narrative:** Visual + voice + robotic-arm smart shadowless lamp.

---

## Workspace Layout

```text
/home/yzy/workspace/
├── camera/                        # PC-first vision: hand + shadow detection
├── voice_control/                  # Wake word + fixed-command speech pipeline
├── open_manipulator/               # OpenMANIPULATOR-X ROS2 workspace (external, copied in)
├── smart_shadow_lamp_ws/           # Main ROS2 system workspace (our integration layer)
├── docs/
│   └── superpowers/
│       ├── specs/                  # Design documents
│       └── plans/                  # Implementation plans
└── AGENTS.md                       # This file
```

---

## Package Map (smart_shadow_lamp_ws)

| Package | Source Dir | Role | Status |
|---------|-----------|------|--------|
| `shadow_lamp_interfaces` | `src/common_interfaces/` | Shared ROS messages | Done |
| `vision_perception` | `src/vision_perception/` | Camera + hand/shadow bridge | Done |
| `voice_control` | `src/voice_control/` | Voice bridge | Done |
| `system_coordinator` | `src/system_coordinator/` | Mode, decision, posture reminder | Done |
| `light_control` | `src/light_control/` | Light hardware control | Skeleton |
| `arm_control` | `src/arm_control/` | Arm → MoveIt Servo bridge | Done |

**ROS Topics:**

- `/vision/state` (`shadow_lamp_interfaces/VisionState`)
- `/voice/command` (`shadow_lamp_interfaces/VoiceCommand`)
- `/system/mode` (`shadow_lamp_interfaces/SystemMode`)
- `/arm/command` (`shadow_lamp_interfaces/ArmCommand`)
- `/light/command` (`shadow_lamp_interfaces/LightCommand`)
- `/servo_node/delta_joint_cmds` (`control_msgs/JointJog`)

---

## Vision Package (`camera/`)

Location: `/home/yzy/workspace/camera/`

**Capabilities:**
- D435 camera access (auto-selects correct `/dev/video6` RealSense color node)
- Hand detection via `MediaPipe Hands`
- Paper shadow detection (rule-based, bright surface → relative darkening)
- Hand-shadow association (selects shadow region nearest to hand)
- Outputs: hand_center, shadow_center, shadow_area, shadow_mask, needs_relight, shadow_vector

**Key files:**
- `scripts/run_pc_hand_shadow_demo.py` — main PC demo entry (supports `--camera`, `--webcam`, `--video`)
- `app/perception/combined_detector.py` — combines hand + shadow results
- `app/perception/shadow_detector.py` — paper-region shadow detection
- `app/perception/hand_detector.py` — MediaPipe Hands wrapper

**Test status:** `pytest tests -q` → 21 passed

---

## Voice Package (`voice_control/`)

Location: `/home/yzy/workspace/voice_control/`

**Capabilities:**
- USB mic recording via `arecord`
- Wake word: `你好小灯`
- Local Vosk Chinese model for offline recognition
- Fixed command parsing
- Commands: `enable_tracking`, `disable_tracking`, `warm_light_mode`, `cool_light_mode`
- TTS fallback: prints text to terminal when no `espeak` available

**Key files:**
- `scripts/run_voice_control.py` — CLI + ROS entry
- `app/command/parser.py` — command pattern matching
- `app/ros2_nodes/voice_control_node.py` — existing ROS node (publishes `String` on `voice/command`)

---

## OpenMANIPULATOR-X (`open_manipulator/`)

Location: `/home/yzy/workspace/open_manipulator/`

A full ROS2 workspace for the 4-DOF OpenMANIPULATOR-X robotic arm.

**Packages:**
- `open_manipulator_x_bringup` — hardware / Gazebo / fake launch
- `open_manipulator_x_description` — URDF, meshes, ros2_control config
- `open_manipulator_x_moveit_config` — MoveIt planning, Servo config
- `open_manipulator_x_teleop` — keyboard teleop via MoveIt Servo
- `open_manipulator_x_gui` — Qt GUI with MoveGroupInterface
- `open_manipulator_x_playground` — hello_moveit example

**Control interfaces:**
- MoveIt `arm` planning group + `gripper` planning group
- `arm_controller`: `joint_trajectory_controller/JointTrajectoryController` (joints 1-4)
- `gripper_controller`: `position_controllers/GripperActionController`
- MoveIt Servo: `/servo_node/delta_joint_cmds` (JointJog), `/servo_node/start_servo` (Trigger)
- Hardware: `dynamixel_hardware_interface/DynamixelHardware` via `/dev/ttyUSB0`

**Simulation launch (standalone):**
```bash
conda deactivate
source /opt/ros/humble/setup.bash
source /home/yzy/workspace/open_manipulator/install/setup.bash
ros2 launch open_manipulator_x_bringup gazebo.launch.py start_rviz:=true
```

---

## System Simulation Chain

**Full launch (one command):**
```bash
cd /home/yzy/workspace/smart_shadow_lamp_ws
./scripts/run_shadow_lamp_sim.sh start_rviz:=false start_voice:=false
```

**What it launches:**
- OpenMANIPULATOR Gazebo + controllers
- MoveIt Servo node
- `vision_state_bridge` → `/vision/state`
- `system_coordinator` → `/system/mode`, `/arm/command`
- `arm_controller` (ours, named `shadow_lamp_arm_controller`) → `/servo_node/delta_joint_cmds`

**Control chain:**
```
/vision/state → system_coordinator → /arm/command → arm_control → /servo_node/delta_joint_cmds → Gazebo joints move
```

---

## Shadow → Arm Direction Logic

**File:** `smart_shadow_lamp_ws/src/system_coordinator/system_coordinator/decision.py`

Current approach:
1. Computes `dx = shadow_x - hand_x`, `dy = shadow_y - hand_y`
2. Normalizes by `image_width/4` → `yaw`, `image_height/4` → `pitch`
3. Deadband of 15px suppresses small noise
4. Outputs `ArmCommandPayload` with `mode=shadow_follow`, `yaw`, `pitch`

**File:** `smart_shadow_lamp_ws/src/arm_control/arm_control/servo_mapper.py`

Maps `yaw` → `joint1` velocity, `pitch` → `joint2` velocity with configurable `velocity_scale` (default 0.6).

**Important:** This is a heuristic directional adjustment. The end effector is now a lamp plane (not a gripper), but the control still operates on joint1+joint2 proxy. True lamp-pose control is future work.

---

## Posture Reminder

**Detection:** `smart_shadow_lamp_ws/src/vision_perception/vision_perception/posture_detector.py`
- Uses `MediaPipe Pose` (optional, degrades gracefully if unavailable)
- Evaluates landmarks: nose, shoulders, hips
- Three issues: `shoulder_tilt`, `body_lean_left_right`, `head_too_close`

**Reminder:** `smart_shadow_lamp_ws/src/system_coordinator/system_coordinator/posture_reminder.py`
- Persistence: 4s before trigger (configurable)
- Cooldown: 45s between same-issue reminders (configurable)
- Reminder texts: `请坐正一点`, `请不要离桌面太近`, `请调整一下肩膀姿势`

**Feedback output:** `smart_shadow_lamp_ws/src/system_coordinator/system_coordinator/feedback_adapter.py`
- Reuses `voice_control/app/feedback/feedback.py`'s `speak_or_print()`
- Direct call via lazy module loading, not through `/voice/command` topic

---

## Shared Messages (shadow_lamp_interfaces)

**VisionState.msg** fields:
```
builtin_interfaces/Time stamp
bool hand_detected
float32 hand_center_x/y
bool shadow_detected
float32 shadow_center_x/y
float32 shadow_area
bool needs_relight
float32 suggested_target_x/y
string source_frame
bool posture_ok
string posture_issue
float32 posture_score
```

**VoiceCommand.msg** fields:
```
builtin_interfaces/Time stamp
string wake_word
string command
float32 confidence
string raw_text
bool confirmed
```

**SystemMode.msg:** `mode`, `reason`, `tracking_enabled`

**ArmCommand.msg:** `mode`, `follow_enabled`, `target_x/y/z`, `yaw`, `pitch`

**LightCommand.msg:** `mode`, `brightness`, `color_temperature`, `enabled`, `target_x/y`

---

## Build and Run

### Build smart_shadow_lamp_ws

```bash
cd /home/yzy/workspace/smart_shadow_lamp_ws
rm -rf build install log
source /opt/ros/humble/setup.bash
export PATH="/usr/bin:/bin:$PATH"   # MUST use system Python 3.10, NOT conda 3.12
colcon build
source install/setup.bash
```

### Run tests

```bash
# smart_shadow_lamp_ws
cd /home/yzy/workspace/smart_shadow_lamp_ws && pytest tests -q

# camera/
cd /home/yzy/workspace/camera && python3 -m pytest tests -q

# voice_control/
cd /home/yzy/workspace/voice_control && python3 -m pytest tests -v
```

### Test status
- `smart_shadow_lamp_ws`: 35 passed
- `camera/`: 21 passed

---

## Environment Constraints

1. **Python version:** ROS Humble requires system Python 3.10. The default conda Python 3.12 will break `rclpy` and `colcon build`. Always `export PATH="/usr/bin:/bin:$PATH"` before building or launching.

2. **ROS daemon:** Use `source /opt/ros/humble/setup.bash && ros2 daemon stop` before clean launches to avoid stale discovery state.

3. **OpenMANIPULATOR runtime:** Must source `/home/yzy/workspace/open_manipulator/install/setup.bash` BEFORE sourcing `smart_shadow_lamp_ws/install/setup.bash`.

4. **Servo compatibility:** This machine has `libgeometric_shapes.so.2.3.2` but `servo_node_main` requires `2.3.4`. The startup script `run_shadow_lamp_sim.sh` auto-creates a symlink in `smart_shadow_lamp_ws/compat_lib/`.

5. **Voice hardware:** `arecord` device `plughw:0,0` may not exist on this machine. When absent, the voice bridge will log warnings but stay alive.

---

## Current Algorithm Summary

### Shadow detection pipeline
1. Find bright paper region (gray > 140 threshold)
2. Within paper region, find areas darker than paper reference (75th percentile minus 60)
3. Filter out pure black objects (below `min_shadow_intensity=35`)
4. Select the shadow candidate nearest to detected hand
5. Output: shadow_center, shadow_mask, shadow_vector

### Arm control pipeline
1. Vision publishes `/vision/state`
2. Coordinator computes `yaw/pitch` from hand-to-shadow offset
3. `ArmCommand` published to `/arm/command`
4. `arm_control` maps to `JointJog` on `/servo_node/delta_joint_cmds`
5. MoveIt Servo drives Gazebo joints

### Posture reminder pipeline
1. Vision includes posture state in `/vision/state` (optional, via MediaPipe Pose)
2. Coordinator tracks posture issue persistence
3. If issue persists >4s and cooldown >45s, triggers `speak_or_print()`

---

## What's NOT Done Yet

- Real light hardware control (`light_control` is skeleton)
- Real arm optimal lamp-pose control (not just joint1+joint2 proxy)
- Voice live hardware validation (mic device status TBD)
- Posture threshold tuning with real camera feed
- True lamp end-effector orientation control (current uses heuristic joint mapping)
- BPU migration for RDK X5
- Wi-Fi inference relay pattern
- System-level launch that includes voice bridge by default

---

## High-Value Additions

These are recommended competition-facing features that are relatively easy to add and give strong demo value even if the judges do not inspect algorithm depth.

1. **System status panel**
   - Show current mode, hand detected, shadow detected, posture status, arm follow status, latest voice command, and whether relight is needed.
   - Best option for making the system's internal state visible during a demo.

2. **Study mode / timer / long-session reminder**
   - A high-level mode that combines shadow follow, posture reminder, and timed rest reminders.

3. **Absence detection / auto standby**
   - If no hand or user activity is detected for a while, stop tracking and enter a low-power or standby state.

4. **Voice status query**
   - Add commands that let the user ask for current mode, current shadow state, or posture status.

5. **Shadow improvement metric**
   - Record and display before/after shadow area to explain that the system is doing closed-loop shadow reduction.

6. **Demo mode / scripted mode**
   - A deterministic mode that simulates visual events and commands, useful when live sensor conditions are unstable.

7. **Lighting modes**
   - Reading mode, eye-care mode, focus mode, night mode, and demo mode, once `light_control` is implemented.

8. **RGB status light**
   - Use RGB only as a status indicator, not as the main illumination source.

9. **Safety constraints**
   - Speed limits, workspace limits, and a stop command for the arm.

10. **Study report**
   - Session duration, number of posture reminders, number of shadow corrections, and number of voice interactions.

**Recommended next showcase feature:**

- Build a **system status panel plus demo mode** first. This gives the strongest presentation benefit with the least risk.
