# GFZ Historical JSON Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Kp/ap available for every SERENE-supported analysis time from `2024-09-28T00:00:00Z` through the latest SERENE HDF5 cycle by querying the official GFZ JSON service.

**Architecture:** Preserve `SereneClient.fetch_kp_ap_indices()` as the loader boundary, but replace the fixed 30-day text resource with two independent JSON queries, one for Kp and one for ap. Cache by index and normalized 96-hour time range, return the existing long-form DataFrame, and use the authoritative SERENE analysis time as the query end so historical and Follow Latest modes cannot drift.

**Tech Stack:** Python 3, pandas, requests-compatible session objects, unittest, Streamlit, SERENE AIDA HDF5, GFZ JSON API.

## Global Constraints

- The combined dashboard range begins at `2024-09-28T00:00:00Z`; do not claim complete AIDA/Kp analysis before that boundary.
- Query only `analysis_time - 96 hours` through `analysis_time`; do not load the whole archive into the risk engine.
- Use `https://kp.gfz.de/app/json/` with `start`, `end`, and `index`; do not send a SERENE token or Streamlit secret to GFZ.
- Kp and ap requests are independent; Kp success remains usable if ap fails.
- Kp failure or incomplete 96-hour Kp coverage keeps Kp-backed HF risks `Unavailable`.
- Do not change SERENE endpoints, AIDA products, TEC/MUF calculations, risk thresholds, maps, forecast policy, or route logic.
- Push only the August repository; the legacy repository remains read-only.

---

## File Structure

- `streamlit_cloud_github/serene_client.py`: GFZ JSON parsing, range-keyed caching, independent Kp/ap requests, and long-form merge.
- `streamlit_cloud_github/data_loader.py`: authoritative SERENE-to-GFZ time alignment and partial-source metadata.
- `streamlit_cloud_github/app.py`: concise GFZ freshness and missing-index presentation.
- `streamlit_cloud_github/tests/test_serene_indices.py`: parser, request, cache, partial-failure, and historical-range unit tests.
- `streamlit_cloud_github/tests/test_api_only_data_loader.py`: manual-history and Follow Latest integration tests.
- `streamlit_cloud_github/README.md`: English source/range/failure documentation.
- `streamlit_cloud_github/部署说明.md`: Chinese deployment and source documentation.

### Task 1: Parse One GFZ JSON Index

**Files:**
- Modify: `streamlit_cloud_github/serene_client.py`
- Test: `streamlit_cloud_github/tests/test_serene_indices.py`

**Interfaces:**
- Consumes: GFZ payload `dict` containing `datetime`, the requested index array (`Kp` or `ap`), and `status`.
- Produces: `SereneClient.parse_gfz_json_index(payload: object, index: str) -> pd.DataFrame` in the existing columns `time`, `variable`, `value`, `data_status`, and `source` (plus the existing global-index fields `lat`, `lon`, `alt`, and `model`).

- [ ] **Step 1: Write failing parser tests**

Add tests using payloads such as:

```python
payload = {
    "datetime": ["2026-07-01T00:00:00Z", "2026-07-01T03:00:00Z"],
    "Kp": [3.0, 4.0],
    "status": ["def", "pre"],
}
frame = SereneClient.parse_gfz_json_index(payload, "Kp")
self.assertEqual(frame["status"].tolist(), ["definitive", "preliminary"])
self.assertEqual(frame["source"].unique().tolist(), ["GFZ Kp/ap JSON service"])
```

Also assert that mismatched arrays, an unsupported index, `NaN`, infinity, and sentinel values produce an empty frame instead of false evidence.

- [ ] **Step 2: Run the parser tests and confirm RED**

Run:

```bash
cd streamlit_cloud_github
../.venv/bin/python -m unittest tests.test_serene_indices.GfzJsonIndicesTest -v
```

Expected: `AttributeError` because `parse_gfz_json_index` does not exist.

- [ ] **Step 3: Implement the minimal parser**

Implement the exact signature:

```python
@staticmethod
def parse_gfz_json_index(payload: object, index: str) -> pd.DataFrame:
    ...
```

Accept only `Kp` and `ap`, require equal array lengths, parse UTC timestamps with `pd.to_datetime(..., utc=True)`, coerce numeric values, reject non-finite/sentinel rows, map `pre`/`def`, and sort by `time_utc`. Preserve each valid timestamp exactly; time-window filtering remains the fetcher's responsibility.

