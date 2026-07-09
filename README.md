# 智能无影灯系统

本仓库是智能无影灯原型系统的完整工程工作区，包含视觉感知、语音交互、系统协调、灯光控制和机械臂控制等模块。系统基于 ROS2 Humble 构建，通过相机感知桌面手部与阴影状态，通过语音命令切换工作模式，并由协调节点统一发布灯光与机械臂控制指令。

## 功能概览

- **手部与阴影检测**：识别手部位置、纸面阴影位置和是否需要补光。
- **姿态提醒**：基于人体关键点检测肩膀姿态，持续异常时发布提醒。
- **语音控制**：支持唤醒词和固定命令识别，例如跟踪模式开关、灯光开关、亮度和色温切换。
- **灯光控制**：板端通过 WS2812 SPI 驱动灯光，根据 ROS 指令切换颜色、亮度和开关状态。
- **机械臂控制**：将高层跟踪命令转换为 MoveIt Servo joint jog 指令，驱动 OpenMANIPULATOR-X 调整灯具姿态。

## 目录结构

```text
workspace/
├── camera/                    # PC-first 相机与手影检测算法
├── voice_control/             # 语音识别、交互逻辑和本地语音反馈资源
├── smart_shadow_lamp_ws/       # ROS2 工作区，封装各功能节点
│   ├── src/common_interfaces/  # 自定义 ROS2 消息接口
│   ├── src/vision_perception/  # 视觉感知 ROS2 桥接节点
│   ├── src/voice_control/      # 语音命令与反馈 ROS2 桥接节点
│   ├── src/system_coordinator/ # 系统协调与决策节点
│   ├── src/light_control/      # 灯光执行节点
│   └── src/arm_control/        # 机械臂执行节点
└── open_manipulator/           # OpenMANIPULATOR-X、MoveIt 和 Dynamixel 相关源码
```

## ROS2 节点通信图说明

### 感知与决策链路

```text
camera / RealSense D435
        │
        ▼
vision_state_bridge  ── /vision/state ──▶ system_coordinator
```

`vision_state_bridge` 从 `camera/` 中复用手部、阴影和姿态检测逻辑，发布 `shadow_lamp_interfaces/msg/VisionState`。消息包含手部中心、阴影中心、阴影面积、是否需要补光、姿态状态和姿态异常类型。

`system_coordinator` 订阅 `/vision/state` 后，根据当前跟踪状态和视觉结果发布机械臂控制、灯光控制和语音反馈。

### 语音命令链路

```text
USB 麦克风
   │
   ▼
voice_command_bridge ── /voice/command ──▶ system_coordinator
```

`voice_command_bridge` 复用 `voice_control/` 的离线语音识别与命令解析逻辑，发布 `shadow_lamp_interfaces/msg/VoiceCommand`。常用命令包括：

- `enable_tracking`
- `disable_tracking`
- `light_on`
- `light_off`
- `brightness_up`
- `brightness_down`
- `warm_light_mode`
- `cool_light_mode`

### 灯光控制链路

```text
system_coordinator ── /light/command ──▶ light_controller ──▶ WS2812 LED
```

`system_coordinator` 根据语音命令生成 `shadow_lamp_interfaces/msg/LightCommand`。`light_controller` 订阅 `/light/command` 后，将灯光模式转换为 RGB 帧，并通过 SPI 输出到 WS2812 灯带。SPI 初始化失败时会退回日志输出，便于无硬件环境调试。

### 机械臂控制链路

```text
system_coordinator ── /arm/command ──▶ shadow_lamp_arm_controller ── /servo_node/delta_joint_cmds ──▶ MoveIt Servo
```

`system_coordinator` 发布 `shadow_lamp_interfaces/msg/ArmCommand`，`shadow_lamp_arm_controller` 将 yaw/pitch 控制量转换为 `control_msgs/msg/JointJog`，再发送到 MoveIt Servo 的 `/servo_node/delta_joint_cmds`。

### 姿态语音提醒链路

```text
vision_state_bridge ── /vision/state ──▶ system_coordinator ── /voice/feedback ──▶ voice_feedback_bridge ──▶ 板端 wav 播放
```

当前姿态提醒只保留肩膀异常。视觉层检测到 `shoulder_tilt` 并持续超过阈值后，`system_coordinator` 发布 `/voice/feedback` 文本 `请调整坐姿`。板端 `voice_feedback_bridge` 订阅该话题，并调用板端本地反馈模块播放 `请调整坐姿.wav`。

## 自定义消息

主要消息定义位于 `smart_shadow_lamp_ws/src/common_interfaces/msg/`。

- `VisionState.msg`：视觉感知状态，包括手部、阴影和姿态字段。
- `VoiceCommand.msg`：语音命令结果，包括唤醒词、命令名、置信度和原始文本。
- `LightCommand.msg`：灯光控制指令，包括模式、亮度、色温和开关状态。
- `ArmCommand.msg`：机械臂控制指令，包括模式、目标点和 yaw/pitch 控制量。
- `SystemMode.msg`：系统模式状态，包括当前模式、原因和跟踪开关状态。

## 构建

建议使用系统 Python 构建 ROS2 工作区，避免 conda Python 与 ROS Humble ABI 不匹配。

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
export PATH="/usr/bin:/bin:$PATH"
colcon build
source install/setup.bash
```

## 演示启动方式

演示时可以将视觉和系统协调放在电脑端，将灯光控制和语音播放放在板端。电脑和板端需要处于相同 ROS Domain，并能通过 DDS 互相发现。

### 电脑端

启动视觉节点，可打开预览窗口：

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
export PATH="/usr/bin:/bin:$PATH"
source install/setup.bash
ros2 launch vision_perception vision_perception.launch.py use_depth_runtime:=true show_preview:=true preview_width:=1600 preview_height:=900 publish_period_sec:=0.05
```

启动系统协调节点：

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
export PATH="/usr/bin:/bin:$PATH"
source install/setup.bash
ros2 run system_coordinator system_coordinator
```

### 板端

启动灯光控制：

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run light_control light_controller
```

启动语音反馈播放：

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run voice_control voice_feedback_bridge
```

如果还需要测试板端语音识别，再启动：

```bash
cd ~/workspace/smart_shadow_lamp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run voice_control voice_command_bridge
```

## 常用调试命令

查看视觉状态：

```bash
ros2 topic echo /vision/state
```

查看语音命令：

```bash
ros2 topic echo /voice/command
```

查看灯光控制：

```bash
ros2 topic echo /light/command
```

查看姿态提醒文本：

```bash
ros2 topic echo /voice/feedback
```

手动触发板端姿态提醒播放：

```bash
ros2 topic pub --once /voice/feedback std_msgs/msg/String "{data: '请调整坐姿'}"
```

## 当前实现说明

- 姿态提醒目前只保留肩膀异常提醒，播报文本为 `请调整坐姿`。
- 视觉预览会显示肩膀关键点计数，并在检测到肩点时绘制紫色肩点和肩线。
- `voice_feedback_bridge` 负责板端播放反馈音频，电脑端 `system_coordinator` 只发布 `/voice/feedback` 文本。
- `light_controller` 默认使用 SPI 驱动 WS2812，失败时回退到日志输出。
- `open_manipulator/` 已作为普通目录纳入主仓库，GitHub 上可直接浏览源码。
