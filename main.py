"""Entrypoint for the Focus Bear cohort analysis prototype."""

from __future__ import annotations

from config import AppConfig
from clients.openai_client import OpenAIClient
from clients.posthog_client import PostHogClient
from pipeline.classify_users import classify_users
from pipeline.export_results import export_results
from pipeline.fetch_events import fetch_user_timelines
from pipeline.fetch_users import fetch_candidate_users
from pipeline.map_events import map_user_timelines


def main() -> None:
    """Run the full prototype pipeline."""
    config = AppConfig.load()
    config.validate()
    config.ensure_directories()

    posthog_client = None
    if config.posthog_use_mock:
        print("Using mock PostHog mode.", flush=True)
    else:
        print("Testing PostHog auth...", flush=True)
        posthog_client = PostHogClient(
            base_url=config.posthog_base_url,
            api_key=config.posthog_api_key,
        )
        posthog_client.test_auth()

    openai_client = OpenAIClient(
        api_key=config.openai_api_key,
        model=config.openai_model,
    )

    print("Fetching users...", flush=True)
    users = fetch_candidate_users(config=config, client=posthog_client)
    if not users:
        print("No users found. Exiting.", flush=True)
        return

    timelines = fetch_user_timelines(config=config, client=posthog_client, users=users)
    mapped_journeys = map_user_timelines(config=config, timelines=timelines)
    classified_journeys = classify_users(openai_client=openai_client, journeys=mapped_journeys)

    print("Writing Excel workbook...", flush=True)
    output_path = export_results(classified_journeys, config.output_xlsx_path)
    print(f"Done. Wrote {len(classified_journeys)} rows to {output_path}", flush=True)


if __name__ == "__main__":
    main()
