# Global HF Route and Cache Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make global HF routes render completely with truthful labels, eliminate visible Plotly compatibility warnings, restore current-contract trial caches, and publish the verified result to the August repository.

**Architecture:** Keep the existing HF propagation calculations unchanged. Add one pure viewport helper consumed by `create_hf_coverage_map`, make endpoint and waypoint labels derive from selected route data, and remove unsupported keyword forwarding at the Streamlit/Plotly boundary. Update the cache generator to preserve Kp horizon evidence, then replace packaged caches only through successful current-contract generation.

**Tech Stack:** Python 3.9, pandas, Plotly, Streamlit 1.50, `unittest`, SERENE AIDA API, GFZ Kp JSON, Git.

## Global Constraints

- Do not change TEC, Kp or PSD thresholds, the 96-hour Kp storm gate, the 30-day same-UTC MUF reference, or the MUF-threshold HF approximation.
- Do not relax `TRIAL_CACHE_SCHEMA_VERSION = 3` or `FORECAST_CONTRACT_VERSION = "analysis-plus-kp-horizon-evidence-v2"`.
- Do not print, copy or commit API credentials.
- Push only to `origin/main` for `ylianxin2003-droid/August-project-version`; never push `legacy-source`.
- Preserve the inline standalone HF study and its two internal explanation expanders.

---

### Task 1: Route-aware map bounds and truthful labels

**Files:**
- Modify: `streamlit_cloud_github/tests/test_hf_coverage.py`
- Modify: `streamlit_cloud_github/hf_coverage.py:318-360,457-613`

**Interfaces:**
- Produces: `_route_geo_bounds(route: pandas.DataFrame) -> tuple[list[float], list[float]]` returning `[lat_min, lat_max]` and `[lon_min, lon_max]`.
- Consumes: sampled route points already passed to `create_hf_coverage_map`.

- [ ] **Step 1: Add failing tests for London to Singapore, date-line routes, endpoint text and midpoint wording**

Add tests that assert literal user-visible outcomes:

```python
def test_london_singapore_map_bounds_include_both_endpoints(self):
    from hf_coverage import create_hf_coverage_map, great_circle_route

    origin = {"name": "London, United Kingdom", "lat": 51.5074, "lon": -0.1278}
    target = {"name": "Singapore", "lat": 1.3521, "lon": 103.8198}
    route = great_circle_route(origin, target, samples=33)
    fig = create_hf_coverage_map(self._map_case(), origin, target, route.to_dict("records"))

    self.assertLessEqual(fig.layout.geo.lonaxis.range[0], -0.1278)
    self.assertGreaterEqual(fig.layout.geo.lonaxis.range[1], 103.8198)
    self.assertLessEqual(fig.layout.geo.lataxis.range[0], 1.3521)
    self.assertGreaterEqual(fig.layout.geo.lataxis.range[1], 51.5074)
```

```python
def test_date_line_route_uses_world_longitude_view(self):
    from hf_coverage import _route_geo_bounds

    route = pd.DataFrame([{"lat": 35.0, "lon": 170.0}, {"lat": 35.0, "lon": -170.0}])
    _lat_range, lon_range = _route_geo_bounds(route)
    self.assertEqual(lon_range, [-180.0, 180.0])
```

Update the existing endpoint-label test to assert `trace.text == ("London",)` and `trace.text == ("Singapore",)`. Update the waypoint test to require `Route midpoint` and forbid `North Atlantic corridor` for London to Singapore.

- [ ] **Step 2: Run the focused tests and confirm expected failures**

```bash
cd /Users/a123/Desktop/August-project-version/streamlit_cloud_github
../.venv/bin/python -m unittest tests.test_hf_coverage -v
```

Expected: failures identify fixed map ranges, hard-coded endpoint text, missing `_route_geo_bounds`, and the North Atlantic midpoint label.

- [ ] **Step 3: Implement the minimal route-aware behaviour**

