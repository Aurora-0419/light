from __future__ import annotations

from dataclasses import dataclass, field


REMINDER_TEXT = {
    "shoulder_tilt": "请调整坐姿",
}


def reminder_text_for_issue(issue: str) -> str:
    return REMINDER_TEXT.get(issue, "")


@dataclass
class ReminderDecision:
    should_remind: bool
    issue: str
    message: str = ""


@dataclass
class PostureReminderStateMachine:
    persistence_seconds: float = 4.0
    cooldown_seconds: float = 45.0
    active_issue: str = ""
    active_issue_since: float | None = None
    last_reminder_at: dict[str, float] = field(default_factory=dict)

    def update(self, *, issue: str, now: float) -> ReminderDecision:
        if not issue:
            self.active_issue = ""
            self.active_issue_since = None
            return ReminderDecision(False, "")

        if issue != self.active_issue:
            self.active_issue = issue
            self.active_issue_since = now
            if self.persistence_seconds <= 0.0:
                last_time = self.last_reminder_at.get(issue)
                if last_time is None or now - last_time >= self.cooldown_seconds:
                    self.last_reminder_at[issue] = now
                    return ReminderDecision(True, issue, reminder_text_for_issue(issue))
            return ReminderDecision(False, issue)

        if self.active_issue_since is None:
            self.active_issue_since = now
            return ReminderDecision(False, issue)

        if now - self.active_issue_since < self.persistence_seconds:
            return ReminderDecision(False, issue)

        last_time = self.last_reminder_at.get(issue)
        if last_time is not None and now - last_time < self.cooldown_seconds:
            return ReminderDecision(False, issue)

        self.last_reminder_at[issue] = now
        return ReminderDecision(True, issue, reminder_text_for_issue(issue))
