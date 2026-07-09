# Smart Shadowless Lamp System

This repository contains the complete engineering workspace for the Smart Shadowless Lamp prototype system. It includes modules for visual perception, voice interaction, system coordination, light control, and robotic arm control. The system is entirely deployed and runs on the RDK X5 board, built upon ROS 2 Humble. It perceives hand and shadow states on the desk via a camera, recognizes voice commands via the on-board microphone, and uniformly publishes light and arm control commands through a central coordination node.

## Features Overview

- **Hand & Shadow Detection**: Detects hand positions, shadow positions on the desk, and determines if supplemental lighting is required.
- **Posture Reminder**: Detects shoulder posture based on human body keypoints and issues a reminder when an abnormal posture persists.
- **Voice Control**: Supports wake-word and fixed-command recognition, such as toggling tracking mode, turning lights on/off, and adjusting brightness or color temperature.
- **Light Control**: Drives WS2812 LEDs via on-board SPI, switching colors, brightness, and on/off states based on ROS commands.
- **Robotic Arm Control**: Converts high-level tracking commands into MoveIt Servo joint jog commands to drive the OpenMANIPULATOR-X, adjusting the lamp's pose.

## Directory Structure

```text
workspace/
├── camera/                    # On-board camera and hand/shadow detection algorithms
├── voice_control/             # Voice recognition, interaction logic, and local voice feedback resources
├── smart_shadow_lamp_ws/       # ROS 2 workspace, encapsulating functional nodes
│   ├── src/common_interfaces/  # Custom ROS 2 message interfaces
│   ├── src/vision_perception/  # Visual perception ROS 2 bridge node
│   ├── src/voice_control/      # Voice command and feedback ROS 2 bridge node
│   ├── src/system_coordinator/ # System coordination and decision-making node
│   ├── src/light_control/      # Light execution node
│   └── src/arm_control/        # Robotic arm execution node
└── open_manipulator/           # OpenMANIPULATOR-X, MoveIt, and Dynamixel related source code
```

## ROS 2 Node Communication Diagrams

### Perception and Decision Link

```text
camera / RealSense D435
        │
        ▼
vision_state_bridge  ── /vision/state ──▶ system_coordinator
```

`vision_state_bridge` reuses the hand, shadow, and posture detection logic from the `camera/` directory on the board, publishing `shadow_lamp_interfaces/msg/VisionState`. The message contains the hand center, shadow center, shadow area, whether fill light is needed, posture state, and abnormal posture type.

`system_coordinator` subscribes to `/vision/state` and publishes robotic arm control, light control, and voice feedback based on the current tracking status and visual results.

### Voice Command Link

```text
USB Microphone
   │
   ▼
voice_command_bridge ── /voice/command ──▶ system_coordinator
```

`voice_command_bridge` reuses the offline voice recognition and command parsing logic from `voice_control/`, publishing `shadow_lamp_interfaces/msg/VoiceCommand`. Commonly used commands include:

- `enable_tracking`
- `disable_tracking`
- `light_on`
- `light_off`
- `brightness_up`
- `brightness_down`
- `warm_light_mode`
- `cool_light_mode`

### Light Control Link

```text
system_coordinator ── /light/command ──▶ light_controller ──▶ WS2812 LED
```

`system_coordinator` generates `shadow_lamp_interfaces/msg/LightCommand` based on voice commands. `light_controller` subscribes to `/light/command`, converts the light mode into RGB frames, and outputs them to the WS2812 LED strip via SPI. If SPI initialization fails, it falls back to log output, making it convenient for debugging without hardware.

### Robotic Arm Control Link

```text
system_coordinator ── /arm/command ──▶ shadow_lamp_arm_controller ── /servo_node/delta_joint_cmds ──▶ MoveIt Servo
```

`system_coordinator` publishes `shadow_lamp_interfaces/msg/ArmCommand`. `shadow_lamp_arm_controller` converts yaw/pitch control variables into `control_msgs/msg/JointJog` and sends them to `/servo_node/delta_joint_cmds` of MoveIt Servo.

### Posture Voice Reminder Link

```text
vision_state_bridge ── /vision/state ──▶ system_coordinator ── /voice/feedback ──▶ voice_feedback_bridge ──▶ On-board WAV playback
```

Currently, the posture reminder only retains shoulder anomalies. Once the vision layer detects `shoulder_tilt` persisting beyond a specific threshold, `system_coordinator` publishes the text `请调整坐姿` ("Please adjust your posture") to `/voice/feedback`. `voice_feedback_bridge` subscribes to this topic and calls the local on-board feedback module to play `请调整坐姿.wav`.

## Custom Messages

Main message definitions are located in `smart_shadow_lamp_ws/src/common_interfaces/msg/`.

- `VisionState.msg`: Visual perception state, including fields for hand, shadow, and posture.
- `VoiceCommand.msg`: Voice command results, including wake word, command name, confidence, and raw text.
- `LightCommand.msg`: Light control instructions, including mode, brightness, color temperature, and switch state.
- `ArmCommand.msg`: Robotic arm control instructions, including mode, target point, and yaw/pitch control variables.
- `SystemMode.msg`: System mode state, including current mode, reason, and tracking switch state.

## Build Instructions

It is highly recommended to use the system Python to build the ROS 2 workspace to avoid ABI mismatch issues between conda's Python and ROS Humble.

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
export PATH="/usr/bin:/bin:$PATH"
colcon build
source install/setup.bash
```

## On-board Demo Startup

For the demo, all ROS 2 nodes run on the RDK X5 board. Before starting, navigate to the workspace and source the ROS 2 environment:

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
```

Start the vision node (you can open a preview window):

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch vision_perception vision_perception.launch.py use_depth_runtime:=true show_preview:=true preview_width:=1600 preview_height:=900 publish_period_sec:=0.05
```

Start the system coordinator node:

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run system_coordinator system_coordinator
```

Start the light controller:

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run light_control light_controller
```

Start voice feedback playback:

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run voice_control voice_feedback_bridge
```

If you also need to test on-board voice recognition, start the command bridge:

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run voice_control voice_command_bridge
```

## Common Debugging Commands

Check vision state:

```bash
ros2 topic echo /vision/state
```

Check voice commands:

```bash
ros2 topic echo /voice/command
```

Check light control commands:

```bash
ros2 topic echo /light/command
```

Check posture reminder text:

```bash
ros2 topic echo /voice/feedback
```

Manually trigger on-board posture reminder playback:

```bash
ros2 topic pub --once /voice/feedback std_msgs/msg/String "{data: '请调整坐姿'}"
```

## Current Implementation Notes

- The posture reminder currently only retains alerts for shoulder anomalies, and the broadcast text is `请调整坐姿` ("Please adjust your posture").
- The visual preview will display a shoulder keypoint count and draw purple shoulder points/lines when shoulders are detected.
- `voice_feedback_bridge` is responsible for playing feedback audio locally on the board, and `system_coordinator` publishes the reminder text via `/voice/feedback`.
- `light_controller` uses SPI to drive the WS2812 by default, falling back to standard ROS log output upon failure.
- `open_manipulator/` has been integrated into the main repository as a standard directory, allowing its source code to be browsed directly on GitHub.
