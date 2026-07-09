# smart_shadow_lamp_ws

ROS2 workspace skeleton for the smart shadowless lamp prototype.

## Goal

This workspace defines the long-term system structure for:

- visual perception
- voice control
- system coordination
- light control
- arm control

The current algorithm development still lives in the existing projects:

- `../camera/` for PC-first vision and hand-shadow detection
- `../voice_control/` for wake word and fixed-command speech control

This workspace gives those modules a stable ROS2 integration target.

## Layout

```text
smart_shadow_lamp_ws/
├── src/
│   ├── common_interfaces/
│   ├── vision_perception/
│   ├── voice_control/
│   ├── system_coordinator/
│   ├── light_control/
│   └── arm_control/
└── tests/
```

## Package Roles

- `common_interfaces`: source directory for the `shadow_lamp_interfaces` ROS package, which owns shared messages for perception, speech, mode, light, and arm commands.
- `vision_perception`: ROS wrapper target for the current `camera/` perception pipeline.
- `voice_control`: ROS wrapper target for the current `../voice_control/` speech pipeline.
- `system_coordinator`: thin orchestration layer for mode and command routing.
- `light_control`: future light execution package.
- `arm_control`: future robot-arm execution package.

## Notes

- This workspace is intentionally a skeleton. It sets the package boundaries and interface contracts first.
- The first migration step is now in place: `vision_perception` and `voice_control` contain thin bridge code that points to the existing `../camera/` and `../voice_control/` projects.
- The next migration step should replace the placeholder ROS nodes with fully parameterized adapters around the current PC demo and speech runner.
- Build and launch files are included as placeholders for later ROS2 integration.

## Build

On this machine, ROS Humble must be built with the system Python runtime instead of the current conda Python.

```bash
source /opt/ros/humble/setup.bash
export PATH="/usr/bin:/bin:$PATH"
colcon build
source install/setup.bash
```

## Simulation Startup Chain

Start the full simulation-first chain with OpenMANIPULATOR bringup, MoveIt Servo, visual bridge, coordinator, and arm control:

```bash
./scripts/run_shadow_lamp_sim.sh start_rviz:=false start_voice:=false
```

Notes:

- `start_rviz:=true` enables RViz on a machine with a desktop session.
- `start_voice:=true` also launches the voice bridge. On a machine without a working `arecord` device, it will keep warning but stay alive.
- The startup script adds a local compatibility library path for `moveit_servo` on this machine.
