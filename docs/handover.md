# Handover Guide

## Purpose

This document is the maintainer reference for the current workbook-only pipeline.

## First-Day Checklist

- Read [README.md](../README.md) for setup and run commands.
- Read [CHANGELOG.md](../CHANGELOG.md) for recent changes.
- Read [architecture.md](architecture.md) for pipeline flow.
- Create your own local `.env` from `.env.example`.
- Run `.venv/bin/python -m unittest discover`.
- Start with `DATA_SOURCE=local_raw` and `CLASSIFICATION_SOURCE=cached`.

## Normal Operating Mode

The normal maintainer path is intentionally local and token-conservative:

```env
DATA_SOURCE=local_raw
CLASSIFICATION_SOURCE=cached
```

This mode expects:

- `data/raw/cohort_persons_used.json`
- matching `data/raw/user_<id>_events.json` files
- either `data/processed/classified_journeys.json` or an existing workbook at `OUTPUT_XLSX_PATH`

Use `.venv/bin/python main.py` to regenerate the workbook from those local artifacts.

## When To Use Other Modes

### `DATA_SOURCE=fixtures`

Use this for controlled debugging or tests against the checked-in fixture dataset.

### `DATA_SOURCE=live`

Use this only when you need to refresh the local raw snapshots from PostHog.

Before a live run, confirm:

- the PostHog key is a personal/private Bearer key
- the cohort and project IDs are correct
- the workbook is closed in Excel
- any temporary `POSTHOG_USER_LIMIT` is intentional

After a live run, switch back to `DATA_SOURCE=local_raw`.

### `CLASSIFICATION_SOURCE=openai`

Use this only when:

- the cached classifications are missing
- the cached user set no longer matches the current local raw dataset
- you intentionally want to refresh classifications

After an OpenAI refresh, switch back to `CLASSIFICATION_SOURCE=cached`.

### `CLASSIFICATION_SOURCE=fallback`

Use this only when you need a no-network deterministic pass.

## Maintainer Tasks

### Refresh The Workbook From Existing Local Data

```bash
.venv/bin/python main.py
```

### Refresh Local Raw Snapshots From PostHog

Set:

```env
DATA_SOURCE=live
CLASSIFICATION_SOURCE=cached
```

Then run:

```bash
.venv/bin/python main.py
```

If the user set changes, rerun once after that with `CLASSIFICATION_SOURCE=openai`.

### Refresh Cached Classifications

Set:

```env
CLASSIFICATION_SOURCE=openai
```

Then run:

```bash
.venv/bin/python main.py
```

This rewrites `data/processed/classified_journeys.json`.

### Adjust Stage Or Category Logic

Start in:

- `pipeline/map_events.py`
- `prompts.py`
- `pipeline/classify_users.py`

### Adjust Workbook Columns Or Styling

Start in `pipeline/export_results.py`.

## Debugging Order

When a run looks wrong, inspect artifacts in this order:

1. `data/raw/cohort_persons_used.json`
2. `data/raw/user_<id>_events.json`
3. `data/processed/user_<id>_payload.json`
4. `data/processed/classified_journeys.json`
5. `data/outputs/onboarding_analysis.xlsx`

This usually isolates whether the issue is in:

- local raw inputs
- deterministic mapping
- cached or fresh classification
- workbook export

## Known Constraints

- The pipeline is local-only and sequential.
- Cached mode is strict about user-set mismatches by design.
- The workbook summary no longer includes embedded Excel charts.
- There is no DOCX supervisor report flow anymore.

## Handover Checklist

- Confirm `.env.example` still matches `AppConfig`.
- Confirm README commands still work with `.venv/bin/python`.
- Confirm workbook columns and summary tables still match analyst expectations.
- Update `CHANGELOG.md` and this handover note whenever defaults or operator flow change.
