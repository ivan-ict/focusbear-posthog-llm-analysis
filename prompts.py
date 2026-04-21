"""Prompt helpers for classifying Focus Bear onboarding journeys."""

from __future__ import annotations

import json
from typing import Any


ALLOWED_CATEGORIES = [
    "Permission issue",
    "Backend issue",
    "Early drop",
    "Exploration without activation",
    "Misclassified / already activated",
]

STAGE_KEYS = [
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

REQUIRED_OUTPUT_KEYS = ["activated", "category", "dropoff_point", "notes", *STAGE_KEYS]


def build_classification_system_prompt() -> str:
    """Return the system prompt for journey classification."""
    allowed_categories = ", ".join(ALLOWED_CATEGORIES)
    schema_keys = ", ".join(REQUIRED_OUTPUT_KEYS)
    return (
        "You classify Focus Bear mobile onboarding journeys. "
        "Use only the evidence in the payload. "
        "Treat rule hints as hints, not ground truth. "
        "Infer which onboarding steps were reached, identify the most likely dropoff point, "
        "classify the user into one allowed category, and write a short factual note. "
        f"Allowed category values: {allowed_categories}. "
        "Return JSON only. "
        f"The JSON must include exactly these keys: {schema_keys}. "
        "Use true or false for activated. "
        "Use only YES or NO for every onboarding step field. "
        "Keep notes concise and factual."
    )


def build_classification_user_prompt(user_payload: dict[str, Any]) -> str:
    """Render the payload sent to the model."""
    payload_json = json.dumps(user_payload, indent=2, ensure_ascii=True)
    return f"Classify this user journey.\n\nPayload:\n{payload_json}"


def build_repair_user_prompt(
    user_payload: dict[str, Any],
    invalid_output: str,
    error_message: str,
) -> str:
    """Render a stricter follow-up prompt when the first response is invalid."""
    payload_json = json.dumps(user_payload, indent=2, ensure_ascii=True)
    return (
        "Your previous answer was invalid.\n"
        f"Problem: {error_message}\n\n"
        "Return valid JSON only with the required keys and allowed values.\n\n"
        f"Previous invalid output:\n{invalid_output}\n\n"
        f"Source payload:\n{payload_json}"
    )
