# HF City-to-City Scenarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add beginner-friendly named HF route scenarios while retaining reproducible advanced coordinates and honest scientific boundaries.

**Architecture:** Put the offline location catalogue and route resolution in a focused pure module, then connect it to the existing Streamlit HF study. The existing great-circle and MUF analysis engine remains unchanged except for dynamic route naming.

**Tech Stack:** Python 3.11, pandas, Streamlit, Plotly, unittest.

## Global Constraints

- Modify and push only the August repository.
- No external geocoding service or new dependency.
- Endpoints are assumed research locations, not verified stations or trajectories.
- Preserve Advanced coordinates mode.
- Use tests before production changes.

---

### Task 1: Offline location and scenario catalogue

**Files:**
- Create: `streamlit_cloud_github/hf_locations.py`
- Create: `streamlit_cloud_github/tests/test_hf_locations.py`

**Interfaces:**
- Produces: `HF_LOCATIONS`, `HF_ROUTE_SCENARIOS`, `location_names()`, and `resolve_route_scenario(name)`.

- [ ] Write tests proving unique valid locations, valid scenario references and Birmingham → New York default resolution.
- [ ] Run `python -m unittest streamlit_cloud_github.tests.test_hf_locations -v` and confirm missing-module RED.
- [ ] Implement the literal offline catalogue and pure resolution helpers.
- [ ] Run the focused test and confirm GREEN.
- [ ] Commit with `feat: add HF route location catalogue`.

### Task 2: Streamlit route-mode controls

**Files:**
- Modify: `streamlit_cloud_github/hf_coverage_ui.py`
- Modify: `streamlit_cloud_github/tests/test_hf_coverage_ui.py`

**Interfaces:**
- Consumes: Task 1 catalogue helpers.
- Produces: `Preset scenario`, `Custom city-to-city`, and `Advanced coordinates` controls that pass endpoint dictionaries to `build_hf_engineering_case`.

- [ ] Add an AppTest that selects custom city mode, selects Birmingham/New York and verifies resolved endpoint captions without exceptions.
- [ ] Run the new AppTest and confirm RED because route-mode controls do not exist.
- [ ] Replace the current transmitter/target preset controls with route-mode controls and an explicit assumed-endpoint disclaimer.
- [ ] Keep manual coordinates in Advanced coordinates mode.
- [ ] Run all HF UI and calculation tests and confirm GREEN.
- [ ] Commit with `feat: add city based HF route scenarios`.

### Task 3: Dynamic figures, documentation and publication

**Files:**
- Modify: `streamlit_cloud_github/hf_coverage.py`
- Modify: `streamlit_cloud_github/tests/test_hf_coverage.py`
- Modify: `README.md`
- Modify: `streamlit_cloud_github/README.md`

**Interfaces:**
- Consumes: endpoint names selected in Task 2.
- Produces: route traces and documentation that use the selected names without implying a fixed or operational route.

- [ ] Add a failing test that a custom route map trace uses the selected endpoint names and a generic assumed-route label.
- [ ] Implement dynamic trace naming without changing the propagation calculation.
- [ ] Update documentation with modes, catalogue scope and limitations.
- [ ] Run the full unittest suite, compileall, diff check and secret scan.
- [ ] Commit, verify the legacy SHA remains unchanged, and push August `main`.
