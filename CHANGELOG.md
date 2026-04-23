# Changelog

This file tracks notable project changes for the Focus Bear cohort prototype.
It is intended for code, configuration-default, documentation, and output-format changes.
It is not a log of individual live analysis runs or workbook results.

## Unreleased

- No unreleased changes.

## 2026-04-23

### Added

- Added a `Summary` worksheet to `data/outputs/onboarding_analysis.xlsx` with aggregate counts, top dropoff points, top backend error events, and deterministic key findings.
- Added dropoff-point normalization so workbook and summary reporting use consistent stage labels.
- Added workbook detail columns for `Error Endpoint URLs`, `Error Status Codes`, and `Blocking Schedule Highest Stage`.
- Added summary sections for error endpoints by affected users, error status codes by affected users, blocking-schedule deepest stage, and a raw `PostHog Insight Parity` view.
- Added deterministic mapping fields for `error_endpoint_urls`, `error_status_codes`, `blocking_schedule_highest_stage`, `last_blocking_schedule_event`, and `error_event_occurrences`.
- Added regression coverage for the `100`-user default, error drilldowns, parity export, dropoff normalization, and summary-sheet output.

### Changed

- Increased the default `POSTHOG_USER_LIMIT` from `20` to `100`.
- Updated workbook export behavior from a single-sheet output to a detail-plus-summary workbook with additional deterministic error and parity drilldowns.

### Documentation

- Updated README, architecture notes, and handover documentation to reflect the current workbook shape, live rerun guidance, and the real analysis workbook path.
- Replaced stale local filesystem links in maintainer docs with GitHub-safe relative links.

## 2026-04-21

### Added

- Initial PostHog + OpenAI onboarding-analysis prototype.
- End-to-end local pipeline for cohort fetch, event fetch, deterministic mapping, LLM classification, and Excel workbook export.
- Maintainer documentation covering setup, architecture, and handover.
- Regression tests for classification propagation and workbook export behavior.

### Changed

- Established the initial local `.xlsx` workbook output at `data/outputs/onboarding_analysis.xlsx`.
