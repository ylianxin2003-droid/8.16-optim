# GFZ Kp/ap Data Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace only the dashboard Kp/ap input with the public GFZ nowcast file while preserving the complete SERENE AIDA and downstream risk pipeline.

**Architecture:** Keep `SereneClient.fetch_kp_ap_indices()` as the existing loader-facing interface, but replace its source-specific internals with a small GFZ text parser and public HTTPS request. Preserve the long-form DataFrame contract so `data_loader.py`, PSD gating, alerts, exports, and visualisations continue to consume Kp/ap without structural changes.

**Tech Stack:** Python 3.9, pandas, requests, unittest, Streamlit.

## Global Constraints

- Only Kp/ap may move to GFZ; all AIDA products remain on SERENE.
- GFZ requires no API token and no new Streamlit secret.
- Missing or incomplete Kp history remains `Unavailable`, never `OK`.
- Kp/ap remain planetary context and must not become regional map cells.
- The risk thresholds and +30/+90 minute AIDA forecast behaviour remain unchanged.
- Commit and push only to `August-project-version`; never modify or push the legacy repository.

---

### Task 1: Parse GFZ Kp/ap nowcast data

**Files:**
- Modify: `streamlit_cloud_github/serene_client.py`
- Test: `streamlit_cloud_github/tests/test_serene_indices.py`

**Interfaces:**
- Produces: `SereneClient.parse_gfz_kp_ap(text: str, start_time: str | None = None, end_time: str | None = None) -> pd.DataFrame`
- Produces internally: `SereneClient._parse_gfz_kp_ap_with_latest(...) -> tuple[pd.DataFrame, pd.Timestamp | None]`
- Preserves columns: `time`, `lat`, `lon`, `alt`, `variable`, `value`, `model`, `source`; adds `data_status`.

- [ ] **Step 1: Write failing parser tests**

Add focused tests using a real-format fixture:

```python
GFZ_TEXT = """# comment
2026 08 12 03.0 04.50 34557.12500 34557.18750  2.000    7 0
2026 08 12 06.0 07.50 34557.25000 34557.31250  1.667    6 1
2026 08 12 09.0 10.50 34557.37500 34557.43750 -1.000   -1 0
"""
```

Assert that comments are ignored, UTC interval-start timestamps are built,
Kp/ap rows are produced, `D=0/1` maps to `preliminary/definitive`, source/model
are GFZ-specific, filtering is inclusive, and `-1` sentinels are omitted.

- [ ] **Step 2: Run parser tests and verify RED**

Run:

```bash
.venv/bin/python -m unittest \
  streamlit_cloud_github.tests.test_serene_indices.GfzIndicesTest -v
```

Expected: failure because `parse_gfz_kp_ap` does not exist.

- [ ] **Step 3: Implement the minimal GFZ parser**

Add the documented column list and parse comment-prefixed whitespace data with
`pd.read_csv(StringIO(text), sep=r"\s+", comment="#", names=...)`. Build UTC
timestamps from date plus start hour, coerce numeric values, remove sentinels,
apply time filters, and emit the compatibility schema.

- [ ] **Step 4: Run parser tests and verify GREEN**

Run the Task 1 command and expect all `GfzIndicesTest` parser cases to pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add streamlit_cloud_github/serene_client.py \
  streamlit_cloud_github/tests/test_serene_indices.py
git commit -m "feat: parse official GFZ Kp ap nowcast"
```

---

### Task 2: Download and cache the public GFZ source

**Files:**
- Modify: `streamlit_cloud_github/serene_client.py`
- Test: `streamlit_cloud_github/tests/test_serene_indices.py`

**Interfaces:**
- Consumes: `_parse_gfz_kp_ap_with_latest(...)` from Task 1.
- Preserves: `fetch_kp_ap_indices(start_time=None, end_time=None) -> tuple[bool, str, pd.DataFrame]`.
- Produces metadata attributes: `kp_ap_source_latest_time`, `kp_ap_data_statuses`.

- [ ] **Step 1: Write failing download tests**

Assert that `fetch_kp_ap_indices()` requests the exact public GFZ HTTPS URL,
sends no `Authorization` header, caches the response across client instances,
records the unfiltered latest timestamp and loaded statuses, and returns a
GFZ-specific message when the selected range is empty or the text is malformed.

- [ ] **Step 2: Run download tests and verify RED**

Run:

```bash
.venv/bin/python -m unittest \
  streamlit_cloud_github.tests.test_serene_indices -v
