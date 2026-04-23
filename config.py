"""Configuration helpers for the Focus Bear cohort prototype."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent


def _parse_bool(value: str | None, default: bool = False) -> bool:
    """Parse a boolean-like environment value."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_optional_positive_int(value: str | None) -> int | None:
    """Parse an optional positive integer environment value."""
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return int(normalized)


@dataclass(slots=True)
class AppConfig:
    """Runtime configuration loaded from a local .env file."""

    openai_api_key: str
    openai_model: str
    posthog_api_key: str
    posthog_base_url: str
    posthog_project_id: str
    posthog_cohort_id: str
    posthog_user_limit: int | None
    posthog_events_lookback_days: int
    posthog_use_mock: bool
    output_xlsx_path: Path
    output_report_path: Path
    raw_dir: Path
    processed_dir: Path
    outputs_dir: Path
    fixtures_dir: Path

    @classmethod
    def load(cls, env_path: Path | None = None) -> "AppConfig":
        """Load configuration values from the provided .env file."""
        env_file = env_path or ROOT_DIR / ".env"
        load_dotenv(env_file)

        output_path_value = os.getenv("OUTPUT_XLSX_PATH") or os.getenv(
            "OUTPUT_CSV_PATH",
            "data/outputs/onboarding_analysis.xlsx",
        )
        output_path = Path(output_path_value)
        if output_path.suffix.lower() != ".xlsx":
            output_path = output_path.with_suffix(".xlsx")
        if not output_path.is_absolute():
            output_path = ROOT_DIR / output_path

        report_path_value = os.getenv("OUTPUT_REPORT_PATH", "data/outputs/onboarding_supervisor_report.docx")
        report_path = Path(report_path_value)
        if report_path.suffix.lower() != ".docx":
            report_path = report_path.with_suffix(".docx")
        if not report_path.is_absolute():
            report_path = ROOT_DIR / report_path

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
            posthog_api_key=os.getenv("POSTHOG_API_KEY", "").strip(),
            posthog_base_url=os.getenv("POSTHOG_BASE_URL", "https://us.posthog.com").strip().rstrip("/"),
            posthog_project_id=os.getenv("POSTHOG_PROJECT_ID", "14246").strip(),
            posthog_cohort_id=os.getenv("POSTHOG_COHORT_ID", "239235").strip(),
            posthog_user_limit=_parse_optional_positive_int(os.getenv("POSTHOG_USER_LIMIT")),
            posthog_events_lookback_days=int(os.getenv("POSTHOG_EVENTS_LOOKBACK_DAYS", "90")),
            posthog_use_mock=_parse_bool(os.getenv("POSTHOG_USE_MOCK"), default=True),
            output_xlsx_path=output_path,
            output_report_path=report_path,
            raw_dir=ROOT_DIR / "data" / "raw",
            processed_dir=ROOT_DIR / "data" / "processed",
            outputs_dir=ROOT_DIR / "data" / "outputs",
            fixtures_dir=ROOT_DIR / "data" / "raw" / "fixtures",
        )

    def validate(self) -> None:
        """Validate required configuration before the pipeline runs."""
        missing = []

        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.openai_model:
            missing.append("OPENAI_MODEL")
        if not self.posthog_use_mock:
            if not self.posthog_api_key:
                missing.append("POSTHOG_API_KEY")
            if not self.posthog_project_id:
                missing.append("POSTHOG_PROJECT_ID")
            if not self.posthog_cohort_id:
                missing.append("POSTHOG_COHORT_ID")

        if missing:
            missing_text = ", ".join(missing)
            raise ValueError(f"Missing required environment variables: {missing_text}")

        if not self.posthog_use_mock and self.posthog_api_key.startswith("phc_"):
            raise ValueError(
                "POSTHOG_API_KEY appears to be a PostHog ingestion key (starts with 'phc_'). "
                "Live cohort and events reads require a personal/private Bearer API key."
            )

        if self.posthog_user_limit is not None and self.posthog_user_limit <= 0:
            raise ValueError("POSTHOG_USER_LIMIT must be greater than 0")
        if self.posthog_events_lookback_days <= 0:
            raise ValueError("POSTHOG_EVENTS_LOOKBACK_DAYS must be greater than 0")

    def ensure_directories(self) -> None:
        """Create local data directories if they do not already exist."""
        for directory in (self.raw_dir, self.processed_dir, self.outputs_dir, self.fixtures_dir):
            directory.mkdir(parents=True, exist_ok=True)
