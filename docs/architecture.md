# Architecture Notes

## Overview

The project is a linear local pipeline:

1. Load and validate runtime config.
2. Load users from local raw snapshots, fixtures, or live PostHog.
3. Load each user’s event timeline from local raw snapshots, fixtures, or live PostHog.
4. Map events into deterministic onboarding hints.
5. Classify each journey from cached results, OpenAI, or deterministic fallback logic.
6. Export a formatted Excel workbook.

`main.py` orchestrates the full flow.

## Current Default Path

Default runtime settings:

- `DATA_SOURCE=local_raw`
- `CLASSIFICATION_SOURCE=cached`

That means the normal path is:

- read `data/raw/cohort_persons_used.json`
- read `data/raw/user_<id>_events.json`
- rebuild deterministic mapping from those raw files
- reuse saved local classifications
- write `data/outputs/onboarding_analysis.xlsx`

## Runtime Flow

### Configuration

`config.py` loads `.env`, normalizes output paths, validates mode-specific credentials, and creates local data directories.

Important behaviors:

- `DATA_SOURCE` must be `local_raw`, `fixtures`, or `live`
- `CLASSIFICATION_SOURCE` must be `cached`, `openai`, or `fallback`
- `OPENAI_API_KEY` is required only for `CLASSIFICATION_SOURCE=openai`
- live mode rejects `POSTHOG_API_KEY` values that look like `phc_...` ingestion keys

### User Loading

`pipeline/fetch_users.py` produces `FetchedUsers` from one of three sources:

- `local_raw`: `data/raw/cohort_persons_used.json` plus optional metadata from `data/raw/cohort_persons_live.json`
- `fixtures`: `data/raw/fixtures/cohort_persons.json`
- `live`: PostHog cohort API, then snapshot writeback into `data/raw/`

### Event Loading

`pipeline/fetch_events.py` produces `UserTimeline` records from one of three sources:

- `local_raw`: `data/raw/user_<id>_events.json`
- `fixtures`: `data/raw/fixtures/person_events.json`
- `live`: PostHog events API, then snapshot writeback into `data/raw/`

In all modes, timelines are deduplicated and sorted chronologically.

### Deterministic Mapping

`pipeline/map_events.py` builds `MappedJourney` values containing:

- stage flags
- activation detection
- permission signals
- canonical backend error tuples
- error endpoint URLs
- error status codes
- blocking-schedule deepest stage
- a compact LLM payload

It also writes per-user payloads into `data/processed/`.

### Classification

`pipeline/classify_users.py` supports three execution modes:

- `cached`: load `data/processed/classified_journeys.json`, or bootstrap the cache from the current workbook and the current deterministic mapping
- `openai`: call OpenAI and refresh `classified_journeys.json`
- `fallback`: skip OpenAI and use deterministic fallback logic only

Cached classifications must match the current mapped user set exactly. Mismatches are treated as operator errors, not silent fallbacks.

### Workbook Export

`pipeline/export_results.py` writes:

- detail worksheet: `Onboarding Analysis`
- summary worksheet: `Summary`

Current workbook behavior:

- timestamps are converted to Australia/Melbourne display values
- dropoff points are normalized before export
- canonical error events are summarized in `Error Event Totals` and `Error Breakdown`
- blocking-schedule deepest-stage counts are included
- key findings are rendered as text
- no Excel charts are embedded

## Artifacts

### `data/raw/`

- cohort snapshot files
- per-user event timeline files
- checked-in fixtures for tests/debugging

### `data/processed/`

- per-user LLM payloads
- `sample_user_payload.json`
- `classified_journeys.json`

### `data/outputs/`

- `onboarding_analysis.xlsx`

## Constraints

- The pipeline is sequential and local-only.
- Cached classification depends on the local raw dataset staying aligned with the saved cache.
- Live runs still depend on external PostHog and OpenAI availability.
- The test suite is focused on config, mapping, classification, and workbook behavior rather than full external integrations.
