"""Export classified journeys to a colorized Excel workbook."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from pipeline.classify_users import ClassifiedJourney


OUTPUT_COLUMNS = [
    "User ID",
    "First App Opened At",
    "Last Event At",
    "Journey Duration",
    "Category",
    "Dropoff Point",
    "Error Events",
    "Notes",
    "Pre Onboarding",
    "Focus Bear Jr Greeting",
    "Sign Up",
    "Habits Introduction",
    "Import Habits",
    "Selecting Goals",
    "Routine Generated",
    "Blocking Intro",
    "Screen Time Access",
    "Set Up Blocking Schedule",
    "Onboarding Complete",
    "Home Screen",
    "Raw Event Count",
]

STATUS_COLUMNS = {
    "Pre Onboarding",
    "Focus Bear Jr Greeting",
    "Sign Up",
    "Habits Introduction",
    "Import Habits",
    "Selecting Goals",
    "Routine Generated",
    "Blocking Intro",
    "Screen Time Access",
    "Set Up Blocking Schedule",
    "Onboarding Complete",
    "Home Screen",
}

CATEGORY_COLUMN = "Category"
ERROR_EVENTS_COLUMN = "Error Events"
NOTES_COLUMN = "Notes"
DATE_COLUMNS = {"First App Opened At", "Last Event At"}
WRAP_TEXT_COLUMNS = {ERROR_EVENTS_COLUMN, NOTES_COLUMN}
MELBOURNE_TZ = ZoneInfo("Australia/Melbourne")
EXCEL_DATETIME_FORMAT = "DD/MM/YYYY HH:mm"

YES_FILL = PatternFill(fill_type="solid", fgColor="C6EFCE")
NO_FILL = PatternFill(fill_type="solid", fgColor="FFC7CE")
HEADER_FILL = PatternFill(fill_type="solid", fgColor="1F2937")
STRIPE_EVEN_FILL = PatternFill(fill_type="solid", fgColor="F7F7F7")
CATEGORY_FILLS = {
    "Permission issue": PatternFill(fill_type="solid", fgColor="FFD966"),
    "Backend issue": PatternFill(fill_type="solid", fgColor="F4CCCC"),
    "Early drop": PatternFill(fill_type="solid", fgColor="F9CB9C"),
    "Exploration without activation": PatternFill(fill_type="solid", fgColor="9FC5E8"),
    "Misclassified / already activated": PatternFill(fill_type="solid", fgColor="B6D7A8"),
}

HEADER_FONT = Font(bold=True, color="FFFFFF")
CENTER_ALIGNMENT = Alignment(horizontal="center", vertical="center")
WRAP_ALIGNMENT = Alignment(wrap_text=True, vertical="top")
MAX_COLUMN_WIDTH = 40
MIN_TEXT_COLUMN_WIDTH = 24


def export_results(rows: list[ClassifiedJourney], output_path: Path) -> Path:
    """Write the final Excel output."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Onboarding Analysis"
    worksheet.freeze_panes = "A2"

    worksheet.append(OUTPUT_COLUMNS)
    _style_header_row(worksheet)

    status_column_indexes = _column_indexes(STATUS_COLUMNS)
    wrap_column_indexes = _column_indexes(WRAP_TEXT_COLUMNS)
    date_column_indexes = _column_indexes(DATE_COLUMNS)
    category_column_index = _column_index(CATEGORY_COLUMN)

    for row in rows:
        worksheet.append(_build_row_values(row))
        row_index = worksheet.max_row
        _style_record_row(
            worksheet,
            row_index=row_index,
            status_column_indexes=status_column_indexes,
            wrap_column_indexes=wrap_column_indexes,
            date_column_indexes=date_column_indexes,
            category_column_index=category_column_index,
        )

    worksheet.auto_filter.ref = worksheet.dimensions
    _autosize_columns(worksheet)
    workbook.save(output_path)
    return output_path


