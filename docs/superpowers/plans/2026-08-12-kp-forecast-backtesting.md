# Kp +30/+90 Forecast and Backtesting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate Auroral Absorption +30/+90 assessments from the SERENE archive start through Follow Latest, using historical GFZ observed outcomes for Backtesting and the current GFZ PAGER/SWIFT ensemble for genuinely future targets.

**Architecture:** Keep observed Kp history and future horizon evidence in separate DataFrames so future information cannot enter Latest, Max-3h, or the prior-96-hour storm gate. A dedicated resolver maps each target to a three-hour interval, prefers an already-published observed outcome, otherwise uses a fresh aligned official ensemble forecast, and returns explicit evidence roles for risk/UI rendering.

**Tech Stack:** Python 3, pandas, requests-compatible sessions, unittest, Streamlit, SERENE AIDA HDF5, GFZ historical JSON and PAGER/SWIFT JSON.

## Global Constraints

- Selectable SERENE range starts at `2024-09-28T00:00:00Z` and ends at the latest HDF5 analysis cycle.
- Earlier GFZ Kp may be fetched only for the first cycle's preceding-96-hour gate.
- Historical +30/+90 values are labelled `GFZ observed outcome — backtesting only` and are never called forecasts.
- Future targets use only a fresh, cycle-aligned GFZ PAGER/SWIFT official ensemble forecast.
- Ensemble median determines the primary category; maximum and `P(Kp >= 8)` express uncertainty without category escalation.
- Do not copy, interpolate, or persist the latest Kp into future horizons.
- Do not change SERENE AIDA acquisition, TEC/MUF/PSD calculations, thresholds, maps, or route logic.
- Commit and push only to `ylianxin2003-droid/August-project-version`; keep `.superpowers/` untracked and the legacy push URL disabled.

---

## File Structure

- `streamlit_cloud_github/serene_client.py`: parse/cache the public latest GFZ ensemble forecast and preserve HTTP freshness metadata.
- `streamlit_cloud_github/data_loader.py`: resolve +30/+90 target intervals independently into a dedicated `kp_horizons` DataFrame.
- `streamlit_cloud_github/icao_risk.py`: consume explicit horizon evidence in the Auroral Absorption summary row.
- `streamlit_cloud_github/app.py`: pass horizon evidence and show role/uncertainty/freshness text.
- `streamlit_cloud_github/tests/test_serene_indices.py`: forecast parser, request, token isolation, cache, and malformed-data tests.
- `streamlit_cloud_github/tests/test_api_only_data_loader.py`: archive boundary, Backtesting, official forecast, mixed horizon, and no-leakage tests.
- `streamlit_cloud_github/tests/test_icao_risk.py`: median classification, uncertainty, sources, and unavailable behavior.
- `streamlit_cloud_github/README.md` and `streamlit_cloud_github/部署说明.md`: English/Chinese source and interpretation documentation.

### Task 1: Parse and Fetch the GFZ Ensemble Forecast

**Files:**
- Modify: `streamlit_cloud_github/serene_client.py`
- Test: `streamlit_cloud_github/tests/test_serene_indices.py`

**Interfaces:**
- Consumes: PAGER/SWIFT dict-of-dicts JSON with `Time (UTC)`, `median`, `maximum`, and `prob >= 8`.
- Produces: `parse_gfz_kp_forecast(payload: object) -> pd.DataFrame` and `fetch_gfz_kp_forecast() -> tuple[bool, str, pd.DataFrame]`; returned columns are `interval_start`, `median`, `maximum`, `probability_kp_ge_8`, `source`, and `issue_time`.

- [ ] **Step 1: Write failing parser tests**

Use a literal two-row payload:

```python
payload = {
    "Time (UTC)": {"0": "12-08-2026 12:00", "1": "12-08-2026 15:00"},
    "median": {"0": 7.5, "1": 8.2},
    "maximum": {"0": 8.4, "1": 9.0},
    "prob >= 8": {"0": 0.2, "1": 0.7},
}
frame = SereneClient.parse_gfz_kp_forecast(payload)
self.assertEqual(frame["median"].tolist(), [7.5, 8.2])
self.assertEqual(frame["probability_kp_ge_8"].tolist(), [0.2, 0.7])
```

Also assert empty output for mismatched keys, invalid timestamps, Kp outside `[0, 9]`, maximum below median, and probability outside `[0, 1]`.

