import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class HfCoverageUiTest(unittest.TestCase):
    def test_plotly_figures_use_full_available_width(self):
        from hf_coverage_ui import _render_plotly_figure

        figure = object()
        with patch("hf_coverage_ui.st.plotly_chart") as plotly_chart:
            _render_plotly_figure(figure)

        plotly_chart.assert_called_once_with(figure, use_container_width=True)

    def _render_case(self, reference_values):
        from streamlit.testing.v1 import AppTest

        rows = [
            {
                "time": "2025-01-01T12:00:00Z",
                "lat": 52.0,
                "lon": -2.0,
                "variable": "MUF3000F2",
                "value": 8.0,
                "reference_value": reference_values[0],
                "product_kind": "analysis",
            },
            {
                "time": "2025-01-01T12:00:00Z",
                "lat": 50.0,
                "lon": -20.0,
                "variable": "MUF3000F2",
                "value": 9.0,
                "reference_value": reference_values[1],
                "product_kind": "analysis",
            },
        ]
        script = f"""
import pandas as pd
import streamlit as st
from data_loader import LoadStatus
from hf_coverage_ui import render_hf_propagation_case_study

st.session_state.status = LoadStatus(
    source="api",
    ok=True,
    metadata={{"analysis_time": "2025-01-01T12:00:00+00:00"}},
)
render_hf_propagation_case_study(pd.DataFrame({rows!r}))
"""
        dashboard = AppTest.from_string(script, default_timeout=20).run()
        self.assertFalse(dashboard.exception, dashboard.exception)
        return dashboard

    def test_non_positive_reference_uses_assumed_psd_ui_copy(self):
        dashboard = self._render_case([None, 0.0])

        self.assertEqual(
            dashboard.slider(key="hf_case_psd_percent").label,
            "Assumed PSD demonstration (%)",
        )
        self.assertEqual(
            dashboard.text_input(key="hf_quiet_time_display").value,
            "Assumed PSD demonstration",
        )
        self.assertTrue(any(
            "Assumed PSD demonstration is active because no positive AIDA "
            "reference is available."
            in caption.value
            for caption in dashboard.caption
        ))

    def test_positive_reference_labels_aida_reference_and_disables_assumption_copy(self):
        dashboard = self._render_case([16.0, 18.0])

        self.assertEqual(
            dashboard.slider(key="hf_case_psd_percent").label,
            "Assumed PSD demonstration (%) — inactive; AIDA reference available",
        )
        self.assertEqual(
            dashboard.text_input(key="hf_quiet_time_display").value,
            "AIDA 30-day same-UTC reference",
        )
        self.assertTrue(any(
            "30-day AIDA reference is active; the assumption slider is ignored."
            in caption.value
            for caption in dashboard.caption
        ))
        warning_text = "\n".join(str(item.value) for item in dashboard.warning)
        self.assertNotIn("keyword arguments have been deprecated", warning_text)

    def test_default_route_is_birmingham_to_new_york(self):
        dashboard = self._render_case([16.0, 18.0])

        self.assertEqual(
            dashboard.selectbox(key="hf_route_mode").value,
            "Preset scenario",
        )
        self.assertEqual(
            dashboard.selectbox(key="hf_route_scenario").value,
            "Birmingham → New York",
        )
        captions = "\n".join(item.value for item in dashboard.caption)
        self.assertIn("Birmingham, United Kingdom", captions)
        self.assertIn("New York, United States", captions)
        self.assertIn("assumed geographic communication endpoints", captions)

    def test_custom_city_mode_uses_named_searchable_endpoints(self):
        dashboard = self._render_case([16.0, 18.0])

        dashboard.selectbox(key="hf_route_mode").select(
            "Custom city-to-city"
        ).run()
        dashboard.selectbox(key="hf_origin_location").select(
            "London, United Kingdom"
        )
        dashboard.selectbox(key="hf_target_location").select(
            "Toronto, Canada"
        ).run()

        captions = "\n".join(item.value for item in dashboard.caption)
        self.assertIn("London, United Kingdom", captions)
        self.assertIn("Toronto, Canada", captions)
        self.assertFalse(dashboard.exception, dashboard.exception)

    def test_advanced_mode_retains_manual_coordinate_inputs(self):
        dashboard = self._render_case([16.0, 18.0])

        dashboard.selectbox(key="hf_route_mode").select(
            "Advanced coordinates"
        ).run()

        self.assertEqual(
            dashboard.number_input(key="hf_custom_tx_lat").label,
            "Origin latitude",
        )
        self.assertEqual(
            dashboard.number_input(key="hf_custom_target_lon").label,
            "Target longitude",
        )


if __name__ == "__main__":
    unittest.main()
