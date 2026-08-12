# Four-Horizon Summary and Kp Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `+30 min`, `+90 min`, `+3 h`, and `+6 h` available across the Summary Table for TEC, PSD, and Kp whenever traceable SERENE/GFZ evidence exists.

**Architecture:** Keep SERENE AIDA spatial forecasts and GFZ global Kp evidence as separate pipelines, then merge them only in the risk-summary layer. Decode the already-requested AIDA 180/360-minute files, extend the row-oriented Kp evidence contract to 180/360 minutes, and retain explicit `source`/`evidence_role` provenance for official future forecasts, historical observed backtesting, and dashboard-generated AIDA fallbacks.

**Tech Stack:** Python 3.9, pandas, Streamlit, requests, official `breid-phys/aida-ionosphere` adapter, `unittest`, Plotly, Parquet/CSV trial caches.

## Global Constraints

- Modify and push only `/Users/a123/Desktop/August-project-version`; never push to `legacy-source`.
- Preserve Kp/ap as planetary context; never render Kp as regional map cells.
- Never convert missing evidence into `OK`; use `UNAVAILABLE` with a reason.
- Historical Kp target values are observed outcomes for backtesting, not archived forecasts.
- Future Kp uses a fresh, aligned GFZ PAGER/SWIFT ensemble row; primary risk uses the ensemble median.
- TEST advisory messages remain limited to `+30 min` and `+90 min`.
- Do not add a new API token or dependency; GFZ remains a public HTTPS source.
- Use `/Users/a123/Desktop/August-project-version/.venv/bin/python` for tests and utilities.
- Keep the pre-existing untracked `.superpowers/` directory untouched.

---

### Task 1: Resolve Four GFZ Kp Horizons

**Files:**
- Modify: `streamlit_cloud_github/data_loader.py`
- Test: `streamlit_cloud_github/tests/test_api_only_data_loader.py`

**Interfaces:**
- Consumes: `SereneClient.fetch_kp_ap_indices(...)` observed rows and `SereneClient.fetch_gfz_kp_forecast()` ensemble rows.
- Produces: `_resolve_kp_horizons(...) -> pd.DataFrame` with one row for each `horizon_minutes` in `(30, 90, 180, 360)` using the existing `KP_HORIZON_COLUMNS` schema.

- [ ] **Step 1: Add failing future-forecast and historical-backtesting tests**

Extend the controlled tests so they assert all four rows and correct three-hour interval alignment:

```python
self.assertEqual(result["horizon_minutes"].tolist(), [30, 90, 180, 360])
self.assertEqual(result["evidence_role"].tolist(), [
    "official_forecast", "official_forecast",
    "official_forecast", "official_forecast",
])
self.assertEqual(result["value"].tolist(), [7.5, 7.5, 6.5, 5.5])
```

For a historical analysis, supply observed Kp rows for every distinct target interval and assert:

```python
self.assertEqual(result["horizon_minutes"].tolist(), [30, 90, 180, 360])
self.assertTrue((result["evidence_role"] == "observed_backtesting").all())
self.assertTrue((result["source"] == "GFZ observed outcome — backtesting only").all())
```

- [ ] **Step 2: Run the focused tests and verify the expected two-horizon failure**

Run:

```bash
cd /Users/a123/Desktop/August-project-version/streamlit_cloud_github
../.venv/bin/python -m unittest tests.test_api_only_data_loader -q
```

Expected: FAIL because the resolver returns only `[30, 90]` and does not request the later observed intervals.

- [ ] **Step 3: Extend the Kp resolver and availability message**

In `data_loader.py`, set:

```python
KP_HORIZON_MINUTES = (30, 90, 180, 360)
```

Keep the existing per-target logic: `target_time = analysis + horizon`,
`interval_start = target_time.floor("3h")`, past targets use observed Kp, and
future targets require a fresh aligned ensemble row. Update the loader message to
`Kp +30/+90/+180/+360 minute horizon evidence resolved.` and ensure missing
historical intervals are fetched in one bounded request from the minimum missing
interval to the maximum missing interval.

- [ ] **Step 4: Run the focused tests and verify all four roles pass**

Run the Task 1 command again. Expected: PASS.

