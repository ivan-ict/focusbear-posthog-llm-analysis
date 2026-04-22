# Handover Guide

## Purpose

This document is for the next maintainer of the Focus Bear cohort prototype. Use it as the operational reference after the initial README quickstart.

## First-Day Checklist

- Read [README.md](/Users/ivan/Documents/003-swinburne-dev/003-2025-S3/ICT80004/focusbear-posthog-llm-analysis/README.md) for setup and run commands.
- Read [CHANGELOG.md](/Users/ivan/Documents/003-swinburne-dev/003-2025-S3/ICT80004/focusbear-posthog-llm-analysis/CHANGELOG.md) for recent project changes.
- Read [architecture.md](/Users/ivan/Documents/003-swinburne-dev/003-2025-S3/ICT80004/focusbear-posthog-llm-analysis/docs/architecture.md) to understand the runtime flow.
- Create your own local `.env` from `.env.example`.
- Verify mock mode first with `POSTHOG_USE_MOCK=true`.
- Run `.venv/bin/python -m unittest discover`.
- Only then switch to live mode if you have valid PostHog and OpenAI access.

## Safe Local Setup

Use this project as a local tool, not a shared deployed service.

Recommended setup sequence:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m unittest discover
```

Then edit `.env` with your own credentials.

Do not depend on:

- `key.md`
- `key.txt`
- another developer’s `.env`

Those files are local artifacts and may contain stale or sensitive values.

## Operating Modes

### Mock Mode

Use mock mode for:

- onboarding a new maintainer
- verifying code changes that do not require live data
- testing workbook output shape without external API dependencies

Required setting:

```env
POSTHOG_USE_MOCK=true
```

Artifacts come from:

- `data/raw/fixtures/cohort_persons.json`
- `data/raw/fixtures/person_events.json`

### Live Mode

Use live mode when you need current cohort results.

Required settings:

- `POSTHOG_USE_MOCK=false`
- valid `POSTHOG_API_KEY`
- valid `OPENAI_API_KEY`

Before a live run, check:

- the PostHog key is a personal/private Bearer key
- the cohort ID and project ID are correct
- the lookback window is large enough for the onboarding period you care about
- the user limit is intentionally set

## Common Maintainer Tasks

### Change How Many Users Are Analyzed

Edit `POSTHOG_USER_LIMIT` in `.env`. The repo default is `100` if the variable is unset.

### Change the Event Lookback Window

Edit `POSTHOG_EVENTS_LOOKBACK_DAYS` in `.env`.

### Change the OpenAI Model

Edit `OPENAI_MODEL` in `.env`.

### Change the Output Location

Edit `OUTPUT_XLSX_PATH` in `.env`.

### Adjust Stage Or Category Logic

Start in:

- `pipeline/map_events.py` for rule hints, event patterns, activation, permission, and backend trace extraction
- `prompts.py` for model instructions and JSON schema expectations
- `pipeline/classify_users.py` for normalization and fallback logic

### Adjust Workbook Columns Or Styling

Start in `pipeline/export_results.py`.

## Debugging Workflow

When a run looks wrong, inspect artifacts in this order:

1. `data/raw/cohort_persons_used.json`
2. `data/raw/user_<id>_events.json`
3. `data/processed/user_<id>_payload.json`
4. `data/outputs/onboarding_analysis.xlsx`

This sequence usually tells you whether the problem happened during:

- user selection
- event fetch
- rule mapping
- LLM classification
- workbook export

## Known Risks And Gaps

- The project is still a prototype and remains tightly scoped to local execution.
- There is no database, job queue, API service, or deployment model.
- Classification depends on OpenAI responses and external network availability.
- The test suite does not cover live PostHog integration or end-to-end classification behavior.
- `codex-requirements.md` is a historical build brief and still contains pre-workbook assumptions such as CSV output.

## Recommended Future Improvements

- Add tests for fetch-layer behavior with fixture edge cases.
- Expand the summary worksheet if stakeholders need more aggregate cuts or charts.
- Add explicit logging instead of plain `print` statements if the prototype becomes longer-lived.
- Add a sanitized sample workbook or screenshots if new analysts need output examples without running live data.
- Remove or relocate local credential helper files if the repo is prepared for broader handover.

## Handover Checklist For The Next Owner

- Confirm `.env.example` still matches `AppConfig`.
- Update `CHANGELOG.md` whenever output format, defaults, or maintainer-facing behavior changes.
- Confirm README commands still work with the documented interpreter paths.
- Confirm the workbook column order and formatting still match analyst expectations.
- Confirm `docs/architecture.md` still matches the actual pipeline flow.
- Update this handover doc whenever a maintainer changes output format, external dependencies, or major pipeline stages.
