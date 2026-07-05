from __future__ import annotations

from system_coordinator.posture_reminder import PostureReminderStateMachine, reminder_text_for_issue


def test_reminder_requires_persistence_before_trigger():
    machine = PostureReminderStateMachine(persistence_seconds=3.0, cooldown_seconds=30.0)

    first = machine.update(issue="shoulder_tilt", now=10.0)
    second = machine.update(issue="shoulder_tilt", now=12.0)
    third = machine.update(issue="shoulder_tilt", now=13.2)

    assert first.should_remind is False
    assert second.should_remind is False
    assert third.should_remind is True
    assert third.message == "请调整一下肩膀姿势"


def test_reminder_respects_cooldown():
    machine = PostureReminderStateMachine(persistence_seconds=0.0, cooldown_seconds=30.0)

    first = machine.update(issue="head_too_close", now=5.0)
    second = machine.update(issue="head_too_close", now=10.0)
    third = machine.update(issue="head_too_close", now=40.5)

    assert first.should_remind is True
    assert second.should_remind is False
    assert third.should_remind is True


def test_reminder_resets_when_posture_recovers():
    machine = PostureReminderStateMachine(persistence_seconds=2.0, cooldown_seconds=30.0)

    machine.update(issue="body_lean_left_right", now=1.0)
    recovered = machine.update(issue="", now=2.0)
    retrigger = machine.update(issue="body_lean_left_right", now=4.5)

    assert recovered.should_remind is False
    assert retrigger.should_remind is False


def test_reminder_generates_expected_message_text():
    assert reminder_text_for_issue("head_too_close") == "请不要离桌面太近"
    assert reminder_text_for_issue("body_lean_left_right") == "请坐正一点"
