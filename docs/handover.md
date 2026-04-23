# Handover Guide

## Purpose

This document is for the next maintainer of the Focus Bear cohort prototype. Use it as the operational reference after the initial README quickstart.

## First-Day Checklist

- Read [README.md](../README.md) for setup and run commands.
- Read [CHANGELOG.md](../CHANGELOG.md) for recent project changes.
- Read [architecture.md](architecture.md) to understand the runtime flow.
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
- any temporary user cap is intentionally set; blank `POSTHOG_USER_LIMIT` means full-cohort mode
- `data/outputs/onboarding_analysis.xlsx` is not open in Excel or another spreadsheet app
- compare analysis results against `data/outputs/onboarding_analysis.xlsx`, not any `data/outputs/~$*` temp file
- if a `data/outputs/~$*` file exists after closing Excel, treat it as a stale local temp lock file rather than as the real workbook

Recommended live rerun command:

```bash
.venv/bin/python main.py
```

## Common Maintainer Tasks

### Temporarily Throttle How Many Users Are Analyzed

Leave `POSTHOG_USER_LIMIT` blank for the normal full-cohort run. Set it to a positive integer only when you need a smaller debugging slice.

### Change the Event Lookback Window

Edit `POSTHOG_EVENTS_LOOKBACK_DAYS` in `.env`.

### Change the OpenAI Model

Edit `OPENAI_MODEL` in `.env`.

### Change the Output Location

Edit `OUTPUT_XLSX_PATH` in `.env`.

### Generate The Supervisor Report

Use this when the workbook already exists and you do not want another live run:

```bash
.venv/bin/python generate_supervisor_report.py
```

The report reads `data/outputs/onboarding_analysis.xlsx` and writes a local DOCX file. It does not call PostHog or OpenAI again.

### Adjust Stage Or Category Logic

Start in:

- `pipeline/map_events.py` for rule hints, event patterns, activation, permission, and backend trace extraction
- `prompts.py` for model instructions and JSON schema expectations
- `pipeline/classify_users.py` for normalization and fallback logic

### Adjust Workbook Columns Or Styling

Start in `pipeline/export_results.py`.

### Rerun The Live Workbook

Use this sequence when you need to refresh `data/outputs/onboarding_analysis.xlsx`:

1. Confirm `.env` is set for live mode and points to the intended cohort.
2. Close the workbook in Excel before rerunning.
3. Use `.venv/bin/python main.py`, not the system Python interpreter.
4. If the run fails on a transient PostHog event-read timeout, retry once before changing code.
5. After completion, verify the workbook timestamp changed and the detail plus summary sheets refreshed.

### Recreate The New Drilldowns In PostHog

- For canonical error review, use a Trends or Events insight filtered to `backend-errored-out`, `backend-timed-out`, and `network-error`.
- Break down by `endpoint_url` and `status_code` when you want the closest equivalent to the workbook `Error Breakdown` table.
- Use `unique users` for affected-user comparisons and `total` when you want raw event volume.
- Match the local filter: only `https://api.focusbear.io/` endpoint URLs participate in canonical endpoint-based backend analysis; other hosts should be treated as excluded noise for this workbook.
- Missing `status_code` values are expected for many `network-error` events.
- For blocking schedule, use the event family `blocking-schedule-*` and classify the deepest stage per user with this precedence:
  - `created`: `blocking-schedule-created`
  - `saved`: `blocking-schedule-save`
  - `configured`: `blocking-schedule-add-new`, `blocking-schedule-select-apps-global`, `blocking-schedule-toggle-global`, `blocking-schedule-remove`
  - `opened`: `blocking-schedule-screen-opened`
- Match the local workbook logic when comparing results:
  - workbook detail rows expose `Error Endpoint URLs`, `Error Status Codes`, and `Blocking Schedule Highest Stage`
  - workbook summary exposes `Error Event Totals`, `Error Breakdown`, and `Blocking Schedule Deepest Stage`
  - workbook summary charts visualize journey categories, top dropoff points, and canonical error events by affected users
  - workbook excludes `not_reached` from the blocking-schedule deepest-stage summary

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

If the workbook is correct but the supervisor report is missing or stale, regenerate the DOCX from the workbook before rerunning the live pipeline.

## Known Risks And Gaps

- The project is still a prototype and remains tightly scoped to local execution.
- There is no database, job queue, API service, or deployment model.
- Classification depends on OpenAI responses and external network availability.
- Live PostHog event fetches can fail transiently on request timeouts; a clean retry may succeed without code changes.
- The test suite does not cover live PostHog integration or end-to-end classification behavior.
- Supervisor report generation depends on local `python-docx` and `matplotlib` availability in `.venv`.
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