- [ ] **Step 4: Run parser tests and the existing index tests**

Run:

```bash
cd streamlit_cloud_github
../.venv/bin/python -m unittest tests.test_serene_indices -v
```

Expected: all tests pass, including legacy CSV compatibility tests.

- [ ] **Step 5: Commit the parser**

```bash
git add streamlit_cloud_github/serene_client.py streamlit_cloud_github/tests/test_serene_indices.py
git commit -m "feat: parse GFZ historical index JSON"
```

### Task 2: Query and Cache Historical Kp/ap Independently

**Files:**
- Modify: `streamlit_cloud_github/serene_client.py`
- Test: `streamlit_cloud_github/tests/test_serene_indices.py`

**Interfaces:**
- Consumes: `fetch_kp_ap_indices(start_time: str | None, end_time: str | None)` and the parser from Task 1.
- Produces: `(ok: bool, message: str, frame: pd.DataFrame)` plus DataFrame attrs `kp_ap_latest_time`, `kp_ap_missing_indices`, and `kp_ap_source`.

- [ ] **Step 1: Write failing request and cache tests**

Create a fake response/session that records request URL, params, and headers. Assert:

```python
self.assertEqual(call["url"], "https://kp.gfz.de/app/json/")
self.assertEqual(call["params"], {
    "start": "2026-06-27T00:00:00+00:00",
    "end": "2026-07-01T00:00:00+00:00",
    "index": "Kp",
})
self.assertNotIn("Authorization", call["headers"])
```

Assert two calls for a cold range (`Kp`, `ap`), no additional calls for the same range, and new calls for a different range. Assert the cache key contains `(index, normalized_start, normalized_end)` so Kp and ap or two dates cannot collide.

- [ ] **Step 2: Write failing partial-failure tests**

Test these contracts:

```python
# Kp succeeds and ap fails
self.assertTrue(ok)
self.assertEqual(frame["index"].unique().tolist(), ["Kp"])
self.assertEqual(frame.attrs["kp_ap_missing_indices"], ["ap"])

# Kp fails, even if ap would succeed
self.assertFalse(ok)
self.assertTrue(frame.empty)
```

Also assert missing or invalid `start_time`/`end_time` returns a controlled error and makes no request.

- [ ] **Step 3: Run the focused tests and confirm RED**

Run:

```bash
cd streamlit_cloud_github
../.venv/bin/python -m unittest tests.test_serene_indices.SereneIndicesTest -v
```

Expected: failures show the current implementation still requests the fixed `Kp_ap_nowcast.txt` resource and has one global text cache.

- [ ] **Step 4: Implement independent JSON fetching and cache isolation**

Replace the active fixed-nowcast path with:

```python
_gfz_index_cache: dict[
    tuple[str, str, str], tuple[float, object]
] = {}
```

Normalize start/end to UTC ISO strings, validate `start <= end`, then request `Kp` and `ap` separately from `/app/json/`. Pass empty/public headers, parse JSON safely, and call `parse_gfz_json_index`. Filter values to the inclusive requested range. Set `ok=True` only when Kp loaded; ap is optional. Join available rows, record missing indices, latest valid Kp/ap time at or before the analysis end, and retain the one-hour TTL.

- [ ] **Step 5: Run index tests and verify GREEN**

Run:

```bash
cd streamlit_cloud_github
../.venv/bin/python -m unittest tests.test_serene_indices -v
```

Expected: all parser/request/cache/failure tests pass and no request contains the SERENE token.

- [ ] **Step 6: Commit the historical request path**

```bash
git add streamlit_cloud_github/serene_client.py streamlit_cloud_github/tests/test_serene_indices.py
git commit -m "fix: query historical Kp ap from GFZ"
```

### Task 3: Align GFZ Windows to SERENE Analysis Time

**Files:**
- Modify: `streamlit_cloud_github/data_loader.py`
- Modify: `streamlit_cloud_github/app.py`
- Test: `streamlit_cloud_github/tests/test_api_only_data_loader.py`

**Interfaces:**
- Consumes: Task 2's `fetch_kp_ap_indices` result and DataFrame attrs.
- Produces: loader metadata `kp_ap_source`, `kp_ap_latest_time`, `kp_ap_data_status`, and `kp_ap_missing_indices`; UI caption reports partial ap failure without invalidating Kp.

- [ ] **Step 1: Write a failing July 2026 alignment test**

Use a fake client that captures call arguments. Load manual analysis `2026-07-01T05:55:00Z` and assert:

