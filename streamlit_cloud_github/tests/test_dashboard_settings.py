import os
import sys
import unittest
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
APP_PATH = PROJECT_ROOT / "app.py"
HF_UI_PATH = PROJECT_ROOT / "hf_coverage_ui.py"
VALIDATION_UI_PATH = PROJECT_ROOT / "validation_ui.py"
CLIENT_PATH = PROJECT_ROOT / "serene_client.py"
REQUIREMENTS_PATH = PROJECT_ROOT / "requirements.txt"
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
README_PATH = REPOSITORY_ROOT / "README.md"
DEVCONTAINER_PATH = REPOSITORY_ROOT / ".devcontainer" / "devcontainer.json"


class DashboardSettingsTest(unittest.TestCase):
    def test_app_uses_current_streamlit_width_parameter(self):
        app_source = APP_PATH.read_text()

        self.assertNotIn("use_container_width", app_source)

    def test_devcontainer_installs_the_application_requirements(self):
        devcontainer = DEVCONTAINER_PATH.read_text()

        self.assertIn(
            "streamlit_cloud_github/requirements.txt",
            devcontainer,
        )

    def test_app_describes_local_grid_not_per_point_api_calls(self):
        app_source = APP_PATH.read_text()

        self.assertNotIn('"TOMIRIS"', app_source)
        self.assertNotIn("capped at {MAX_GRID_POINTS}", app_source)
        self.assertIn("Local map points", app_source)
        self.assertIn("Rolling/analysis states", app_source)
        self.assertIn("Official forecast states", app_source)
        self.assertIn("calculated locally", app_source)
        self.assertNotIn("output catalog", app_source.lower())

    def test_legacy_point_grid_api_path_is_removed(self):
        client_source = CLIENT_PATH.read_text()

        self.assertNotIn("MAX_GRID_POINTS", client_source)
        self.assertNotIn("def _fetch_calc_grid", client_source)
        self.assertNotIn("def fetch_model_output", client_source)

    def test_legacy_catalogue_code_is_removed(self):
        client_source = CLIENT_PATH.read_text()

        self.assertNotIn("BeautifulSoup", client_source)
        self.assertNotIn("fetch_aida_catalog", client_source)
        self.assertNotIn("param_2d", client_source)
        self.assertIn("breid-phys/aida-ionosphere", client_source)

    def test_invalid_timeout_falls_back_to_default(self):
        from config import _parse_timeout

        self.assertEqual(_parse_timeout("not-a-number"), 30)
        self.assertEqual(_parse_timeout("0"), 30)
        self.assertEqual(_parse_timeout("45"), 45)

    def test_upstream_aida_dependency_is_pinned(self):
        requirements = REQUIREMENTS_PATH.read_text()

        self.assertIn("numpy>=1.25,<2", requirements)
        self.assertIn("pandas<2", requirements)
        self.assertIn(
            "git+https://github.com/breid-phys/aida-ionosphere.git@v0.1.3",
            requirements,
        )
        self.assertNotIn("beautifulsoup4", requirements)

    def test_streamlit_fragment_runtime_is_declared(self):
        requirements = REQUIREMENTS_PATH.read_text()

        self.assertIn("streamlit>=1.37,<2", requirements)

    def test_sidebar_uses_one_full_icao_path_without_refresh_controls(self):
        from streamlit.testing.v1 import AppTest

        dashboard = AppTest.from_file(str(APP_PATH), default_timeout=20).run()

        radio_labels = [widget.label for widget in dashboard.radio]
        checkbox_labels = [widget.label for widget in dashboard.checkbox]
        self.assertNotIn("Mode", radio_labels)
        self.assertNotIn("Follow latest near-real-time", checkbox_labels)
        self.assertNotIn("Auto-refresh every 15 minutes", checkbox_labels)
        self.assertFalse(dashboard.date_input(key="end_date").disabled)
        self.assertFalse(dashboard.time_input(key="end_time_clock").disabled)

    def test_data_provenance_is_exposed_in_status_panel(self):
        source = APP_PATH.read_text(encoding="utf-8") + (
            PROJECT_ROOT / "app_utils.py"
        ).read_text(encoding="utf-8")

        for label in (
            "Requested analysis",
            "Actual AIDA output",
            "Data age",
            "Retrieved",
            "Forecast horizons",
        ):
            self.assertIn(label, source)

    def test_actual_analysis_output_time_uses_returned_state_time(self):
        import app
        from data_loader import LoadStatus

        returned = pd.Timestamp("2026-08-10T08:47:00Z")
        requested = pd.Timestamp("2026-08-10T08:50:00Z")
        state = SimpleNamespace(
            status=LoadStatus(metadata={
                "analysis_time": requested.isoformat(),
            }),
            icao_bundle=SimpleNamespace(products=pd.DataFrame([{
                "product_kind": "analysis",
                "time": requested,
                "valid_time": requested,
                "requested_time": requested,
                "actual_output_time": returned,
            }])),
        )

        with patch.object(app.st, "session_state", state):
            actual = app._actual_analysis_output_time()

        self.assertEqual(actual, returned)

    def test_forecast_audit_explains_api_file_time_and_local_valid_time(self):
        from streamlit.testing.v1 import AppTest

        script = """
import pandas as pd
import streamlit as st
from app import _render_forecast_request_audit
from data_loader import LoadStatus

st.session_state.status = LoadStatus(metadata={
    "forecast_request_audit": [{
        "analysis_time": "2026-08-10T08:50:00+00:00",
        "valid_time": "2026-08-10T10:20:00+00:00",
        "forecast_parameter": 90,
        "latency": "ultra",
        "downloaded_from_serene": True,
        "message": "downloaded",
    }],
})
_render_forecast_request_audit(pd.DataFrame())
"""
        dashboard = AppTest.from_string(script, default_timeout=20).run()

        self.assertFalse(dashboard.exception, dashboard.exception)
        audit_copy = " ".join(caption.value for caption in dashboard.caption)
        self.assertIn(
            "SERENE API request sends the analysis time as file_time and the "
            "horizon as period",
            audit_copy,
        )
        self.assertIn(
            "forecast valid time is derived locally as analysis time plus period",
            audit_copy,
        )
        self.assertNotIn("request sends that valid time", audit_copy)

    def test_example_uses_raw_api_host(self):
        example = ENV_EXAMPLE_PATH.read_text()

        self.assertIn(
            "SERENE_API_BASE_URL=https://spaceweather.bham.ac.uk",
            example,
        )
        self.assertIn("SERENE_AIDA_ARCHIVE_START=2024-09-28T00:00:00Z", example)

    def test_combine_date_time_to_iso8601(self):
        from app_utils import combine_date_time_iso

        value = combine_date_time_iso(date(2026, 6, 7), time(12, 0, 43))

        self.assertEqual(value, "2026-06-07T12:00:43")

    def test_default_time_range_avoids_unpublished_near_realtime_output(self):
        from app_utils import default_time_range

        now = datetime(2026, 6, 22, 18, 49, 37, tzinfo=timezone.utc)

        start, end = default_time_range(now)

        self.assertEqual(
            end,
            datetime(2026, 6, 22, 18, 30, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(start, end - timedelta(hours=6))

    def test_aida_date_inputs_use_archive_minimum(self):
        app_source = APP_PATH.read_text()

        self.assertEqual(app_source.count("min_value=AIDA_ARCHIVE_START"), 1)
        self.assertIn('"Analysis date"', app_source)
        self.assertNotIn('"Start date"', app_source)

    def test_analysis_widgets_do_not_mix_session_state_with_value_defaults(self):
        app_source = APP_PATH.read_text()
        date_widget = app_source.split("end_date = st.date_input(", 1)[1].split(
            ")", 1
        )[0]
        time_widget = app_source.split("end_clock = st.time_input(", 1)[1].split(
            ")", 1
        )[0]

        self.assertIn('if "end_date" not in st.session_state', app_source)
        self.assertIn('if "end_time_clock" not in st.session_state', app_source)
        self.assertNotIn("\n            value=", date_widget)
        self.assertNotIn("\n            value=", time_widget)

    def test_app_distinguishes_global_and_regional_risk(self):
        app_source = APP_PATH.read_text()

        self.assertIn("Global Kp/ap are excluded", app_source)
        self.assertIn("analysis time", app_source)
        self.assertIn('st.metric(f"Peak {variable}"', app_source)

    def test_app_exposes_serene_only_icao_products(self):
        app_source = APP_PATH.read_text()

        self.assertIn("ICAO/PECASUS-style summary table", app_source)
        self.assertIn("Current aviation risk and evidence status", app_source)
        self.assertIn("Evidence completeness", app_source)
        self.assertIn("Categorical risk map", app_source)
        self.assertIn("Raw variable maps", app_source)
        self.assertIn("Automated text-based SPWX research messages", app_source)
        self.assertIn("load_icao_products", app_source)
        self.assertIn("build_icao_summary", app_source)
        self.assertIn("create_icao_category_map", app_source)
        self.assertIn("only SERENE-supported, derived, or proxy indicators", app_source)
        self.assertNotIn("Not available from SERENE", app_source)
        self.assertIn("generate_icao_message", app_source)
        self.assertIn("Download GNSS research message", app_source)
        self.assertIn("Download HF COM research message", app_source)

    def test_app_uses_full_icao_processing_for_every_load(self):
        app_source = APP_PATH.read_text()

        self.assertIn("Full ICAO-style mode", app_source)
        self.assertIn('params["include_three_hour_window"] = True', app_source)
        self.assertIn('params["include_psd_baseline"] = True', app_source)
        self.assertNotIn("Quick Demo", app_source)
        self.assertIn("Demo / validation storm windows", app_source)
        self.assertNotIn("Historical risk windows", app_source)

    def test_event_windows_are_optional_shortcuts_not_time_locks(self):
        app_source = APP_PATH.read_text()

        self.assertIn("Custom analysis time can be entered manually", app_source)
        self.assertIn("Use selected event time", app_source)
        self.assertIn("apply_event_time_sidebar", app_source)
        self.assertNotIn("apply_event_time_main", app_source)

    def test_app_defaults_to_global_grid_and_cache_mode(self):
        app_source = APP_PATH.read_text()

        self.assertIn('st.number_input("Lat min", value=-90.0', app_source)
        self.assertIn('st.number_input("Lat max", value=90.0', app_source)
        self.assertIn('st.number_input("Lon min", value=-180.0', app_source)
        self.assertIn('st.number_input("Lon max", value=180.0', app_source)
        self.assertIn('st.slider("Grid step (degrees)", 2.0, 30.0, 15.0, 1.0)', app_source)
        self.assertIn("The default grid is global for aviation-scale awareness", app_source)
        self.assertIn("Cached trial output", app_source)
        self.assertIn("Live SERENE API", app_source)

    def test_app_mentions_cached_trial_outputs_in_method_text(self):
        app_source = APP_PATH.read_text()

        self.assertIn("cached trial outputs", app_source.lower())
        self.assertIn("Live SERENE API", app_source)
        self.assertIn("Save current result as cached trial output", app_source)

    def test_four_horizon_map_and_summary_render_without_audit_only_copy(self):
        from streamlit.testing.v1 import AppTest

        script = '''
import pandas as pd
import streamlit as st
from app import _render_categorical_risk_map, _render_pecasus_summary_table
from data_loader import IcaoProductBundle, LoadStatus
from icao_risk import build_icao_summary

products = pd.DataFrame([
    {
        "indicator": "Vertical TEC", "horizon": horizon,
        "lat": 50.0, "lon": 0.0, "value": value,
        "time": "2026-08-12T13:00:00Z", "source": "SERENE official forecast",
    }
    for horizon, value in [
        ("Latest", 10.0), ("+30 min", 20.0), ("+90 min", 30.0),
        ("+3h", 40.0), ("+6h", 50.0),
    ]
])
kp_horizons = pd.DataFrame([
    {
        "horizon_minutes": period,
        "target_time": "2026-08-12T13:00:00Z",
        "value": 5.0,
        "evidence_role": "official_forecast",
        "source": "GFZ official PAGER/SWIFT ensemble forecast",
        "ensemble_maximum": 6.0,
        "probability_kp_ge_8": 0.0,
        "issue_time": "2026-08-12T12:00:00Z",
        "data_status": "forecast",
    }
    for period in (30, 90, 180, 360)
])
status = LoadStatus(metadata={"available_primary_forecast_periods": [30, 90, 180, 360]})
st.session_state.status = status
st.session_state.icao_bundle = IcaoProductBundle(
    products=products, status=status, kp_horizons=kp_horizons,
)
st.session_state.icao_summary = build_icao_summary(
    products, pd.DataFrame(), kp_horizons=kp_horizons,
)
_render_categorical_risk_map()
_render_pecasus_summary_table()
'''
        dashboard = AppTest.from_string(script, default_timeout=20).run()

        self.assertFalse(dashboard.exception, dashboard.exception)
        self.assertEqual(dashboard.radio[0].options, [
            "Latest", "+30 min", "+90 min", "+3h", "+6h",
        ])
        dashboard.radio[0].set_value("+6h").run()
        self.assertFalse(dashboard.exception, dashboard.exception)
        rendered_copy = " ".join(
            str(item.value) for item in [*dashboard.caption, *dashboard.markdown]
        )
        self.assertIn("Kp +30/+90/+3h/+6h horizon evidence", rendered_copy)
        self.assertIn("backtesting only", rendered_copy)
        self.assertNotIn("audit only", rendered_copy.lower())

    def test_app_exposes_hf_propagation_case_study(self):
        app_source = APP_PATH.read_text()
        hf_ui_source = HF_UI_PATH.read_text()
        hf_ui_one_line = hf_ui_source.replace("\n", " ")
        readme = README_PATH.read_text()

        self.assertIn("render_hf_propagation_case_study", app_source)
        self.assertNotIn("def _render_hf_propagation_case_study", app_source)
        self.assertIn("Engineering Impact: HF Communication Coverage", hf_ui_source)
        self.assertIn("Phase 1: MUF-based coverage proxy", hf_ui_source)
        self.assertIn("Phase 2: experimental Trace", hf_ui_source)
        self.assertIn("Trace HF ray-tracing", hf_ui_source)
        self.assertIn("MUF-threshold demonstration", hf_ui_source)
        self.assertIn("Engineering workflow: Input", hf_ui_source)
        self.assertIn("Processing = quiet/background MUF compared with storm MUF", hf_ui_source)
        self.assertIn("Engineering meaning = PSD lowers MUF", hf_ui_source)
        self.assertIn("Decision support = route status", hf_ui_source)
        self.assertIn("Quiet coverage", hf_ui_source)
        self.assertIn("Storm coverage", hf_ui_source)
        self.assertIn("Coverage loss", hf_ui_source)
        self.assertIn("Route profile", hf_ui_source)
        self.assertIn("Validation profile", hf_ui_source)
        self.assertIn("quiet/background MUF compares with storm MUF", hf_ui_source)
        self.assertIn("Quiet route availability", hf_ui_source)
        self.assertIn("Route coverage reduction", hf_ui_source)
        self.assertIn("Degraded route", hf_ui_source)
        self.assertIn("Unavailable route", hf_ui_source)
        self.assertIn("Route decision support", hf_ui_source)
        self.assertIn("Frequency sweep", hf_ui_source)
        self.assertIn("Research comparison only", hf_ui_source)
        self.assertIn("model-based", hf_ui_one_line)
        self.assertIn("storm-case recommendation", hf_ui_one_line)
        self.assertIn("not operational frequency advice", hf_ui_source)
        self.assertIn("not an operational", hf_ui_source.replace("\n", " "))
        self.assertIn("not a full propagation solver", hf_ui_source.replace("\n", " "))
        self.assertIn("does not generate physical ray paths", hf_ui_source)
        self.assertIn("altitude-resolved electron-density", hf_ui_source)
        self.assertIn("HF communication study", readme)
        self.assertIn("does not perform physical ray tracing", readme)
        self.assertIn("Data sources and provenance", readme)
        self.assertIn("Communication Impact", readme)

    def test_app_exposes_validation_section_for_decision_support(self):
        app_source = APP_PATH.read_text()
        validation_source = VALIDATION_UI_PATH.read_text()

        self.assertIn("render_validation_section", app_source)
        self.assertNotIn("def _render_validation_section", app_source)
        self.assertIn("Validation and engineering assumptions", validation_source)
        self.assertIn("Historical event replay", validation_source)
        self.assertIn("Quiet vs storm comparison", validation_source)
        self.assertIn("PSD sensitivity", validation_source)
        self.assertIn("Frequency sensitivity", validation_source)
        self.assertIn("Route assessment verification", validation_source)
        self.assertIn("MUF-threshold engineering proxy", validation_source)

    def test_readme_explains_four_horizon_primary_evidence(self):
        readme = README_PATH.read_text()
        readme_one_line = readme.replace("\n", " ")

        self.assertIn("+30 minutes, +90 minutes, +3 hours and +6 hours", readme_one_line)
        self.assertIn("OFFICIAL SERENE API", readme_one_line)
        self.assertIn("Every forecast value carries a source label", readme_one_line)
        self.assertIn("UNAVAILABLE", readme_one_line)
        self.assertIn("TEST research messages", readme_one_line)
        self.assertNotIn("audit only", readme.lower())
        self.assertNotIn(
            "columns use official SERENE AIDA forecast HDF5 products",
            readme,
        )


if __name__ == "__main__":
    unittest.main()