Implement `_route_geo_bounds` with 8-degree latitude padding and 10-degree longitude padding, clamped to valid world bounds. Use a full longitude range when the normalised span exceeds 180 degrees. Derive endpoint display labels using `str(name).split(",", 1)[0]`. Replace `North Atlantic corridor` with `Route midpoint`.

- [ ] **Step 4: Run the HF coverage tests and confirm they pass**

Run the command from Step 2. Expected: all `test_hf_coverage` tests pass.

- [ ] **Step 5: Commit the isolated map fix**

```bash
git add streamlit_cloud_github/hf_coverage.py streamlit_cloud_github/tests/test_hf_coverage.py
git commit -m "fix: render global HF routes truthfully"
```

---

### Task 2: Remove visible Plotly keyword warnings

**Files:**
- Modify: `streamlit_cloud_github/tests/test_hf_coverage_ui.py`
- Modify: `streamlit_cloud_github/hf_coverage_ui.py:248-305`
- Modify: `streamlit_cloud_github/app.py:1142-1456`

**Interfaces:**
- Consumes: Streamlit 1.50's default responsive `st.plotly_chart(figure)` behaviour.
- Produces: rendered application alerts that do not contain `keyword arguments have been deprecated`.

- [ ] **Step 1: Add a failing rendered-warning regression test**

In `test_positive_reference_labels_aida_reference_and_disables_assumption_copy`, collect rendered warning text and assert:

```python
warning_text = "\n".join(str(item.value) for item in dashboard.warning)
self.assertNotIn("keyword arguments have been deprecated", warning_text)
```

- [ ] **Step 2: Run the focused UI test and verify it fails**

```bash
../.venv/bin/python -m unittest tests.test_hf_coverage_ui.HfCoverageUiTest.test_positive_reference_labels_aida_reference_and_disables_assumption_copy -v
```

Expected: FAIL because Streamlit 1.50 renders the forwarded Plotly keyword warning.

- [ ] **Step 3: Remove only `width="stretch"` from every `st.plotly_chart` call**

Leave widget and dataframe width settings unchanged. Do not introduce `use_container_width` because Streamlit already defaults Plotly charts to responsive width in this runtime.

- [ ] **Step 4: Run all Streamlit UI and app helper tests**

```bash
../.venv/bin/python -m unittest tests.test_hf_coverage_ui tests.test_icao_app_helpers tests.test_dashboard_settings -v
```

Expected: tests pass and no Plotly keyword deprecation line appears.

- [ ] **Step 5: Commit the compatibility fix**

```bash
git add streamlit_cloud_github/app.py streamlit_cloud_github/hf_coverage_ui.py streamlit_cloud_github/tests/test_hf_coverage_ui.py
git commit -m "fix: remove Plotly compatibility warnings"
```

---

### Task 3: Preserve Kp horizon evidence during cache generation

**Files:**
- Modify: `streamlit_cloud_github/tests/test_trial_cache.py`
- Modify: `streamlit_cloud_github/generate_trial_outputs.py:30-72`

**Interfaces:**
- Consumes: `IcaoProductBundle.kp_horizons`.
- Produces: `build_icao_summary(..., kp_horizons=bundle.kp_horizons)` and saved current-contract cache bundles.

- [ ] **Step 1: Add a failing generator integration test**

Use a temporary cache directory and patch only the external loader and generator event list. Return a real bundle containing observed-backtesting +30/+90 Kp rows. Patch `save_trial_bundle` with a wrapper that calls the real function in the temporary directory, then load the result and assert the summary's Auroral Absorption row has a numeric `+30 min forecast`, source text containing `backtesting`, and a non-empty saved `kp_horizons` frame.

- [ ] **Step 2: Run the generator test and verify it fails**

```bash
../.venv/bin/python -m unittest tests.test_trial_cache.TrialCacheTest.test_generation_utility_preserves_kp_horizon_evidence -v
```

