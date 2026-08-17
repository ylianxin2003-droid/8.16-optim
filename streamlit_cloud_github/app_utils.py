"""Small UI helpers for the Streamlit dashboard."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import pandas as pd

from config import SERENE_AIDA_ARCHIVE_START

DEFAULT_AIDA_ARCHIVE_START = "2024-09-28T00:00:00Z"


def _parse_archive_start(value: str) -> pd.Timestamp:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        parsed = pd.Timestamp(DEFAULT_AIDA_ARCHIVE_START)
    return parsed


AIDA_ARCHIVE_START_UTC = _parse_archive_start(SERENE_AIDA_ARCHIVE_START)
AIDA_ARCHIVE_START = AIDA_ARCHIVE_START_UTC.date()


def validate_requested_window(
    start_time: str,
    end_time: str,
    publication_safe_now: pd.Timestamp | None = None,
) -> str | None:
    """Return a user-facing error for an invalid or unpublished UTC window."""
    start = pd.to_datetime(start_time, errors="coerce", utc=True)
    end = pd.to_datetime(end_time, errors="coerce", utc=True)
    if pd.isna(start) or pd.isna(end):
        return "The requested analysis window is invalid."
    if start > end:
        return "The analysis start must be before the analysis end."
    safe_now = publication_safe_now
    if safe_now is None:
        safe_now = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=15)
    if end > safe_now:
        return "The analysis end is in the unpublished future window."
    return None


def advisory_metadata_for_load(
    success: bool,
    current_sequence: int,
    generated_time: pd.Timestamp,
) -> dict[str, Any]:
    """Create stable session-local advisory metadata for one load attempt."""
    if not success:
        return {
            "sequence": int(current_sequence),
            "generated_time": None,
            "number": None,
        }
    sequence = int(current_sequence) + 1
    generated = pd.Timestamp(generated_time)
    return {
        "sequence": sequence,
        "generated_time": generated,
        "number": f"{generated.year}/{sequence:03d}",
    }


def loaded_api_state(
    status: Any,
    explicit_connected: bool | None,
    explicit_message: str,
) -> tuple[str, str]:
    """Return display severity and text for API connection/load evidence."""
    if explicit_connected is True:
        return "success", explicit_message
    if explicit_connected is False:
        return "warning", explicit_message
    if getattr(status, "source", None) == "api" and bool(getattr(status, "ok", False)):
        return "success", "Live load succeeded; the SERENE API returned AIDA data."
    return "info", "Not tested. Use the sidebar connection test or load live data."


def build_provenance_metadata(
    requested_time: Any,
    actual_time: Any,
    retrieved_time: Any,
    now: Any,
    official_forecasts: int,
) -> list[dict[str, str]]:
    """Build full-width, non-truncated provenance values for the first screen."""
    actual = _as_utc_timestamp(actual_time)
    current = _as_utc_timestamp(now)
    if actual is None or current is None:
        age = "N/A"
    else:
        minutes = max(0, int((current - actual).total_seconds() // 60))
        age = f"{minutes} min"
    return [
        {"label": "Requested analysis", "value": _format_utc_value(requested_time)},
        {"label": "Actual AIDA output", "value": _format_utc_value(actual_time)},
        {"label": "Retrieved", "value": _format_utc_value(retrieved_time)},
        {"label": "Data age", "value": age},
        {"label": "Forecast horizons", "value": f"{int(official_forecasts)} official"},
    ]


def _as_utc_timestamp(value: Any) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(parsed) else pd.Timestamp(parsed)


def _format_utc_value(value: Any) -> str:
    parsed = _as_utc_timestamp(value)
    return "N/A" if parsed is None else parsed.strftime("%Y-%m-%d %H:%M UTC")


def combine_date_time_iso(date_value: date, time_value: time) -> str:
    """Combine separate Streamlit date/time values into an ISO 8601 string."""
    return datetime.combine(date_value, time_value).strftime("%Y-%m-%dT%H:%M:%S")


def default_time_range(reference_time: datetime | None = None) -> tuple[datetime, datetime]:
    """Return a six-hour UTC window ending on a published AIDA cadence."""
    now = reference_time or datetime.now(timezone.utc)
    delayed = now - timedelta(minutes=15)
    end = delayed.replace(
        minute=(delayed.minute // 5) * 5,
        second=0,
        microsecond=0,
    )
    return end - timedelta(hours=6), end


def historical_risk_windows() -> pd.DataFrame:
    """Recent high-risk geomagnetic storm windows from official Kp/ap data."""
    return pd.DataFrame([
        {
            "Time UTC": "2024-10-10 18:00 to 2024-10-11 03:00",
            "Peak Kp": "8.7",
            "Peak ap": "300",
            "Risk": "G4 Severe geomagnetic storm",
            "Select range": "2024-10-10T18:00:00 to 2024-10-11T02:55:00",
        },
        {
            "Time UTC": "2025-01-01 15:00 to 18:00",
            "Peak Kp": "8.0",
            "Peak ap": "207",
            "Risk": "G4 Severe geomagnetic storm",
            "Select range": "2025-01-01T15:00:00 to 2025-01-01T17:55:00",
        },
        {
            "Time UTC": "2025-11-12 00:00 to 06:00",
            "Peak Kp": "8.7",
            "Peak ap": "300",
            "Risk": "G4 Severe geomagnetic storm",
            "Select range": "2025-11-12T00:00:00 to 2025-11-12T05:55:00",
        },
        {
            "Time UTC": "2026-01-19 18:00 to 2026-01-20 00:00",
            "Peak Kp": "8.7",
            "Peak ap": "300",
            "Risk": "G4 Severe geomagnetic storm",
            "Select range": "2026-01-19T18:00:00 to 2026-01-19T23:55:00",
        },
    ])


def build_data_preview(df: pd.DataFrame) -> pd.DataFrame:
    """Return backend-style data rows formatted safely for Streamlit."""
    preview = df.copy()
    for col in ("alert_type", "risk_level", "alert_reason", "possible_aviation_impact"):
        if col not in preview.columns:
            preview[col] = ""
    return make_streamlit_safe_dataframe(preview)


def make_streamlit_safe_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return a display-only frame with object values safe for Streamlit Arrow."""
    if df.empty:
        return df.copy()
    safe = df.copy()
    for column in safe.columns:
        series = safe[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            safe[column] = series.apply(_format_streamlit_value)
        elif series.dtype == "object":
            safe[column] = series.apply(_format_streamlit_value)
    return safe


def _format_streamlit_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple, set)):
        return str(value)
    if isinstance(value, pd.Timestamp):
        timestamp = value
        if timestamp.tzinfo is not None:
            timestamp = timestamp.tz_convert("UTC")
            return timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    if value is None or pd.isna(value):
        return ""
    return value


