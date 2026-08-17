import os
import sys
import unittest

import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class HfRouteDirectionArrowTest(unittest.TestCase):
    def test_long_route_adds_three_direction_arrows(self):
        try:
            import plotly.graph_objects as go
        except ModuleNotFoundError:
            self.skipTest("plotly is not installed in this local test interpreter")

        from hf_coverage_ui import _add_route_direction_arrows

        route = pd.DataFrame({
            "lat": [52.0 - index * 0.35 for index in range(33)],
            "lon": [-2.0 - index * 2.25 for index in range(33)],
        })
        fig = go.Figure()

        result = _add_route_direction_arrows(fig, route)

        self.assertIs(result, fig)
        self.assertEqual(len(fig.data), 1)
        trace = fig.data[0]
        self.assertEqual(trace.name, "Route direction")
        self.assertEqual(trace.mode, "markers")
        self.assertEqual(len(trace.lat), 3)
        self.assertFalse(bool(trace.showlegend))
        self.assertEqual(trace.marker.color, "#0D47A1")
        self.assertTrue(all(
            symbol in {
                "triangle-left",
                "triangle-right",
                "triangle-up",
                "triangle-down",
            }
            for symbol in list(trace.marker.symbol)
        ))

    def test_short_route_is_left_unchanged(self):
        try:
            import plotly.graph_objects as go
        except ModuleNotFoundError:
            self.skipTest("plotly is not installed in this local test interpreter")

        from hf_coverage_ui import _add_route_direction_arrows

        route = pd.DataFrame({
            "lat": [52.0, 50.0],
            "lon": [-2.0, -20.0],
        })
        fig = go.Figure()

        result = _add_route_direction_arrows(fig, route)

        self.assertIs(result, fig)
        self.assertEqual(len(fig.data), 0)


if __name__ == "__main__":
    unittest.main()