```

Expected: failures showing the current SERENE URL/schema/source text.

- [ ] **Step 3: Replace only the Kp/ap request internals**

Introduce constants for the GFZ base URL/path. Reuse the existing bounded
in-memory cache and public `_request_from_base()` path. Set
`kp_ap_source_latest_time` and `kp_ap_data_statuses` on both fresh and cached
loads. Keep request or parsing failures non-fatal.

- [ ] **Step 4: Run download tests and verify GREEN**

Run the Task 2 command and expect all index tests to pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add streamlit_cloud_github/serene_client.py \
  streamlit_cloud_github/tests/test_serene_indices.py
git commit -m "fix: load Kp ap directly from GFZ"
```

---

### Task 3: Preserve downstream behaviour and expose provenance

**Files:**
- Modify: `streamlit_cloud_github/data_loader.py`
- Modify: `streamlit_cloud_github/app.py`
- Test: `streamlit_cloud_github/tests/test_api_only_data_loader.py`
- Test: `streamlit_cloud_github/tests/test_icao_app_helpers.py`
- Test: `streamlit_cloud_github/tests/test_dashboard_settings.py`

**Interfaces:**
- Consumes: existing index DataFrame plus `kp_ap_data_statuses`.
- Adds metadata: `kp_ap_source="GFZ Helmholtz Centre for Geosciences"` and `kp_ap_data_statuses=[...]`.
- Preserves: `_kp_history_is_complete`, `kp_storm_eligible`, summary schema and map exclusions.

- [ ] **Step 1: Write failing provenance and regression tests**

Assert that loader metadata names GFZ, reports preliminary/definitive values,
retains complete-96-hour Kp gating, keeps AIDA product kinds unchanged, and the
status panel helper returns GFZ freshness/provenance wording. Retain the test
that regional maps reject Kp/ap.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
.venv/bin/python -m unittest \
  streamlit_cloud_github.tests.test_api_only_data_loader \
  streamlit_cloud_github.tests.test_icao_app_helpers \
  streamlit_cloud_github.tests.test_dashboard_settings -v
```

Expected: failures because current metadata and UI wording identify SERENE.

- [ ] **Step 3: Add GFZ metadata and UI wording**

Read the client status attributes into `LoadStatus.metadata`, change only
Kp/ap-specific labels/warnings/captions, and leave all product calculation and
risk classification functions unchanged.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 3 command and expect all focused tests to pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add streamlit_cloud_github/data_loader.py streamlit_cloud_github/app.py \
  streamlit_cloud_github/tests/test_api_only_data_loader.py \
  streamlit_cloud_github/tests/test_icao_app_helpers.py \
  streamlit_cloud_github/tests/test_dashboard_settings.py
git commit -m "feat: expose GFZ Kp ap provenance"
```

---

### Task 4: Update documentation and verify the complete system

**Files:**
- Modify: `streamlit_cloud_github/README.md`
- Modify: `streamlit_cloud_github/部署说明.md`
- Test: `streamlit_cloud_github/tests/test_dashboard_settings.py`

**Interfaces:**
- Documents the implemented boundary: SERENE for AIDA, GFZ only for Kp/ap.

- [ ] **Step 1: Write failing documentation assertions**

Require both documents to identify the GFZ public source, no-token behaviour,
preliminary/definitive distinction, and unchanged SERENE AIDA scope.

- [ ] **Step 2: Run documentation tests and verify RED**

```bash
.venv/bin/python -m unittest \
  streamlit_cloud_github.tests.test_dashboard_settings -v
```

Expected: failure because the documents still describe SERENE Kp/ap.

- [ ] **Step 3: Update English and Chinese documentation**

Remove stale SERENE Kp/ap-source statements and add the exact GFZ provenance,
licence/citation note, status meaning, and failure behaviour.

- [ ] **Step 4: Run the complete automated suite**

```bash
.venv/bin/python -m unittest discover -s streamlit_cloud_github/tests -q
```

Expected: all tests pass with zero failures.

- [ ] **Step 5: Run live acceptance checks**

Verify the GFZ endpoint without credentials, parse the latest timestamp and
preceding 96 hours, then use the existing local SERENE token only from the
untracked `.env` to confirm AIDA still loads analysis and +30/+90 products.
Never print or commit the token.

- [ ] **Step 6: Run repository safety checks**

```bash
git diff --check
git status --short
git remote -v
```

Confirm `.env`/secrets are untracked, `.superpowers/` is not staged, `origin`
is August, and legacy push remains disabled.

- [ ] **Step 7: Commit documentation**

```bash
git add streamlit_cloud_github/README.md \
  streamlit_cloud_github/部署说明.md \
  streamlit_cloud_github/tests/test_dashboard_settings.py
git commit -m "docs: explain direct GFZ geomagnetic indices"
```

- [ ] **Step 8: Push and verify August main**

```bash
git push origin main
test "$(git rev-parse HEAD)" = \
  "$(git ls-remote origin refs/heads/main | awk '{print $1}')"
```

Do not push any other remote.
