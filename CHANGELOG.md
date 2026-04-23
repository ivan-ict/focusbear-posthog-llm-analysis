# Changelog

This file tracks notable project changes for the Focus Bear cohort prototype.
It is intended for code, configuration-default, documentation, and output-format changes.
It is not a log of individual live analysis runs or workbook results.

## Unreleased

### Added

- Added a `Summary` worksheet to `data/outputs/onboarding_analysis.xlsx` with aggregate counts, top dropoff points, top backend error events, and deterministic key findings.
- Added dropoff-point normalization so workbook and summary reporting use consistent stage labels.
- Added workbook detail columns for `Error Endpoint URLs` and `Blocking Schedule Highest Stage`.
- Added summary sections for error endpoints by affected users and blocking-schedule deepest stage.
- Added deterministic mapping fields for `error_endpoint_urls`, `blocking_schedule_highest_stage`, and `last_blocking_schedule_event`.
- Added regression coverage for the `100`-user default, dropoff normalization, and summary-sheet output.

### Changed

- Increased the default `POSTHOG_USER_LIMIT` from `20` to `100`.
- Updated workbook export behavior from a single-sheet output to a detail-plus-summary workbook.

### Documentation

- Updated README, architecture notes, and handover documentation to reflect the new workbook shape and the `100`-user default.
- Updated maintainer docs with the new error-endpoint and blocking-schedule drilldowns plus live rerun guidance for `.venv`, stale `~$` Excel lock files, and transient PostHog read timeouts.
- Fixed stale documentation links so they point to the current `focusbear-posthog-llm-analysis` repo paths.

## 2026-04-21

### Added

- Initial PostHog + OpenAI onboarding-analysis prototype.
- End-to-end local pipeline for cohort fetch, event fetch, deterministic mapping, LLM classification, and Excel workbook export.
- Maintainer documentation covering setup, architecture, and handover.
- Regression tests for classification propagation and workbook export behavior.

### Changed

- Established the initial local `.xlsx` workbook output at `data/outputs/onboarding_analysis.xlsx`.
