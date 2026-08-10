import os
import sys
import unittest

import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from realtime import (
    auto_refresh_eligible,
    safe_analysis_time,
    should_reload_anchor,
)


class RealtimeHelpersTest(unittest.TestCase):
    def test_safe_analysis_time_subtracts_delay_and_floors_to_five_minutes(self):
        reference = pd.Timestamp("2026-08-10T09:09:51Z")

        self.assertEqual(
            safe_analysis_time(reference),
            pd.Timestamp("2026-08-10T08:50:00Z"),
        )

    def test_auto_refresh_requires_live_quick_follow_latest(self):
        self.assertTrue(
            auto_refresh_eligible("Live SERENE API", "Quick Demo", True, True)
        )
        self.assertFalse(
            auto_refresh_eligible(
                "Live SERENE API", "Full ICAO-style mode", True, True
            )
        )

    def test_auto_refresh_rejects_non_live_data_loading_mode(self):
        self.assertFalse(
            auto_refresh_eligible("Cached trial output", "Quick Demo", True, True)
        )

    def test_auto_refresh_rejects_when_follow_latest_is_disabled(self):
        self.assertFalse(
            auto_refresh_eligible("Live SERENE API", "Quick Demo", False, True)
        )

    def test_auto_refresh_rejects_when_auto_refresh_is_disabled(self):
        self.assertFalse(
            auto_refresh_eligible("Live SERENE API", "Quick Demo", True, False)
        )

    def test_gate_helper_annotations_match_the_public_contract(self):
        auto_refresh_hints = auto_refresh_eligible.__annotations__
        reload_hints = should_reload_anchor.__annotations__

        self.assertEqual(
            auto_refresh_hints,
            {
                "data_loading_mode": "str",
                "dashboard_mode": "str",
                "follow_latest": "bool",
                "auto_refresh": "bool",
                "return": "bool",
            },
        )
        self.assertEqual(
            reload_hints,
            {
                "candidate": "pd.Timestamp",
                "last_loaded": "str | pd.Timestamp | None",
                "return": "bool",
            },
        )

    def test_same_anchor_is_not_reloaded(self):
        anchor = pd.Timestamp("2026-08-10T08:50:00Z")

        self.assertFalse(should_reload_anchor(anchor, anchor.isoformat()))
