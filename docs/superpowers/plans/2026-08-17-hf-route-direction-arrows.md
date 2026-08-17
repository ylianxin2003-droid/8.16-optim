# HF Route Direction Arrows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make HF route direction visually obvious by retaining the existing blue route line and route-sample markers while adding approximately three directional arrow markers from transmitter/origin to target/destination.

**Architecture:** This is a display-only change inside `create_hf_coverage_map()` in `streamlit_cloud_github/hf_coverage.py`. The scientific route sampling, HF availability calculations, degraded-route detection, endpoint markers, map bounds, hover data, and numerical outputs remain unchanged. Direction arrows are derived only from adjacent rendered route points and use Plotly-supported triangle marker symbols.

**Tech Stack:** Python 3.11, pandas, Plotly `graph_objects.Scattergeo`, unittest.

## Global Constraints

- Preserve all current Dashboard functionality and scientific calculations.
- Preserve the existing blue dashed route and small blue route-sample markers.
- Preserve the red origin star, purple target marker, degraded-route markers, hover behaviour, legend route label, and map bounds.
- Add approximately three blue direction arrows distributed along sufficiently long routes.
- Arrow direction must follow the local origin-to-destination route direction as closely as practical using Plotly marker symbols.
- Short routes must remain valid and must not raise errors.
- Do not alter HF coverage percentages, route availability, longest degraded segment, frequency sweep results, or route sampling.

---

### Task 1: Add tested route-direction arrow rendering

**Files:**
- Modify: `streamlit_cloud_github/tests/test_hf_coverage.py`
- Modify: `streamlit_cloud_github/hf_coverage.py`

**Interfaces:**
- Consumes: `create_hf_coverage_map(case, transmitter, target=None, route=None, title=None, map_mode=...)` and the existing `route_frame` DataFrame containing ordered `lat`/`lon` route samples.
- Produces: One additional Plotly `Scattergeo` trace named `Route direction` for sufficiently long routes, with approximately three blue triangular markers and `showlegend=False`. Existing traces remain unchanged.

- [ ] **Step 1: Write the failing test for route direction markers**

Add a test beside the existing HF map tests in `streamlit_cloud_github/tests/test_hf_coverage.py`:

```python
def test_hf_map_adds_direction_arrows_without_replacing_route_samples(self):
    from hf_coverage import create_hf_coverage_map, great_circle_route

    case = pd.DataFrame([{
        "lat": 45.0,
        "lon": -30.0,
        "quiet_muf_mhz": 12.0,
        "storm_muf_mhz": 8.4,
        "selected_frequency_mhz": 10.0,
        "coverage_change": "Degraded during storm",
    }])
    origin = {
        "name": "Birmingham, United Kingdom",
        "lat": 52.4862,
        "lon": -1.8904,
    }
    target = {
        "name": "New York, United States",
        "lat": 40.7128,
        "lon": -74.0060,
    }
    route = great_circle_route(origin, target, samples=33)

    fig = create_hf_coverage_map(
        case,
        origin,
        target,
        route=route.to_dict("records"),
        map_mode="quiet",
    )

    route_trace = next(
        trace for trace in fig.data
        if trace.name == "Assumed route: Birmingham, United Kingdom → New York, United States"
    )
    arrow_trace = next(trace for trace in fig.data if trace.name == "Route direction")

    self.assertEqual(route_trace.mode, "lines+markers")
    self.assertGreater(len(route_trace.lat), 3)
    self.assertEqual(arrow_trace.mode, "markers")
    self.assertEqual(len(arrow_trace.lat), 3)
    self.assertFalse(bool(arrow_trace.showlegend))
    self.assertEqual(arrow_trace.marker.color, "#0D47A1")
    self.assertTrue(
        all(
            symbol in {"triangle-left", "triangle-right", "triangle-up", "triangle-down"}
            for symbol in list(arrow_trace.marker.symbol)
        )
    )
```

- [ ] **Step 2: Run the focused test and verify it fails before implementation**

Run:

```bash
cd streamlit_cloud_github
python -m unittest tests.test_hf_coverage.HfCoverageTest.test_hf_map_adds_direction_arrows_without_replacing_route_samples -v
```

Expected: FAIL because no `Route direction` trace exists yet.

- [ ] **Step 3: Implement the minimal display-only direction-arrow trace**

In `create_hf_coverage_map()` immediately after the existing `Assumed route` trace, add route-arrow selection without changing `route_frame` or route calculations:

```python
    if len(route_frame) >= 8:
        arrow_indices = sorted({
            len(route_frame) // 4,
            len(route_frame) // 2,
            3 * len(route_frame) // 4,
        })
        arrow_lats: list[float] = []
        arrow_lons: list[float] = []
        arrow_symbols: list[str] = []

        for idx in arrow_indices:
            if idx >= len(route_frame) - 1:
                continue
            current = route_frame.iloc[idx]
            next_point = route_frame.iloc[idx + 1]
            dlat = float(next_point["lat"]) - float(current["lat"])
            dlon = float(next_point["lon"]) - float(current["lon"])

            if abs(dlon) >= abs(dlat):
                symbol = "triangle-right" if dlon > 0 else "triangle-left"
            else:
                symbol = "triangle-up" if dlat > 0 else "triangle-down"

            arrow_lats.append(float(current["lat"]))
            arrow_lons.append(float(current["lon"]))
            arrow_symbols.append(symbol)

        if arrow_lats:
            fig.add_trace(
                go.Scattergeo(
                    lat=arrow_lats,
                    lon=arrow_lons,
                    mode="markers",
                    name="Route direction",
                    marker={
                        "size": 13,
                        "color": "#0D47A1",
                        "symbol": arrow_symbols,
                    },
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
```

Do not change the existing `route_line_mode = "lines+markers"` or its route marker data.

- [ ] **Step 4: Run the focused test and the existing HF coverage tests**

Run:

```bash
cd streamlit_cloud_github
python -m unittest tests.test_hf_coverage.HfCoverageTest.test_hf_map_adds_direction_arrows_without_replacing_route_samples -v
python -m unittest tests.test_hf_coverage -v
```

Expected: PASS. Existing route names, endpoint labels, bounds, profile plots, and scientific result tests remain unchanged.

- [ ] **Step 5: Run the full automated test suite**

Run:

```bash
cd streamlit_cloud_github
python -m unittest discover -s tests -v
```

Expected: all existing tests plus the new direction-arrow regression test pass.

- [ ] **Step 6: Commit the implementation**

```bash
git add streamlit_cloud_github/hf_coverage.py streamlit_cloud_github/tests/test_hf_coverage.py
git commit -m "ui: add HF route direction arrows"
```

## Self-review

- Spec coverage: the plan preserves route samples and all scientific logic while adding three origin-to-target direction markers.
- Placeholder scan: no TBD/TODO or unspecified implementation steps remain.
- Type consistency: the implementation operates on the existing pandas `route_frame` and creates a Plotly `Scattergeo` trace; no new public API is introduced.
