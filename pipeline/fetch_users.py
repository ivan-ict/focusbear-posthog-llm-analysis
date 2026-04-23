"""Fetch and normalize cohort users."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from config import AppConfig
from clients.posthog_client import PostHogClient


@dataclass(slots=True)
class CandidateUser:
    """Normalized cohort person record used by the pipeline."""

    person_id: str
    distinct_id: str
    distinct_ids: list[str]
    name: str
    email: str
    properties: dict[str, Any]
    raw: dict[str, Any]


@dataclass(slots=True)
class FetchedUsers:
    """Normalized cohort users plus cohort metadata for export/debugging."""

    users: list[CandidateUser]
    cohort_id: str
    cohort_name: str
    cohort_total_count: int


def fetch_candidate_users(config: AppConfig, client: PostHogClient | None) -> FetchedUsers:
    """Fetch users from the cohort endpoint or local fixtures."""
    if config.posthog_use_mock:
        payload = _load_json(config.fixtures_dir / "cohort_persons.json")
    else:
        if client is None:
            raise ValueError("PostHog client is required in live mode.")
        payload = client.fetch_cohort_persons(
            project_id=config.posthog_project_id,
            cohort_id=config.posthog_cohort_id,
            limit=config.posthog_user_limit,
        )
        _write_json(config.raw_dir / "cohort_persons_live.json", payload)

    results = payload.get("results", [])
    normalized_users: list[CandidateUser] = []
    for raw_person in results:
        user = _normalize_person(raw_person)
        if user is None:
            print("Skipping cohort person without a usable distinct ID.", flush=True)
            continue
        normalized_users.append(user)
        if config.posthog_user_limit is not None and len(normalized_users) >= config.posthog_user_limit:
            break

    _write_json(config.raw_dir / "cohort_persons_used.json", [user.raw for user in normalized_users])
    return FetchedUsers(
        users=normalized_users,
        cohort_id=str(payload.get("id") or config.posthog_cohort_id),
        cohort_name=str(payload.get("name") or "").strip(),
        cohort_total_count=int(payload.get("count") or len(normalized_users)),
    )


def _normalize_person(raw_person: dict[str, Any]) -> CandidateUser | None:
    """Convert a raw PostHog person into the project's internal format."""
    properties = raw_person.get("properties") or {}
    distinct_ids = _extract_distinct_ids(raw_person)
    if not distinct_ids:
        return None

    primary_distinct_id = distinct_ids[0]
    person_id = str(raw_person.get("id") or raw_person.get("uuid") or primary_distinct_id)
    name = (
        str(properties.get("name") or properties.get("$name") or raw_person.get("name") or "").strip()
    )
    email = str(properties.get("email") or properties.get("$email") or raw_person.get("email") or "").strip()

    return CandidateUser(
        person_id=person_id,
        distinct_id=primary_distinct_id,
        distinct_ids=distinct_ids,
        name=name,
        email=email,
        properties=properties,
        raw=raw_person,
    )


def _extract_distinct_ids(raw_person: dict[str, Any]) -> list[str]:
    """Extract and deduplicate distinct IDs from the raw person payload."""
    candidates: list[str] = []

    raw_distinct_ids = raw_person.get("distinct_ids")
    if isinstance(raw_distinct_ids, list):
        candidates.extend(str(item).strip() for item in raw_distinct_ids if str(item).strip())

    single_distinct_id = raw_person.get("distinct_id")
    if single_distinct_id:
        candidates.append(str(single_distinct_id).strip())

    seen: set[str] = set()
    ordered_ids: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            ordered_ids.append(candidate)
    return ordered_ids


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON document from disk."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    """Write a JSON document to disk."""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