- [ ] **Step 2: Verify parser RED**

Run:

```bash
.venv/bin/python -m unittest streamlit_cloud_github.tests.test_serene_indices.GfzKpForecastTest -v
```

Expected: `AttributeError` because `parse_gfz_kp_forecast` is absent.

- [ ] **Step 3: Implement the minimal parser**

Implement UTC parsing with format `%d-%m-%Y %H:%M`, numeric validation, common row-key intersection, sorting, and source label `GFZ official PAGER/SWIFT ensemble forecast`.

- [ ] **Step 4: Write failing fetch/cache/token tests**

Assert the exact URL:

```text
https://spaceweather.gfz.de/fileadmin/Kp-Forecast/CSV/kp_product_file_FORECAST_PAGER_SWIFT_LAST.json
```

Assert no Authorization header, one-hour shared cache reuse, `Last-Modified` parsing into UTC `issue_time`, and controlled failure for bad HTTP/JSON.

- [ ] **Step 5: Verify fetch RED, implement, and run GREEN**

Run the new class before and after implementing `_gfz_kp_forecast_cache` and the public request. Then run:

```bash
.venv/bin/python -m unittest streamlit_cloud_github.tests.test_serene_indices -v
```

Expected: all index and forecast tests pass.

- [ ] **Step 6: Commit the forecast client**

```bash
git add streamlit_cloud_github/serene_client.py streamlit_cloud_github/tests/test_serene_indices.py
git commit -m "feat: load official GFZ Kp ensemble forecast"
```

### Task 2: Resolve +30/+90 Evidence Without Future Leakage

**Files:**
- Modify: `streamlit_cloud_github/data_loader.py`
- Test: `streamlit_cloud_github/tests/test_api_only_data_loader.py`

**Interfaces:**
- Consumes: analysis `pd.Timestamp`, observed GFZ Kp returned separately for target intervals, and the forecast DataFrame from Task 1.
- Produces: `IcaoProductBundle.kp_horizons: pd.DataFrame` with `horizon_minutes`, `target_time`, `interval_start`, `value`, `evidence_role`, `source`, `ensemble_maximum`, `probability_kp_ge_8`, `data_status`, `issue_time`, and `availability_reason`.

- [ ] **Step 1: Write failing archive and July Backtesting tests**

For `2024-09-28T00:00:00Z`, assert +30/+90 map to the `00:00` observed interval. For `2026-07-01T05:55:00Z`, assert +30 maps to `06:00` and +90 maps to `06:00`, with role `observed_backtesting`, explicit source, no ensemble fields, and no call to the latest forecast.

- [ ] **Step 2: Write failing current and mixed-source tests**

For a latest analysis whose future targets are not observed, provide forecast rows and assert role `official_forecast`, median value, maximum, probability, and issue time. Add a boundary case where +30 is observed but +90 is forecast, proving independent resolution.

- [ ] **Step 3: Write failing stale/unaligned/no-leakage tests**

Assert stale or unrelated `LAST` data leaves the affected horizon unavailable. Assert future observed/forecast rows never enter `bundle.indices`, never change Latest/Max-3h, and never affect `_kp_history_is_complete` or `kp_storm_eligible`.

- [ ] **Step 4: Verify loader RED**

Run:

```bash
.venv/bin/python -m unittest streamlit_cloud_github.tests.test_api_only_data_loader -v
```

Expected: failures because `IcaoProductBundle` has no `kp_horizons` and the resolver is absent.

- [ ] **Step 5: Implement the resolver and bundle field**

Add `kp_horizons` as a new DataFrame field. Query observed Kp through the latest horizon interval independently from the preceding-96-hour DataFrame. Resolve each horizon observed-first, then forecast. Validate forecast alignment using interval coverage plus a recent `issue_time`; do not call the latest forecast when both target observations exist.

- [ ] **Step 6: Run loader GREEN and regression tests**

Run:

```bash
.venv/bin/python -m unittest streamlit_cloud_github.tests.test_api_only_data_loader streamlit_cloud_github.tests.test_icao_risk -v
```

Expected: archive, July, current, mixed, stale, and no-leakage cases pass.

- [ ] **Step 7: Commit horizon resolution**

