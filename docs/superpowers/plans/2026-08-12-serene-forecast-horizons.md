# SERENE Published Forecast Horizons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the August dashboard use the actual latest SERENE analysis cycle, present verified +30-minute and +90-minute official forecasts, and keep +3-hour/+6-hour request outcomes in the audit surface rather than the primary risk display.

**Architecture:** The loader will separate primary display horizons `(30, 90)` from audit-only horizons `(180, 360)`. When near-real-time following is enabled, it will download the latest Ultra state once, derive its authoritative AIDA time, and use that exact cycle for forecasts, rolling history, PSD references and Kp queries. Risk and message builders will model only the two primary horizons; Streamlit will dynamically omit an unavailable primary horizon from decision-facing components while preserving all request outcomes and failure classes in status metadata.

**Tech Stack:** Python 3.9, Streamlit, pandas, NumPy, Plotly, `aida==0.1.3`, `requests`, `unittest`, Git.

## Global Constraints

- Work only in `/Users/a123/Desktop/August-project-version` and push only to `ylianxin2003-droid/August-project-version`.
- Do not modify or push `ylianxin2003-droid/primay-test-frist-version`.
- Primary forecast horizons are exactly +30 minutes and +90 minutes.
- +3-hour and +6-hour forecast requests remain auditable but never become primary risk columns, map horizons, chart series or research-message fields.
- A missing or failed forecast must never be converted into `OK`, zero, persistence, or another official-looking category.
- Use the actual AIDA state time returned by SERENE for near-real-time forecast `file_time`; do not use a guessed wall-clock anchor.
- Distinguish HTTP 401/403, HTTP 404, network failure and HDF5/decode failure in audit metadata.
- Keep official and dashboard-generated forecast provenance explicit.
- Do not commit `.env`, API tokens or generated secret-bearing files.

---

## File structure

- `streamlit_cloud_github/aida_adapter.py`: extract the authoritative UTC time from a raw official AIDA state.
- `streamlit_cloud_github/data_loader.py`: resolve the latest cycle, request primary/audit-only forecast periods, classify request outcomes and populate metadata.
- `streamlit_cloud_github/icao_risk.py`: build risk cells and summary fields for Latest, Max3h, +30 min and +90 min only.
- `streamlit_cloud_github/icao_message.py`: format only supplied +30/+90 forecast fields.
- `streamlit_cloud_github/app.py`: pass follow-latest intent, hide unavailable primary horizons, show dynamic availability evidence and update UI wording.
- `streamlit_cloud_github/README.md` and `streamlit_cloud_github/部署说明.md`: document the verified forecast contract and provenance.
- Existing files under `streamlit_cloud_github/tests/`: regression, contract and UI-source tests.

---

### Task 1: Resolve the authoritative latest AIDA analysis cycle

**Files:**
- Modify: `streamlit_cloud_github/aida_adapter.py`
- Modify: `streamlit_cloud_github/data_loader.py`
- Modify: `streamlit_cloud_github/app.py`
- Test: `streamlit_cloud_github/tests/test_aida_adapter.py`
- Test: `streamlit_cloud_github/tests/test_api_only_data_loader.py`
- Test: `streamlit_cloud_github/tests/test_dashboard_settings.py`

**Interfaces:**
- Produces: `read_aida_state_time(payload: bytes, state_factory: Callable[[], Any] | None = None) -> pd.Timestamp`.
- Changes: `load_icao_products(..., follow_latest: bool = False) -> IcaoProductBundle`.
- Metadata: `requested_analysis_time`, `analysis_time`, `actual_analysis_output_time`, and `analysis_anchor_source` with values `latest_serene_state` or `user_selected_time`.

- [ ] **Step 1: Add failing adapter tests for raw-state time extraction**

Add tests that pass a fake state whose `Time` is epoch `1786521300.0` and assert:

```python
actual = read_aida_state_time(b"raw-state", state_factory=lambda: FakeState())
self.assertEqual(actual, pd.Timestamp("2026-08-12T10:35:00Z"))
```

Also make the fake `readFile()` assert that its temporary file exists, and add a malformed-state test expecting `AidaGridError`.

- [ ] **Step 2: Run the adapter tests and confirm the new interface is missing**

Run:

```bash
.venv/bin/python -m unittest streamlit_cloud_github.tests.test_aida_adapter -v
```

Expected: FAIL because `read_aida_state_time` is not yet defined.

- [ ] **Step 3: Implement `read_aida_state_time` through the official interpreter**

