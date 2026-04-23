"""Minimal PostHog API client for cohort and event reads."""

from __future__ import annotations

from typing import Any

import requests


class PostHogClient:
    """Thin wrapper around the PostHog HTTP API."""

    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def test_auth(self) -> dict[str, Any]:
        """Call a simple auth endpoint to validate the API key."""
        return self._request_json("GET", "/api/users/@me/")

    def fetch_cohort_persons(
        self,
        project_id: str,
        cohort_id: str,
        limit: int | None,
    ) -> dict[str, Any]:
        """Fetch cohort members, optionally truncating to a caller-provided cap."""
        path = f"/api/projects/{project_id}/cohorts/{cohort_id}/persons/"
        params = {"format": "json"}

        collected_results: list[dict[str, Any]] = []
        current_url: str | None = path
        first_request = True
        last_page: dict[str, Any] = {}

        while current_url and (limit is None or len(collected_results) < limit):
            page = self._request_json("GET", current_url, params=params if first_request else None)
            first_request = False
            last_page = page if isinstance(page, dict) else {"results": page}

            if isinstance(page, list):
                batch = page
                current_url = None
            else:
                batch = page.get("results", [])
                current_url = page.get("next")

            collected_results.extend(batch)

        return {
            "count": last_page.get("count", len(collected_results)),
            "results": collected_results[:limit] if limit is not None else collected_results,
            "next": current_url,
        }

    def fetch_events(
        self,
        project_id: str,
        distinct_id: str,
        after: str,
        before: str,
        limit_per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch all events for a distinct ID within a bounded time window."""
        path = f"/api/projects/{project_id}/events/"
        params = {
            "format": "json",
            "distinct_id": distinct_id,
            "after": after,
            "before": before,
            "limit": limit_per_page,
            "offset": 0,
        }

        events: list[dict[str, Any]] = []
        current_url: str | None = path
        first_request = True

        while current_url:
            page = self._request_json("GET", current_url, params=params if first_request else None)
            first_request = False

            if isinstance(page, list):
                batch = page
                current_url = None
            else:
                batch = page.get("results", [])
                current_url = page.get("next")

            events.extend(batch)

            if not batch:
                break

        return events

    def _request_json(
        self,
        method: str,
        path_or_url: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Send a request and decode the JSON response."""
        url = path_or_url if path_or_url.startswith("http") else f"{self.base_url}{path_or_url}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            if getattr(exc, "response", None) is not None and exc.response is not None:
                if exc.response.status_code == 401:
                    raise RuntimeError(
                        f"PostHog request failed for {url}: unauthorized. "
                        "Use a personal/private Bearer API key, not a project ingestion key."
                    ) from exc
            raise RuntimeError(f"PostHog request failed for {url}: {exc}") from exc

        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(f"PostHog response was not valid JSON for {url}") from exc
