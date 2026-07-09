# Posture Reminder Design

## Goal

Add a posture-reminder capability to the smart shadow lamp system so the camera can detect obviously poor study posture and the system can issue throttled reminders without interfering with the existing shadow-follow and voice-command architecture.

## Scope

This increment adds a new perception result and reminder path for study posture.

In scope:

- detect coarse posture problems from a fixed camera view
- publish posture state together with the existing vision state
- let the coordinator decide when a reminder should be triggered
- keep reminder output separate from lamp-follow logic

Out of scope:

- medical-grade posture evaluation
- personalized body calibration
- direct mechanical-arm correction from posture state
- replacing the current shadow-follow logic

## Primary Use Case

The user is reading or doing homework under the smart lamp. If the user gradually leans too far, tilts strongly to one side, or moves their head too close to the work surface for several seconds, the system reminds them by voice or text.

## Approach

Use a PC-first posture detector based on body keypoints rather than a new heavy model.

Recommended method:

- keep the current hand and shadow detection path intact
- add an upper-body posture detector using `MediaPipe Pose`
- evaluate a small number of rule-based posture checks from landmarks
- publish a compact posture status in the same `VisionState` message family
- let `system_coordinator` apply persistence and cooldown before issuing reminders

This keeps the new feature consistent with the current project strategy: fast feedback on PC first, clear logic, and later optional migration to board-side inference or offboard PC inference.

## Why This Approach

This posture feature shares the same camera and the same reminder/output path as the current system, but it should remain logically independent from lamp-follow control.

Rule-based posture evaluation is appropriate here because:

- the scene is controlled
- the camera viewpoint is relatively fixed
- the desired reminder categories are coarse, not medical
- the implementation cost is much lower than training a classifier

## Posture States

First version should only classify three coarse issues:

1. `body_lean_left_right`
   The torso center is significantly offset relative to the study area or shoulder center line.

2. `head_too_close`
   The head appears too low or too close relative to shoulders and torso, consistent with leaning too near the desk.

3. `shoulder_tilt`
   The shoulder line angle exceeds a configured threshold for a sustained period.

If none of these fire, posture is considered acceptable.

## Detection Signals

The detector should primarily use:

- nose
- left and right shoulder
- left and right ear if available
- left and right hip if available

Derived signals:

- shoulder line angle
- torso center offset
- nose-to-shoulder vertical relation
- shoulder-to-hip body axis tilt

The exact thresholds should be configurable and treated as scene-specific.

## Vision Output Contract

Extend the vision-side state with three posture fields:

- `posture_ok: bool`
- `posture_issue: string`
- `posture_score: float`

Semantics:

- `posture_ok` is `true` when no configured issue is active
- `posture_issue` is one of the supported issue names or empty string
- `posture_score` is a normalized severity score for the active issue, used only for debugging and tuning in the first version

These fields should be added to the shared ROS message package so downstream packages do not need ad hoc side channels.

## Coordinator Behavior

`system_coordinator` should not remind immediately on one bad frame.

It should apply:

- persistence window: posture issue must stay active for several seconds before reminder
- cooldown window: once reminded, the same issue should not retrigger immediately
- mode guard: reminders should only happen when the system is in a user-active mode, not during startup or clearly invalid tracking states

This is critical to avoid a noisy system.

## Reminder Output

First version reminder path:

- publish a reminder intent inside coordinator logic
- log or print a readable message first
- later connect that same reminder intent to TTS or spoken feedback

Suggested first reminder messages:

- `请坐正一点`
- `请不要离桌面太近`
- `请调整一下肩膀姿势`

The exact spoken phrase should stay outside the detector logic.

## Package Boundaries

### vision_perception

- add posture detector module
- convert posture result into extended `VisionState`
- keep detector independent from hand-shadow control code

### shadow_lamp_interfaces

- extend `VisionState.msg` with posture fields

### system_coordinator

- read posture state
- manage persistence and cooldown
- decide whether to issue reminder intent

### voice_control

- no new recognition requirement for this increment
- later may consume reminder intent for spoken playback

## Failure Handling

If pose landmarks are unavailable:

- posture detection should report neutral or unavailable state
- the system must not emit posture reminders based on missing landmarks
- lamp-follow and shadow detection should continue working independently

If posture landmarks flicker:

- persistence logic in the coordinator should suppress spurious reminders

## Testing Strategy

Tests should focus on deterministic logic, not on camera hardware.

Required test layers:

- posture rule evaluation on synthetic or mocked landmarks
- message mapping into `VisionState`
- coordinator persistence and cooldown logic
- no-regression checks for existing hand-shadow bridge behavior

Manual verification:

- run on PC camera feed
- simulate left lean, right lean, near-head posture, and normal posture
- confirm reminders do not spam continuously

## Risks

1. Camera placement sensitivity
   Thresholds may need tuning based on angle and distance.

2. Pose landmark instability
   Low light or partial occlusion may reduce reliability.

3. Reminder fatigue
   Without cooldown and persistence, the feature becomes annoying quickly.

## Implementation Sequence

1. Add posture detector logic in `vision_perception`
2. Extend `VisionState.msg`
3. Update the vision bridge to publish posture fields
4. Add reminder state machine to `system_coordinator`
5. Add non-spoken text reminder output for first verification
6. Optionally connect reminder output to later speech playback

## Non-Goals for This Increment

- no body tracking for mechanical-arm motion
- no student identity tracking
- no long-term ergonomic scoring dashboard
- no classifier training or custom dataset work
