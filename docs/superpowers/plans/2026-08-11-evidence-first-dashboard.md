# Evidence-First Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved evidence-first Streamlit dashboard, prevent missing HF evidence from producing an unqualified overall OK, and publish the verified result only to the August repository.

**Architecture:** Add pure evidence and aggregation helpers to `icao_risk.py`, then make `app.py` render all top-level cards and provenance from those shared results. Keep the existing scientific loading pipeline intact, reduce the full HF interface to a compact standalone-study entry on the main page, and protect the changes with unit and Streamlit smoke tests.

**Tech Stack:** Python 3.11, pandas, Streamlit, Plotly, unittest, Git/GitHub.

## Global Constraints

- Modify only `/Users/a123/Desktop/August-project-version`; do not modify or push the legacy repository.
- Preserve `OK`, `MODERATE`, `SEVERE`, and `UNAVAILABLE` as component-risk categories.
- GNSS `OK` plus HF COM `UNAVAILABLE` must render overall `PARTIAL DATA`.
- Severity and data completeness are separate results.
- Preserve explicit official-forecast, dashboard-estimate, and unavailable provenance.
- Keep detailed HF/Trace work as a standalone study; the main dashboard shows only a compact summary entry.
- Never claim ICAO certification or operational validation.
- No production-code change is made before its failing test is observed.

---

### Task 1: Evidence aggregation contract

**Files:**
- Modify: `streamlit_cloud_github/icao_risk.py`
- Modify: `streamlit_cloud_github/tests/test_icao_risk.py`

**Interfaces:**
- Consumes: a summary `pandas.DataFrame` containing `Domain` and `Status`.
- Produces: `build_overall_risk_cards(summary) -> dict[str, str]` with four keys and `build_evidence_completeness(summary) -> dict[str, object]` with `available`, `required`, `percent`, `status`, and `missing`.

- [ ] **Step 1: Write failing aggregation tests**

```python
def test_partial_inputs_do_not_produce_unqualified_overall_ok(self):
    summary = pd.DataFrame([
        {"Domain": "GNSS", "Indicator": "Vertical TEC", "Status": "OK"},
        {"Domain": "HF COM", "Indicator": "Post-Storm Depression", "Status": "UNAVAILABLE"},
        {"Domain": "HF COM", "Indicator": "Auroral Absorption", "Status": "UNAVAILABLE"},
    ])
    cards = build_overall_risk_cards(summary)
    self.assertEqual(cards["Overall Risk"], "PARTIAL DATA")
    self.assertEqual(cards["Data Completeness"], "PARTIAL")

def test_severe_risk_is_preserved_when_other_evidence_is_missing(self):
    summary = pd.DataFrame([
        {"Domain": "GNSS", "Indicator": "Vertical TEC", "Status": "SEVERE"},
        {"Domain": "HF COM", "Indicator": "Post-Storm Depression", "Status": "UNAVAILABLE"},
    ])
    self.assertEqual(build_overall_risk_cards(summary)["Overall Risk"], "SEVERE + PARTIAL DATA")
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m unittest streamlit_cloud_github.tests.test_icao_risk.IcaoRiskTest.test_partial_inputs_do_not_produce_unqualified_overall_ok streamlit_cloud_github.tests.test_icao_risk.IcaoRiskTest.test_severe_risk_is_preserved_when_other_evidence_is_missing -v`

Expected: FAIL because the current helper ignores unavailable component evidence and has no fourth card.

- [ ] **Step 3: Implement minimal pure aggregation helpers**

```python
def build_evidence_completeness(summary):
    frame = _as_frame(summary)
    required_rows = frame[frame["Indicator"].isin(
        ["Vertical TEC", "Post-Storm Depression", "Auroral Absorption"]
    )]
    available = int(required_rows["Status"].isin({"OK", "MODERATE", "SEVERE"}).sum())
    required = len(required_rows)
    percent = round(available / required * 100) if required else 0
    status = "COMPLETE" if required and available == required else (
        "PARTIAL" if available else "UNAVAILABLE"
    )
    missing = required_rows.loc[
        ~required_rows["Status"].isin({"OK", "MODERATE", "SEVERE"}), "Indicator"
    ].astype(str).tolist()
    return {"available": available, "required": required, "percent": percent,
            "status": status, "missing": missing}
```

Update overall aggregation so available severity is retained, but any unavailable required domain adds `PARTIAL DATA`; add the fourth `Data Completeness` card.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run: `python -m unittest streamlit_cloud_github.tests.test_icao_risk -v`

Expected: all `IcaoRiskTest` tests pass.

- [ ] **Step 5: Commit the independently testable aggregation change**

```bash
git add streamlit_cloud_github/icao_risk.py streamlit_cloud_github/tests/test_icao_risk.py
git commit -m "fix: expose partial dashboard evidence"
```

### Task 2: Provenance metadata and API state

**Files:**
- Modify: `streamlit_cloud_github/app_utils.py`
- Modify: `streamlit_cloud_github/app.py`
- Modify: `streamlit_cloud_github/tests/test_icao_app_helpers.py`

**Interfaces:**
- Consumes: `LoadStatus`, requested time, actual output time, refresh time, current UTC.
- Produces: `build_provenance_metadata(requested_time, actual_time, retrieved_time, now, official_forecasts) -> list[dict[str, str]]` and `loaded_api_state(status, explicit_connected, explicit_message) -> tuple[str, str]`.

- [ ] **Step 1: Write failing tests for readable timestamps and successful-load API status**

