import os
import sys
import unittest
from unittest.mock import Mock, patch

import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


GFZ_TEXT = """# PURPOSE: test fixture using the documented GFZ layout
2026 08 12 03.0 04.50 34557.12500 34557.18750  2.000    7 0
2026 08 12 06.0 07.50 34557.25000 34557.31250  1.667    6 1
2026 08 12 09.0 10.50 34557.37500 34557.43750 -1.000   -1 0
"""


class GfzIndicesTest(unittest.TestCase):
    def test_parser_preserves_time_values_source_and_data_status(self):
        from serene_client import SereneClient

        frame = SereneClient.parse_gfz_kp_ap(GFZ_TEXT)

        self.assertEqual(len(frame), 4)
        self.assertEqual(set(frame["variable"]), {"Kp", "ap"})
        self.assertEqual(set(frame["source"]), {"GFZ Kp/ap nowcast"})
        self.assertEqual(set(frame["model"]), {"GFZ Geomagnetic Indices"})
        self.assertEqual(
            set(frame["data_status"]), {"preliminary", "definitive"}
        )
        kp = frame[frame["variable"] == "Kp"].sort_values("time")
        self.assertEqual(
            kp["time"].tolist(),
            [
                pd.Timestamp("2026-08-12T03:00:00Z"),
                pd.Timestamp("2026-08-12T06:00:00Z"),
            ],
        )
        self.assertEqual(kp["value"].tolist(), [2.0, 1.667])

    def test_parser_filters_inclusively_and_omits_missing_sentinels(self):
        from serene_client import SereneClient

        frame = SereneClient.parse_gfz_kp_ap(
            GFZ_TEXT,
            start_time="2026-08-12T06:00:00Z",
            end_time="2026-08-12T09:00:00Z",
        )

        self.assertEqual(len(frame), 2)
        self.assertEqual(set(frame["variable"]), {"Kp", "ap"})
        self.assertEqual(
            set(frame["time"]), {pd.Timestamp("2026-08-12T06:00:00Z")}
        )
        self.assertNotIn(-1.0, frame["value"].tolist())

    def test_parser_returns_empty_frame_for_malformed_input(self):
        from serene_client import SereneClient

        frame = SereneClient.parse_gfz_kp_ap("not a GFZ data row")

        self.assertTrue(frame.empty)


class GfzJsonIndicesTest(unittest.TestCase):
    def test_parser_preserves_values_source_and_mapped_status(self):
        from serene_client import SereneClient

        payload = {
            "datetime": [
                "2026-07-01T00:00:00Z",
                "2026-07-01T03:00:00Z",
            ],
            "Kp": [3.0, 4.0],
            "status": ["def", "pre"],
        }

        frame = SereneClient.parse_gfz_json_index(payload, "Kp")

        self.assertEqual(frame["time"].tolist(), [
            pd.Timestamp("2026-07-01T00:00:00Z"),
            pd.Timestamp("2026-07-01T03:00:00Z"),
        ])
        self.assertEqual(frame["value"].tolist(), [3.0, 4.0])
        self.assertEqual(frame["variable"].tolist(), ["Kp", "Kp"])
        self.assertEqual(
            frame["data_status"].tolist(),
            ["definitive", "preliminary"],
        )
        self.assertEqual(
            frame["source"].unique().tolist(),
            ["GFZ Kp/ap JSON service"],
        )

    def test_parser_rejects_malformed_arrays_and_invalid_values(self):
        from serene_client import SereneClient

        malformed = {
            "datetime": ["2026-07-01T00:00:00Z"],
            "ap": [7.0, 8.0],
            "status": ["def"],
        }
        invalid = {
            "datetime": [
                "2026-07-01T00:00:00Z",
                "2026-07-01T03:00:00Z",
                "2026-07-01T06:00:00Z",
            ],
            "ap": [-1.0, float("nan"), float("inf")],
            "status": ["def", "pre", "pre"],
        }

        self.assertTrue(
            SereneClient.parse_gfz_json_index(malformed, "ap").empty
        )
        self.assertTrue(
            SereneClient.parse_gfz_json_index(invalid, "ap").empty
        )
        self.assertTrue(
            SereneClient.parse_gfz_json_index(malformed, "Dst").empty
        )