def mappable_variable_options(df: pd.DataFrame, contains_any: tuple[str, ...] = ()) -> list[str]:
    """Return variables that have numeric latitude and longitude rows."""
    required = {"variable", "lat", "lon"}
    if df.empty or not required.issubset(df.columns):
        return []

    work = df[list(required)].copy()
    work["lat"] = pd.to_numeric(work["lat"], errors="coerce")
    work["lon"] = pd.to_numeric(work["lon"], errors="coerce")
    work = work.dropna(subset=["lat", "lon"])
    if work.empty:
        return []
    variables = sorted(work["variable"].dropna().astype(str).unique())
    if contains_any:
        needles = tuple(part.lower() for part in contains_any)
        variables = [
            var for var in variables
            if any(part in var.lower() for part in needles)
        ]
    return variables


def parse_select_range_to_widgets(select_range: str) -> dict[str, Any] | None:
    """Parse a table range into sidebar widget state values."""
    start, end = _parse_range(select_range)
    if start is None or end is None:
        return None
    return {
        "start_date": start.date(),
        "start_time_clock": start.time().replace(microsecond=0),
        "end_date": end.date(),
        "end_time_clock": end.time().replace(microsecond=0),
    }


def _parse_range(value: str) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    start_text, sep, end_text = value.partition(" to ")
    if not sep:
        return None, None
    return _parse_datetime(start_text), _parse_datetime(end_text)


def _parse_datetime(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    try:
        parsed = pd.to_datetime(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed
