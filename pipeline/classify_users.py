"""Classify mapped onboarding journeys with OpenAI."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from clients.openai_client import OpenAIClient
from pipeline.map_events import MappedJourney, STAGE_LABELS
from prompts import ALLOWED_CATEGORIES, REQUIRED_OUTPUT_KEYS, STAGE_KEYS


@dataclass(slots=True)
class ClassifiedJourney:
    """Final normalized output row written to Excel."""

    user_id: str
    first_app_opened_at: str
    last_event_at: str
    journey_duration: str
    category: str
    dropoff_point: str
    error_events: list[str]
    error_endpoint_urls: list[str]
    error_status_codes: list[str]
    blocking_schedule_highest_stage: str
    error_event_occurrences: list[dict[str, Any]]
    notes: str
    activated: bool
    pre_onboarding: str
    focus_bear_jr_greeting: str
    sign_up: str
    habits_introduction: str
    import_habits: str
    selecting_goals: str
    routine_generated: str
    blocking_intro: str
    screen_time_access: str
    set_up_blocking_schedule: str
    onboarding_complete: str
    home_screen: str
    raw_event_count: int


def classify_users(openai_client: OpenAIClient, journeys: list[MappedJourney]) -> list[ClassifiedJourney]:
    """Classify all journeys and normalize the results."""
    results: list[ClassifiedJourney] = []
    for journey in journeys:
        print(f"Classifying user {journey.user_id}...", flush=True)
        try:
            raw_response = openai_client.classify_user(journey.llm_payload)
            results.append(_normalize_response(journey, raw_response))
        except Exception as exc:
            print(f"Classification failed for user {journey.user_id}: {exc}", flush=True)
            results.append(_fallback_classification(journey, str(exc)))
    return results


def _normalize_response(journey: MappedJourney, response: dict[str, Any]) -> ClassifiedJourney:
    """Validate and normalize the model response."""
    missing_keys = [key for key in REQUIRED_OUTPUT_KEYS if key not in response]
    if missing_keys:
        raise ValueError(f"Missing keys in OpenAI response: {', '.join(missing_keys)}")

    category = _normalize_category(response.get("category"))
    activated = _normalize_bool(response.get("activated"))
    stage_values = {stage: _normalize_yes_no(response.get(stage)) for stage in STAGE_KEYS}
    notes = str(response.get("notes") or "").strip()
    if not notes:
        notes = "No note returned by the model."
    dropoff_point = normalize_dropoff_point(response.get("dropoff_point"))

    return ClassifiedJourney(
        user_id=journey.user_id,
        first_app_opened_at=journey.first_app_opened_at,
        last_event_at=journey.last_event_at,
        journey_duration=journey.journey_duration,
        category=category,
        dropoff_point=dropoff_point,
        error_events=journey.error_events,
        error_endpoint_urls=journey.error_endpoint_urls,
        error_status_codes=journey.error_status_codes,
        blocking_schedule_highest_stage=journey.blocking_schedule_highest_stage,
        error_event_occurrences=journey.error_event_occurrences,
        notes=notes,
        activated=activated,
        pre_onboarding=stage_values["pre_onboarding"],
        focus_bear_jr_greeting=stage_values["focus_bear_jr_greeting"],
        sign_up=stage_values["sign_up"],
        habits_introduction=stage_values["habits_introduction"],
        import_habits=stage_values["import_habits"],
        selecting_goals=stage_values["selecting_goals"],
        routine_generated=stage_values["routine_generated"],
        blocking_intro=stage_values["blocking_intro"],
        screen_time_access=stage_values["screen_time_access"],
        set_up_blocking_schedule=stage_values["set_up_blocking_schedule"],
        onboarding_complete=stage_values["onboarding_complete"],
        home_screen=stage_values["home_screen"],
        raw_event_count=journey.raw_event_count,
    )


def _fallback_classification(journey: MappedJourney, error_message: str) -> ClassifiedJourney:
    """Build a deterministic fallback when the LLM response is unavailable."""
    category = "Early drop"
    if journey.activation_detected:
        category = "Misclassified / already activated"
    elif journey.error_events:
        category = "Backend issue"
    elif journey.permission_events:
        category = "Permission issue"
    elif journey.raw_event_count > 8:
        category = "Exploration without activation"

    highest_stage = _highest_stage_label(journey.stage_flags)
    notes = (
        "Fallback classification used. "
        f"Reason: {error_message}. "
        f"Activation={journey.activation_detected}. "
        f"Errors={', '.join(journey.error_events) or 'none'}. "
        f"Permissions={', '.join(journey.permission_events) or 'none'}."
    )

    return ClassifiedJourney(
        user_id=journey.user_id,
        first_app_opened_at=journey.first_app_opened_at,
        last_event_at=journey.last_event_at,
        journey_duration=journey.journey_duration,
        category=category,
        dropoff_point=highest_stage,
        error_events=journey.error_events,
        error_endpoint_urls=journey.error_endpoint_urls,
        error_status_codes=journey.error_status_codes,
        blocking_schedule_highest_stage=journey.blocking_schedule_highest_stage,
        error_event_occurrences=journey.error_event_occurrences,
        notes=notes,
        activated=journey.activation_detected,
        pre_onboarding=_yes_no(journey.stage_flags.get("pre_onboarding", False)),
        focus_bear_jr_greeting=_yes_no(journey.stage_flags.get("focus_bear_jr_greeting", False)),
        sign_up=_yes_no(journey.stage_flags.get("sign_up", False)),
        habits_introduction=_yes_no(journey.stage_flags.get("habits_introduction", False)),
        import_habits=_yes_no(journey.stage_flags.get("import_habits", False)),
        selecting_goals=_yes_no(journey.stage_flags.get("selecting_goals", False)),
        routine_generated=_yes_no(journey.stage_flags.get("routine_generated", False)),
        blocking_intro=_yes_no(journey.stage_flags.get("blocking_intro", False)),
        screen_time_access=_yes_no(journey.stage_flags.get("screen_time_access", False)),
        set_up_blocking_schedule=_yes_no(journey.stage_flags.get("set_up_blocking_schedule", False)),
        onboarding_complete=_yes_no(journey.stage_flags.get("onboarding_complete", False)),
        home_screen=_yes_no(journey.stage_flags.get("home_screen", False)),
        raw_event_count=journey.raw_event_count,
    )


def _normalize_category(value: Any) -> str:
    """Normalize a model category to one of the allowed values."""
    text = str(value or "").strip()
    for allowed in ALLOWED_CATEGORIES:
        if text.lower() == allowed.lower():
            return allowed
    raise ValueError(f"Invalid category returned by model: {text}")


def _normalize_bool(value: Any) -> bool:
    """Normalize booleans returned by the model."""
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"true", "yes", "1"}:
        return True
    if text in {"false", "no", "0"}:
        return False
    raise ValueError(f"Invalid activated value returned by model: {value}")


def _normalize_yes_no(value: Any) -> str:
    """Normalize a model field to YES or NO."""
    if isinstance(value, bool):
        return "YES" if value else "NO"
    text = str(value or "").strip().upper()
    if text in {"YES", "NO"}:
        return text
    raise ValueError(f"Invalid YES/NO value returned by model: {value}")


def _highest_stage_label(stage_flags: dict[str, bool]) -> str:
    """Return the furthest stage reached from the deterministic mapping."""
    reached = [STAGE_LABELS[stage] for stage in STAGE_KEYS if stage_flags.get(stage)]
    return reached[-1] if reached else "Unknown"


def normalize_dropoff_point(value: Any) -> str:
    """Normalize a model dropoff point to a canonical stage label."""
    text = str(value or "").strip()
    if not text:
        return "Unknown"

    normalized = _normalize_dropoff_key(text)
    if normalized == "unknown":
        return "Unknown"

    for stage in STAGE_KEYS:
        stage_label = STAGE_LABELS[stage]
        if normalized in {_normalize_dropoff_key(stage), _normalize_dropoff_key(stage_label)}:
            return stage_label

    return "Unknown"


def _normalize_dropoff_key(value: str) -> str:
    """Return a stable comparison key for dropoff point variants."""
    collapsed = re.sub(r"[_\-\s]+", " ", value.strip().lower())
    return collapsed.strip()


def _yes_no(value: bool) -> str:
    """Return YES or NO for a boolean."""
    return "YES" if value else "NO"
