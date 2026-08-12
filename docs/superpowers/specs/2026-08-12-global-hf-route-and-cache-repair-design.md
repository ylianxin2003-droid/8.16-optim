# Global HF Route and Cache Repair Design

## Purpose

Complete the inline standalone HF study by making every named or custom route
visually honest, removing user-visible plotting warnings, and restoring the
packaged cached-trial workflow under the current forecast evidence contract.

## Scope

- Keep the standalone HF study inline in the dashboard body.
- Replace the fixed North Atlantic map viewport with route-aware geographic
  bounds.
- Display the selected endpoint city or region names beside their markers.
- Use a geographically neutral route midpoint label.
- Remove Plotly keyword arguments that Streamlit 1.50 forwards as deprecated
  Plotly configuration.
- Ensure generated summaries receive the bundle's Kp horizon evidence.
- Regenerate the packaged Quick Demo and Full ICAO-style trial outputs with the
  current cache schema and forecast contract.
- Push the verified commits only to the August repository. The legacy remote
  remains read-only.

The work does not change TEC, Kp or PSD thresholds; the 96-hour Kp storm gate;
the 30-day same-UTC MUF reference; or the MUF-threshold HF approximation.

## Route-Aware Map

The coverage figure will derive its viewport from the sampled great-circle
route and both endpoints, not from the full analysis grid. It will add bounded
latitude and longitude padding so markers and text are not placed directly on
the plot edge.

For an ordinary route whose longitude span is no greater than 180 degrees, the
map uses the padded minimum and maximum route longitude. If a route crosses the
international date line and its normalised longitude span exceeds 180 degrees,
the figure uses a full-world longitude range. This avoids drawing a misleading
narrow viewport across the wrong side of the globe.

Latitude bounds remain clamped to -90 through 90 degrees. Longitude bounds
remain clamped to -180 through 180 degrees. Empty or malformed route inputs
fall back to the existing North Atlantic research view rather than raising a
page exception.

## Endpoint and Waypoint Labels

Endpoint annotations use concise display names derived from the selected names:
the text before the first comma, for example `London` and `Singapore`. The
legend and hover text retain the complete endpoint names. Text remains dark and
high contrast.

The great-circle route midpoint is labelled `Route midpoint`. A selected
endpoint called `North Atlantic corridor` retains that exact endpoint name, but
unrelated routes such as London to Singapore are never described as passing
through a North Atlantic corridor.

## Plot Rendering Compatibility

`st.plotly_chart` calls will rely on Streamlit's responsive default instead of
passing `width="stretch"` through the Plotly keyword argument compatibility
path. Dataframes and other Streamlit widgets keep their supported
`width="stretch"` settings. The rendered plots remain responsive while the
deprecation alert disappears under the project's installed Streamlit 1.50
runtime.

## Trial Cache Contract

The generator will pass `bundle.kp_horizons` to `build_icao_summary`. Saved
bundles already include the same Kp horizon frame through `save_trial_bundle`.
Each generated cache must therefore contain:

- cache schema version 3;
- forecast contract `analysis-plus-kp-horizon-evidence-v2`;
- `kp_horizons` data or an explicitly empty current-contract frame;
- summary sources that distinguish official forecasts, observed backtesting
  outcomes and unavailable evidence.

Existing incompatible folders will not be accepted by relaxing the loader.
They will be replaced only after a successful live generation for the matching
cache key. Authentication values are read into the generation process but are
never copied into committed files or printed.

## Failure Handling

- A failed live generation leaves the corresponding existing cache folder
  recoverable through Git and is reported rather than being labelled current.
- If one event cannot be regenerated, it is not presented as a verified cache.
- Missing AIDA or Kp evidence remains `UNAVAILABLE`; cache repair never turns
  missing evidence into `OK`.
- Browser verification distinguishes a genuine loaded cache from an API
  fallback state.

## Verification

Automated tests will cover:

1. London-to-Singapore viewport includes both endpoints.
2. A date-line-crossing route selects a world longitude range.
3. Endpoint traces show the selected concise names with dark text.
4. Route midpoint wording is neutral.
5. HF Streamlit rendering contains no Plotly keyword deprecation alert.
6. The generator passes Kp horizon evidence into the saved summary.
7. Every packaged cache declares the current schema and forecast contract.

The complete unit-test suite must pass. Browser verification will load a
current-contract Full ICAO cache, select London to Singapore, inspect the full
route map, confirm both internal explanation expanders remain, and check for
visible Streamlit exceptions or Plotly deprecation alerts. The final Git push
will target `origin/main` for
`ylianxin2003-droid/August-project-version`; `legacy-source` will not be pushed.