```python
def test_successful_live_load_is_not_described_as_api_not_tested(self):
    status = LoadStatus(source="api", ok=True, message="Live AIDA loaded")
    level, text = loaded_api_state(status, None, "Not tested yet.")
    self.assertEqual(level, "success")
    self.assertIn("live load succeeded", text.lower())

def test_provenance_metadata_exposes_full_utc_values(self):
    rows = build_provenance_metadata(
        "2026-08-11T17:35:00Z", pd.Timestamp("2026-08-11T17:35:00Z"),
        pd.Timestamp("2026-08-11T17:36:00Z"), pd.Timestamp("2026-08-11T18:00:00Z"), 3,
    )
    self.assertEqual(rows[0]["value"], "2026-08-11 17:35 UTC")
    self.assertEqual(rows[-1]["value"], "3 official")
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `python -m unittest streamlit_cloud_github.tests.test_icao_app_helpers -v`

Expected: FAIL because the pure provenance and API-state helpers do not exist.

- [ ] **Step 3: Implement helpers and render a full-width provenance strip**

Implement the pure functions in `app_utils.py`; use them in `_render_connection_panel`. Replace narrow timestamp metrics with a table/HTML strip that displays requested, actual, retrieved/last-successful, data age, and official forecast count without ellipsis. Derive a successful API badge from a successful live load when the separate connection-test button was not clicked.

- [ ] **Step 4: Run helper and Streamlit smoke tests**

Run: `python -m unittest streamlit_cloud_github.tests.test_icao_app_helpers -v`

Expected: all helper tests pass and `AppTest` reports no exception.

- [ ] **Step 5: Commit provenance behaviour**

```bash
git add streamlit_cloud_github/app_utils.py streamlit_cloud_github/app.py streamlit_cloud_github/tests/test_icao_app_helpers.py
git commit -m "feat: show traceable dashboard provenance"
```

### Task 3: Evidence-first first screen and standalone HF entry

**Files:**
- Modify: `streamlit_cloud_github/app.py`
- Modify: `streamlit_cloud_github/tests/test_icao_app_helpers.py`

**Interfaces:**
- Consumes: the four-card dictionary and completeness result from Task 1.
- Produces: first-screen header, four aligned evidence cards, compact HF study entry, and reordered primary map/table content.

- [ ] **Step 1: Write failing Streamlit behaviour test**

```python
def test_loaded_cached_trial_renders_evidence_first_sections(self):
    app = AppTest.from_file(app_path, default_timeout=30).run()
    load = next(button for button in app.sidebar.button
                if button.label == "Load / Refresh data")
    app = load.click().run(timeout=30)
    visible = "\n".join(item.value for item in app.markdown)
    self.assertIn("Data Completeness", visible)
    self.assertIn("Standalone HF Communication Engineering Study", visible)
    self.assertFalse(app.exception)
```

The test must drive the real app widgets; it must not assert source-code strings.

- [ ] **Step 2: Run the focused UI test and confirm RED**

Run: `python -m unittest streamlit_cloud_github.tests.test_icao_app_helpers.IcaoAppHelpersTest.test_loaded_cached_trial_renders_evidence_first_sections -v`

Expected: FAIL because the approved sections are not rendered.

- [ ] **Step 3: Implement the approved first-screen hierarchy**

Update CSS for `PARTIAL DATA` and completeness states. Render the professional title and research-prototype badge, the four cards, evidence detail (`available / required`, percentage and missing indicators), categorical map, and ICAO table before secondary content. Each card includes a concise evidence reason.

Replace the direct main-page call to `render_hf_propagation_case_study(df)` with a compact `Standalone HF Communication Engineering Study` card. Put the existing detailed renderer inside a collapsed expander or a clearly separated study area so it is not presented as part of the live risk pipeline. Do not hard-code quantitative coverage values unless they are calculated from the current study data.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run: `python -m unittest streamlit_cloud_github.tests.test_icao_app_helpers -v`

Expected: all helper and UI tests pass.

- [ ] **Step 5: Commit the UI change**

```bash
git add streamlit_cloud_github/app.py streamlit_cloud_github/tests/test_icao_app_helpers.py
git commit -m "feat: add evidence-first dashboard layout"
```

### Task 4: Documentation, regression, and publication

**Files:**
- Modify: `README.md`
- Modify: `streamlit_cloud_github/README.md`
- Modify: `docs/engineering_review.md`

**Interfaces:**
- Consumes: verified behaviour from Tasks 1–3.
- Produces: deployment-facing documentation with honest scientific and operational limits.

- [ ] **Step 1: Update documentation from verified behaviour**

Document the new `PARTIAL DATA` rule, separate completeness result, timestamp/provenance strip, forecast badges, compact HF study boundary, and the distinction between software verification and operational validation.

- [ ] **Step 2: Run the complete automated suite**

Run: `cd streamlit_cloud_github && python -m unittest discover -s tests -v`

Expected: zero failures and zero errors.

- [ ] **Step 3: Run syntax, secret, and diff checks**

```bash
python -m compileall -q streamlit_cloud_github
git diff --check
git grep -nE 'SERENE_API_TOKEN\s*=\s*["'"'][^"'"']+' -- ':!*.md'
```

Expected: compile and diff checks exit 0; secret scan returns no credential assignment.

- [ ] **Step 4: Run a local Streamlit browser smoke check**

Start the app using the configured workspace Python, open the local page, load one cached trial, and verify the four cards, full timestamps, map/table order, compact HF study entry, and no visible exceptions at desktop width.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md streamlit_cloud_github/README.md docs/engineering_review.md docs/superpowers/plans/2026-08-11-evidence-first-dashboard.md
git commit -m "docs: explain evidence-first dashboard"
```

- [ ] **Step 6: Verify repository scope and push August main**

```bash
git status -sb
git remote -v
git ls-remote legacy-source refs/heads/main
git push origin main
```

Expected: only `origin` receives the new commits; `legacy-source` remains unchanged and push-disabled.