Expected: the saved Kp frame exists but the generated summary lacks the +30/+90 Kp evidence because the generator does not pass `kp_horizons` to `build_icao_summary`.

- [ ] **Step 3: Pass the horizon frame into the summary builder**

```python
summary = build_icao_summary(
    bundle.products,
    bundle.indices,
    eligible=bundle.kp_storm_eligible,
    kp_horizons=bundle.kp_horizons,
)
```

- [ ] **Step 4: Run all cache tests**

```bash
../.venv/bin/python -m unittest tests.test_trial_cache -v
```

Expected: all cache tests pass.

- [ ] **Step 5: Commit the generator fix**

```bash
git add streamlit_cloud_github/generate_trial_outputs.py streamlit_cloud_github/tests/test_trial_cache.py
git commit -m "fix: preserve Kp evidence in trial caches"
```

---

### Task 4: Regenerate and validate packaged trial outputs

**Files:**
- Replace successful outputs under: `streamlit_cloud_github/data/trial_outputs/*`

**Interfaces:**
- Consumes: the existing local SERENE credentials without printing or copying them.
- Produces: Quick Demo and Full ICAO-style cache folders under the current contract.

- [ ] **Step 1: Run Quick Demo generation with credentials loaded only into the process environment**

Use `python-dotenv` to load `/Users/a123/Desktop/dashboard-2/.env` for the child process, then run:

```bash
python generate_trial_outputs.py --mode "Quick Demo" --grid-step 15
```

Expected: four cache folders are successfully saved. If fewer are saved, stop and report the exact failed analysis times.

- [ ] **Step 2: Run Full ICAO-style generation**

```bash
python generate_trial_outputs.py --mode "Full ICAO-style mode" --grid-step 15
```

Expected: four cache folders are successfully saved. This step may take longer because it requests the three-hour window and 30-day PSD reference.

- [ ] **Step 3: Validate every packaged cache without contacting the API**

Run a local validation script that calls `load_trial_bundle` for every folder and asserts schema version 3, forecast contract v2, non-empty AIDA products, and `kp_horizons` columns matching the current contract. Print only folder names and validation results.

- [ ] **Step 4: Scan generated files for credential names and obvious token material**

Use the existing cache-secret tests plus a targeted file scan for `SERENE_API_TOKEN`, `SERENE_AUTH_SCHEME`, `password`, and the environment token value without printing the token. Any match blocks committing.

- [ ] **Step 5: Commit only validated cache outputs**

```bash
git add streamlit_cloud_github/data/trial_outputs
git commit -m "data: refresh current-contract trial outputs"
```

---

### Task 5: Full verification, browser QA and August publication

**Files:**
- Verify: all committed project changes.

**Interfaces:**
- Produces: fresh test evidence, visual evidence and a verified `origin/main` push.

- [ ] **Step 1: Run the complete test suite**

```bash
cd /Users/a123/Desktop/August-project-version/streamlit_cloud_github
PYTHONWARNINGS=ignore ../.venv/bin/python -m unittest discover -s tests -q
```

Expected: zero failures; record exact test count and time. No Plotly keyword warning should appear.

- [ ] **Step 2: Browser-check the real local main app in Cached trial output mode**

Load a regenerated Full ICAO cache, confirm the inline study appears, select London to Singapore, and inspect the map. Both city labels and the complete route must be visible. Inspect a date-line route through Advanced coordinates or a controlled visual harness. Confirm both internal expanders remain and no deprecation or exception alert appears.

- [ ] **Step 3: Verify repository and remote scope**

```bash
git status -sb
git diff --check
git remote -v
git log --oneline origin/main..HEAD
```

Expected: only the pre-existing untracked `.superpowers/` directory remains; `origin` is the August repository; `legacy-source` push is disabled.

- [ ] **Step 4: Push the current main branch to August**

```bash
git push origin main
```

- [ ] **Step 5: Verify the remote commit exactly matches local HEAD**

```bash
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Expected: both commit hashes are identical.
