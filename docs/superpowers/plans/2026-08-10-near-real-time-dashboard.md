# Near-Real-Time Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct current-day SERENE forecast requests, add safe optional 15-minute near-real-time refresh, expose Kp/ap source freshness, and publish all work only to `August-project-version`.

**Architecture:** Preserve the existing Streamlit pipeline and isolate new time/refresh decisions in pure helpers so they can be tested without Streamlit. The data loader will send the analysis timestamp to the forecast endpoint and derive forecast valid times locally. The UI will follow a safe UTC-minus-15-minute anchor and use a Streamlit fragment only as a lightweight scheduler; all scientific loading remains in the existing `_do_load` path.

**Tech Stack:** Python 3.11, Streamlit, pandas, requests, unittest, SERENE AIDA API, Git/GitHub.

## Global Constraints

- Modify and push only `/Users/a123/Desktop/August-project-version` and `ylianxin2003-droid/August-project-version`.
- Keep `ylianxin2003-droid/primay-test-frist-version` unchanged at `951c1cf79adc3d66e7aaf62baa472853ba3f8b87`.
- Use current UTC minus 15 minutes, floored to five minutes, as the near-real-time analysis anchor.
- Automatic refresh is optional, defaults off, runs every 15 minutes, and is eligible only for `Live SERENE API`, `Quick Demo`, and `Follow latest near-real-time`.
- Never invent Kp, ap, PSD, HF COM risk, forecast data, or operational advisories.
- Never commit `.env`, Streamlit Secrets, API tokens, raw credentials, or token-bearing logs.
- Preserve observations when forecasts, Kp/ap, or scheduled refreshes fail.

---

### Task 1: Correct Forecast Analysis-Time Requests

**Files:**
- Modify: `streamlit_cloud_github/data_loader.py:188-220`
- Modify: `streamlit_cloud_github/tests/test_api_only_data_loader.py:125-160`

**Interfaces:**
- Consumes: `SereneClient.download_aida_forecast(requested_time: str, latency: str, period_minutes: int)`.
- Produces: forecast calls anchored at the analysis timestamp and audit rows with separate `analysis_time` and `valid_time`.

- [ ] **Step 1: Change the loader test to require analysis-time forecast requests**

```python
self.assertEqual(client.forecast_requests, [
    ("2026-06-21T20:00:00+00:00", "ultra", 90),
    ("2026-06-21T20:00:00+00:00", "ultra", 180),
    ("2026-06-21T20:00:00+00:00", "ultra", 360),
])
self.assertEqual(
    [row["valid_time"] for row in bundle.status.metadata["forecast_request_audit"]],
    [
        "2026-06-21T21:30:00+00:00",
        "2026-06-21T23:00:00+00:00",
        "2026-06-22T02:00:00+00:00",
    ],
)
```

- [ ] **Step 2: Run the focused test and verify the old future-time behaviour fails**

Run:

```bash
python -m unittest tests.test_api_only_data_loader.ApiOnlyDataLoaderTest.test_icao_products_use_one_download_per_time_and_official_forecasts -v
```

Expected: FAIL because current calls use `analysis + period` as `requested_time`.

- [ ] **Step 3: Pass the analysis timestamp to every forecast request**

```python
forecast_time = analysis + pd.Timedelta(minutes=period)
ok, message, payload = client.download_aida_forecast(
    analysis.isoformat(), latency, period
)
```

Retain `forecast_time` for audit metadata and display validity.

- [ ] **Step 4: Run focused forecast and loader tests**

Run:

```bash
python -m unittest tests.test_api_only_data_loader tests.test_aida_output_client -v
```

Expected: PASS.

- [ ] **Step 5: Commit the forecast correction**

```bash
git add streamlit_cloud_github/data_loader.py streamlit_cloud_github/tests/test_api_only_data_loader.py
git commit -m "fix: anchor forecasts to analysis time"
```

---

### Task 2: Add Pure Near-Real-Time Decision Helpers

**Files:**
- Create: `streamlit_cloud_github/realtime.py`
- Create: `streamlit_cloud_github/tests/test_realtime.py`

**Interfaces:**
- Produces: `safe_analysis_time(reference_time: datetime | pd.Timestamp | None = None) -> pd.Timestamp`.
- Produces: `auto_refresh_eligible(data_loading_mode: str, dashboard_mode: str, follow_latest: bool, auto_refresh: bool) -> bool`.
- Produces: `should_reload_anchor(candidate: pd.Timestamp, last_loaded: str | pd.Timestamp | None) -> bool`.

