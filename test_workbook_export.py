"""Tests for classified output normalization and workbook export."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook

from config import AppConfig
from pipeline.classify_users import (
    ClassifiedJourney,
    _fallback_classification,
    _normalize_response,
    normalize_dropoff_point,
)
from pipeline.export_results import EXCEL_DATETIME_FORMAT, export_results
from pipeline.map_events import MappedJourney


class ConfigTests(unittest.TestCase):
    def test_load_defaults_to_100_users(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                config = AppConfig.load(env_path=env_path)

        self.assertEqual(config.posthog_user_limit, 100)


class ClassificationTests(unittest.TestCase):
    def test_normalize_response_preserves_error_events(self) -> None:
        journey = _build_mapped_journey(error_events=["backend-errored-out", "network-error"])

        result = _normalize_response(
            journey,
            {
                "activated": False,
                "category": "Backend issue",
                "dropoff_point": "Routine Generated",
                "notes": "Backend failed after signup.",
                "pre_onboarding": "YES",
                "focus_bear_jr_greeting": "YES",
                "sign_up": "YES",
                "habits_introduction": "NO",
                "import_habits": "NO",
                "selecting_goals": "NO",
                "routine_generated": "NO",
                "blocking_intro": "NO",
                "screen_time_access": "NO",
                "set_up_blocking_schedule": "NO",
                "onboarding_complete": "NO",
                "home_screen": "NO",
            },
        )

        self.assertEqual(result.error_events, ["backend-errored-out", "network-error"])

    def test_fallback_classification_preserves_error_events(self) -> None:
        journey = _build_mapped_journey(error_events=["signin-error"], permission_events=["request-overlay-permissions"])

        result = _fallback_classification(journey, "OpenAI unavailable")

        self.assertEqual(result.category, "Backend issue")
        self.assertEqual(result.error_events, ["signin-error"])

    def test_normalize_dropoff_point_collapses_stage_variants(self) -> None:
        self.assertEqual(normalize_dropoff_point("set_up_blocking_schedule"), "Set Up Blocking Schedule")
        self.assertEqual(normalize_dropoff_point("Set Up Blocking Schedule"), "Set Up Blocking Schedule")
        self.assertEqual(normalize_dropoff_point("screen-time-access"), "Screen Time Access")
        self.assertEqual(normalize_dropoff_point("something custom"), "Unknown")


class ExportResultsTests(unittest.TestCase):
    def test_export_results_writes_readable_workbook(self) -> None:
        rows = [
            _build_classified_journey(
                user_id="user-backend",
                first_app_opened_at="2026-06-01T00:15:00+00:00",
                last_event_at="2026-06-01T03:45:00+00:00",
                category="Backend issue",
                error_events=["backend-errored-out", "network-error"],
                notes="Two backend errors observed during onboarding.",
                pre_onboarding="YES",
                sign_up="YES",
                dropoff_point="set_up_blocking_schedule",
            ),
            _build_classified_journey(
                user_id="user-permission",
                first_app_opened_at="2026-06-02T01:00:00+00:00",
                last_event_at="2026-06-02T01:30:00+00:00",
                category="Permission issue",
                error_events=["backend-errored-out"],
                notes="Permission prompt shown repeatedly.",
                dropoff_point="Set Up Blocking Schedule",
                onboarding_complete="YES",
            ),
            _build_classified_journey(
                user_id="user-early",
                first_app_opened_at="2026-06-03T01:00:00+00:00",
                last_event_at="2026-06-03T01:30:00+00:00",
                category="Early drop",
                error_events=[],
                notes="User stopped before routine generation.",
                dropoff_point="Routine Generated",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "onboarding_analysis.xlsx"
            export_results(rows, output_path)

            workbook = load_workbook(output_path)
            worksheet = workbook["Onboarding Analysis"]
            summary_sheet = workbook["Summary"]

            self.assertEqual(
                [cell.value for cell in worksheet[1]],
                [
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
                ],
            )
            self.assertEqual(workbook.sheetnames, ["Onboarding Analysis", "Summary"])
            self.assertEqual(worksheet.freeze_panes, "A2")
            self.assertEqual(worksheet.auto_filter.ref, "A1:U4")

            self.assertEqual(worksheet["B2"].value, datetime(2026, 6, 1, 10, 15))
            self.assertEqual(worksheet["C2"].value, datetime(2026, 6, 1, 13, 45))
            self.assertEqual(worksheet["B2"].number_format, EXCEL_DATETIME_FORMAT)
            self.assertEqual(worksheet["C2"].number_format, EXCEL_DATETIME_FORMAT)

            self.assertEqual(worksheet["F2"].value, "Set Up Blocking Schedule")
            self.assertEqual(worksheet["F3"].value, "Set Up Blocking Schedule")
            self.assertEqual(worksheet["G2"].value, "backend-errored-out, network-error")
            self.assertEqual(worksheet["G3"].value, None)
            self.assertEqual(worksheet["G4"].value, None)

            self.assertTrue(worksheet["G2"].alignment.wrap_text)
            self.assertTrue(worksheet["H2"].alignment.wrap_text)
            self.assertEqual(worksheet["G2"].alignment.vertical, "top")
            self.assertEqual(worksheet["I2"].alignment.horizontal, "center")

            self.assertTrue(_rgb(worksheet["A1"]).endswith("1F2937"))
            self.assertTrue(_rgb(worksheet["A2"]).endswith("F7F7F7"))
            self.assertFalse(_rgb(worksheet["A3"]).endswith("F7F7F7"))
            self.assertTrue(_rgb(worksheet["E2"]).endswith("F4CCCC"))
            self.assertTrue(_rgb(worksheet["E3"]).endswith("FFD966"))
            self.assertTrue(_rgb(worksheet["I2"]).endswith("C6EFCE"))
            self.assertTrue(_rgb(worksheet["J2"]).endswith("FFC7CE"))

            self.assertEqual(summary_sheet["A1"].value, "Metric")
            self.assertEqual(summary_sheet["B2"].value, 3)
            self.assertEqual(summary_sheet["B3"].value, 1)
            self.assertEqual(summary_sheet["B4"].value, "33.3%")

            summary_rows = list(summary_sheet.iter_rows(values_only=True))
            self.assertIn(("Backend issue", 1, "33.3%"), summary_rows)
            self.assertIn(("Permission issue", 1, "33.3%"), summary_rows)
            self.assertIn(("Early drop", 1, "33.3%"), summary_rows)
            self.assertIn(("Set Up Blocking Schedule", 2, None), summary_rows)
            self.assertIn(("Routine Generated", 1, None), summary_rows)
            self.assertIn(("backend-errored-out", 1, None), summary_rows)
            self.assertIn(("network-error", 1, None), summary_rows)

            findings = [row[0] for row in summary_rows if row and isinstance(row[0], str)]
            self.assertIn("Largest category: Permission issue (1/3, 33.3%).", findings)
            self.assertIn("Most common dropoff point: Set Up Blocking Schedule (2 users).", findings)
            self.assertIn("Most common backend error: backend-errored-out (1 occurrences).", findings)
            self.assertIn("Onboarding completion rate: 33.3% (1/3).", findings)


def _build_mapped_journey(
    *,
    error_events: list[str] | None = None,
    permission_events: list[str] | None = None,
) -> MappedJourney:
    """Create a compact mapped journey fixture."""
    stage_flags = {
        "pre_onboarding": True,
        "focus_bear_jr_greeting": True,
        "sign_up": True,
        "habits_introduction": False,
        "import_habits": False,
        "selecting_goals": False,
        "routine_generated": False,
        "blocking_intro": False,
        "screen_time_access": False,
        "set_up_blocking_schedule": False,
        "onboarding_complete": False,
        "home_screen": False,
    }
    return MappedJourney(
        user_id="user-123",
        distinct_id="distinct-123",
        raw_event_count=5,
        first_app_opened_at="2026-06-01T00:15:00+00:00",
        last_event_at="2026-06-01T01:15:00+00:00",
        journey_duration="1h",
        stage_flags=stage_flags,
        activation_detected=False,
        error_events=error_events or [],
        permission_events=permission_events or [],
        top_event_counts=[],
        timeline_excerpt=[],
        llm_payload={},
    )


def _build_classified_journey(
    *,
    user_id: str,
    first_app_opened_at: str,
    last_event_at: str,
    category: str,
    error_events: list[str],
    notes: str,
    dropoff_point: str = "Routine Generated",
    onboarding_complete: str = "NO",
    pre_onboarding: str = "NO",
    sign_up: str = "NO",
) -> ClassifiedJourney:
    """Create a classified row fixture."""
    return ClassifiedJourney(
        user_id=user_id,
        first_app_opened_at=first_app_opened_at,
        last_event_at=last_event_at,
        journey_duration="3h 30m",
        category=category,
        dropoff_point=dropoff_point,
        error_events=error_events,
        notes=notes,
        activated=False,
        pre_onboarding=pre_onboarding,
        focus_bear_jr_greeting="NO",
        sign_up=sign_up,
        habits_introduction="NO",
        import_habits="NO",
        selecting_goals="NO",
        routine_generated="NO",
        blocking_intro="NO",
        screen_time_access="NO",
        set_up_blocking_schedule="NO",
        onboarding_complete=onboarding_complete,
        home_screen="NO",
        raw_event_count=12,
    )


def _rgb(cell: object) -> str:
    """Return an RGB-style fill value for assertions."""
    return str(cell.fill.fgColor.rgb or "")


if __name__ == "__main__":
    unittest.main()
