import json
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


class GfzKpForecastTest(unittest.TestCase):
    def setUp(self):
        from serene_client import SereneClient

        SereneClient._gfz_kp_forecast_cache = None

    @staticmethod
    def _payload():
        return {
            "Time (UTC)": {
                "0": "12-08-2026 12:00",
                "1": "12-08-2026 15:00",
            },
            "median": {"0": 7.5, "1": 8.2},
            "maximum": {"0": 8.4, "1": 9.0},
            "prob >= 8": {"0": 0.2, "1": 0.7},
        }

    def test_parser_preserves_ensemble_values_and_utc_intervals(self):
        from serene_client import SereneClient

        frame = SereneClient.parse_gfz_kp_forecast(self._payload())

        self.assertEqual(frame["interval_start"].tolist(), [
            pd.Timestamp("2026-08-12T12:00:00Z"),
            pd.Timestamp("2026-08-12T15:00:00Z"),
        ])
        self.assertEqual(frame["median"].tolist(), [7.5, 8.2])
        self.assertEqual(frame["maximum"].tolist(), [8.4, 9.0])
        self.assertEqual(
            frame["probability_kp_ge_8"].tolist(), [0.2, 0.7]
        )
        self.assertEqual(frame["source"].unique().tolist(), [
            "GFZ official PAGER/SWIFT ensemble forecast"
        ])

    def test_parser_rejects_incomplete_or_scientifically_invalid_rows(self):
        from serene_client import SereneClient

        malformed_cases = [
            {
                "Time (UTC)": {"0": "12-08-2026 12:00"},
                "median": {"0": 7.5},
                "maximum": {"1": 8.4},
                "prob >= 8": {"0": 0.2},
            },
            {
                "Time (UTC)": {"0": "not-a-time"},
                "median": {"0": 7.5},
                "maximum": {"0": 8.4},
                "prob >= 8": {"0": 0.2},
            },
            {
                "Time (UTC)": {"0": "12-08-2026 12:00"},
                "median": {"0": 9.1},
                "maximum": {"0": 9.1},
                "prob >= 8": {"0": 0.2},
            },
            {
                "Time (UTC)": {"0": "12-08-2026 12:00"},
                "median": {"0": 8.5},
                "maximum": {"0": 8.4},
                "prob >= 8": {"0": 0.2},
            },
            {
                "Time (UTC)": {"0": "12-08-2026 12:00"},
                "median": {"0": 7.5},
                "maximum": {"0": 8.4},
                "prob >= 8": {"0": 1.1},
            },
        ]

        for payload in malformed_cases:
            with self.subTest(payload=payload):
                self.assertTrue(
                    SereneClient.parse_gfz_kp_forecast(payload).empty
                )

    def test_fetch_uses_public_last_product_without_serene_token(self):
        from serene_client import SereneClient

        response = Mock(
            ok=True,
            status_code=200,
            text=json.dumps(self._payload()),
            headers={"Last-Modified": "Wed, 12 Aug 2026 13:05:20 GMT"},
        )
        client = SereneClient(
            base_url="https://api.example", token="private-token"
        )
        client._session.request = Mock(return_value=response)

        ok, message, frame = client.fetch_gfz_kp_forecast()

        self.assertTrue(ok, message)
        self.assertEqual(
            frame["issue_time"].unique().tolist(),
            [pd.Timestamp("2026-08-12T13:05:20Z")],
        )
        request = client._session.request.call_args
        self.assertEqual(
            request.kwargs["url"],
            "https://spaceweather.gfz.de/fileadmin/Kp-Forecast/CSV/"
            "kp_product_file_FORECAST_PAGER_SWIFT_LAST.json",
        )
        self.assertEqual(request.kwargs["headers"], {})
        self.assertNotIn("Authorization", request.kwargs["headers"])

    def test_fetch_cache_is_shared_and_bad_payload_is_controlled(self):
        from serene_client import SereneClient

        valid = Mock(
            ok=True,
            status_code=200,
            text=json.dumps(self._payload()),
            headers={"Last-Modified": "Wed, 12 Aug 2026 13:05:20 GMT"},
        )
        with patch(
            "serene_client.requests.Session.request", return_value=valid
        ) as request:
            first = SereneClient(token="one")
            second = SereneClient(token="two")
            first_result = first.fetch_gfz_kp_forecast()
            second_result = second.fetch_gfz_kp_forecast()

        self.assertTrue(first_result[0])
        self.assertTrue(second_result[0])
        self.assertEqual(request.call_count, 1)

        SereneClient._gfz_kp_forecast_cache = None
        invalid = Mock(
            ok=True,
            status_code=200,
            text="not json",
            headers={},
        )
        client = SereneClient(token="private-token")
        client._session.request = Mock(return_value=invalid)
        ok, message, frame = client.fetch_gfz_kp_forecast()
        self.assertFalse(ok)
        self.assertTrue(frame.empty)
        self.assertIn("malformed JSON", message)