- [ ] **Step 1: Write failing tests for the safe anchor and refresh gates**

```python
def test_safe_analysis_time_subtracts_delay_and_floors_to_five_minutes(self):
    reference = pd.Timestamp("2026-08-10T09:09:51Z")
    self.assertEqual(
        safe_analysis_time(reference),
        pd.Timestamp("2026-08-10T08:50:00Z"),
    )

def test_auto_refresh_requires_live_quick_follow_latest(self):
    self.assertTrue(auto_refresh_eligible(
        "Live SERENE API", "Quick Demo", True, True
    ))
    self.assertFalse(auto_refresh_eligible(
        "Live SERENE API", "Full ICAO-style mode", True, True
    ))

def test_same_anchor_is_not_reloaded(self):
    anchor = pd.Timestamp("2026-08-10T08:50:00Z")
    self.assertFalse(should_reload_anchor(anchor, anchor.isoformat()))
```

- [ ] **Step 2: Run the new tests and verify the module is missing**

Run:

```bash
python -m unittest tests.test_realtime -v
```

Expected: ERROR with `ModuleNotFoundError: No module named 'realtime'`.

- [ ] **Step 3: Implement the pure helper module**

```python
from __future__ import annotations

from datetime import datetime
import pandas as pd

PUBLICATION_DELAY = pd.Timedelta(minutes=15)
AIDA_CADENCE = "5min"

def safe_analysis_time(reference_time: datetime | pd.Timestamp | None = None) -> pd.Timestamp:
    now = pd.Timestamp.now(tz="UTC") if reference_time is None else pd.Timestamp(reference_time)
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    else:
        now = now.tz_convert("UTC")
    return (now - PUBLICATION_DELAY).floor(AIDA_CADENCE)

def auto_refresh_eligible(data_loading_mode, dashboard_mode, follow_latest, auto_refresh):
    return bool(
        data_loading_mode == "Live SERENE API"
        and dashboard_mode == "Quick Demo"
        and follow_latest
        and auto_refresh
    )

def should_reload_anchor(candidate, last_loaded):
    if last_loaded is None:
        return True
    return pd.Timestamp(candidate) != pd.Timestamp(last_loaded)
```

- [ ] **Step 4: Run helper tests**

Run:

```bash
python -m unittest tests.test_realtime -v
```

Expected: PASS.

- [ ] **Step 5: Commit the helper module**

```bash
git add streamlit_cloud_github/realtime.py streamlit_cloud_github/tests/test_realtime.py
git commit -m "feat: add near-real-time refresh rules"
```

---

### Task 3: Integrate Follow-Latest and Scheduled Refresh Controls

**Files:**
- Modify: `streamlit_cloud_github/app.py:64-283`
- Modify: `streamlit_cloud_github/tests/test_dashboard_settings.py`
- Modify: `streamlit_cloud_github/requirements.txt`

**Interfaces:**
- Consumes: `safe_analysis_time`, `auto_refresh_eligible`, and `should_reload_anchor` from `realtime.py`.
- Produces: sidebar controls, synchronized UTC widgets, refresh metadata, and deduplicated scheduled loads through `_do_load(params)`.

- [ ] **Step 1: Add failing source-contract tests for the controls and safe scheduler**

```python
def test_dashboard_exposes_follow_latest_and_auto_refresh(self):
    source = Path(APP_PATH).read_text(encoding="utf-8")
    self.assertIn("Follow latest near-real-time", source)
    self.assertIn("Auto-refresh every 15 minutes", source)
    self.assertIn("@st.fragment(run_every=\"15m\")", source)
    self.assertIn("auto_refresh_eligible", source)

def test_full_mode_auto_refresh_is_blocked_in_copy(self):
    source = Path(APP_PATH).read_text(encoding="utf-8")
    self.assertIn("Automatic refresh is limited to Live SERENE API + Quick Demo", source)
```

- [ ] **Step 2: Run the dashboard settings tests and verify they fail**

Run:

```bash
python -m unittest tests.test_dashboard_settings -v
```

Expected: FAIL because the controls and scheduler are not present.

- [ ] **Step 3: Add session defaults and synchronize latest-time widgets before rendering**

Add session keys for `follow_latest`, `auto_refresh`, `last_auto_loaded_anchor`, `last_successful_refresh`, and `last_refresh_attempt`. Before date/time widgets are created, set `end_date` and `end_time_clock` from `safe_analysis_time()` whenever follow-latest is enabled.

- [ ] **Step 4: Add sidebar controls and eligibility messaging**

