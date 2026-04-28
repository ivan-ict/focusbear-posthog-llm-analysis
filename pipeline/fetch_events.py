"""Fetch and sort user event timelines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from config import AppConfig
from clients.posthog_client import PostHogClient
from pipeline.fetch_users import CandidateUser


@dataclass(slots=True)
class UserTimeline:
    """A normalized user plus their ordered event list."""

    user: CandidateUser
    events: list[dict[str, Any]]


def fetch_user_timelines(
    config: AppConfig,
    client: PostHogClient | None,
    users: list[CandidateUser],
) -> list[UserTimeline]:
    """Fetch per-user event timelines from local snapshots, fixtures, or PostHog."""
    if config.data_source == "fixtures":
        fixture_events = _load_json(config.fixtures_dir / "person_events.json")
        timelines = _load_mock_timelines(config=config, users=users, fixture_events=fixture_events)
    elif config.data_source == "live":
        if client is None:
            raise ValueError("PostHog client is required in live mode.")
        timelines = _load_live_timelines(config=config, client=client, users=users)
    else:
        timelines = _load_local_raw_timelines(config=config, users=users)

    return timelines


def _load_mock_timelines(
    config: AppConfig,
    users: list[CandidateUser],
    fixture_events: dict[str, list[dict[str, Any]]],
) -> list[UserTimeline]:
    """Load event timelines from the checked-in fixture file."""
    timelines: list[UserTimeline] = []
    for user in users:
        print(f"Fetching events for user {user.person_id}...", flush=True)
        combined_events: list[dict[str, Any]] = []
        for distinct_id in user.distinct_ids:
            combined_events.extend(fixture_events.get(distinct_id, []))
        ordered_events = _sort_events(_dedupe_events(combined_events))
        _write_json(config.raw_dir / f"user_{user.person_id}_events.json", ordered_events)
        timelines.append(UserTimeline(user=user, events=ordered_events))
    return timelines


def _load_live_timelines(
    config: AppConfig,
    client: PostHogClient,
    users: list[CandidateUser],
) -> list[UserTimeline]:
    """Fetch user event timelines from the PostHog events API."""
    before_dt = datetime.now(timezone.utc)
    after_dt = before_dt - timedelta(days=config.posthog_events_lookback_days)
    before = before_dt.isoformat()
    after = after_dt.isoformat()

    timelines: list[UserTimeline] = []
    for user in users:
        print(f"Fetching events for user {user.person_id}...", flush=True)
        combined_events: list[dict[str, Any]] = []
        for distinct_id in user.distinct_ids:
            events = client.fetch_events(
                project_id=config.posthog_project_id,
                distinct_id=distinct_id,
                after=after,
                before=before,
            )
            combined_events.extend(events)

        ordered_events = _sort_events(_dedupe_events(combined_events))
        _write_json(config.raw_dir / f"user_{user.person_id}_events.json", ordered_events)
        timelines.append(UserTimeline(user=user, events=ordered_events))
    return timelines


def _load_local_raw_timelines(
    config: AppConfig,
    users: list[CandidateUser],
) -> list[UserTimeline]:
    """Load event timelines from existing raw user snapshot files."""
    timelines: list[UserTimeline] = []
    for user in users:
        print(f"Loading cached events for user {user.person_id}...", flush=True)
        events_path = config.raw_dir / f"user_{user.person_id}_events.json"
        if not events_path.exists():
            raise FileNotFoundError(
                f"Missing local raw events for user {user.person_id}: {events_path}. "
                "Switch to DATA_SOURCE=live to refresh snapshots."
            )
        ordered_events = _sort_events(_dedupe_events(_load_json_list(events_path)))
        timelines.append(UserTimeline(user=user, events=ordered_events))
    return timelines


def _dedupe_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate events by event ID when available."""
    deduped: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for event in events:
        event_id = str(event.get("id") or "")
        if event_id:
            if event_id in seen_ids:
                continue
            seen_ids.add(event_id)
        deduped.append(event)

    return deduped


def _sort_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort events in ascending timestamp order."""
    return sorted(events, key=lambda event: _event_sort_key(event.get("timestamp")))


def _event_sort_key(value: Any) -> tuple[int, str]:
    """Build a stable sort key for an event timestamp."""
    if not value:
        return (1, "")
    timestamp = str(value)
    normalized = timestamp.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return (0, parsed.isoformat())
    except ValueError:
        return (0, timestamp)


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON document from disk."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    """Load a JSON list from disk."""
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON list at {path}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    """Write a JSON document to disk."""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
