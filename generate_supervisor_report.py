"""Entrypoint for generating a supervisor-facing DOCX report from the workbook."""

from __future__ import annotations

from config import AppConfig
from pipeline.report_supervisor import generate_supervisor_report


def main() -> None:
    """Generate the supervisor report from the current workbook output."""
    config = AppConfig.load()
    config.ensure_directories()

    print("Reading workbook output...", flush=True)
    output_path = generate_supervisor_report(
        workbook_path=config.output_xlsx_path,
        output_path=config.output_report_path,
    )
    print(f"Done. Wrote supervisor report to {output_path}", flush=True)


if __name__ == "__main__":
    main()
