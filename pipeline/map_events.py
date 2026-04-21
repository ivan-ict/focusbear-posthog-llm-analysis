"""Map raw user timelines into deterministic onboarding features."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from fnmatch import fnmatch
import json
from pathlib import Path
from typing import Any

from config import AppConfig
from pipeline.fetch_events import UserTimeline


STAGE_ORDER = [
    "pre_onboarding",
    "focus_bear_jr_greeting",
    "sign_up",
    "habits_introduction",
    "import_habits",
    "selecting_goals",
    "routine_generated",
    "blocking_intro",
    "screen_time_access",
    "set_up_blocking_schedule",
    "onboarding_complete",
    "home_screen",
]

STAGE_LABELS = {
    "pre_onboarding": "Pre Onboarding",
    "focus_bear_jr_greeting": "Focus Bear Jr Greeting",
    "sign_up": "Sign Up",
    "habits_introduction": "Habits Introduction",
    "import_habits": "Import Habits",
    "selecting_goals": "Selecting Goals",
    "routine_generated": "Routine Generated",
    "blocking_intro": "Blocking Intro",
    "screen_time_access": "Screen Time Access",
    "set_up_blocking_schedule": "Set Up Blocking Schedule",
    "onboarding_complete": "Onboarding Complete",
    "home_screen": "Home Screen",
}

STAGE_PATTERNS = {
    "pre_onboarding": ["user-open-the-app-for-the-first-time", "day-of-usage-*"],
    "focus_bear_jr_greeting": [
        "junior-bear-*",
        "in-onboarding-*",
        "onboarding-captain-bear-intro-screen-opened",
    ],
    "sign_up": [
        "signup",
        "signup-*-success",
        "button-signin-*",
        "login",
        "agree-to-terms-of-service-and-privacy-policy",
    ],
    "habits_introduction": [
        "onboarding-user-achievement-*",
        "onboarding-setup-habits-*",
        "interacting-with-carousel",
    ],
    "import_habits": [
        "onboarding-habit-list-import-*",
        "onboarding-habit-import-upload-*",
    ],
    "selecting_goals": [
        "healthy-habits-selected",
        "stay-focused-at-work-selected",
        "interested-in-todo-list",
        "save-goals-something-else",
        "custom-goal-selected",
        "onboarding-user-achievement-goal-selected",
    ],
    "routine_generated": [
        "onboarding-routine-suggestion-*",
        "routine-suggestions-no-habits-suggested",
    ],
    "blocking_intro": [
        "blocking-permission-intro-*",
        "user-has-seen-permission-intro",
        "open-permission-video-tutorial",
    ],
    "screen_time_access": ["request-*permission*", "grant-*", "activated-permission-*"],
    "set_up_blocking_schedule": ["blocking-schedule-*"],
    "onboarding_complete": ["onboarding-complete*", "completed-onboarding*"],
    "home_screen": [
        "simple-home-screen-opened",
        "launcher-opened",
        "start-morning-routine",
        "start-evening-routine",
        "start-custom-routine",
        "start-routine-on-first-day",
        "start-focus-mode-manually",
        "completed-focus-session",
    ],
}

ACTIVATION_EVENTS = {
    "start-morning-routine",
    "start-evening-routine",
    "start-custom-routine",
    "start-routine-on-first-day",
    "start-focus-mode-manually",
    "completed-focus-session",
}

ERROR_EVENTS = {
    "backend-errored-out",
    "backend-timed-out",
    "network-error",
    "signin-error",
    "signup-error",
    "authentication-error",
}

PERMISSION_PATTERNS = [
    "request-overlay-permissions",
    "request-usage-state-permissions",
    "request-notification-permissions",
    "request-*permission*",
    "grant-*",
    "activated-permission-*",
]


@dataclass(slots=True)
class MappedJourney:
    """Rule-based summary of a user's onboarding journey."""

    user_id: str
    distinct_id: str
    raw_event_count: int
    first_app_opened_at: str
    last_event_at: str
    journey_duration: str
    stage_flags: dict[str, bool]
    activation_detected: bool
    error_events: list[str]
    permission_events: list[str]
    top_event_counts: list[dict[str, Any]]
    timeline_excerpt: list[dict[str, Any]]
    llm_payload: dict[str, Any]


def map_user_timelines(config: AppConfig, timelines: list[UserTimeline]) -> list[MappedJourney]:
    """Build deterministic features for each user timeline."""
    journeys: list[MappedJourney] = []
    for timeline in timelines:
        journey = _map_single_timeline(timeline)
        _write_json(
            config.processed_dir / f"user_{journey.user_id}_payload.json",
            journey.llm_payload,
        )
        journeys.append(journey)

    if journeys:
        _write_json(config.processed_dir / "sample_user_payload.json", journeys[0].llm_payload)
    return journeys