- [ ] **Step 5: Commit the Kp data-contract change**

```bash
git add streamlit_cloud_github/data_loader.py \
  streamlit_cloud_github/tests/test_api_only_data_loader.py
git commit -m "feat: resolve four Kp evidence horizons"
```

---

### Task 2: Promote AIDA 3 h and 6 h Files to Display Products

**Files:**
- Modify: `streamlit_cloud_github/data_loader.py`
- Test: `streamlit_cloud_github/tests/test_api_only_data_loader.py`
- Test: `streamlit_cloud_github/tests/test_aida_output_client.py`

**Interfaces:**
- Consumes: `SereneClient.download_aida_forecast(analysis_time, latency, period_minutes)` for periods 30, 90, 180, and 360.
- Produces: product rows with `product_kind` values `forecast_30`, `forecast_90`, `forecast_180`, and `forecast_360`; metadata `available_primary_forecast_periods` ordered `[30, 90, 180, 360]` when all decode successfully.

- [ ] **Step 1: Change the one-download-per-period test to require four decoded products**

Update the existing assertions to:

```python
self.assertEqual(set(bundle.products["product_kind"]), {
    "analysis", "rolling", "forecast_30", "forecast_90",
    "forecast_180", "forecast_360",
})
self.assertEqual(bundle.status.metadata["primary_forecast_states"], 4)
self.assertEqual(
    bundle.status.metadata["available_primary_forecast_periods"],
    [30, 90, 180, 360],
)
self.assertEqual(
    [row["display_role"] for row in bundle.status.metadata["forecast_request_audit"]],
    ["primary", "primary", "primary", "primary"],
)
```

Retain the assertion that the client receives exactly four forecast requests.

- [ ] **Step 2: Run the focused loader/client tests and verify 180/360 are absent**

```bash
cd /Users/a123/Desktop/August-project-version/streamlit_cloud_github
../.venv/bin/python -m unittest \
  tests.test_api_only_data_loader \
  tests.test_aida_output_client -q
```

Expected: FAIL because 180/360 payloads are downloaded but skipped before decoding.

- [ ] **Step 3: Make all four AIDA periods primary**

Replace the split constants with:

```python
PRIMARY_FORECAST_PERIODS = (30, 90, 180, 360)
FORECAST_PERIODS = PRIMARY_FORECAST_PERIODS
```

Remove the `if period not in PRIMARY_FORECAST_PERIODS: continue` audit-only
branch. Preserve independent failure handling so one missing forecast does not
discard the successful analysis or other horizons. Keep `valid_time` equal to
`analysis + period` and leave `total_official_aida_downloads` semantics unchanged.

- [ ] **Step 4: Run the Task 2 tests and verify four decoded products**

Run the Task 2 command again. Expected: PASS.

- [ ] **Step 5: Commit the AIDA promotion**

```bash
git add streamlit_cloud_github/data_loader.py \
  streamlit_cloud_github/tests/test_api_only_data_loader.py \
  streamlit_cloud_github/tests/test_aida_output_client.py
git commit -m "feat: decode AIDA three and six hour forecasts"
```

---

### Task 3: Extend the Risk Summary Contract

**Files:**
- Modify: `streamlit_cloud_github/icao_risk.py`
- Test: `streamlit_cloud_github/tests/test_icao_risk.py`

**Interfaces:**
- Consumes: AIDA product kinds from Task 2 and four Kp evidence rows from Task 1.
- Produces: `build_icao_summary(...) -> pd.DataFrame` with four value/status/source groups and `build_categorical_cells(..., horizon)` supporting `+3h` and `+6h`.

- [ ] **Step 1: Add failing four-horizon summary tests**

Add official AIDA rows for `forecast_180` and `forecast_360`, plus Kp evidence
rows for 180 and 360. Assert:

```python
self.assertEqual(tec["+3h forecast"], 160.0)
self.assertEqual(tec["+3h status"], "MODERATE")
self.assertEqual(tec["+3h source"], "SERENE official forecast")
self.assertEqual(psd["+6h forecast"], 55.0)
self.assertEqual(psd["+6h status"], "SEVERE")
self.assertEqual(kp["+3h forecast"], 8.2)
self.assertEqual(kp["+3h status"], "MODERATE")
self.assertEqual(kp["+6h forecast"], 9.0)
self.assertEqual(kp["+6h status"], "SEVERE")
```

