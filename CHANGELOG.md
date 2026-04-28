# Changelog

## Unreleased

- Switched the default runtime flow from live/mock toggling to explicit `DATA_SOURCE` and `CLASSIFICATION_SOURCE` modes.
- Made `DATA_SOURCE=local_raw` the default so the pipeline reuses previously retrieved raw snapshots in `data/raw/`.
- Made `CLASSIFICATION_SOURCE=cached` the default so the pipeline reuses saved local classifications and avoids fresh OpenAI token spend by default.
- Added local classification cache persistence at `data/processed/classified_journeys.json`.
- Added workbook bootstrap support for cached classification when the JSON cache does not yet exist.
- Removed the supervisor DOCX report flow, including `generate_supervisor_report.py`, `pipeline/report_supervisor.py`, report config, and related dependencies.
- Removed embedded Excel charts from the summary worksheet while keeping the summary tables and key findings.
- Updated tests for cached classification behavior, workbook-only output, and chart removal.
- Rewrote README, architecture notes, handover notes, and `.env.example` to match the current local-first operator workflow.