Reuse `_official_state_factory()`, a temporary `.h5` file and `_normalise_state_time()`:

```python
def read_aida_state_time(payload, state_factory=None):
    factory = state_factory or _official_state_factory
    state = factory()
    try:
        with tempfile.NamedTemporaryFile(suffix=".h5") as handle:
            handle.write(payload)
            handle.flush()
            state.readFile(handle.name)
    except Exception as exc:
        raise AidaGridError(
            f"Official AIDA interpreter could not read the raw state time: {exc}"
        ) from exc
    return _normalise_state_time(state.Time)
```

- [ ] **Step 4: Add failing loader tests for `follow_latest=True`**

Extend the fake SERENE client to record calls. Assert that follow-latest loading:

```python
self.assertEqual(client.analysis_calls[0], (None, "ultra"))
self.assertEqual(bundle.status.metadata["analysis_time"], "2026-08-12T10:35:00+00:00")
self.assertEqual(bundle.status.metadata["analysis_anchor_source"], "latest_serene_state")
self.assertTrue(all(call[0] == "2026-08-12T10:35:00+00:00" for call in client.forecast_calls))
```

Retain a separate test proving `follow_latest=False` uses the normalized user-selected time and sets `analysis_anchor_source` to `user_selected_time`.

- [ ] **Step 5: Run the loader tests and confirm the new argument/behaviour fails**

Run:

```bash
.venv/bin/python -m unittest streamlit_cloud_github.tests.test_api_only_data_loader -v
```

Expected: FAIL because `load_icao_products` does not accept `follow_latest` and still forecasts from the guessed requested time.

- [ ] **Step 6: Implement single-download latest-cycle resolution**

In `load_icao_products`, create the client before rolling/baseline times are built. For `follow_latest=True`:

1. Call `download_aida_raw_output(None, "ultra")` once.
2. Extract `analysis = read_aida_state_time(payload)`.
3. Keep the payload as `prefetched_analysis_payload`.
4. Build rolling, baseline, Kp and forecast times from that authoritative `analysis`.
5. When the rolling loop reaches `analysis`, calculate from the prefetched payload rather than downloading it again.

For `follow_latest=False`, preserve the existing normalized selected-time path. Store both requested and authoritative timestamps in metadata.

- [ ] **Step 7: Pass follow-latest state from the Streamlit loader call**

Change the call in `_load_dashboard_data` to include:

```python
follow_latest=bool(params.get("follow_latest", False)),
```

Update sidebar wording from “latest safely published AIDA cadence” to “latest analysis cycle reported by SERENE”.

- [ ] **Step 8: Run focused tests**

Run:

```bash
.venv/bin/python -m unittest \
  streamlit_cloud_github.tests.test_aida_adapter \
  streamlit_cloud_github.tests.test_api_only_data_loader \
  streamlit_cloud_github.tests.test_dashboard_settings -v
```

Expected: PASS.

- [ ] **Step 9: Commit the authoritative-cycle change**

```bash
git add streamlit_cloud_github/aida_adapter.py \
  streamlit_cloud_github/data_loader.py \
  streamlit_cloud_github/app.py \
  streamlit_cloud_github/tests/test_aida_adapter.py \
  streamlit_cloud_github/tests/test_api_only_data_loader.py \
  streamlit_cloud_github/tests/test_dashboard_settings.py
git commit -m "fix: anchor forecasts to latest SERENE cycle"
```

---

### Task 2: Separate primary forecast products from audit-only requests

**Files:**
- Modify: `streamlit_cloud_github/data_loader.py`
- Modify: `streamlit_cloud_github/tests/test_api_only_data_loader.py`
- Modify: `streamlit_cloud_github/tests/test_data_preview.py`

**Interfaces:**
- Produces constants `PRIMARY_FORECAST_PERIODS = (30, 90)`, `AUDIT_ONLY_FORECAST_PERIODS = (180, 360)`, and `FORECAST_PERIODS = PRIMARY_FORECAST_PERIODS + AUDIT_ONLY_FORECAST_PERIODS`.
- Each audit row produces `forecast_parameter`, `display_role`, `outcome`, `analysis_time`, `valid_time`, `latency`, `downloaded_from_serene`, and `message`.
- `outcome` is one of `available`, `not_published`, `authentication_failed`, `network_failed`, or `decode_failed`.
- Metadata produces `available_primary_forecast_periods: list[int]`.

- [ ] **Step 1: Write failing tests for the four request outcomes and two display horizons**

Create client responses for:

```python
{
    30: (True, "Downloaded", b"forecast-30"),
    90: (True, "Downloaded", b"forecast-90"),
    180: (False, "status 404", None),
    360: (False, "SERENE rejected the API token", None),
}
```

Assert:

```python
self.assertEqual(bundle.status.metadata["available_primary_forecast_periods"], [30, 90])
self.assertEqual(set(bundle.products["product_kind"]), {"analysis", "forecast_30", "forecast_90"})
self.assertEqual([row["display_role"] for row in audit], ["primary", "primary", "audit_only", "audit_only"])
self.assertEqual([row["outcome"] for row in audit], ["available", "available", "not_published", "authentication_failed"])
```

Add separate mocked exceptions/messages proving network and decode failures map to `network_failed` and `decode_failed`.

- [ ] **Step 2: Run focused loader tests and verify failure**

```bash
.venv/bin/python -m unittest streamlit_cloud_github.tests.test_api_only_data_loader -v
```

Expected: FAIL because the loader currently requests `(90, 180, 360)`, lacks `display_role`/`outcome`, and includes every decoded forecast in products.

- [ ] **Step 3: Implement forecast-period separation and request classification**

Define the three constants, request all four periods for evidence, and append product frames only when `period in PRIMARY_FORECAST_PERIODS`. Add a pure helper:

```python
def _forecast_request_outcome(ok: bool, message: str, decoded: bool = True) -> str:
    text = str(message).casefold()
    if ok and decoded:
        return "available"
    if "401" in text or "403" in text or "token" in text:
        return "authentication_failed"
    if "404" in text or "not available" in text or "not provide" in text:
        return "not_published"
    if "timeout" in text or "connection" in text or "network" in text:
        return "network_failed"
    return "decode_failed"
```

For successfully downloaded audit-only payloads, record `available` without running the local grid calculation. For primary decode failure, update the existing audit row to `decode_failed` and do not append a frame.

- [ ] **Step 4: Store available primary periods and corrected counts**

Derive `available_primary_forecast_periods` from successfully decoded primary frames. Preserve `forecast_downloads` as the count of all official HDF5 downloads and add `primary_forecast_states` as the count of usable primary forecast states.

- [ ] **Step 5: Run loader and data-preview tests**

```bash
.venv/bin/python -m unittest \
  streamlit_cloud_github.tests.test_api_only_data_loader \
  streamlit_cloud_github.tests.test_data_preview -v
```

Expected: PASS.

- [ ] **Step 6: Commit loader horizon separation**

```bash
git add streamlit_cloud_github/data_loader.py \
  streamlit_cloud_github/tests/test_api_only_data_loader.py \
  streamlit_cloud_github/tests/test_data_preview.py
git commit -m "feat: separate displayed and audited forecast horizons"
```

---

### Task 3: Restrict risk products and research messages to +30/+90 minutes

**Files:**
- Modify: `streamlit_cloud_github/icao_risk.py`
- Modify: `streamlit_cloud_github/icao_message.py`
- Test: `streamlit_cloud_github/tests/test_icao_risk.py`
- Test: `streamlit_cloud_github/tests/test_icao_message.py`
- Test: `streamlit_cloud_github/tests/test_icao_visualisation.py`

**Interfaces:**
- `FORECAST_HORIZONS = {"+30 min": 30, "+90 min": 90}`.
- Summary forecast fields are exactly `+30 min forecast/status/source` and `+90 min forecast/status/source`.
- `generate_icao_message(..., forecasts: Mapping[int, str | None], ...)` accepts only keys 30 and 90 and emits only supplied, available forecast categories.

- [ ] **Step 1: Write failing risk-summary and map tests**

Add `forecast_30` and `forecast_90` rows and assert:

```python
self.assertIn("+30 min forecast", summary.columns)
self.assertIn("+90 min forecast", summary.columns)
self.assertNotIn("+3h forecast", summary.columns)
self.assertNotIn("+6h forecast", summary.columns)
self.assertEqual(set(FORECAST_HORIZONS), {"+30 min", "+90 min"})
```

Verify `build_categorical_cells(..., "+30 min")` uses only `forecast_30`, while +3h raises the existing unsupported-horizon error.

- [ ] **Step 2: Write failing research-message tests**

Use `{30: "OK", 90: "MODERATE"}` and assert the message contains `FCST SWX +30 MIN` and `FCST SWX +90 MIN`, but no `+3 HR` or `+6 HR`. Add a test where `{30: None, 90: "OK"}` and assert +30 is omitted rather than reported as a safe category.

- [ ] **Step 3: Run the risk/message tests and verify failure**

```bash
.venv/bin/python -m unittest \
  streamlit_cloud_github.tests.test_icao_risk \
  streamlit_cloud_github.tests.test_icao_message \
  streamlit_cloud_github.tests.test_icao_visualisation -v
```

Expected: FAIL because +30 is absent and +3h/+6h are still primary fields.

- [ ] **Step 4: Implement the two-horizon risk schema**

Replace `SUMMARY_COLUMNS`, `FORECAST_HORIZONS`, normalization aliases and row construction so all primary forecast handling uses +30/+90. Preserve Latest and Max3h unchanged, including the rule that Max3h is historical rather than predictive.

- [ ] **Step 5: Implement supplied-horizon message formatting**

Replace the fixed `(90, 180, 360)` loop with:

```python
for period_minutes in (30, 90):
    category = forecasts.get(period_minutes)
    if category is None:
        continue
    label = "+30 MIN" if period_minutes == 30 else "+90 MIN"
```

Reject unsupported forecast keys with `ValueError` so +3h/+6h cannot silently re-enter research messages.

- [ ] **Step 6: Run the focused tests**

Run the Step 3 command again. Expected: PASS.

- [ ] **Step 7: Commit risk and message changes**

```bash
git add streamlit_cloud_github/icao_risk.py \
  streamlit_cloud_github/icao_message.py \
  streamlit_cloud_github/tests/test_icao_risk.py \
  streamlit_cloud_github/tests/test_icao_message.py \
  streamlit_cloud_github/tests/test_icao_visualisation.py
git commit -m "feat: present verified short-range forecast horizons"
```

---

### Task 4: Make the Streamlit decision surface availability-aware

**Files:**
- Modify: `streamlit_cloud_github/app.py`
- Test: `streamlit_cloud_github/tests/test_dashboard_settings.py`
- Test: `streamlit_cloud_github/tests/test_icao_app_helpers.py`

**Interfaces:**
- Produces `_available_primary_periods(status: LoadStatus) -> list[int]`.
- Produces `_visible_summary_columns(summary: pd.DataFrame, status: LoadStatus) -> list[str]`.
- Produces `_forecast_availability_message(status: LoadStatus) -> str`.

- [ ] **Step 1: Add failing pure-helper tests**

Construct audit metadata with 30/90 available and 180/360 not published. Assert:

```python
self.assertEqual(_available_primary_periods(status), [30, 90])
self.assertIn("+30 min forecast", _visible_summary_columns(summary, status))
self.assertNotIn("+3h forecast", _visible_summary_columns(summary, status))
self.assertIn("+3 h and +6 h not currently published", _forecast_availability_message(status))
```

Add partial availability with only period 30 successful and assert all +90 value/status/source columns are omitted from the primary table and +90 is absent from map horizon choices.

- [ ] **Step 2: Run helper/UI tests and verify failure**

```bash
.venv/bin/python -m unittest \
  streamlit_cloud_github.tests.test_icao_app_helpers \
  streamlit_cloud_github.tests.test_dashboard_settings -v
```

Expected: FAIL because the helper interfaces and +30 UI do not exist.

- [ ] **Step 3: Implement dynamic primary-table and map visibility**

Before styling the summary, select base columns plus the three forecast columns for each period returned by `_available_primary_periods`. Build map radio options from `Latest` plus available primary period labels. If no official primary forecast is available, retain Latest only and show an informational message rather than an empty control.

- [ ] **Step 4: Update research-message inputs**

Build forecast dictionaries from successful periods only:

```python
forecasts = {
    period: _available_category(row[f"{label} status"])
    for period, label in ((30, "+30 min"), (90, "+90 min"))
    if period in available_periods
}
```

Use the same logic for GNSS and HF COM messages.

- [ ] **Step 5: Render status and audit evidence**

Add the availability message to “SERENE API and data status”. Update forecast-audit rows with `Display role` and `Outcome`. Map outcomes to readable phrases without rewriting their underlying evidence:

- `available` -> `Official HDF5 retrieved`
- `not_published` -> `Not published for this analysis cycle`
- `authentication_failed` -> `Authentication rejected`
- `network_failed` -> `Temporary network failure`
- `decode_failed` -> `Downloaded file could not be interpreted`

Update the audit caption to explain periods `30, 90, 180, 360`, and state that 180/360 are audit-only.

