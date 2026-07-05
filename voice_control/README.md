# voice_control

独立的语音控制 ROS 功能包工作空间。

## 当前功能

- `USB` 麦克风录音封装，基于 `arecord`
- 唤醒词与固定指令解析
- 本地 `Vosk` 中文小模型接入
- TTS 不可用时自动降级为终端文本反馈
- `ROS2` 节点封装，发布 `voice/command`

## 目录结构

- `app/audio/`: 录音封装
- `app/command/`: 唤醒词与固定指令解析
- `app/speech/`: 本地离线识别桥接
- `app/feedback/`: TTS/文本反馈
- `app/ros2_nodes/`: ROS2 节点包装
- `scripts/`: CLI 与 ROS2 启动入口
- `models/`: 本地离线语音模型
- `tests/`: 单元测试

## 已配置能力

- 平台：`RDK X5`
- 录音设备：`plughw:0,0`
- 本地离线识别：`Vosk`
- 本地中文模型：`models/vosk-model-small-cn -> vosk-model-small-cn-0.22`
- TTS：当前未检测到 `espeak/espeak-ng`，所以默认走文本反馈

## 支持的固定指令

- `你好小灯 开启跟踪模式`
- `你好小灯 关闭跟踪模式`
- `你好小灯 切换暖光模式`
- `你好小灯 切换冷光模式`

## 运行方式

在 `workspace/voice_control/` 下执行。

### 1. 运行环境检查

```bash
python3 scripts/run_voice_control.py --dry-run
```

### 2. 单次录音 + 本地识别

```bash
python3 scripts/run_voice_control.py --once
```

### 3. ROS2 节点

```bash
source /opt/tros/humble/setup.bash
python3 scripts/run_voice_control.py
```

### 4. 测试

```bash
python3 -m pytest tests -v
```

## 当前限制

- 第一版重点是 `唤醒词 + 固定指令`，不是自由对话助手。
- 当前唤醒是通过识别文本里是否包含 `你好小灯` 实现，不是单独训练的低功耗唤醒网络。
- 如果后面要做更强的实时唤醒或更复杂的本地语音识别，需要继续评估更合适的模型和是否要转到 `BPU` 支持格式。
- 当前没有本地 TTS 引擎，所以反馈默认输出到终端；后续可接 `espeak-ng` 或独立 TTS 服务。
