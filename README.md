# Focus Bear Cohort Prototype

This project analyzes Focus Bear mobile onboarding journeys for a PostHog cohort. It fetches cohort members, collects each user timeline, maps deterministic onboarding signals, asks OpenAI to classify each journey, and exports the results to a formatted Excel workbook for business review.

## What This Repo Does

- fetches up to `POSTHOG_USER_LIMIT` users from a PostHog cohort
- fetches and sorts each user’s event timeline
- derives deterministic rule hints such as stages reached, permission events, and backend error events
- sends a structured per-user payload to OpenAI for classification
- exports a workbook at `data/outputs/onboarding_analysis.xlsx` with detail and summary sheets

The pipeline is a local prototype. It is designed for analyst review and comparison with manual onboarding analysis, not for production deployment.

## Project Layout

- `main.py`: runs the full workflow
- `config.py`: loads and validates environment variables
- `clients/posthog_client.py`: PostHog auth, cohort fetch, and event fetch
- `clients/openai_client.py`: OpenAI classification wrapper with one repair retry
- `pipeline/fetch_users.py`: normalizes cohort users
- `pipeline/fetch_events.py`: loads mock or live timelines and writes raw event files
- `pipeline/map_events.py`: derives rule hints and structured LLM payloads
- `pipeline/classify_users.py`: normalizes model output and fallback classification
- `pipeline/export_results.py`: writes the formatted Excel workbook
- `test_workbook_export.py`: regression tests for classification propagation and workbook output
- `CHANGELOG.md`: project change history
- `docs/architecture.md`: architecture and data-flow reference
- `docs/handover.md`: maintainer onboarding and handover notes

## Setup

1. Create a virtual environment:

```bash
python3 -m venv .venv
```

2. Install dependencies:

```bash
.venv/bin/pip install -r requirements.txt
```

3. Create a local `.env` from the example:

```bash
cp .env.example .env
```

4. Fill in `.env` with your own local credentials:

- `OPENAI_API_KEY`: OpenAI API key used for journey classification
- `OPENAI_MODEL`: model name, default `gpt-4.1-mini`
- `POSTHOG_API_KEY`: PostHog personal/private Bearer API key
- `POSTHOG_BASE_URL`: PostHog host, default `https://us.posthog.com`
- `POSTHOG_PROJECT_ID`: PostHog project ID
- `POSTHOG_COHORT_ID`: target cohort ID
- `POSTHOG_USER_LIMIT`: maximum users to analyze in one run, default `100`
- `POSTHOG_EVENTS_LOOKBACK_DAYS`: event lookback window for live mode
- `POSTHOG_USE_MOCK`: `true` for fixtures, `false` for live APIs
- `OUTPUT_XLSX_PATH`: output workbook path

Do not treat `key.md`, `key.txt`, or any existing local `.env` values as canonical setup documentation. They are local workspace artifacts and may contain sensitive or stale credentials.

Important: a PostHog ingestion key that starts with `phc_` is not valid for this project’s live API reads. Live runs require a personal/private Bearer API key.

## Run

Run the full pipeline with:

```bash
.venv/bin/python main.py
```

Typical runtime messages are:

- `Testing PostHog auth...` in live mode
- `Fetching users...`
- `Fetching events for user ...`
- `Classifying user ...`
- `Writing Excel workbook...`

## Modes

### Mock Mode

Set `POSTHOG_USE_MOCK=true` to use the checked-in fixtures under `data/raw/fixtures/`. This is the safest way for a new maintainer to verify the pipeline shape without making live PostHog or OpenAI assumptions.

### Live Mode

Set `POSTHOG_USE_MOCK=false` to read from PostHog. In live mode the script:

- validates PostHog auth up front
- fetches up to `POSTHOG_USER_LIMIT` cohort users
- fetches each user’s events inside the configured lookback window
- still writes debug artifacts to `data/raw/` and `data/processed/`

Live mode also calls OpenAI for each analyzed user, so it depends on working network access, valid credentials, and model availability.

## Output Artifacts

- `data/raw/`: raw cohort payloads and per-user event timelines
- `data/processed/`: per-user structured payloads sent to the model
- `data/outputs/onboarding_analysis.xlsx`: final business-review workbook

The workbook currently:

- writes a detail worksheet named `Onboarding Analysis`
- writes a summary worksheet named `Summary`
- displays `First App Opened At` and `Last Event At` in Australia/Melbourne time using `DD/MM/YYYY HH:mm`
- includes a dedicated `Error Events` column for backend-issue rows
- normalizes `Dropoff Point` values to consistent stage labels before export
- uses a dark header, alternating row striping, category highlighting, and red/green YES/NO status cells

## Test

Run the current regression suite with:

```bash
.venv/bin/python -m unittest discover
```

The existing tests cover:

- config defaulting `POSTHOG_USER_LIMIT` to `100`
- classification propagation of `error_events`
- fallback classification behavior
- dropoff point normalization across label variants
- workbook headers, formatting, colors, localized datetime export, and summary-sheet output

## Troubleshooting

- `ModuleNotFoundError`: install dependencies into `.venv` and use the `.venv/bin/python` interpreter explicitly.
- `unauthorized` from PostHog: confirm `POSTHOG_API_KEY` is a personal/private Bearer key, not an ingestion key.
- DNS or connection errors in live mode: verify network access and that `POSTHOG_BASE_URL` is reachable from your environment.
- Empty or partial workbook output: check `data/raw/` and `data/processed/` first; those files are the fastest way to see whether the issue was in fetch, mapping, or classification.
- Invalid model output: the OpenAI client retries once with a stricter repair prompt before fallback classification logic is used.

## Additional Docs

- [Changelog](/Users/ivan/Documents/003-swinburne-dev/003-2025-S3/ICT80004/focusbear-posthog-llm-analysis/CHANGELOG.md)
- [Architecture Notes](/Users/ivan/Documents/003-swinburne-dev/003-2025-S3/ICT80004/focusbear-posthog-llm-analysis/docs/architecture.md) with Mermaid system-flow and artifact-flow diagrams
- [Handover Guide](/Users/ivan/Documents/003-swinburne-dev/003-2025-S3/ICT80004/focusbear-posthog-llm-analysis/docs/handover.md)
