# Architecture Notes

## Overview

The project is a linear local pipeline:

1. Load and validate runtime config.
2. Fetch cohort users from PostHog or local fixtures.
3. Fetch each user’s event timeline.
4. Map events into deterministic onboarding hints.
5. Classify each journey with OpenAI.
6. Export a formatted Excel workbook.
7. Generate an optional supervisor DOCX report from the workbook.

`main.py` orchestrates the full flow and owns the runtime order.

## Diagrams

### System Flow

```mermaid
flowchart TD
    ENV[".env / AppConfig.load()"]
    MAIN["main.py"]
    MODE{"POSTHOG_USE_MOCK?"}
    FIXTURES["data/raw/fixtures/*.json"]
    PH["PostHog API"]
    FU["pipeline/fetch_users.py"]
    FE["pipeline/fetch_events.py"]
    MAP["pipeline/map_events.py"]
    OAI["clients/openai_client.py\n+ pipeline/classify_users.py"]
    EXP["pipeline/export_results.py"]
    XLSX["data/outputs/onboarding_analysis.xlsx"]
    REPORT["pipeline/report_supervisor.py"]
    DOCX["data/outputs/onboarding_supervisor_report.docx"]

    ENV --> MAIN
    MAIN --> MODE
    MODE -->|true| FIXTURES
    MODE -->|false| PH
    FIXTURES --> FU
    PH --> FU
    FIXTURES --> FE
    PH --> FE
    FU --> FE
    FE --> MAP
    MAP --> OAI
    OAI --> EXP
    EXP --> XLSX
    XLSX --> REPORT
    REPORT --> DOCX
```

### Artifact Flow

```mermaid
flowchart LR
    FIX["Mock fixtures\ncohort_persons.json\nperson_events.json"]
    USERS["fetch_users"]
    EVENTS["fetch_events"]
    MAP["map_events"]
    CLASSIFY["classify_users"]
    EXPORT["export_results"]
    REPORT["report_supervisor"]

    RAW1["data/raw/cohort_persons_live.json\n+ cohort_persons_used.json"]
    RAW2["data/raw/user_<id>_events.json"]
    PROC["data/processed/user_<id>_payload.json\n+ sample_user_payload.json"]
    OUT["data/outputs/onboarding_analysis.xlsx"]
    DOCX["data/outputs/onboarding_supervisor_report.docx"]

    FIX --> USERS
    FIX --> EVENTS
    USERS --> RAW1
    USERS --> EVENTS
    EVENTS --> RAW2
    EVENTS --> MAP
    MAP --> PROC
    MAP --> CLASSIFY
    CLASSIFY --> EXPORT
    EXPORT --> OUT
    OUT --> REPORT
    REPORT --> DOCX
```

## Runtime Flow

### 1. Configuration

`config.py` loads `.env`, normalizes paths, validates required variables, and creates the local data directories used by the pipeline.

Important configuration behaviors:

- `POSTHOG_USE_MOCK=true` bypasses live PostHog fetches
- `POSTHOG_USER_LIMIT` is optional; blank means full-cohort mode
- `OUTPUT_XLSX_PATH` is normalized to an `.xlsx` path even if a CSV-style name is supplied
- `OUTPUT_REPORT_PATH` is normalized to a `.docx` path for offline supervisor reporting
- live mode rejects `POSTHOG_API_KEY` values that look like `phc_...` ingestion keys

### 2. PostHog Access

`clients/posthog_client.py` wraps the minimal PostHog HTTP operations used by the project:

- `test_auth()` validates the Bearer key
- `fetch_cohort_persons(...)` fetches the configured cohort members, optionally with a caller-provided cap
- `fetch_events(...)` fetches events for a distinct ID in a bounded time window

This module intentionally isolates PostHog endpoint details so the rest of the pipeline can stay stable if the API contract changes.

### 3. User Normalization

`pipeline/fetch_users.py` converts raw PostHog persons into `CandidateUser` records and returns cohort metadata with the normalized user list.

`CandidateUser` contains:

- `person_id`
- `distinct_id`
- `distinct_ids`
- `name`
- `email`
- `properties`
- `raw`

The module also writes:

- `data/raw/cohort_persons_live.json` in live mode
- `data/raw/cohort_persons_used.json` for the filtered user set actually analyzed

### 4. Event Timeline Loading

`pipeline/fetch_events.py` builds `UserTimeline` records from either:

- `data/raw/fixtures/person_events.json` in mock mode
- PostHog `/events/` API responses in live mode

Key behaviors:

- timelines are combined across all known `distinct_ids`
- events are deduplicated by event ID when available
- events are sorted ascending by timestamp
- each user’s final raw event timeline is written to `data/raw/user_<id>_events.json`

### 5. Deterministic Mapping

`pipeline/map_events.py` transforms each `UserTimeline` into a `MappedJourney`.

`MappedJourney` contains:

- normalized first and last timestamps
- journey duration
- stage flags
- activation detection
- `error_events`
- `error_endpoint_urls`
- `error_status_codes`
- `permission_events`
- `blocking_schedule_highest_stage`
- `last_blocking_schedule_event`
- `error_event_occurrences`
- top event counts
- a trimmed timeline excerpt
- the final `llm_payload`

The mapper is where the non-LLM logic lives:

