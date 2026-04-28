# Focus Bear Cohort Prototype

This project analyzes Focus Bear mobile onboarding journeys for a PostHog cohort. It maps per-user event timelines into onboarding signals, classifies each journey, and exports the results to a formatted Excel workbook for review.

## Current Default Workflow

The default path is now fully local:

- `DATA_SOURCE=local_raw` reads the already retrieved cohort snapshot in `data/raw/`
- `CLASSIFICATION_SOURCE=cached` reuses saved local classifications instead of calling OpenAI again
- the output is a single workbook at `data/outputs/onboarding_analysis.xlsx`

Live PostHog fetches and fresh OpenAI classification are still supported, but they are explicit opt-ins.

## Project Layout

- `main.py`: runs the full workflow
- `config.py`: loads and validates environment variables
- `clients/posthog_client.py`: PostHog auth, cohort fetch, and event fetch
- `clients/openai_client.py`: OpenAI classification wrapper with one repair retry
- `pipeline/fetch_users.py`: loads users from local raw snapshots, fixtures, or live PostHog
- `pipeline/fetch_events.py`: loads timelines from local raw snapshots, fixtures, or live PostHog
- `pipeline/map_events.py`: derives rule hints and structured LLM payloads
- `pipeline/classify_users.py`: cached, OpenAI, or fallback classification logic
- `pipeline/export_results.py`: writes the formatted Excel workbook
- `test_workbook_export.py`: regression tests for classification and workbook output

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Environment variables:

- `DATA_SOURCE`: `local_raw`, `fixtures`, or `live`
- `CLASSIFICATION_SOURCE`: `cached`, `openai`, or `fallback`
- `OPENAI_API_KEY`: required only when `CLASSIFICATION_SOURCE=openai`
- `OPENAI_MODEL`: model name, default `gpt-4.1-mini`
- `POSTHOG_API_KEY`: required only when `DATA_SOURCE=live`
- `POSTHOG_BASE_URL`: PostHog host, default `https://us.posthog.com`
- `POSTHOG_PROJECT_ID`: required only when `DATA_SOURCE=live`
- `POSTHOG_COHORT_ID`: required only when `DATA_SOURCE=live`
- `POSTHOG_USER_LIMIT`: optional emergency cap for live runs
- `POSTHOG_EVENTS_LOOKBACK_DAYS`: live-mode event lookback window
- `OUTPUT_XLSX_PATH`: output workbook path

Important: a PostHog key that starts with `phc_` is an ingestion key and is not valid for live API reads in this project.

## Run

Run the pipeline with:

```bash
.venv/bin/python main.py
```

Typical runtime messages are:

- `Using local data source: local_raw.`
- `Using classification source: cached.`
- `Fetching users...`
- `Loading cached events for user ...`
- `Writing Excel workbook...`

## Data And Classification Modes

### `DATA_SOURCE=local_raw`

Default mode. Uses existing raw snapshot files:

- `data/raw/cohort_persons_used.json`
- `data/raw/cohort_persons_live.json` when present, for cohort metadata
- `data/raw/user_<id>_events.json`

This mode fails fast if a required per-user event file is missing.

### `DATA_SOURCE=fixtures`

Uses the checked-in fixtures under `data/raw/fixtures/`. This is mainly for tests and controlled debugging.

### `DATA_SOURCE=live`

Reads the cohort and event timelines from PostHog, then refreshes the local raw snapshot files in `data/raw/`.

### `CLASSIFICATION_SOURCE=cached`

Default mode. Reuses saved local classifications:

- first from `data/processed/classified_journeys.json`
- otherwise by bootstrapping from the current workbook at `OUTPUT_XLSX_PATH`

Cached mode validates that the cached user set matches the current local raw dataset. If not, rerun once with `CLASSIFICATION_SOURCE=openai`.

### `CLASSIFICATION_SOURCE=openai`

Calls OpenAI for each mapped journey and refreshes `data/processed/classified_journeys.json`.

### `CLASSIFICATION_SOURCE=fallback`

Skips OpenAI entirely and uses deterministic fallback classification only.

## Output Artifacts

- `data/raw/`: cohort snapshots and per-user event timelines
- `data/processed/`: mapped LLM payloads plus `classified_journeys.json`
- `data/outputs/onboarding_analysis.xlsx`: final workbook
- `data/outputs/~$*`: local Excel temp/lock files, not real analysis output

The workbook currently:

- writes a detail worksheet named `Onboarding Analysis`
- writes a summary worksheet named `Summary`
- displays `First App Opened At` and `Last Event At` in Australia/Melbourne time using `DD/MM/YYYY HH:mm`
- includes cohort/run metadata on the summary sheet
- includes `Error Events`, `Error Endpoint URLs`, `Error Status Codes`, and `Blocking Schedule Highest Stage`
- summarizes canonical error events in `Error Event Totals` and `Error Breakdown`
- summarizes blocking-schedule deepest stage
- includes key findings text
- does not embed Excel charts

## Test

Run the regression suite with:

```bash
.venv/bin/python -m unittest discover
```

## Troubleshooting

- Missing cached data in default mode: confirm `data/raw/` contains `cohort_persons_used.json` and matching `user_<id>_events.json` files.
- Cached classifications do not match the current local raw dataset: rerun once with `CLASSIFICATION_SOURCE=openai`.
- `unauthorized` from PostHog in live mode: confirm `POSTHOG_API_KEY` is a personal/private Bearer key, not an ingestion key.
- Workbook appears locked: compare against `data/outputs/onboarding_analysis.xlsx`, not any `data/outputs/~$*` temp file, and close Excel before rerunning.

## Additional Docs

- [Changelog](CHANGELOG.md)
- [Architecture Notes](docs/architecture.md)
- [Handover Guide](docs/handover.md)
