# Inline Standalone HF Study Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display the standalone HF communication engineering study directly in the dashboard body while preserving its internal explanation expanders and existing scientific behaviour.

**Architecture:** Keep `_render_main()` and the existing HF renderer boundary unchanged. Replace the outer disclosure wrapper inside `_render_standalone_hf_study()` with a direct renderer call, then protect the user-visible contract with a Streamlit application regression test. Documentation and verification are limited to this presentation change; logic findings are reported separately.

**Tech Stack:** Python 3, Streamlit, pandas, Plotly, `unittest`, Streamlit `AppTest`.

## Global Constraints

- Remove only the outer `Open standalone study details` expander.
- Retain `How to interpret this HF case study` and `Trace integration status` as internal expanders.
- Do not alter HF calculations, risk thresholds, data sources, availability decisions or research limitations.
- Keep all project changes in `/Users/a123/Desktop/August-project-version`.

---

### Task 1: Protect and implement direct study rendering

**Files:**
- Modify: `streamlit_cloud_github/tests/test_icao_app_helpers.py:249-308`
- Modify: `streamlit_cloud_github/app.py:917-933`

**Interfaces:**
- Consumes: `_render_standalone_hf_study(df: pandas.DataFrame) -> None` and `render_hf_propagation_case_study(df: pandas.DataFrame) -> None`.
- Produces: a loaded dashboard whose visible subheaders include `Engineering Impact: HF Communication Coverage`, whose expander labels exclude `Open standalone study details`, and whose internal explanation expander labels remain present.

- [ ] **Step 1: Add a failing user-visible regression assertion**

Extend `test_loaded_trial_renders_evidence_first_sections` after the second `app.run()`:

```python
subheadings = [item.value for item in app.subheader]
expander_labels = [item.label for item in app.expander]
self.assertIn("Engineering Impact: HF Communication Coverage", subheadings)
self.assertNotIn("Open standalone study details", expander_labels)
self.assertIn("How to interpret this HF case study", expander_labels)
self.assertIn("Trace integration status", expander_labels)
```

This test catches a reintroduced outer disclosure wrapper while also catching accidental removal of either intended internal disclosure panel.

- [ ] **Step 2: Run the focused test and verify the expected failure**

Run:

```bash
cd /Users/a123/Desktop/August-project-version/streamlit_cloud_github
../.venv/bin/python -m unittest tests.test_icao_app_helpers.IcaoAppHelperTests.test_loaded_trial_renders_evidence_first_sections -v
```

Expected: FAIL because `Engineering Impact: HF Communication Coverage` is not rendered while the outer expander is closed, or because `Open standalone study details` is still present.

- [ ] **Step 3: Make the minimal production change**

Replace the outer wrapper in `_render_standalone_hf_study()`:

```python
render_hf_propagation_case_study(df)
```

Do not change `hf_coverage_ui.py`.

- [ ] **Step 4: Run the focused test and verify it passes**

Run the same command as Step 2.

Expected: one test passes with no Streamlit exception.

- [ ] **Step 5: Commit the rendering change and regression test**

```bash
git add streamlit_cloud_github/app.py streamlit_cloud_github/tests/test_icao_app_helpers.py
git commit -m "feat: show standalone HF study inline"
```

---

### Task 2: Align user documentation

**Files:**
- Modify: `streamlit_cloud_github/README.md:170-188`

**Interfaces:**
- Consumes: the inline rendering behaviour delivered by Task 1.
- Produces: documentation that accurately describes the study as an inline dashboard section and retains all proxy-model limitations.

- [ ] **Step 1: Replace the stale collapsed-entry wording**

Change the first paragraph to:

```markdown
The dashboard presents an inline standalone engineering HF propagation case
study inspired by the [Trace HF ray-tracing toolkit](https://pytrace.readthedocs.io/en/latest/).
```

Keep the statements that full Trace ray tracing is not integrated, that the current method is a MUF proxy, and that missing reference data activates a clearly labelled assumed-PSD demonstration.

- [ ] **Step 2: Check documentation consistency**

Run:

```bash
rg -n "collapsed entry|inline standalone|Open standalone study details" streamlit_cloud_github/README.md streamlit_cloud_github/app.py
git diff --check
```

Expected: no `collapsed entry` or removed outer-label references remain in production documentation/code; `git diff --check` exits 0.

- [ ] **Step 3: Commit the documentation update**

```bash
git add streamlit_cloud_github/README.md
git commit -m "docs: describe inline HF study"
```

---

### Task 3: Verify logic and rendered behaviour

**Files:**
- Inspect: `streamlit_cloud_github/icao_risk.py`
- Inspect: `streamlit_cloud_github/data_loader.py`
- Inspect: `streamlit_cloud_github/hf_coverage.py`
- Inspect: `streamlit_cloud_github/hf_coverage_ui.py`
- Test: `streamlit_cloud_github/tests/`

**Interfaces:**
- Consumes: the complete Streamlit dashboard and existing test fixtures.
- Produces: fresh automated and visual evidence, plus a report that distinguishes confirmed behaviour from any remaining defect or external-data limitation.

- [ ] **Step 1: Run the complete test suite**

```bash
cd /Users/a123/Desktop/August-project-version/streamlit_cloud_github
../.venv/bin/python -m unittest discover -s tests -v
```

Expected: all discovered tests pass. Record the exact count and elapsed time.

- [ ] **Step 2: Audit key status and HF contracts**

Review tests and implementations for these literal outcomes:

- missing indicator input remains `UNAVAILABLE`, never implicit `OK`;
- PSD is `OK` below 30%, `MODERATE` from 30% to below 50%, and `SEVERE` from 50% when the Kp storm gate is active;
- inactive Kp storm gating returns PSD `OK`, while missing gate evidence returns `UNAVAILABLE`;
- official forecast and backtesting outcome provenance remain distinguishable;
- route computation uses the selected endpoints and frequency, and missing MUF input produces an explicit message rather than a route result.

Run the focused logic modules if the full-suite output does not make these contracts explicit:

```bash
../.venv/bin/python -m unittest tests.test_icao_risk tests.test_hf_coverage tests.test_hf_coverage_ui tests.test_historical_risk_windows -v
```

- [ ] **Step 3: Start the local dashboard**

```bash
cd /Users/a123/Desktop/August-project-version/streamlit_cloud_github
../.venv/bin/python -m streamlit run app.py --server.headless true --server.port 8502
```

Keep the process running only for the visual check.

- [ ] **Step 4: Inspect the page in the browser**

Verify the loaded dashboard or a controlled loaded-trial state shows:

- `Standalone HF Communication Engineering Study` in the main flow;
- `Engineering Impact: HF Communication Coverage` without clicking an outer expander;
- usable route controls and a rendered plot/map when MUF data is present;
- the two internal explanation expanders still available;
- no overlapping endpoint labels, clipped chart content or visible Streamlit exception.

If live credentials or upstream data prevent a loaded state, report that boundary and rely on the real Streamlit `AppTest` fixture for the loaded-state contract rather than fabricating API evidence.

- [ ] **Step 5: Inspect the final diff and repository state**

```bash
git status --short
git diff HEAD~2 --check
git log -3 --oneline
```

Expected: only the approved design, implementation, regression test and README changes are committed; the pre-existing `.superpowers/` untracked directory remains untouched.
