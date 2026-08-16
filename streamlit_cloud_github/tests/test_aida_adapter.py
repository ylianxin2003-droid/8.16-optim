import os
import sys
import unittest

import numpy as np


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class FakeAIDAState:
    def __init__(self):
        self.Time = 1735740000.0
        self.read_path = None
        self.last_kwargs = None

    def readFile(self, path):
        self.read_path = path
        if not os.path.exists(path):
            raise AssertionError("temporary raw state must exist while readFile runs")

    def calc(self, **kwargs):
        self.last_kwargs = kwargs
        lats = np.asarray(kwargs["lat"], dtype=float)
        lons = np.asarray(kwargs["lon"], dtype=float)
        values = np.add.outer(lons, lats)
        return {
            "TEC": values,
            "foF2": values + 1,
            "MUF3000": values + 2,
            "NmF2": values + 3,
            "hmF2": values + 4,
        }


class AidaAdapterTest(unittest.TestCase):
    def test_field_frame_preserves_lon_major_lat_minor_order(self):
        import aida_adapter

        self.assertTrue(hasattr(aida_adapter, "_field_frame"))

        frame = aida_adapter._field_frame(
            values=np.asarray([[20.0, 25.0, 30.0], [25.0, 30.0, 35.0]]),
            target_lats=np.asarray([0.0, 5.0, 10.0]),
            target_lons=np.asarray([20.0, 25.0]),
            variable="TEC",
            output_time="2025-01-01T14:00:00Z",
        )

        self.assertEqual(frame["lat"].tolist(), [0.0, 5.0, 10.0, 0.0, 5.0, 10.0])
        self.assertEqual(frame["lon"].tolist(), [20.0, 20.0, 20.0, 25.0, 25.0, 25.0])
        self.assertEqual(frame["value"].tolist(), [20.0, 25.0, 30.0, 25.0, 30.0, 35.0])

    def test_raw_state_time_is_read_from_official_state(self):
        import pandas as pd

        from aida_adapter import read_aida_state_time

        state = FakeAIDAState()
        state.Time = 1786530900.0

        actual = read_aida_state_time(
            b"raw-state",
            state_factory=lambda: state,
        )

        self.assertEqual(actual, pd.Timestamp("2026-08-12T10:35:00Z"))
        self.assertFalse(os.path.exists(state.read_path))

    def test_raw_state_time_rejects_invalid_official_time(self):
        from aida_adapter import read_aida_state_time
        from aida_grid import AidaGridError

        state = FakeAIDAState()
        state.Time = "not-a-time"

        with self.assertRaisesRegex(AidaGridError, "Invalid official AIDA state time"):
            read_aida_state_time(
                b"raw-state",
                state_factory=lambda: state,
            )

    def test_adapter_calculates_exact_grid_and_maps_muf_name(self):
        from aida_adapter import calculate_aida_grid

        frame = calculate_aida_grid(
            b"raw-state",
            region={"lat_min": 0, "lat_max": 10, "lon_min": 20, "lon_max": 30},
            step=5,
            variables=["TEC", "MUF3000F2"],
            state_factory=FakeAIDAState,
        )

        self.assertEqual(sorted(frame["lat"].unique().tolist()), [0.0, 5.0, 10.0])
        self.assertEqual(sorted(frame["lon"].unique().tolist()), [20.0, 25.0, 30.0])
        self.assertEqual(set(frame["variable"]), {"TEC", "MUF3000F2"})
        muf = frame[
            (frame["lat"] == 5)
            & (frame["lon"] == 25)
            & (frame["variable"] == "MUF3000F2")
        ]
        self.assertEqual(float(muf.iloc[0]["value"]), 32.0)
        self.assertIn("breid-phys/aida-ionosphere", frame.iloc[0]["source"])

    def test_adapter_calls_upstream_grid_contract(self):
        from aida_adapter import calculate_aida_grid

        state = FakeAIDAState()
        calculate_aida_grid(
            b"raw-state",
            region={"lat_min": -5, "lat_max": 5, "lon_min": 0, "lon_max": 10},
            step=5,
            variables=["TEC"],
            state_factory=lambda: state,
        )

        self.assertEqual(state.last_kwargs["grid"], "3D")
        self.assertTrue(state.last_kwargs["TEC"])
        self.assertFalse(state.last_kwargs["MUF3000"])
        self.assertTrue(state.last_kwargs["collapse_particles"])
        self.assertTrue(state.last_kwargs["as_dict"])
        self.assertFalse(os.path.exists(state.read_path))

    def test_adapter_preserves_state_time_as_actual_output_time(self):
        import pandas as pd

        from aida_adapter import calculate_aida_grid

        frame = calculate_aida_grid(
            b"raw-state",
            region={"lat_min": 0, "lat_max": 0, "lon_min": 0, "lon_max": 0},
            step=5,
            variables=["TEC"],
            state_factory=FakeAIDAState,
        )

        expected = pd.Timestamp("2025-01-01T14:00:00Z")
        self.assertIn("actual_output_time", frame.columns)
        self.assertEqual(frame.iloc[0]["actual_output_time"], expected)
        self.assertEqual(frame.iloc[0]["time"], expected)

    def test_adapter_rejects_incorrect_upstream_array_orientation(self):
        from aida_adapter import calculate_aida_grid
        from aida_grid import AidaGridError

        class WrongShapeState(FakeAIDAState):
            def calc(self, **kwargs):
                return {"TEC": np.zeros((3, 2))}

        with self.assertRaisesRegex(AidaGridError, "expected"):
            calculate_aida_grid(
                b"raw-state",
                region={"lat_min": 0, "lat_max": 10, "lon_min": 20, "lon_max": 30},
                step=5,
                variables=["TEC"],
                state_factory=WrongShapeState,
            )


if __name__ == "__main__":
    unittest.main()
