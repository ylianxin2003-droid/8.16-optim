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

    def test_loaded_trial_renders_evidence_first_sections(self):
        from streamlit.testing.v1 import AppTest
        from data_loader import IcaoProductBundle, LoadStatus
        from icao_risk import build_icao_summary

        app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
        products = pd.DataFrame([
            {
                "time": "2026-08-11T17:35:00Z",
                "actual_output_time": "2026-08-11T17:35:00Z",
                "variable": "TEC",
                "product_kind": "analysis",
                "lat": 50.0,
                "lon": 0.0,
                "value": 100.0,
                "source": "SERENE AIDA analysis",
            },
            {
                "time": "2026-08-11T17:35:00Z",
                "actual_output_time": "2026-08-11T17:35:00Z",
                "variable": "MUF3000F2",
                "product_kind": "analysis",
                "lat": 50.0,
                "lon": 0.0,
                "value": 8.0,
                "psd_percent": pd.NA,
                "source": "SERENE AIDA analysis",
            },
        ])
        status = LoadStatus(
            source="api",
            ok=True,
            message="Loaded live AIDA data",
            metadata={
                "analysis_time": "2026-08-11T17:35:00Z",
                "actual_analysis_output_time": "2026-08-11T17:35:00Z",
                "forecast_downloads": 0,
            },
        )
        bundle = IcaoProductBundle(
            products=products,
            status=status,
            kp_storm_eligible=None,
        )
        summary = build_icao_summary(products, pd.DataFrame(), eligible=None)
        data = products.copy()
        app = AppTest.from_file(app_path, default_timeout=30).run()
        app.session_state["data"] = data
        app.session_state["status"] = bundle.status
        app.session_state["icao_bundle"] = bundle
        app.session_state["icao_summary"] = summary

        app = app.run(timeout=30)

        headings = [item.value for item in app.subheader]
        markdown = "\n".join(str(item.value) for item in app.markdown)
        self.assertIn("Evidence completeness", headings)
        self.assertIn("Standalone HF Communication Engineering Study", headings)
        self.assertIn("Data Completeness", markdown)
        self.assertFalse(app.exception, [item.value for item in app.exception])

    def test_summary_table_normalises_mixed_values_before_arrow_serialisation(self):
        from app import _style_pecasus_table

        summary = pd.DataFrame({
            "Indicator": ["Vertical TEC", "Post-Storm Depression"],
            "Latest value": [100.0, "N/A"],
            "Status": ["OK", "UNAVAILABLE"],
        })

        styled = _style_pecasus_table(summary)

        self.assertTrue(
            styled.data.applymap(lambda value: isinstance(value, str)).all().all()
        )


if __name__ == "__main__":
    unittest.main()