class SereneIndicesTest(unittest.TestCase):
    def setUp(self):
        from serene_client import SereneClient

        SereneClient._gfz_index_cache = {}

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

    @staticmethod
    def _json_response(payload, *, ok=True, status_code=200):
        return Mock(
            ok=ok,
            status_code=status_code,
            text=json.dumps(payload),
        )

    @staticmethod
    def _index_payload(index, values):
        return {
            "datetime": [
                "2026-06-30T21:00:00Z",
                "2026-07-01T00:00:00Z",
            ],
            index: values,
            "status": ["def", "pre"],
        }

    def test_public_gfz_json_uses_exact_range_without_api_token(self):
        from serene_client import SereneClient

        responses = [
            self._json_response(self._index_payload("Kp", [3.0, 4.0])),
            self._json_response(self._index_payload("ap", [7.0, 9.0])),
        ]
        client = SereneClient(base_url="https://api.example", token="private-token")
        client._session.request = Mock(side_effect=responses)

        ok, _message, frame = client.fetch_kp_ap_indices(
            "2026-06-27T00:00:00Z",
            "2026-07-01T00:00:00Z",
        )

        self.assertTrue(ok)
        self.assertFalse(frame.empty)
        self.assertEqual(client._session.request.call_count, 2)
        for request, index in zip(
            client._session.request.call_args_list,
            ("Kp", "ap"),
        ):
            self.assertEqual(request.kwargs["url"], "https://kp.gfz.de/app/json/")
            self.assertEqual(request.kwargs["params"], {
                "start": "2026-06-27T00:00:00Z",
                "end": "2026-07-01T00:00:00Z",
                "index": index,
            })
            self.assertNotIn("Authorization", request.kwargs["headers"])
        self.assertEqual(
            set(frame["source"]), {"GFZ Kp/ap JSON service"}
        )
        self.assertEqual(
            getattr(client, "kp_ap_data_statuses", None),
            ["definitive", "preliminary"],
        )

    def test_gfz_cache_is_shared_for_same_range_and_isolated_by_range(self):
        from serene_client import SereneClient

        def response_for_request(*_args, **kwargs):
            index = kwargs["params"]["index"]
            values = [3.0, 4.0] if index == "Kp" else [7.0, 9.0]
            return self._json_response(self._index_payload(index, values))

        with patch(
            "serene_client.requests.Session.request",
            side_effect=response_for_request,
        ) as request:
            first = SereneClient(base_url="https://api.example", token="one")
            second = SereneClient(base_url="https://api.example", token="two")

            first.fetch_kp_ap_indices(
                "2026-06-27T00:00:00Z", "2026-07-01T00:00:00Z"
            )
            second.fetch_kp_ap_indices(
                "2026-06-27T00:00:00Z", "2026-07-01T00:00:00Z"
            )
            second.fetch_kp_ap_indices(
                "2026-06-28T00:00:00Z", "2026-07-02T00:00:00Z"
            )

        self.assertEqual(request.call_count, 4)

    def test_gfz_exact_range_cache_is_bounded(self):
        from serene_client import SereneClient

        payload = self._index_payload("Kp", [3.0, 4.0])
        client = SereneClient(base_url="https://api.example", token="private-token")
        client._request_from_base = Mock(
            return_value=(True, "OK", json.dumps(payload))
        )

        with patch.dict(
            os.environ,
            {"SERENE_GFZ_INDEX_CACHE_MAX_ENTRIES": "2"},
        ):
            for day in (1, 2, 3):
                client._fetch_gfz_json_index(
                    "Kp",
                    f"2026-07-0{day}T00:00:00Z",
                    f"2026-07-0{day}T03:00:00Z",
                )

        self.assertEqual(len(SereneClient._gfz_index_cache), 2)
        self.assertNotIn(
            ("Kp", "2026-07-01T00:00:00Z", "2026-07-01T03:00:00Z"),
            SereneClient._gfz_index_cache,
        )

    def test_gfz_exact_range_cache_prunes_expired_entries(self):
        from serene_client import KP_AP_CACHE_TTL_SECONDS, SereneClient

        expired_key = ("Kp", "2026-06-01T00:00:00Z", "2026-06-01T03:00:00Z")
        fresh_key = ("Kp", "2026-06-02T00:00:00Z", "2026-06-02T03:00:00Z")
        now = 10_000.0
        SereneClient._gfz_index_cache = {
            expired_key: (now - KP_AP_CACHE_TTL_SECONDS, {"expired": True}),
            fresh_key: (now - 1.0, {"fresh": True}),
        }
        payload = self._index_payload("Kp", [3.0, 4.0])
        client = SereneClient(base_url="https://api.example", token="private-token")
        client._request_from_base = Mock(
            return_value=(True, "OK", json.dumps(payload))
        )

        with patch("serene_client.time.monotonic", return_value=now):
            client._fetch_gfz_json_index(
                "Kp",
                "2026-07-01T00:00:00Z",
                "2026-07-01T03:00:00Z",
            )

        self.assertNotIn(expired_key, SereneClient._gfz_index_cache)
        self.assertIn(fresh_key, SereneClient._gfz_index_cache)

    def test_kp_success_remains_usable_when_ap_request_fails(self):
        from serene_client import SereneClient

        responses = [
            self._json_response(self._index_payload("Kp", [3.0, 4.0])),
            self._json_response({}, ok=False, status_code=503),
        ]
        client = SereneClient(base_url="https://api.example", token="private-token")
        client._session.request = Mock(side_effect=responses)

        ok, message, frame = client.fetch_kp_ap_indices(
            "2026-06-27T00:00:00Z", "2026-07-01T00:00:00Z"
        )

        self.assertTrue(ok)
        self.assertEqual(frame["variable"].unique().tolist(), ["Kp"])
        self.assertEqual(frame.attrs["kp_ap_missing_indices"], ["ap"])
        self.assertEqual(
            getattr(client, "kp_ap_source_latest_time", None),
            pd.Timestamp("2026-07-01T00:00:00Z"),
        )
        self.assertIn("ap unavailable", message)

    def test_kp_failure_returns_unavailable_even_if_ap_would_succeed(self):
        from serene_client import SereneClient

        responses = [
            self._json_response({}, ok=False, status_code=503),
            self._json_response(self._index_payload("ap", [7.0, 9.0])),
        ]
        client = SereneClient(base_url="https://api.example", token="private-token")
        client._session.request = Mock(side_effect=responses)

        ok, message, frame = client.fetch_kp_ap_indices(
            "2026-06-27T00:00:00Z", "2026-07-01T00:00:00Z"
        )

        self.assertFalse(ok)
        self.assertTrue(frame.empty)
        self.assertIn("Kp unavailable", message)

    def test_invalid_or_missing_range_makes_no_gfz_request(self):
        from serene_client import SereneClient

        client = SereneClient(base_url="https://api.example", token="private-token")
        client._session.request = Mock()

        ok, message, frame = client.fetch_kp_ap_indices()

        self.assertFalse(ok)
        self.assertTrue(frame.empty)
        self.assertIn("start and end", message)
        client._session.request.assert_not_called()

        ok, _message, frame = client.fetch_kp_ap_indices(
            "not-a-time", "2026-07-01T00:00:00Z"
        )
        self.assertFalse(ok)
        self.assertTrue(frame.empty)
        client._session.request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