Render `Follow latest near-real-time` enabled by default and `Auto-refresh every 15 minutes` disabled by default. Disable automatic refresh outside Live Quick Demo follow-latest mode and show the exact restriction message.

- [ ] **Step 5: Add the 15-minute fragment scheduler**

```python
@st.fragment(run_every="15m")
def _auto_refresh_tick(params: dict) -> None:
    if not auto_refresh_eligible(
        params["data_loading_mode"], params["mode"],
        params["follow_latest"], params["auto_refresh"],
    ):
        return
    anchor = safe_analysis_time()
    if should_reload_anchor(anchor, st.session_state.last_auto_loaded_anchor):
        st.session_state.pending_auto_refresh = anchor.isoformat()
        st.rerun()
```

On the full rerun, consume `pending_auto_refresh`, rebuild the latest parameters, call `_do_load(params)`, and set `last_auto_loaded_anchor` only after a successful load.

- [ ] **Step 6: Display refresh provenance**

Show requested analysis time, actual returned output time, data age, last successful refresh, and next refresh status in the SERENE API/data status panel. A failed scheduled refresh retains the prior dataset and displays the failed attempt time.

- [ ] **Step 7: Pin a Streamlit version with fragment scheduling support**

Change `streamlit` to `streamlit>=1.37,<2` in `requirements.txt` so `st.fragment(run_every=...)` is part of the declared runtime contract.

- [ ] **Step 8: Run UI-contract and helper tests**

Run:

```bash
python -m unittest tests.test_dashboard_settings tests.test_realtime -v
```

Expected: PASS.

- [ ] **Step 9: Commit the UI integration**

```bash
git add streamlit_cloud_github/app.py streamlit_cloud_github/requirements.txt streamlit_cloud_github/tests/test_dashboard_settings.py
git commit -m "feat: add optional near-real-time refresh"
```

---

### Task 4: Expose Official Kp/ap Source Freshness

**Files:**
- Modify: `streamlit_cloud_github/serene_client.py:523-591`
- Modify: `streamlit_cloud_github/data_loader.py:223-300`
- Modify: `streamlit_cloud_github/app.py:430-470`
- Modify: `streamlit_cloud_github/tests/test_serene_indices.py`
- Modify: `streamlit_cloud_github/tests/test_api_only_data_loader.py`

**Interfaces:**
- Produces: `SereneClient.kp_ap_source_latest_time: pd.Timestamp | None` after each Kp/ap fetch.
- Produces: bundle metadata key `kp_ap_source_latest_time` as an ISO string or `None`.
- Consumes: existing `kp_ap_status` and 96-hour completeness gate without weakening either.

- [ ] **Step 1: Write failing tests for stale source metadata**

```python
def test_empty_filtered_range_reports_latest_official_timestamp(self):
    csv_text = (
        "time,Kp,ap,rAp\n"
        "2026-07-07T03:00:00Z,0.7,3,4\n"
    )
    response = Mock(ok=True, text=csv_text)
    client = SereneClient(base_url="https://api.example", token="private-token")
    client._session.request = Mock(return_value=response)
    ok, message, frame = client.fetch_kp_ap_indices(
        "2026-08-06T08:50:00Z", "2026-08-10T08:50:00Z"
    )
    self.assertFalse(ok)
    self.assertTrue(frame.empty)
    self.assertEqual(
        client.kp_ap_source_latest_time,
        pd.Timestamp("2026-07-07T03:00:00Z"),
    )
    self.assertIn("2026-07-07 03:00 UTC", message)
```

- [ ] **Step 2: Run index tests and verify the metadata expectation fails**

Run:

```bash
python -m unittest tests.test_serene_indices -v
```

Expected: FAIL because the client does not expose the latest source timestamp.

- [ ] **Step 3: Parse freshness before applying the requested time filter**

Read the CSV once, compute the maximum valid `time`, store it on the client, and then apply existing filtering. If the filtered frame is empty, include the latest official timestamp in the sanitized message.

- [ ] **Step 4: Add freshness to loader metadata and UI**

Set `kp_ap_source_latest_time` in `LoadStatus.metadata`. When Kp/ap is unavailable, show `Latest official Kp/ap timestamp: ...` in the API/data status panel. Do not modify the PSD eligibility calculation.

- [ ] **Step 5: Run index and loader tests**

Run:

```bash
python -m unittest tests.test_serene_indices tests.test_api_only_data_loader -v
```

Expected: PASS.

- [ ] **Step 6: Commit the freshness reporting**