class SereneIndicesTest(unittest.TestCase):
    def setUp(self):
        from serene_client import SereneClient

        SereneClient._kp_ap_csv_cache = None

    def test_parse_kp_ap_csv_filters_selected_time_range(self):
        from serene_client import SereneClient

        csv_text = (
            "time,Kp,ap,rAp\n"
            "2024-05-10T21:00:00Z,8.7,300,250\n"
            "2024-05-11T00:00:00Z,9.0,400,300\n"
            "2024-06-01T00:00:00Z,2.0,7,8\n"
        )

        df = SereneClient.parse_kp_ap_csv(
            csv_text,
            start_time="2024-05-11T00:00:00",
            end_time="2024-05-11T03:00:00",
        )

        self.assertEqual(set(df["variable"]), {"Kp", "ap"})
        self.assertEqual(len(df), 2)
        self.assertEqual(df["source"].iloc[0], "SERENE API Kp/ap")

    def test_kp_ap_rows_generate_geomagnetic_storm_risk(self):
        from alert_engine import generate_alerts, generate_overall_risk

        df = pd.DataFrame([
            {
                "time": "2024-05-11T00:00:00Z",
                "lat": None,
                "lon": None,
                "variable": "Kp",
                "value": 9.0,
                "model": "SERENE Indices",
            },
            {
                "time": "2024-05-11T00:00:00Z",
                "lat": None,
                "lon": None,
                "variable": "ap",
                "value": 400,
                "model": "SERENE Indices",
            },
        ])

        alerts = generate_alerts(df)
        overall, _summary = generate_overall_risk(alerts)

        self.assertEqual(overall, "G5 Extreme")
        self.assertIn("Geomagnetic storm risk", set(alerts["alert_type"]))
        self.assertIn("G5 Extreme", set(alerts["risk_level"]))

    def test_public_gfz_download_uses_exact_url_without_api_token(self):
        from serene_client import SereneClient

        response = Mock(ok=True, text=GFZ_TEXT)
        client = SereneClient(base_url="https://api.example", token="private-token")
        client._session.request = Mock(return_value=response)

        ok, _message, frame = client.fetch_kp_ap_indices()

        self.assertTrue(ok)
        self.assertFalse(frame.empty)
        request = client._session.request.call_args
        self.assertEqual(
            request.kwargs["url"],
            "https://kp.gfz.de/fileadmin/files_for_gfz_cms/"
            "Kp_ap_nowcast.txt",
        )
        headers = request.kwargs["headers"]
        self.assertNotIn("Authorization", headers)
        self.assertEqual(set(frame["source"]), {"GFZ Kp/ap nowcast"})
        self.assertEqual(
            getattr(client, "kp_ap_data_statuses", None),
            ["definitive", "preliminary"],
        )

    def test_public_gfz_download_is_reused_across_client_instances(self):
        from serene_client import SereneClient

        response = Mock(ok=True, text=GFZ_TEXT)
        with patch("serene_client.requests.Session.request", return_value=response) as request:
            first = SereneClient(base_url="https://api.example", token="one")
            second = SereneClient(base_url="https://api.example", token="two")

            first.fetch_kp_ap_indices()
            second.fetch_kp_ap_indices()

        self.assertEqual(request.call_count, 1)

    def test_empty_filtered_range_reports_latest_gfz_timestamp(self):
        from serene_client import SereneClient

        response = Mock(ok=True, text=GFZ_TEXT)
        client = SereneClient(base_url="https://api.example", token="private-token")
        client._session.request = Mock(return_value=response)

        ok, message, frame = client.fetch_kp_ap_indices(
            "2026-08-13T00:00:00Z", "2026-08-14T00:00:00Z"
        )

        self.assertFalse(ok)
        self.assertTrue(frame.empty)
        self.assertEqual(
            getattr(client, "kp_ap_source_latest_time", None),
            pd.Timestamp("2026-08-12T06:00:00Z"),
        )
        self.assertIn("GFZ Kp/ap", message)
        self.assertIn("2026-08-12 06:00 UTC", message)

    def test_cached_gfz_text_sets_latest_timestamp_and_statuses_on_each_client(self):
        from serene_client import SereneClient

        response = Mock(ok=True, text=GFZ_TEXT)
        with patch("serene_client.requests.Session.request", return_value=response):
            first = SereneClient(base_url="https://api.example", token="one")
            second = SereneClient(base_url="https://api.example", token="two")

            first.fetch_kp_ap_indices()
            second.fetch_kp_ap_indices()

        expected = pd.Timestamp("2026-08-12T06:00:00Z")
        self.assertEqual(getattr(first, "kp_ap_source_latest_time", None), expected)
        self.assertEqual(getattr(second, "kp_ap_source_latest_time", None), expected)
        self.assertEqual(first.kp_ap_data_statuses, ["definitive", "preliminary"])
        self.assertEqual(second.kp_ap_data_statuses, ["definitive", "preliminary"])

    def test_malformed_gfz_text_is_reported_without_raising(self):
        from serene_client import SereneClient

        response = Mock(ok=True, text="not a GFZ data row")
        client = SereneClient(base_url="https://api.example", token="private-token")
        client._session.request = Mock(return_value=response)

        ok, message, frame = client.fetch_kp_ap_indices()

        self.assertFalse(ok)
        self.assertTrue(frame.empty)
        self.assertIn("GFZ Kp/ap", message)


if __name__ == "__main__":
    unittest.main()