- [ ] **Step 6: Remove outdated +3h/+6h primary wording**

Update the sidebar mode help, main caption, table caption and explanatory panels. The primary UI must say it presents verified +30/+90 official products, while the audit panel records longer-period availability.

- [ ] **Step 7: Run focused application tests**

Run the Step 2 command again. Expected: PASS.

- [ ] **Step 8: Commit Streamlit presentation changes**

```bash
git add streamlit_cloud_github/app.py \
  streamlit_cloud_github/tests/test_icao_app_helpers.py \
  streamlit_cloud_github/tests/test_dashboard_settings.py
git commit -m "feat: show only available primary forecasts"
```

---

### Task 5: Align documentation, run full verification and push only August

**Files:**
- Modify: `streamlit_cloud_github/README.md`
- Modify: `streamlit_cloud_github/部署说明.md`
- Verify: all files under `streamlit_cloud_github/tests/`

**Interfaces:**
- Documentation states that the evaluated 2026-08-12 cycles returned official +30/+90 HDF5 products and 404 for +3h/+6h, without claiming this is permanent SERENE behaviour.
- Documentation distinguishes official forecasts, generated research fallbacks and audit-only availability checks.

- [ ] **Step 1: Update README and deployment documentation**

Document:

- latest-cycle resolution through the authoritative AIDA state time;
- primary +30/+90 presentation;
- audit-only +3h/+6h requests;
- the meaning of 401/403, 404, network and decode outcomes;
- Max3h as a historical rolling maximum;
- the need to configure `SERENE_API_TOKEN` in Streamlit Cloud Secrets without committing `.env`.

Include the report-safe paragraph from the approved design and label it as evidence from evaluated cycles, not a permanent upstream guarantee.

- [ ] **Step 2: Scan for stale primary +3h/+6h claims**

Run:

```bash
rg -n "\+3h|\+6h|180, 360|90, 180, 360|forecast_180|forecast_360" \
  streamlit_cloud_github \
  -g '*.py' -g '*.md'
```

Expected: remaining matches are limited to loader audit-only constants, audit tests, explicit unavailability explanations and historical compatibility tests. No decision-facing claim presents them as primary forecasts.

- [ ] **Step 3: Run formatting and secret checks**

```bash
git diff --check
git status --short
git ls-files | rg '(^|/)\.env$|secrets\.toml$' && exit 1 || true
```

Expected: no whitespace errors; `.env` and `secrets.toml` are not tracked; only intended August files are changed.

- [ ] **Step 4: Run the complete test suite**

```bash
.venv/bin/python -m unittest discover -s streamlit_cloud_github/tests -v
```

Expected: all tests pass with final output `OK`.

- [ ] **Step 5: Run a live token-safe API smoke test**

Using the local `.env` without printing its token:

1. Request latest Ultra and Rapid analyses.
2. Extract their actual AIDA cycle times.
3. Request periods 30, 90, 180 and 360 against those exact cycles.
4. Confirm 30/90 successful responses are HDF5.
5. Record 180/360 responses as current-cycle evidence; do not require them to remain 404 forever.

Expected for the 2026-08-12 evidence snapshot: 30/90 return HTTP 200 HDF5 and 180/360 return HTTP 404 for both Ultra and Rapid.

- [ ] **Step 6: Start Streamlit and perform a browser smoke test**

Run:

```bash
.venv/bin/streamlit run streamlit_cloud_github/app.py --server.headless true
```

Verify through the browser:

- follow-latest loads the server-reported cycle;
- the main table/map/message surfaces show successful +30/+90 horizons only;
- +3h/+6h appear only in status/audit evidence;
- authentication and upstream unavailability are visually distinct;
- no token appears in UI warnings, metadata or downloadable data.

- [ ] **Step 7: Commit documentation and final test alignment**

```bash
git add streamlit_cloud_github/README.md \
  streamlit_cloud_github/部署说明.md \
  streamlit_cloud_github/tests
git commit -m "docs: explain verified SERENE forecast availability"
```

- [ ] **Step 8: Verify the destination remote before pushing**

```bash
git remote -v
git branch --show-current
```

Expected: `origin` points to `ylianxin2003-droid/August-project-version` and the intended branch is `main`. If either differs, stop without pushing.

- [ ] **Step 9: Push the verified August branch**

```bash
git push origin main
```

After pushing, compare local `HEAD` with:

```bash
git ls-remote origin refs/heads/main
```

Expected: the hashes match. Do not run any push command in the old repository.