```bash
git add streamlit_cloud_github/serene_client.py streamlit_cloud_github/data_loader.py streamlit_cloud_github/app.py streamlit_cloud_github/tests/test_serene_indices.py streamlit_cloud_github/tests/test_api_only_data_loader.py
git commit -m "feat: report Kp source freshness"
```

---

### Task 5: Update User and Deployment Documentation

**Files:**
- Modify: `README.md`
- Modify: `streamlit_cloud_github/README.md`
- Modify: `streamlit_cloud_github/部署说明.md`
- Create: `docs/near_real_time_verification_2026-08-10.md`

**Interfaces:**
- Consumes: implemented control names, timing rules, live-test evidence, and Kp freshness behaviour.
- Produces: deployment and assessment evidence with no credentials.

- [ ] **Step 1: Document the exact operating definition**

State that observations use the latest safely published AIDA state, normally UTC minus 15 minutes floored to five minutes; this is near-real-time research monitoring, not an operational zero-latency service.

- [ ] **Step 2: Document safe refresh controls**

Explain that optional automatic refresh is limited to Live API + Quick Demo + Follow latest, while Full Mode remains manual because of its much larger request count.

- [ ] **Step 3: Record the four browser-test results and forecast root cause**

Include the 2026-08-07 through 2026-08-10 table from the approved design, the analysis-time correction, and the requirement to re-test the new deployment.

- [ ] **Step 4: Document Kp/ap freshness honestly**

Record that the official CSV observed on 2026-08-10 ended at `2026-07-07T03:00:00Z`; Kp-dependent PSD/HF products remain unavailable until sufficient official history exists.

- [ ] **Step 5: Run documentation assertions**

Run:

```bash
rg -n "near-real-time|15 minutes|Quick Demo|Kp/ap|2026-07-07|analysis time" README.md streamlit_cloud_github/README.md streamlit_cloud_github/部署说明.md docs/near_real_time_verification_2026-08-10.md
```

Expected: every required topic appears and no file contains a real token.

- [ ] **Step 6: Commit documentation**

```bash
git add README.md streamlit_cloud_github/README.md streamlit_cloud_github/部署说明.md docs/near_real_time_verification_2026-08-10.md
git commit -m "docs: explain near-real-time operation"
```

---

### Task 6: Full Verification and Publish to the August Repository

**Files:**
- Verify: all tracked files
- Modify only if a verification failure requires an in-scope correction.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: verified `August-project-version/main` and evidence that the legacy repository remains unchanged.

- [ ] **Step 1: Install the declared Python 3.11 dependencies in an isolated environment**

Create a task-local virtual environment outside the repository or in ignored `.venv`, install `streamlit_cloud_github/requirements.txt`, and do not copy the legacy `.env` into the new repository.

- [ ] **Step 2: Run the complete test suite**

Run:

```bash
cd streamlit_cloud_github
python -m unittest discover -s tests -v
```

Expected: all tests PASS.

- [ ] **Step 3: Run repository safety scans**

Run:

```bash
git status --short
git ls-files | rg '(^|/)\.env$|secrets\.toml$' && exit 1 || true
rg -n "SERENE_API_TOKEN\s*=\s*['\"][^'\"]+" . --glob '!docs/**' --glob '!*.example' && exit 1 || true
git diff --check origin/main...HEAD
```

Expected: no secret files, no hard-coded token, and no whitespace errors.

- [ ] **Step 4: Start Streamlit and perform a local smoke check**

Run:

```bash
streamlit run streamlit_cloud_github/app.py --server.headless true
```

Verify the page starts, the follow-latest control defaults on, auto-refresh defaults off, and Full Mode disables automatic refresh. Live scientific acceptance remains separate from a no-secret local startup.

- [ ] **Step 5: Review commits and push only to the August origin**

Run:

```bash
git remote -v
git status -sb
git log --oneline --decorate -8
git push origin main
```

Expected: `origin` is `August-project-version`; `legacy-source` has disabled push URL.

- [ ] **Step 6: Verify both remote heads**

Run:

```bash
git ls-remote https://github.com/ylianxin2003-droid/August-project-version.git refs/heads/main
git ls-remote https://github.com/ylianxin2003-droid/primay-test-frist-version.git refs/heads/main
```

Expected: August points to the new implementation commit; legacy remains exactly `951c1cf79adc3d66e7aaf62baa472853ba3f8b87`.

- [ ] **Step 7: Live deployment acceptance**

After the August repository is deployed with valid Streamlit Secrets, test today, yesterday, two days prior, and 72 hours prior. Confirm today uses analysis `file_time` for all forecasts, record official forecast availability without fabricating missing files, and confirm Kp-dependent products remain unavailable when official history is stale.