```bash
git add streamlit_cloud_github/data_loader.py streamlit_cloud_github/tests/test_api_only_data_loader.py
git commit -m "feat: resolve Kp forecast and backtesting horizons"
```

### Task 3: Render Horizon Risk and Ensemble Uncertainty

**Files:**
- Modify: `streamlit_cloud_github/icao_risk.py`
- Modify: `streamlit_cloud_github/app.py`
- Test: `streamlit_cloud_github/tests/test_icao_risk.py`
- Test: `streamlit_cloud_github/tests/test_icao_app_helpers.py`

**Interfaces:**
- Consumes: `build_icao_summary(products, indices, eligible, kp_horizons=None)`.
- Produces: Auroral Absorption +30/+90 value, status, role-aware source, maximum/probability evidence, and low-probability high-impact warning.

- [ ] **Step 1: Write failing risk summary tests**

Assert median `7.5` produces `OK` even when maximum `8.4`; source remains official forecast and warning says the ensemble reaches Kp >= 8. Assert median `8.2` is `MODERATE`, observed Backtesting uses actual Kp, and missing rows remain unavailable without fabricated OK.

- [ ] **Step 2: Verify risk RED**

Run:

```bash
.venv/bin/python -m unittest streamlit_cloud_github.tests.test_icao_risk -v
```

Expected: current `_kp_summary_row` hard-codes both horizons unavailable.

- [ ] **Step 3: Implement optional horizon input**

Extend the public function compatibly so existing callers/tests without horizon evidence still work. Populate existing +30/+90 columns and add role/uncertainty fields without changing Latest or Max-3h classification.

- [ ] **Step 4: Write failing app integration tests and implement display**

Assert `app.py` passes `bundle.kp_horizons` into `build_icao_summary`; the evidence panel renders official forecast median/maximum/probability/freshness and the exact Backtesting disclaimer. Update visible wording from generic forecast to assessment where it covers both roles.

- [ ] **Step 5: Run risk/UI GREEN**

Run:

```bash
.venv/bin/python -m unittest streamlit_cloud_github.tests.test_icao_risk streamlit_cloud_github.tests.test_icao_app_helpers streamlit_cloud_github.tests.test_dashboard_settings -v
```

Expected: all risk, helper, and static Dashboard checks pass.

- [ ] **Step 6: Commit presentation changes**

```bash
git add streamlit_cloud_github/icao_risk.py streamlit_cloud_github/app.py streamlit_cloud_github/tests/test_icao_risk.py streamlit_cloud_github/tests/test_icao_app_helpers.py
git commit -m "feat: show Kp horizon evidence and uncertainty"
```

### Task 4: Documentation, Live Acceptance, and August Push

**Files:**
- Modify: `streamlit_cloud_github/README.md`
- Modify: `streamlit_cloud_github/部署说明.md`

**Interfaces:**
- Consumes: completed Tasks 1-3.
- Produces: documented, regression-tested, live-verified August `main`.

- [ ] **Step 1: Update English and Chinese documentation**

Document the verified SERENE start, observed Backtesting versus official forecast distinction, three-hour mapping, median/maximum/probability interpretation, and failure behavior. State that historical outcomes are not archived forecasts.

- [ ] **Step 2: Run the complete test suite**

```bash
.venv/bin/python -m unittest discover -s streamlit_cloud_github/tests -v
```

Expected: zero failures and zero errors.

- [ ] **Step 3: Run live acceptance without printing secrets**

Using `/Users/a123/Desktop/dashboard-2/.env`, verify:

- archive start produces Backtesting evidence;
- `2026-07-01T05:55:00Z` produces +30/+90 observed outcomes;
- Follow Latest uses official ensemble values when targets are future;
- all AIDA product rows retain SERENE sources;
- Latest/Max-3h/96-hour gate remain observed-only.

- [ ] **Step 4: Check repository safety**

```bash
git diff --check
git status --short
git remote -v
git ls-files | rg '(^|/)(\.env|secrets\.toml)$' || true
```

Expected: only `.superpowers/` is untracked, no secret file is tracked, and legacy push remains disabled.

- [ ] **Step 5: Commit docs and push August only**

```bash
git add streamlit_cloud_github/README.md streamlit_cloud_github/部署说明.md
git commit -m "docs: explain Kp forecast and backtesting evidence"
git push origin main
```

Verify local and remote `main` hashes match; do not push `legacy-source`.
