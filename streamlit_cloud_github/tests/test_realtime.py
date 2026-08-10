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

    def test_same_anchor_is_not_reloaded(self):
        anchor = pd.Timestamp("2026-08-10T08:50:00Z")

        self.assertFalse(should_reload_anchor(anchor, anchor.isoformat()))