Add a categorical-cell assertion:

```python
cells = build_categorical_cells(products, "Vertical TEC", "+6h")
self.assertEqual(cells.iloc[0]["category"], "SEVERE")
```

- [ ] **Step 2: Run the risk tests and verify missing-column failures**

```bash
cd /Users/a123/Desktop/August-project-version/streamlit_cloud_github
../.venv/bin/python -m unittest tests.test_icao_risk -q
```

Expected: FAIL because `FORECAST_HORIZONS` and `SUMMARY_COLUMNS` stop at 90 minutes.

- [ ] **Step 3: Add four horizon labels and generate fields consistently**

Set:

```python
FORECAST_HORIZONS = {
    "+30 min": 30,
    "+90 min": 90,
    "+3h": 180,
    "+6h": 360,
}
```

Append the six `+3h`/`+6h` fields to `SUMMARY_COLUMNS`. In
`_spatial_summary_row`, derive value, status, and source for every entry in
`FORECAST_HORIZONS` rather than hard-coding only two local variables. In
`_kp_summary_row`, resolve all four minutes with `_kp_horizon_summary` and emit
the same fields. Extend `_canonical_horizon` so `forecast_180`, `forecast_360`,
`180`, `360`, `+3 h`, and `+6 h` normalise to the new canonical labels. Preserve
`_fallback_prediction_rows` so missing official AIDA
rows can produce clearly labelled trend/persistence predictions; retain PSD
eligibility classification.

- [ ] **Step 4: Run risk and TEST-message regression suites**

```bash
../.venv/bin/python -m unittest \
  tests.test_icao_risk \
  tests.test_icao_message -q
```

Expected: PASS, including the existing rejection of unsupported 180/360 TEST-message fields.

- [ ] **Step 5: Commit the summary contract**

```bash
git add streamlit_cloud_github/icao_risk.py \
  streamlit_cloud_github/tests/test_icao_risk.py
git commit -m "feat: expose four risk forecast horizons"
```

---

### Task 4: Restore Four Horizon Groups in the Dashboard

**Files:**
- Modify: `streamlit_cloud_github/app.py`
- Test: `streamlit_cloud_github/tests/test_icao_app_helpers.py`
- Test: `streamlit_cloud_github/tests/test_dashboard_settings.py`

**Interfaces:**
- Consumes: `FORECAST_HORIZONS` and Summary Table fields from Task 3; `available_primary_forecast_periods` from Task 2.
- Produces: four styled horizon groups, four spatial map choices when usable, four-row Kp evidence table, and per-period availability text.

- [ ] **Step 1: Add failing UI-helper tests**

Change controlled status metadata to `[30, 90, 180, 360]` and assert:

```python
self.assertEqual(_available_primary_periods(status), [30, 90, 180, 360])
visible = _visible_summary_columns(summary, status)
for label in ("+30 min", "+90 min", "+3h", "+6h"):
    self.assertIn(f"{label} forecast", visible)
self.assertIn("+30 min, +90 min, +3 h and +6 h retrieved", message)
```

Extend `_kp_horizon_evidence_table` input to 180/360 and assert its `Horizon`
column equals `['+30 min', '+90 min', '+3 h', '+6 h']` in sorted order.
Update dashboard-copy tests to reject `audit only` wording.

- [ ] **Step 2: Run helper/settings tests and verify the current two-period failure**

```bash
cd /Users/a123/Desktop/August-project-version/streamlit_cloud_github
../.venv/bin/python -m unittest \
  tests.test_icao_app_helpers \
  tests.test_dashboard_settings -q
```

Expected: FAIL because helper ordering, styling, visibility, titles, and captions stop at 90 minutes.

- [ ] **Step 3: Generalise table visibility, styling, and availability copy**

In `app.py`:

- Include `+3h status` and `+6h status` in `_style_pecasus_table`.
- Return available periods in `(30, 90, 180, 360)` order.
- Evaluate visibility for `(30, '+30 min')`, `(90, '+90 min')`,
  `(180, '+3h')`, and `(360, '+6h')`.
