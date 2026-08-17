import os
import sys
import unittest

import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class DataPreviewTest(unittest.TestCase):
    def test_data_preview_converts_mixed_object_values_for_streamlit(self):
        from app_utils import build_data_preview

        df = pd.DataFrame([
            {
                "time": pd.Timestamp("2026-01-19T23:55:00Z"),
                "lat": 50.0,
                "lon": -5.0,
                "variable": "TEC",
                "value": 7.3,
                "request_metadata": {"forecast": 90},
            },
            {
                "time": "N/A",
                "lat": None,
                "lon": None,
                "variable": "MUF3000F2",
                "value": pd.NA,
                "request_metadata": ["missing"],
            },
        ])

        preview = build_data_preview(df)

        self.assertEqual(preview.loc[0, "time"], "2026-01-19 23:55:00 UTC")
        self.assertEqual(preview.loc[1, "time"], "N/A")
        self.assertIsInstance(preview.loc[0, "request_metadata"], str)
        self.assertIsInstance(preview.loc[1, "request_metadata"], str)


if __name__ == "__main__":
    unittest.main()