def _build_row_values(row: ClassifiedJourney) -> list[Any]:
    """Return export values in the workbook column order."""
    error_events = ", ".join(row.error_events) if row.category == "Backend issue" else ""
    return [
        row.user_id,
        _format_excel_datetime_value(row.first_app_opened_at),
        _format_excel_datetime_value(row.last_event_at),
        row.journey_duration,
        row.category,
        row.dropoff_point,
        error_events,
        row.notes,
        row.pre_onboarding,
        row.focus_bear_jr_greeting,
        row.sign_up,
        row.habits_introduction,
        row.import_habits,
        row.selecting_goals,
        row.routine_generated,
        row.blocking_intro,
        row.screen_time_access,
        row.set_up_blocking_schedule,
        row.onboarding_complete,
        row.home_screen,
        row.raw_event_count,
    ]


def _format_excel_datetime_value(value: str) -> datetime | str:
    """Convert an ISO timestamp to a Melbourne-local naive datetime for Excel."""
    if not value:
        return ""

    normalized = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return value

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=MELBOURNE_TZ)
    else:
        parsed = parsed.astimezone(MELBOURNE_TZ)
    return parsed.replace(tzinfo=None)


def _style_header_row(worksheet: Worksheet) -> None:
    """Apply workbook styling to the header row."""
    for cell in worksheet[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGNMENT


def _style_record_row(
    worksheet: Worksheet,
    row_index: int,
    status_column_indexes: set[int],
    wrap_column_indexes: set[int],
    date_column_indexes: set[int],
    category_column_index: int,
) -> None:
    """Apply row striping, wrapping, category fills, and status styling."""
    _apply_row_striping(worksheet, row_index)
    _style_category_cell(worksheet.cell(row=row_index, column=category_column_index))

    for column_index in wrap_column_indexes:
        worksheet.cell(row=row_index, column=column_index).alignment = WRAP_ALIGNMENT

    for column_index in status_column_indexes:
        cell = worksheet.cell(row=row_index, column=column_index)
        cell.alignment = CENTER_ALIGNMENT
        _style_status_cell(cell)

    for column_index in date_column_indexes:
        cell = worksheet.cell(row=row_index, column=column_index)
        if isinstance(cell.value, datetime):
            cell.number_format = EXCEL_DATETIME_FORMAT


def _apply_row_striping(worksheet: Worksheet, row_index: int) -> None:
    """Apply subtle alternating fill across non-header rows."""
    if row_index % 2 != 0:
        return
    for cell in worksheet[row_index]:
        cell.fill = STRIPE_EVEN_FILL


def _style_category_cell(cell: Any) -> None:
    """Color the category cell using a fixed mapping."""
    fill = CATEGORY_FILLS.get(str(cell.value or "").strip())
    if fill is not None:
        cell.fill = fill


def _style_status_cell(cell: Any) -> None:
    """Color YES and NO cells in the status columns."""
    cell_value = str(cell.value or "").strip().upper()
    if cell_value == "YES":
        cell.fill = YES_FILL
    elif cell_value == "NO":
        cell.fill = NO_FILL


def _column_index(column_name: str) -> int:
    """Return the 1-based index of a workbook column."""
    return OUTPUT_COLUMNS.index(column_name) + 1


def _column_indexes(column_names: set[str]) -> set[int]:
    """Return 1-based indexes for the provided workbook columns."""
    return {
        index
        for index, column_name in enumerate(OUTPUT_COLUMNS, start=1)
        if column_name in column_names
    }


def _autosize_columns(worksheet: Worksheet) -> None:
    """Resize columns to a readable width with a fixed cap."""
    for column in worksheet.columns:
        values = [str(cell.value or "") for cell in column]
        max_length = max((len(value) for value in values), default=0)
        column_letter = column[0].column_letter
        column_name = str(column[0].value or "")
        width = min(max_length + 2, MAX_COLUMN_WIDTH)
        if column_name in WRAP_TEXT_COLUMNS:
            width = max(width, MIN_TEXT_COLUMN_WIDTH)
        worksheet.column_dimensions[column_letter].width = width