- Make `_visible_summary_columns` retain every horizon group unconditionally;
  evidence availability is represented by each row's value/status/source cells,
  not by removing table columns.
- Rename the evidence heading to `Kp +30/+90/+3h/+6h horizon evidence` and render
  labels `+3 h` and `+6 h` for 180/360 rows.
- Replace audit-only availability text with a four-period per-cycle summary.
- Update the table caption to distinguish official future forecasts from GFZ
  historical observed backtesting.

Make the categorical-map radio list all entries from `FORECAST_HORIZONS`.
Official AIDA rows are preferred; the existing labelled AIDA fallback supplies
the map when its prerequisites are valid; otherwise the map shows its existing
no-data explanation.

- [ ] **Step 4: Run UI helper, settings, and rendering regression suites**

```bash
../.venv/bin/python -m unittest \
  tests.test_icao_app_helpers \
  tests.test_dashboard_settings \
  tests.test_hf_coverage_ui -q
```

Expected: PASS with no Streamlit/Plotly compatibility-warning assertions failing.

- [ ] **Step 5: Commit the dashboard restoration**

```bash
git add streamlit_cloud_github/app.py \
  streamlit_cloud_github/tests/test_icao_app_helpers.py \
  streamlit_cloud_github/tests/test_dashboard_settings.py
git commit -m "feat: restore four-horizon summary display"
```

---

### Task 5: Version and Regenerate Trial Caches

**Files:**
- Modify: `streamlit_cloud_github/trial_cache.py`
- Modify: `streamlit_cloud_github/data/trial_outputs/`
- Test: `streamlit_cloud_github/tests/test_trial_cache.py`

**Interfaces:**
- Consumes: four-horizon `IcaoProductBundle` and Summary Table from Tasks 1–3.
- Produces: cache schema version `4`, forecast contract `four-horizon-evidence-v3`, and eight loadable packaged caches.

- [ ] **Step 1: Add a failing current-contract cache test**

Change expected contract assertions to:

```python
self.assertEqual(stored["cache_schema_version"], 4)
self.assertEqual(stored["forecast_contract_version"], "four-horizon-evidence-v3")
self.assertEqual(
    loaded_bundle.kp_horizons["horizon_minutes"].tolist(),
    [30, 90, 180, 360],
)
self.assertIn("+3h forecast", loaded_summary.columns)
self.assertIn("+6h forecast", loaded_summary.columns)
```

Keep the legacy-cache rejection and secret-removal tests.

- [ ] **Step 2: Run the cache tests and verify version mismatch**

```bash
cd /Users/a123/Desktop/August-project-version/streamlit_cloud_github
../.venv/bin/python -m unittest tests.test_trial_cache -q
```

Expected: FAIL because schema 3/two-horizon caches are still current.

- [ ] **Step 3: Bump the cache contract**

Set:

```python
TRIAL_CACHE_SCHEMA_VERSION = 4
FORECAST_CONTRACT_VERSION = "four-horizon-evidence-v3"
```

Retain strict rejection of older contracts and the existing atomic cleanup of
failed Parquet writes.

- [ ] **Step 4: Run cache tests with controlled fixtures**

Run the Task 5 test command. Expected: PASS.

- [ ] **Step 5: Regenerate all eight packaged caches using credentials only in process memory**

Run Quick Demo and Full ICAO generation through the repository venv. Load
`/Users/a123/Desktop/dashboard-2/.env` with `dotenv_values`, assign only the four
SERENE settings to `os.environ`, and invoke:

```python
generate_trial_outputs(mode="Quick Demo", stop_on_error=True)
generate_trial_outputs(mode="Full ICAO-style mode", stop_on_error=True)
```

Expected: `4/4` saved for each mode. Never copy `.env` into the repository and
never print the token.

- [ ] **Step 6: Validate cache completeness and credentials**

For every cache folder, call `load_trial_bundle(folder.name)` and assert:

