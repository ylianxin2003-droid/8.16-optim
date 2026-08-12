# SERENE Published Forecast Horizons Design

Date: 2026-08-12

## Objective

Align the dashboard with the forecast products that the authenticated SERENE
AIDA API currently publishes. The primary risk presentation will show the
successfully retrieved 30-minute and 90-minute horizons. The 3-hour and 6-hour
horizons will be removed from operational-looking results, while their upstream
unavailability remains visible in the data-status and forecast-audit evidence.

This change is limited to the August project repository. The earlier
`primay-test-frist-version` repository must remain unchanged.

## Evidence and rationale

Authenticated checks on 2026-08-12 used the latest analysis cycle returned by
SERENE rather than a guessed wall-clock time:

| Product | Latest analysis cycle (UTC) | +30 min | +90 min | +3 h | +6 h |
|---|---:|---:|---:|---:|---:|
| Ultra | 10:35 | HTTP 200 HDF5 | HTTP 200 HDF5 | HTTP 404 | HTTP 404 |
| Rapid | 09:05 | HTTP 200 HDF5 | HTTP 200 HDF5 | HTTP 404 | HTTP 404 |

The supervisor's historical example also succeeded through the official
`aida==0.1.3` interface:

```python
Model.fromAPI(
    time=np.datetime64("2025-01-01T13:55:00"),
    model="AIDA",
    latency="rapid",
    forecast=90,
)
```

The loaded model valid time was 15:25 UTC, confirming that `forecast=90`
represents a 90-minute lead from the supplied analysis cycle.

The dashboard must not present an unavailable official file as either a safe
forecast or a software failure. Showing only verified forecast horizons in the
main decision surface produces a clearer interface, while retaining the audit
evidence prevents selective or misleading reporting.

## User-facing design

### Primary results

The main risk summary, forecast charts, map horizon controls and research
messages will use these horizons:

- +30 min
- +90 min

The +3 h and +6 h result columns, chart series, map choices and message fields
will be removed from the primary decision surface. No placeholder category,
zero, persistence value or assumed `OK` state will replace an absent official
forecast.

### Data-status evidence

The SERENE API and data-status area will retain a compact availability entry:

> Official SERENE forecast availability: +30 min and +90 min retrieved; +3 h
> and +6 h not currently published for this analysis cycle.

Wording must be derived from request results. If a later cycle has a different
availability pattern, the status must report that pattern rather than repeating
a hard-coded claim.

The forecast request audit will retain one row per attempted horizon, including
request cycle, lead period, HTTP-derived availability state, valid time when
available, and source. Unavailable horizons belong in this audit surface only,
not in the risk result table.

### Provenance

Every displayed forecast value will retain a source label. Official HDF5 data
must be labelled `SERENE official forecast`. Any existing dashboard-generated
trend or persistence output must remain explicitly labelled as generated and
must not be silently substituted into an official-only result.

For the default presentation, only successfully retrieved official +30-minute
and +90-minute products will be displayed. Generated fallbacks may remain
available as research diagnostics, but they must not make an absent official
3-hour or 6-hour product appear operationally available.

## Data flow

1. Obtain the selected or latest published SERENE analysis cycle.
2. Request official AIDA forecasts for 30 and 90 minutes for the primary result.
3. Record the outcome of each request in forecast-audit metadata.
4. Calculate local grid values and risk categories only for successfully
   decoded HDF5 forecast states.
5. Build main tables, figures, maps and messages from the available primary
   horizons.
6. Present unavailable upstream horizons in the status/audit area without
   assigning a risk category.

The implementation must use the actual analysis cycle associated with the
SERENE state. An arbitrary current clock time must not be used as a forecast
cycle because the forecast API requires an exact published `file_time`.

## Components affected

- `data_loader.py`: primary forecast periods and request metadata.
- `icao_risk.py`: +30-minute summary fields and removal of +3 h/+6 h primary
  output fields.
- `app.py`: main table, status copy, forecast audit, charts and map controls.
- `icao_message.py`: research-message forecast horizons.
- Forecast and dashboard tests: expected horizons, availability behaviour,
  provenance and missing-data safety.
- README/deployment documentation: supported and currently displayed horizons.

No changes are required in the old repository.

## Error handling

- HTTP 200 with valid HDF5: decode and display the forecast with its official
  source and valid time.
- HTTP 404: record `not published for this analysis cycle`; do not classify it
  as `OK`, `MODERATE` or `SEVERE`.
- HTTP 401/403: report authentication failure separately from forecast
  availability; do not claim that the upstream product is absent.
- Non-HDF5 or malformed HDF5: record a decode/contract failure and suppress the
  affected forecast value.
- Network timeout: record a temporary retrieval failure; do not convert it into
  an upstream `not published` conclusion.

## Testing and acceptance criteria

The change is acceptable when all of the following are true:

1. The application requests and correctly decodes official 30-minute and
   90-minute AIDA forecasts.
2. The main result table, charts, map choices and research message show +30 min
   and +90 min only.
3. A 404 for +3 h or +6 h cannot create a risk category and does not appear as
   a primary result column.
4. The status/audit area distinguishes not-published, authentication, network
   and decode failures.
5. Forecast provenance is visible for every displayed forecast.
6. The current analysis value and historical rolling Max-3h value retain their
   existing meanings; Max-3h is not presented as a future forecast.
7. Unit tests cover successful official forecasts, partial availability and
   missing official forecasts.
8. The complete repository test suite passes.
9. No token, `.env` file or other secret is committed.
10. Only the August repository is committed and pushed.

## Report wording

The dissertation should describe the behaviour as adaptive availability
handling, not as removal of failed results:

> The dashboard validates each requested SERENE AIDA forecast against the
> authenticated API response. At the evaluation time, official 30-minute and
> 90-minute products were available, whereas 3-hour and 6-hour files were not
> published for the tested cycles. The primary decision surface therefore
> displays only verified forecast horizons, while the audit panel retains the
> unavailable requests and their provenance. Missing upstream data are never
> interpreted as a safe condition.

This is an evidence-bounded statement for the evaluated cycles, not a claim
that SERENE can never publish longer horizons.
