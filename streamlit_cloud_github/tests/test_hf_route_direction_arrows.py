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

    def test_arrow_rotation_follows_each_local_route_segment_and_reverses(self):
        """Catch fixed/cardinal arrows that do not follow a curved route."""
        try:
            import plotly.graph_objects as go
        except ModuleNotFoundError:
            self.skipTest("plotly is not installed in this local test interpreter")

        from hf_coverage_ui import _add_route_direction_arrows

        # At the three arrow positions the hand-built route runs east, south,
        # and west respectively.  Expected angles are clockwise from north.
        lat = [0.0] * 33
        lon = [0.0] * 33
        for index in range(0, 11):
            lat[index] = 0.0
            lon[index] = float(index)
        for index in range(11, 22):
            lat[index] = float(11 - index)
            lon[index] = 10.0
        for index in range(22, 33):
            lat[index] = -10.0
            lon[index] = float(32 - index)
        route = pd.DataFrame({"lat": lat, "lon": lon})

        forward = go.Figure()
        _add_route_direction_arrows(forward, route)
        forward_marker = forward.data[0].marker
        self.assertEqual(tuple(forward_marker.symbol), ("triangle-up",) * 3)
        self.assertEqual(tuple(round(value) for value in forward_marker.angle), (90, -180, -90))
        self.assertEqual(forward_marker.angleref, "up")

        reverse = go.Figure()
        _add_route_direction_arrows(reverse, route.iloc[::-1].reset_index(drop=True))
        reverse_marker = reverse.data[0].marker
        self.assertEqual(tuple(reverse_marker.symbol), ("triangle-up",) * 3)
        self.assertEqual(tuple(round(value) for value in reverse_marker.angle), (90, 0, -90))
        self.assertEqual(reverse_marker.angleref, "up")

    def test_arrows_use_segment_midpoints_instead_of_covering_route_samples(self):
        """Catch direction arrows placed directly on top of blue route dots."""
        try:
            import plotly.graph_objects as go
        except ModuleNotFoundError:
            self.skipTest("plotly is not installed in this local test interpreter")

        from hf_coverage_ui import _add_route_direction_arrows

        route = pd.DataFrame({
            "lat": [0.0] * 33,
            "lon": [float(index) for index in range(33)],
        })
        fig = go.Figure()

        _add_route_direction_arrows(fig, route)

        trace = fig.data[0]
        self.assertEqual(tuple(round(value, 6) for value in trace.lat), (0.0, 0.0, 0.0))
        self.assertEqual(
            tuple(round(value, 6) for value in trace.lon),
            (8.5, 16.5, 24.5),
        )
        route_points = set(zip(route["lat"], route["lon"]))
        self.assertTrue(all(
            (lat, lon) not in route_points
            for lat, lon in zip(trace.lat, trace.lon)
        ))

    def test_direction_rotation_crosses_date_line_on_shortest_path(self):
        """Catch longitude subtraction that points west at the date line."""
        try:
            import plotly.graph_objects as go
        except ModuleNotFoundError:
            self.skipTest("plotly is not installed in this local test interpreter")

        from hf_coverage_ui import _add_route_direction_arrows

        unwrapped_lon = [170.0 + index * 0.8 for index in range(33)]
        route = pd.DataFrame({
            "lat": [0.0] * 33,
            "lon": [((value + 180.0) % 360.0) - 180.0 for value in unwrapped_lon],
        })
        fig = go.Figure()

        _add_route_direction_arrows(fig, route)

        self.assertEqual(
            tuple(round(value) for value in fig.data[0].marker.angle),
            (90, 90, 90),
        )

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
