import os
import sys
import unittest

import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class HistoricalRiskWindowsTest(unittest.TestCase):
    def test_historical_events_respect_aida_archive_start(self):
        from app_utils import AIDA_ARCHIVE_START, historical_risk_windows

        windows = historical_risk_windows()
        starts = pd.to_datetime(
            windows["Select range"].str.split(" to ").str[0],
            utc=True,
        )

        archive_start = pd.Timestamp(AIDA_ARCHIVE_START, tz="UTC")
        self.assertTrue((starts >= archive_start).all())

    def test_historical_table_contains_recent_serene_events(self):
        from app_utils import historical_risk_windows

        windows = historical_risk_windows()

        self.assertIn("Risk", windows.columns)
        self.assertIn("Peak Kp", windows.columns)
        self.assertIn("Peak ap", windows.columns)
        self.assertNotIn("Kp", windows.columns)
        self.assertNotIn("ap", windows.columns)
        self.assertIn(
            "2024-10-10T18:00:00 to 2024-10-11T02:55:00",
            set(windows["Select range"]),
        )

    def test_historical_load_ranges_stop_inside_the_displayed_interval(self):
        from app_utils import historical_risk_windows

        windows = historical_risk_windows()
        ends = pd.to_datetime(
            windows["Select range"].str.split(" to ").str[1],
            utc=True,
        )

        self.assertTrue((ends.dt.minute == 55).all())

    def test_select_range_parses_to_sidebar_widget_values(self):
        from datetime import date, time

        from app_utils import parse_select_range_to_widgets

        parsed = parse_select_range_to_widgets(
            "2024-10-10T18:00:00 to 2024-10-11T02:55:00"
        )

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["start_date"], date(2024, 10, 10))
        self.assertEqual(parsed["start_time_clock"], time(18, 0))
        self.assertEqual(parsed["end_date"], date(2024, 10, 11))
        self.assertEqual(parsed["end_time_clock"], time(2, 55))

if __name__ == "__main__":
    unittest.main()
