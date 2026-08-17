# HF Route Direction Arrows — Design

## Goal
Make the HF route direction immediately understandable to users without changing any scientific calculation or route-sampling behaviour.

## Scope
Only modify the Plotly rendering in `streamlit_cloud_github/hf_coverage.py`, inside `create_hf_coverage_map()`.

## Visual Design
- Keep the existing blue dashed route line.
- Keep the existing small blue route-sample markers because they communicate the sampled route geometry.
- Add approximately three blue directional arrow markers distributed along the route.
- Each arrow direction is inferred from the next route sample using Plotly-supported triangle marker symbols.
- Preserve the red star for the origin/transmitter and the purple marker for the destination/receiver.
- Preserve degraded-route markers, legend text, hover behaviour, map bounds and all other map layers.

## Behavioural Constraints
- No change to route generation or sample count.
- No change to HF coverage calculations, route availability, degraded-segment calculation, frequency sweep or engineering interpretation.
- No change to data loading, caching, provenance or Streamlit controls.
- The modification must be display-only.

## Testing
- Existing HF coverage and UI tests must continue to pass.
- Add or update a focused rendering test if practical to confirm the arrow trace is created without changing route data or numerical outputs.
- Verify the Birmingham → New York map visibly shows direction from origin to destination.

## Success Criteria
Users can identify the origin-to-destination direction at a glance while all existing Dashboard functionality and numerical results remain unchanged.
