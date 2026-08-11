import os
import sys
import unittest

import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class IcaoAppHelpersTest(unittest.TestCase):
    def test_requested_window_rejects_reversed_range(self):
        from app_utils import validate_requested_window

        error = validate_requested_window(
            "2026-06-24T13:00:00Z",
            "2026-06-24T12:00:00Z",
            publication_safe_now=pd.Timestamp("2026-06-24T14:00:00Z"),
        )

        self.assertIn("before", error)

    def test_requested_window_rejects_unpublished_future(self):
        from app_utils import validate_requested_window

        error = validate_requested_window(
            "2026-06-24T10:00:00Z",
            "2026-06-24T13:50:00Z",
            publication_safe_now=pd.Timestamp("2026-06-24T13:45:00Z"),
        )

        self.assertIn("future", error)

    def test_advisory_metadata_is_stable_and_clears_on_failed_load(self):
        from app_utils import advisory_metadata_for_load

        generated = pd.Timestamp("2026-06-24T12:00:00Z")
        success = advisory_metadata_for_load(True, 4, generated)
        failure = advisory_metadata_for_load(False, success["sequence"], generated)

        self.assertEqual(success["sequence"], 5)
        self.assertEqual(success["number"], "2026/005")
        self.assertEqual(success["generated_time"], generated)
        self.assertEqual(failure, {
            "sequence": 5,
            "generated_time": None,
            "number": None,
        })

    def test_successful_live_load_is_not_described_as_api_not_tested(self):
        from app_utils import loaded_api_state
        from data_loader import LoadStatus

        status = LoadStatus(source="api", ok=True, message="Live AIDA loaded")

        level, text = loaded_api_state(status, None, "Not tested yet.")

        self.assertEqual(level, "success")
        self.assertIn("live load succeeded", text.lower())

    def test_provenance_metadata_exposes_full_utc_values(self):
        from app_utils import build_provenance_metadata

        rows = build_provenance_metadata(
            "2026-08-11T17:35:00Z",
            pd.Timestamp("2026-08-11T17:35:00Z"),
            pd.Timestamp("2026-08-11T17:36:00Z"),
            pd.Timestamp("2026-08-11T18:00:00Z"),
            3,
        )

        self.assertEqual(rows[0], {
            "label": "Requested analysis",
            "value": "2026-08-11 17:35 UTC",
        })
        self.assertEqual(rows[1]["value"], "2026-08-11 17:35 UTC")
        self.assertEqual(rows[2]["value"], "2026-08-11 17:36 UTC")
        self.assertEqual(rows[3]["value"], "25 min")
        self.assertEqual(rows[-1]["value"], "3 official")

    def test_display_data_keeps_rolling_products_for_time_series(self):
        from app import _build_display_data
        from data_loader import IcaoProductBundle, LoadStatus

        products = pd.DataFrame([
            {
                "time": "2025-01-01T17:50:00Z",
                "variable": "TEC",
                "value": 11.0,
                "product_kind": "rolling",
            },
            {
                "time": "2025-01-01T17:55:00Z",
                "variable": "TEC",
                "value": 12.0,
                "product_kind": "analysis",
            },
        ])
        indices = pd.DataFrame([{
            "time": "2025-01-01T17:55:00Z",
            "variable": "Kp",
            "value": 8.0,
        }])
        bundle = IcaoProductBundle(
            products=products,
            indices=indices,
            status=LoadStatus(source="api", ok=True, message="loaded"),
        )

        display = _build_display_data(bundle)

        self.assertEqual(len(display), 3)
        self.assertIn("rolling", set(display["product_kind"].dropna()))

    def test_streamlit_app_starts_without_exception(self):
        from streamlit.testing.v1 import AppTest

        app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
        app = AppTest.from_file(app_path, default_timeout=30).run()

        self.assertFalse(app.exception, [item.value for item in app.exception])


if __name__ == "__main__":
    unittest.main()
