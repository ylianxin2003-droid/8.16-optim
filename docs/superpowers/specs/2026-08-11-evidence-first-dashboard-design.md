# Evidence-First Dissertation Dashboard Design

Date: 2026-08-11

## Purpose

Refine the August SERENE/AIDA Streamlit research prototype for a University of
Birmingham ECE MSc dissertation. The dashboard must look professionally
engineered while keeping every risk claim traceable to available data. It must
support a live demonstration without implying that the prototype is an
operationally validated aviation warning service.

This design extends the approved near-real-time behaviour in
`2026-08-10-near-real-time-dashboard-design.md`. It does not change the legacy
repository.

## Approved Direction

The selected direction is **A: Evidence-first**. The primary audience is the
dissertation assessor. The first screen prioritises:

1. current scientific status;
2. completeness and freshness of the evidence;
3. traceability from risk category to source and time; and
4. a compact link to the standalone HF engineering study.

Visual impact comes from clear hierarchy, consistent status language, maps and
quantitative evidence—not from control-room styling or unsupported operational
claims.

## Scope Boundary

### Main dashboard

- SERENE/AIDA analysis and official forecast products;
- requested, actual and retrieved UTC timestamps;
- GNSS, HF COM and overall risk status;
- evidence/data-completeness status;
- ICAO-style current, maximum and forecast table;
- risk maps, forecast provenance, generated research messages and limitations;
- historical validation summaries and future polygon-warning work where
  evidence exists.

### Standalone HF communication study

The full quiet-versus-storm maps, route analysis, frequency sweep, coverage
metrics and Trace detail remain a standalone quantitative engineering study.
The main page contains only a compact evidence card such as:

> HF Communication Engineering Study — standalone quiet/storm comparison;
> coverage 91% to 84%, loss 6 percentage points; research prototype.

Final values must come from the verified study output, not hard-coded display
copy. A link or expander leads to the detailed study. This preserves the
engineering contribution requested by the supervisor without presenting Trace
as an integrated dashboard warning product.

## First-Screen Information Architecture

### Header and provenance strip

- Product title: `SERENE AIDA Aviation Space Weather Monitor`.
- Badges: `LIVE AIDA` when applicable and `RESEARCH PROTOTYPE` always.
- Full-width metadata: requested time, actual AIDA time, retrieved time, data
  age and number of available official forecast horizons.
- Long timestamps must never be truncated inside small metric widgets.

### Four status cards

1. **GNSS Risk**
2. **HF COM Risk**
3. **Overall Risk**
4. **Data Completeness**

Each risk card shows category, concise reason, source time and source/product.
The fourth card removes the current empty-column layout and makes uncertainty a
first-class engineering result.

### Main evidence area

- Large risk map with indicator, unit, valid time and source visible together.
- Compact ICAO-style table for latest, rolling maximum and supported forecast
  horizons.
- Observation, official SERENE forecast and dashboard estimate use different
  line styles and explicit source badges.
- Kp/ap remains a global measure and is never drawn as regional cells.

### Supporting area

- Evidence-completeness panel lists required, available, stale and missing
  inputs.
- Compact HF study card links to the standalone quantitative work.
- Detailed diagnostics and API status remain available below the primary
  decision view rather than dominating it.

## Status Vocabulary and Visual Rules

Risk indicators use only:

- `OK` — green;
- `MODERATE` — amber;
- `SEVERE` — red;
- `UNAVAILABLE` — grey.

Evidence state uses:

- `COMPLETE`;
- `PARTIAL`;
- `STALE`;
- `UNAVAILABLE`.

The same colours and terms have the same meaning in cards, maps, tables,
messages and legends. Colour is reinforced with text and icons so meaning does
not depend on colour alone.

## Overall-Risk Aggregation

The overall category must not hide missing evidence:

| Available component results | Overall presentation |
|---|---|
| All required indicators are `OK` | `OK` |
| At least one `MODERATE`, none `SEVERE`, none missing | `MODERATE` |
| At least one `SEVERE`, none missing | `SEVERE` |
| Some `OK`, some unavailable | `PARTIAL DATA` |
| `MODERATE` or `SEVERE` plus unavailable inputs | Preserve worst risk and add `PARTIAL DATA` badge |
| All required indicators unavailable | `UNAVAILABLE` |

Therefore GNSS `OK` plus HF COM `UNAVAILABLE` cannot produce an unqualified
overall `OK`.

`Data Completeness` is calculated separately from risk severity. Its percentage
uses a documented set of required inputs for the selected mode and horizon; the
UI must expose the numerator and denominator rather than showing an unexplained
percentage.