def _map_single_timeline(timeline: UserTimeline) -> MappedJourney:
    """Convert a raw timeline into a model-friendly payload."""
    event_names = [_event_name(event) for event in timeline.events if _event_name(event)]
    first_app_opened_at = _find_first_event_timestamp(
        timeline.events,
        target_event_name="user-open-the-app-for-the-first-time",
    )
    last_event_at = _find_last_event_timestamp(timeline.events)
    journey_duration = _format_journey_duration(first_app_opened_at, last_event_at)
    stage_flags = {stage: False for stage in STAGE_ORDER}

    for event_name in event_names:
        for stage, patterns in STAGE_PATTERNS.items():
            if any(_matches_pattern(event_name, pattern) for pattern in patterns):
                stage_flags[stage] = True

    activation_detected = any(event_name in ACTIVATION_EVENTS for event_name in event_names)
    if activation_detected:
        stage_flags["home_screen"] = True
    if stage_flags["home_screen"] and stage_flags["set_up_blocking_schedule"]:
        stage_flags["onboarding_complete"] = True

    error_events = sorted({name for name in event_names if name in ERROR_EVENTS})
    permission_events = sorted(
        {name for name in event_names if any(_matches_pattern(name, pattern) for pattern in PERMISSION_PATTERNS)}
    )

    event_counter = Counter(event_names)
    top_event_counts = [
        {"event": event_name, "count": count}
        for event_name, count in event_counter.most_common(15)
    ]

    highest_stage = _highest_stage(stage_flags)
    llm_payload = {
        "user": {
            "person_id": timeline.user.person_id,
            "primary_distinct_id": timeline.user.distinct_id,
            "distinct_ids": timeline.user.distinct_ids,
            "name": timeline.user.name,
            "email": timeline.user.email,
        },
        "rule_hints": {
            "stage_flags": {stage: _yes_no(value) for stage, value in stage_flags.items()},
            "highest_reached_stage": highest_stage,
            "activation_detected": activation_detected,
            "error_events": error_events,
            "permission_events": permission_events,
            "raw_event_count": len(timeline.events),
        },
        "event_name_counts": top_event_counts,
        "timeline_excerpt": _timeline_excerpt(timeline.events),
        "recent_event_names": event_names[-30:],
    }

    return MappedJourney(
        user_id=timeline.user.person_id,
        distinct_id=timeline.user.distinct_id,
        raw_event_count=len(timeline.events),
        first_app_opened_at=first_app_opened_at,
        last_event_at=last_event_at,
        journey_duration=journey_duration,
        stage_flags=stage_flags,
        activation_detected=activation_detected,
        error_events=error_events,
        permission_events=permission_events,
        top_event_counts=top_event_counts,
        timeline_excerpt=_timeline_excerpt(timeline.events),
        llm_payload=llm_payload,
    )


def _timeline_excerpt(events: list[dict[str, Any]], max_events: int = 30) -> list[dict[str, Any]]:
    """Return a small chronological event excerpt for the LLM."""
    excerpt = []
    for event in events[:max_events]:
        excerpt.append(
            {
                "timestamp": event.get("timestamp"),
                "event": _event_name(event),
                "properties": _compact_properties(event.get("properties") or {}),
            }
        )
    return excerpt


def _compact_properties(properties: dict[str, Any], max_keys: int = 5) -> dict[str, Any]:
    """Trim large event property maps down to a small stable subset."""
    compact: dict[str, Any] = {}
    for key in sorted(properties.keys())[:max_keys]:
        compact[key] = properties[key]
    return compact


def _event_name(event: dict[str, Any]) -> str:
    """Extract a normalized event name."""
    return str(event.get("event") or "").strip().lower()


def _find_first_event_timestamp(events: list[dict[str, Any]], target_event_name: str) -> str:
    """Return the first timestamp for the requested event name."""
    for event in events:
        if _event_name(event) != target_event_name:
            continue
        timestamp = _normalize_timestamp(event.get("timestamp"))
        if timestamp:
            return timestamp
    return ""


def _find_last_event_timestamp(events: list[dict[str, Any]]) -> str:
    """Return the timestamp of the last event in the sorted timeline."""
    for event in reversed(events):
        timestamp = _normalize_timestamp(event.get("timestamp"))
        if timestamp:
            return timestamp
    return ""


def _normalize_timestamp(value: Any) -> str:
    """Normalize event timestamps to ISO 8601 strings when possible."""
    if not value:
        return ""
    timestamp = str(value).strip()
    if not timestamp:
        return ""
    normalized = timestamp.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).isoformat()
    except ValueError:
        return timestamp


def _format_journey_duration(first_app_opened_at: str, last_event_at: str) -> str:
    """Build a human-readable duration from first app open to last event."""
    if not first_app_opened_at or not last_event_at:
        return ""

    try:
        started_at = datetime.fromisoformat(first_app_opened_at)
        ended_at = datetime.fromisoformat(last_event_at)
    except ValueError:
        return ""

    delta = ended_at - started_at
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return ""

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds and not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts) if parts else "0m"


def _matches_pattern(event_name: str, pattern: str) -> bool:
    """Return True when an event name matches a wildcard pattern."""
    return fnmatch(event_name.lower(), pattern.lower())


def _highest_stage(stage_flags: dict[str, bool]) -> str:
    """Return the furthest rule-based stage reached."""
    reached = [STAGE_LABELS[stage] for stage in STAGE_ORDER if stage_flags.get(stage)]
    return reached[-1] if reached else "Unknown"


def _yes_no(value: bool) -> str:
    """Return YES or NO for a boolean."""
    return "YES" if value else "NO"


def _write_json(path: Path, payload: Any) -> None:
    """Write a JSON document to disk."""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
