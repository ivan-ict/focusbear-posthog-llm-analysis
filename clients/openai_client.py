"""Minimal OpenAI client wrapper for journey classification."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from prompts import (
    build_classification_system_prompt,
    build_classification_user_prompt,
    build_repair_user_prompt,
)


class OpenAIClient:
    """Thin wrapper for classifying a single user journey."""

    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def classify_user(self, user_payload: dict[str, Any]) -> dict[str, Any]:
        """Classify a user journey and retry once if parsing fails."""
        system_prompt = build_classification_system_prompt()
        first_user_prompt = build_classification_user_prompt(user_payload)
        first_text = self._complete(system_prompt, first_user_prompt)

        try:
            return json.loads(first_text)
        except json.JSONDecodeError as exc:
            repair_prompt = build_repair_user_prompt(
                user_payload=user_payload,
                invalid_output=first_text,
                error_message=str(exc),
            )
            repaired_text = self._complete(system_prompt, repair_prompt)
            try:
                return json.loads(repaired_text)
            except json.JSONDecodeError as repair_exc:
                raise RuntimeError(f"OpenAI returned invalid JSON twice: {repair_exc}") from repair_exc

    def _complete(self, system_prompt: str, user_prompt: str) -> str:
        """Create a completion and return the raw text."""
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned an empty response.")
        return content