## Scientific Traceability

For each TEC, PSD, Kp/ap or derived result, retain and expose:

- value and unit;
- risk category and boundary rule;
- input product and endpoint class;
- analysis and valid time;
- whether the value is observation, official forecast or dashboard estimate;
- missing, stale or degraded-data reason.

Existing ICAO-style research thresholds remain subject to the scientific-source
review. In particular, the implementation and dissertation must not describe a
MUF3000F2 proxy as the official ICAO foF2 PSD definition. Until the calculation
is scientifically aligned and validated, the UI must identify the parameter and
method actually used.

## Data and Interaction Flow

1. The user selects live/latest or historical mode and a time.
2. The application obtains the SERENE/AIDA analysis and supported official
   forecast products.
3. It records requested time, actual returned time and retrieval time.
4. Each indicator is classified independently from its required inputs.
5. Each result carries value, unit, source, time, rule and availability reason.
6. The application computes evidence completeness.
7. The application aggregates overall risk using the table above.
8. Cards, table, map and message render from the same result objects so they
   cannot silently disagree.

Changing indicator, map region or display tab should not repeat scientific API
downloads when the underlying analysis anchor and inputs are unchanged.

## Forecast Provenance

Every displayed horizon carries exactly one badge:

- `OFFICIAL SERENE FORECAST`;
- `DASHBOARD ESTIMATE`; or
- `UNAVAILABLE`.

Analysis and forecasts must not be joined by an ambiguous single line. Charts
show a visual boundary between historical/analysis data and future valid times.
The dashboard never extrapolates a missing official product without labelling
the result as an estimate and documenting the method.

## Failure and Degraded Modes

- API failure: `UNAVAILABLE — API request failed`, with a sanitised reason.
- Missing parameter: name the missing input, for example `Kp/ap unavailable`.
- Stale input: show `STALE`, source timestamp and calculated data age.
- Partial inputs: use the overall aggregation rules above.
- Missing forecast: show `UNAVAILABLE`; do not imply prediction.
- Retained previous result: label `LAST KNOWN DATA` and its timestamp.
- Observation succeeds but forecast fails: preserve the observation and isolate
  the forecast failure.
- Initial API status must reflect the successful scientific load; it must not
  simultaneously say `not tested` after live data has already been retrieved.

## Performance and API Discipline

Full ICAO-style mode may require 37 rolling/analysis states, three forecast
states and up to 30 baseline states. It remains manual-only. Cached result
objects should be reused across presentation changes. Verification records:

- API download count;
- first-load and cached-rerun duration;
- cache hits or avoided duplicate calls; and
- failures by product class.

No performance statement is made without a measured configuration and time.

## Validation Strategy

### Automated tests

- every overall-risk aggregation combination;
- evidence completeness numerator, denominator and state;
- TEC, PSD and Kp threshold boundaries;
- missing, stale and mixed-availability inputs;
- requested, actual, retrieved and forecast-valid timestamps;
- official forecast versus estimate provenance;
- observation survival after forecast failure;
- sanitised errors and absence of secrets;
- consistency between card, table and generated-message result objects.

### Live and visual checks

- today, yesterday, two days ago and at least 72 hours ago;
- +90 minute, +3 hour and +6 hour official forecast availability;
- `OK`, `MODERATE`, `SEVERE`, `UNAVAILABLE` and `PARTIAL DATA` displays;
- stale Kp/ap and missing-parameter scenarios;
- desktop and narrow/mobile layouts;
- full timestamps, units, legends and readable source badges;
- first-load and cached interaction performance.

### Dissertation evidence

The report distinguishes:

- software verification;
- scientific threshold/method validation;
- historical-event or case-study validation; and
- operational validation, which has not been performed.

Passing software tests demonstrates implementation correctness against the
specified rules; it does not certify aviation operational suitability.

## Acceptance Criteria

1. GNSS `OK` plus HF `UNAVAILABLE` is presented as `PARTIAL DATA`, not `OK`.
2. Four first-screen cards render without an empty column.
3. Requested, actual and retrieved UTC timestamps are fully readable.
4. Every risk or forecast states its source, time and availability/provenance.
5. Data completeness is separate from severity and is reproducible from a
   visible numerator and denominator.
6. Observation, official forecast and estimate are visually distinguishable.
7. Missing/stale inputs cannot silently generate a supported risk category.
8. The main dashboard contains only a compact HF study entry; detailed HF/Trace
   work remains a standalone study.
9. No page claims ICAO certification or operational validation.
10. Focused tests and the complete regression suite pass before deployment.
11. The old repository remains unchanged; all implementation occurs only in the
    August repository.
