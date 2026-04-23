# Changelog

This file tracks notable project changes for the Focus Bear cohort prototype.
It is intended for code, configuration-default, documentation, and output-format changes.
It is not a log of individual live analysis runs or workbook results.

## Unreleased

### Added

- Added an offline supervisor-report generator that reads `data/outputs/onboarding_analysis.xlsx` and writes `data/outputs/onboarding_supervisor_report.docx` without calling PostHog or OpenAI again.
- Added deterministic report content with professional headings, aggregate findings tables, and locally rendered charts for journey categories, top dropoff points, and canonical error events.
- Added `OUTPUT_REPORT_PATH` config support and `.env.example` guidance for the generated DOCX path.
- Added regression coverage for offline DOCX generation and report privacy checks.

### Changed

- Ignored generated DOCX outputs under `data/outputs/*.docx` so supervisor reports stay local and out of git by default.
- Removed the accidentally tracked Excel temp lock file `data/outputs/~$onboarding_analysis.xlsx` from the repo and ignored future `data/outputs/~$*` artifacts.
- Clarified in maintainer docs that Excel `~$` files are local troubleshooting artifacts only and should never be committed.
- Restricted canonical endpoint-based backend analysis to `https://api.focusbear.io/` and filtered out other hosts such as `https://events.aws.focusbear.io/` from journey and summary analysis.
- Refreshed README, architecture notes, and handover guidance so setup commands, output-artifact privacy, and offline report generation instructions match the current implementation.

## 2026-04-23

### Added

- Added a `Summary` worksheet to `data/outputs/onboarding_analysis.xlsx` with aggregate counts, top dropoff points, top backend error events, and deterministic key findings.
- Added dropoff-point normalization so workbook and summary reporting use consistent stage labels.
- Added workbook detail columns for `Error Endpoint URLs`, `Error Status Codes`, and `Blocking Schedule Highest Stage`.
- Added summary sections for `Error Event Totals`, tuple-based `Error Breakdown`, and blocking-schedule deepest stage.
- Added summary-sheet metadata for cohort ID, cohort name, users available, users analyzed, applied cap, and lookback window.
- Added native Excel charts for journey categories, top dropoff points, and canonical error events by affected users.
- Added deterministic mapping fields for `error_endpoint_urls`, `error_status_codes`, `blocking_schedule_highest_stage`, `last_blocking_schedule_event`, and `error_event_occurrences`.
- Added regression coverage for full-cohort default mode, canonical error drilldowns, chart export, dropoff normalization, and summary-sheet output.

### Changed

- Changed `POSTHOG_USER_LIMIT` from a default cap to an optional override; blank now means full-cohort analysis.
- Updated workbook export behavior from separate endpoint/status/parity summary blocks to a single canonical error summary keyed by `event`, `endpoint_url`, and `status_code`.
- Expanded canonical error aggregation to include `backend-timed-out` in the summary path.

### Documentation

- Updated README, architecture notes, handover guidance, and `.env.example` to reflect full-cohort default behavior, the redesigned summary sheet, and the real analysis workbook path.
- Replaced stale local filesystem links in maintainer docs with GitHub-safe relative links.

## 2026-04-21

### Added

- Initial PostHog + OpenAI onboarding-analysis prototype.
- End-to-end local pipeline for cohort fetch, event fetch, deterministic mapping, LLM classification, and Excel workbook export.
- Maintainer documentation covering setup, architecture, and handover.
- Regression tests for classification propagation and workbook export behavior.

### Changed

- Established the initial local `.xlsx` workbook output at `data/outputs/onboarding_analysis.xlsx`.
