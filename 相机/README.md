# 相机

基于 `RDK X5` 的 `RealSense + 最小识别 demo` 工作空间。

## 当前功能

- `D435` 彩色流接入
- 最小前景/手部候选识别 demo
- `PC first` 手部 + 阴影联合检测模块
- 运行时后端判断，明确提示 `RDK X5` 上更重模型应转 `BPU`
- `ROS2` 薄包装节点入口

## 目录结构

- `app/camera/`: 相机接入
- `app/perception/`: 最小识别 demo
- `app/perception/hand_detector.py`: 可选 `MediaPipe Hands` 包装
- `app/perception/shadow_detector.py`: 规则法阴影检测
- `app/perception/combined_detector.py`: 手部 + 阴影联合结果
- `app/runtime/`: RDK X5 运行时与后端判断
- `app/ros2_nodes/`: ROS2 节点包装
- `scripts/`: 直接运行与 ROS2 启动入口
- `tests/`: 单元测试

## 运行方式

在 `workspace/相机/` 下执行。

### 1. 运行环境检查

```bash
python3 scripts/run_realsense_demo.py --dry-run
```

### 2. 真实相机单帧 demo

```bash
python3 -c "from pathlib import Path; from scripts.run_realsense_demo import run_demo; print(run_demo(save_frame=Path('/tmp/opencode/realsense_demo_frame.png')))"
```

### 3. ROS2 感知节点

```bash
source /opt/tros/humble/setup.bash
python3 scripts/run_ros2_perception_node.py
```

### 4. 测试

```bash
python3 -m pytest tests -v
```

### 5. PC 手部 + 阴影联合 demo

建议先在电脑上安装依赖：

```bash
pip install mediapipe opencv-python numpy
```

然后运行：

```bash
python3 scripts/run_pc_hand_shadow_demo.py
```

默认会优先自动选择 `RealSense D435` 的彩色相机节点；如果没有检测到可用的 `RealSense` 彩色节点，才回退到电脑默认摄像头。
启动时会打印实际打开的源，例如 `opening source: /dev/video6`。
当前窗口中的蓝色覆盖区域表示被选中的纸面阴影候选，选择逻辑会优先贴近检测到的人手，而不是单纯选择画面里最大的黑块。

如果要明确使用 `RealSense D435` 的彩色相机，不要用默认 `--webcam`，直接指定设备：

```bash
python3 scripts/run_pc_hand_shadow_demo.py --camera /dev/video6
```

如果要强制使用电脑默认摄像头：

```bash
python3 scripts/run_pc_hand_shadow_demo.py --webcam
```

或者：

```bash
python3 scripts/run_pc_hand_shadow_demo.py --video your_video.mp4
```

## RDK X5 约束

- 当前工程默认把 `RDK X5` 视为 `CPU/BPU` 平台，不假设 `CUDA` 可用。
- 当前 `D435` 在这块板上，`pyrealsense2` 路径不够稳定，因此代码默认优先走更稳的 `V4L2` 彩色流路径。
- 这意味着当前第一版 demo 重点是 `彩色流 + 最小识别`，而不是完整 `RealSense depth pipeline`。
- 更重的检测/分割模型不应默认直接压在 `CPU` 上跑；如果需要部署到板端，应优先评估并转换为地平线 `BPU` 支持格式。

## 后续建议

- 当前最推荐先在 `PC` 上跑通 `MediaPipe Hands + OpenCV 阴影检测`，确认效果。
- 之后再二选一：
  - 把手部模型迁移到 `RDK X5`，评估并转换为 `BPU`
  - 保持 `PC推理 + Wi-Fi回传结果` 给 `RDK X5`
- 若你要接灯控或机械臂，可直接在当前 `ROS2` 包装层上继续扩展。
