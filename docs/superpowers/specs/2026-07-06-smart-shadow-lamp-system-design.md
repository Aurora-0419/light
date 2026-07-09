# Smart Shadow Lamp System Design

## Goal

Build a ROS2-oriented system structure for a smart shadowless lamp prototype, with current scope limited to camera perception and microphone plus voice control. Light execution and robot-arm motion remain out of scope for the current implementation but must have stable integration points.

## Scope

Current scope:

- define the long-term ROS2 package layout
- define shared message contracts
- create package boundaries for vision, speech, coordinator, light, and arm layers
- keep the existing `相机/` and `voice_control/` projects as the active implementation sources for now

Out of scope for this increment:

- migrating the current perception code into ROS2 packages
- migrating the current speech code into ROS2 packages
- implementing real light hardware control
- implementing real robot-arm motion control

## Architecture

The system is split into independent ROS2 packages linked through shared interfaces. `vision_perception` and `voice_control` publish structured state and commands. `system_coordinator` handles mode and routing decisions. `light_control` and `arm_control` are execution targets that stay decoupled from perception and speech internals.

## Workspace Layout

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

## Package Responsibilities

### shadow_lamp_interfaces

Owns the ROS message contracts. The source directory is `smart_shadow_lamp_ws/src/common_interfaces/`, but the ROS package name is `shadow_lamp_interfaces` to avoid collision with the ROS underlay metapackage named `common_interfaces`.

- `VisionState.msg`
- `VoiceCommand.msg`
- `SystemMode.msg`
- `LightCommand.msg`
- `ArmCommand.msg`

### vision_perception

Will wrap the current PC-first hand and shadow detection work from `相机/` and publish `/vision/state`.

### voice_control

Will wrap the current wake word and fixed command pipeline from `voice_control/` and publish `/voice/command`.

### system_coordinator

Maintains system mode and translates high-level state into future light or arm commands. It must stay thin and not absorb perception or speech logic.

### light_control

Future hardware-facing package for brightness, color temperature, and lighting modes.

### arm_control

Future hardware-facing package for lamp position adjustment through the robot arm.

## ROS Topics

- `/vision/state`
- `/voice/command`
- `/system/mode`
- `/light/command`
- `/arm/command`

## Message Principles

- use custom ROS messages instead of raw strings or ad hoc JSON
- keep message fields concrete and typed
- keep package-level dependencies one-directional through interfaces

## Migration Strategy

1. keep algorithm development in the existing projects until the behavior is stable
2. move ROS-facing publication logic into `smart_shadow_lamp_ws`
3. replace placeholder nodes with adapters around the existing code
4. later decide whether board-side execution, BPU conversion, or PC inference over Wi-Fi is the right deployment path

## Verification

The current increment is verified by filesystem tests that assert the full ROS2 workspace skeleton exists, including the shared message package and all package entry points.