```python
assert bundle.status.metadata["cache_schema_version"] == 4
assert set(bundle.kp_horizons["horizon_minutes"]) == {30, 90, 180, 360}
assert len(summary) == 3
assert {"+3h forecast", "+6h forecast"}.issubset(summary.columns)
```

Scan cache-folder bytes for `SERENE_API_TOKEN`, `SERENE_AUTH_SCHEME`, and the
configured token value; expected matches: zero.

- [ ] **Step 7: Commit code and generated outputs**

```bash
git add streamlit_cloud_github/trial_cache.py \
  streamlit_cloud_github/tests/test_trial_cache.py \
  streamlit_cloud_github/data/trial_outputs
git commit -m "data: package four-horizon trial outputs"
```

---

### Task 6: Align Documentation and Complete End-to-End Verification

**Files:**
- Modify: `streamlit_cloud_github/README.md`
- Modify: `streamlit_cloud_github/部署说明.md`
- Verify: `streamlit_cloud_github/tests/`

**Interfaces:**
- Consumes: final four-horizon behaviour and source labels.
- Produces: deployment/report-safe documentation, browser evidence, and a verified August `main` push.

- [ ] **Step 1: Update scientific and deployment wording**

Document these exact rules:

- SERENE AIDA 30/90/180/360 official files are decoded when available.
- GFZ future Kp is an official PAGER/SWIFT ensemble forecast up to 72 hours.
- Historical Kp horizons are observed outcomes for backtesting, not archived forecasts.
- All four Summary Table groups remain visible; missing evidence is
  `UNAVAILABLE`, never silently `OK`.
- Kp remains global and is not placed in regional map cells.
- TEST messages remain 30/90 only.

Remove statements that call 3 h/6 h `audit only`.

- [ ] **Step 2: Run the fresh complete unit suite**

```bash
cd /Users/a123/Desktop/August-project-version/streamlit_cloud_github
PYTHONWARNINGS=ignore ../.venv/bin/python -m unittest discover -s tests -q
```

Expected: exit code 0 and zero failed/error tests.

- [ ] **Step 3: Run structural and secret checks**

```bash
cd /Users/a123/Desktop/August-project-version
git diff --check
git status -sb
git remote -v
```

Expected: no whitespace errors; only intended tracked changes plus the untouched
`.superpowers/`; `origin` is `August-project-version`; `legacy-source` push is
disabled.

- [ ] **Step 4: Browser-check one historical Full ICAO case**

Start local Streamlit on port 8502. Select Cached trial output, Full ICAO-style
mode, `2025-01-01 17:55 UTC`, then load. Verify:

- Summary Table has all four horizon groups for all three rows.
- Kp sources say `GFZ observed outcome — backtesting only`.
- 3 h/6 h maps are selectable for TEC and PSD.
- The standalone HF study remains inline.
- No Streamlit exception or compatibility warning appears.

- [ ] **Step 5: Browser-check one current Live SERENE case**

Start Streamlit with the four SERENE settings injected from the external `.env`
without printing them. Select Live SERENE API, Quick Demo, Follow latest, and
load. Verify:

- AIDA reports 30/90/180/360 availability independently.
- Kp has official GFZ sources at all four horizons when the current aligned
  product is fresh.
- Summary status colours match the Kp 8/9 and TEC/PSD thresholds.
- The forecast-source fields distinguish SERENE and GFZ.
- No traceback or widget/Plotly deprecation warning appears.

- [ ] **Step 6: Commit documentation and any verified copy-only adjustments**

```bash
git add streamlit_cloud_github/README.md streamlit_cloud_github/部署说明.md
git commit -m "docs: explain four-horizon forecast provenance"
```

- [ ] **Step 7: Re-run completion gates after the final commit**

Run the complete unit suite, `git diff --check`, cache validation, and secret
scan again. Expected: all pass on the exact tree to be pushed.

- [ ] **Step 8: Push only August main and verify the remote hash**

```bash
git push origin main
local_hash=$(git rev-parse HEAD)
remote_hash=$(git ls-remote origin refs/heads/main | awk '{print $1}')
test "$local_hash" = "$remote_hash"
```

Expected: push target is
`https://github.com/ylianxin2003-droid/August-project-version.git` and both hashes
match. Do not invoke `git push legacy-source`.
