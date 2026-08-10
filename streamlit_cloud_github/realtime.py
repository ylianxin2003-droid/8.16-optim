from __future__ import annotations

from datetime import datetime

import pandas as pd


PUBLICATION_DELAY = pd.Timedelta(minutes=15)
AIDA_CADENCE = "5min"


def safe_analysis_time(
    reference_time: datetime | pd.Timestamp | None = None,
) -> pd.Timestamp:
    now = (
        pd.Timestamp.now(tz="UTC")
        if reference_time is None
        else pd.Timestamp(reference_time)
    )
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    else:
        now = now.tz_convert("UTC")
    return (now - PUBLICATION_DELAY).floor(AIDA_CADENCE)


def auto_refresh_eligible(
    data_loading_mode, dashboard_mode, follow_latest, auto_refresh
):
    return bool(
        data_loading_mode == "Live SERENE API"
        and dashboard_mode == "Quick Demo"
        and follow_latest
        and auto_refresh
    )


def should_reload_anchor(candidate, last_loaded):
    if last_loaded is None:
        return True
    return pd.Timestamp(candidate) != pd.Timestamp(last_loaded)