```python
self.assertEqual(captured["end_time"], "2026-07-01T05:55:00+00:00")
self.assertEqual(captured["start_time"], "2026-06-27T05:55:00+00:00")
```

Return 32 complete Kp slots and verify Auroral Absorption and PSD are evaluated rather than made unavailable by the former 30-day limitation.

- [ ] **Step 2: Write a failing Follow Latest alignment test**

Mock the latest HDF5 state time as `2026-08-12T09:00:00Z`, deliberately different from the computer clock, and assert the GFZ end is exactly that HDF5 time and the start is exactly 96 hours earlier. Also assert forecast `file_time` remains the same HDF5 analysis time.

- [ ] **Step 3: Write failing metadata and regression tests**

Assert `kp_ap_missing_indices == ["ap"]` reaches `LoadStatus.metadata`, the caption identifies ap as unavailable, and Kp-backed risks still use Kp. Preserve assertions that AIDA product kinds/source labels are unchanged and that GFZ indices are not rendered as regional map cells.

- [ ] **Step 4: Run loader tests and confirm RED**

Run:

```bash
cd streamlit_cloud_github
../.venv/bin/python -m unittest tests.test_api_only_data_loader -v
```

Expected: at least the new partial-metadata assertion fails before propagation is implemented.

- [ ] **Step 5: Implement exact alignment and metadata propagation**

Keep the existing ordering: determine authoritative AIDA `analysis`, then calculate `analysis - pd.Timedelta(hours=96)`, then fetch GFZ. Copy `kp_ap_missing_indices` into loader metadata and make `_kp_ap_source_freshness_caption` state the missing index without claiming the Kp source failed. Do not change the 32-slot Kp completeness gate.

- [ ] **Step 6: Run loader and risk regression tests**

Run:

```bash
cd streamlit_cloud_github
../.venv/bin/python -m unittest tests.test_api_only_data_loader tests.test_icao_risk -v
```

Expected: historical, latest, partial-ap, completeness, and risk tests all pass.

- [ ] **Step 7: Commit SERENE time alignment**

```bash
git add streamlit_cloud_github/data_loader.py streamlit_cloud_github/app.py streamlit_cloud_github/tests/test_api_only_data_loader.py
git commit -m "feat: align GFZ indices to SERENE cycles"
```

### Task 4: Documentation and End-to-End Verification

**Files:**
- Modify: `streamlit_cloud_github/README.md`
- Modify: `streamlit_cloud_github/部署说明.md`

**Interfaces:**
- Consumes: completed behavior from Tasks 1-3.
- Produces: source-traceable user documentation and verified August repository state.

- [ ] **Step 1: Update English and Chinese documentation**

Replace the 30-day-nowcast description with: public GFZ JSON, no extra API token, queryable for every SERENE-supported time from `2024-09-28`, 96-hour per-analysis windows, SERENE-HDF5 latest alignment, and independent ap failure. State explicitly that SERENE remains the AIDA/forecast source and only Kp/ap come from GFZ.

- [ ] **Step 2: Run the complete automated suite**

Run:

```bash
cd streamlit_cloud_github
../.venv/bin/python -m unittest discover -s tests -v
```

Expected: all tests pass with zero failures and zero errors.

- [ ] **Step 3: Run live historical acceptance**

Using the local `.env` token without printing it, load `2026-07-01T05:55:00Z`. Verify Kp/ap contain the preceding 96-hour GFZ window, the Kp completeness gate passes, and AIDA analysis remains a SERENE product.

- [ ] **Step 4: Run live Follow Latest acceptance**

Load Follow Latest. Verify the GFZ query end equals the downloaded SERENE HDF5 analysis time, Kp/ap are not future-dated, and available +30/+90 AIDA forecasts remain sourced from SERENE.

- [ ] **Step 5: Check repository safety and commit docs**

Run:

```bash
git diff --check
git status --short
git remote -v
git grep -n "SERENE_TOKEN\|Bearer " -- ':!streamlit_cloud_github/.env.example'
```

Expected: no whitespace errors; `.superpowers/` remains untracked; no token is tracked; the legacy push URL remains disabled.

```bash
git add streamlit_cloud_github/README.md streamlit_cloud_github/部署说明.md
git commit -m "docs: document historical GFZ Kp ap coverage"
```

- [ ] **Step 6: Push only the August repository**

```bash
git push origin main
```

Expected: August `origin/main` advances; no push is attempted to `legacy-source`.