- wildcard stage matching via `STAGE_PATTERNS`
- activation detection via `ACTIVATION_EVENTS`
- backend tracing via `ERROR_EVENTS`
- canonical error-tuple aggregation via `backend-errored-out`, `backend-timed-out`, and `network-error`
- canonical endpoint-backed errors are restricted to `https://api.focusbear.io/` endpoint URLs
- error endpoint extraction via the `endpoint_url` event property from canonical error tuples
- error status-code extraction via the `status_code` event property from canonical error tuples when present
- blocking-schedule deepest-stage derivation from the `blocking-schedule-*` event family
- permission signal extraction via `PERMISSION_PATTERNS`

The mapper writes model-ready payloads to `data/processed/user_<id>_payload.json` and also keeps `sample_user_payload.json` for quick inspection.

### 6. OpenAI Classification

`clients/openai_client.py` and `pipeline/classify_users.py` own the LLM step.

Prompt construction lives in `prompts.py`. The prompt requires a strict JSON response with:

- `activated`
- `category`
- `dropoff_point`
- `notes`
- all onboarding stage YES/NO fields

Classification behavior:

- first attempt uses the standard system and user prompts
- if JSON parsing fails, the client retries once with a repair prompt
- if the overall classification step still fails, `pipeline/classify_users.py` uses deterministic fallback logic

The fallback classifier promotes:

- `Misclassified / already activated` if activation was detected
- `Backend issue` if mapped `error_events` exist
- `Permission issue` if permission events exist
- `Exploration without activation` if the raw event count is high enough
- otherwise `Early drop`

### 7. Workbook Export

`pipeline/export_results.py` writes the final `ClassifiedJourney` rows to Excel.

Current workbook behavior:

- output file is `.xlsx`
- detail worksheet name is `Onboarding Analysis`
- summary worksheet name is `Summary`
- timestamps are converted to Australia/Melbourne display values at export time
- summary sheet includes cohort/run metadata such as cohort ID, cohort name, users available, users analyzed, optional cap, and lookback window
- workbook includes a dedicated `Error Events` column
- workbook includes `Error Endpoint URLs`, `Error Status Codes`, and `Blocking Schedule Highest Stage` detail columns
- dropoff points are normalized to canonical stage labels before export and summary counting
- summary sheet includes `Error Event Totals` and an `Error Breakdown` table keyed by `event`, `endpoint_url`, and `status_code`
- summary sheet includes blocking-schedule deepest-stage counts
- summary sheet includes native Excel charts for journey categories, top dropoff points, and canonical error events by affected users
- header, striping, category colors, and YES/NO status coloring are applied

The exporter is presentation-focused. Internal timestamp storage remains ISO strings until export.

### 8. Supervisor Report Generation

`pipeline/report_supervisor.py` reads the exported workbook and builds an offline supervisor-facing DOCX report.

Current report behavior:

- input workbook is `data/outputs/onboarding_analysis.xlsx` unless `OUTPUT_XLSX_PATH` overrides it
- output report is `data/outputs/onboarding_supervisor_report.docx` unless `OUTPUT_REPORT_PATH` overrides it
- report generation is deterministic and does not call PostHog or OpenAI again
- narrative sections are derived from workbook aggregates rather than per-user notes
- embedded charts are rendered locally with `matplotlib`
- the generated DOCX excludes user IDs, emails, and raw per-user notes by design
- generated Excel and DOCX outputs are intended as local artifacts and are ignored by git

`generate_supervisor_report.py` is the standalone entrypoint for this offline step.

## Key Runtime Models

### `AppConfig`

Loaded in `config.py`, used by every pipeline stage for env-driven behavior and path management.

### `CandidateUser`

Normalized cohort person record produced by `pipeline/fetch_users.py`.

### `FetchedUsers`

Normalized cohort users plus the cohort metadata used in workbook export.

### `UserTimeline`

User plus ordered events, produced by `pipeline/fetch_events.py`.

### `MappedJourney`

Rule-based summary and LLM payload, produced by `pipeline/map_events.py`.

### `ClassifiedJourney`

Normalized final row used by the exporter, produced by `pipeline/classify_users.py`.

### `AnalysisMetadata`

Run metadata passed into the exporter so the summary sheet can describe the analyzed cohort and runtime settings.

### `SupervisorReportData`

Aggregate report inputs parsed from the workbook summary and detail sheets, used by `pipeline/report_supervisor.py` to build the supervisor DOCX.

## Data And Artifact Flow

### `data/raw/`

Used for PostHog debug visibility:

- cohort payload snapshots
- per-user event timelines
- fixtures for mock mode

### `data/processed/`

Used for model inspection:

- per-user OpenAI payloads
- one sample payload for quick reading

### `data/outputs/`

User-facing generated artifacts:

- `onboarding_analysis.xlsx` as the main local workbook artifact
- `onboarding_supervisor_report.docx` as the aggregate-only local supervisor report

### `data/outputs/`

Used for analyst-facing output:

- `onboarding_analysis.xlsx`

## Known Constraints

- The pipeline is sequential. There is no concurrency control or batching layer.
- The test suite is small and focused on workbook/classification behavior, not full API integration.
- Live runs depend on external PostHog and OpenAI availability.
- Live runs can also fail transiently on slow PostHog event reads because the client uses a bounded request timeout.
- The repo also contains historical build notes and local credential artifacts that should not be treated as the system design source of truth.
