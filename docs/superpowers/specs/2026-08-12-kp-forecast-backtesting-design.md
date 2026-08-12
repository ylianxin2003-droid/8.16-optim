# Kp +30/+90 Forecast and Backtesting Design

## Objective

Populate the Auroral Absorption `+30 min` and `+90 min` assessments for every
selectable SERENE AIDA analysis time from `2024-09-28T00:00:00Z` through the
latest SERENE HDF5 cycle, without presenting observations as forecasts or
allowing future information to leak into the preceding-96-hour storm gate.

This design extends the historical GFZ JSON integration in
`2026-08-12-gfz-historical-json-design.md`. It changes only the Kp horizon
evidence used by the Auroral Absorption row. SERENE AIDA, TEC, MUF3000F2, PSD,
risk thresholds, maps, route logic, and forecast policy remain unchanged.

## Verified Range Boundary

The selectable analysis range begins at:

`2024-09-28T00:00:00Z`

Live authenticated checks established that:

- AIDA Rapid at `2024-09-27T23:55:00Z` is unavailable;
- AIDA Rapid at `2024-09-28T00:00:00Z` is downloadable as HDF5;
- GFZ provides definitive Kp at and after the AIDA archive boundary.

The upper boundary is the authoritative analysis time read from the latest
SERENE HDF5 state, not the user's computer clock.

The dashboard shall not offer an AIDA analysis time before this boundary.
Internally, the preceding-96-hour storm gate may fetch Kp from before the
boundary, beginning as early as `2024-09-24T00:00:00Z`. Those earlier Kp rows
are context for the first supported AIDA cycle, not separately selectable
dashboard analyses.

## Source Products

### Observed Kp

Historical and near-real-time Kp observations come from the public GFZ JSON
service:

`https://kp.gfz.de/app/json/`

The existing independent, range-keyed Kp/ap acquisition remains the source for
Latest, Max-3h, and the preceding-96-hour storm gate.

### Official Kp Forecast

Future Kp comes from the GFZ PAGER/SWIFT ensemble forecast JSON:

`https://spaceweather.gfz.de/fileadmin/Kp-Forecast/CSV/kp_product_file_FORECAST_PAGER_SWIFT_LAST.json`

GFZ documents that this product:

- runs hourly;
- forecasts up to 72 hours ahead;
- represents the traditional three-hour Kp intervals;
- provides ensemble minimum, quartiles, median, maximum, and threshold
  probabilities.

The public `LAST` file is a latest-cycle product. No public issue-time archive
was identified that can reconstruct what this product forecast at every
historical SERENE analysis time. The latest file must therefore never be
applied to an unrelated historical cycle.

## Horizon Resolution

For each AIDA analysis time, calculate these targets independently:

- `target_30 = analysis_time + 30 minutes`
- `target_90 = analysis_time + 90 minutes`

GFZ Kp timestamps denote three-hour interval starts. Map each target to:

`interval_start = floor(target_time, 3 hours)`

Each horizon is resolved independently using the following order.

### Observed Outcome

If GFZ has published an observed Kp value for the target interval, use that
value and label the evidence:

`GFZ observed outcome — backtesting only`

This is a retrospective outcome assessment, not a forecast that was available
at the analysis time. It allows every historical SERENE cycle to be evaluated
against what subsequently occurred.

For observed outcome evidence:

- the primary value is the observed Kp;
- ensemble maximum and probability are not applicable;
- GFZ preliminary/definitive status is retained;
- the Dashboard and report must use the term `Backtesting`, not `Official
  forecast`.

### Official Ensemble Forecast

If the observed target interval is not yet available, try the current GFZ
PAGER/SWIFT forecast. Use it only when:

- the requested interval exists in the downloaded forecast;
- the forecast file is aligned to the current/latest SERENE cycle rather than
  an unrelated historical selection;
- its HTTP `Last-Modified` time and forecast interval coverage pass freshness
  validation;
- all required values are finite and within valid Kp/probability ranges.

For official forecast evidence:

- use ensemble `median` as the primary Kp value;
- retain ensemble `maximum`;
- retain `prob >= 8` as the probability of the Moderate threshold being met;
- label the evidence `GFZ official PAGER/SWIFT ensemble forecast`;
- retain forecast file issue/freshness metadata where available.

### Unavailable

If neither source can supply a scientifically aligned horizon, leave only that
horizon `UNAVAILABLE` and record the reason. Do not:

- copy the latest Kp into a future horizon;
- interpolate a Kp value locally;
- apply the current `LAST` forecast to a historical date;
- turn missing evidence into `OK`.

One horizon may be available while the other remains unavailable.

## Risk and Uncertainty Rules

The existing Auroral Absorption proxy thresholds do not change:

- `Kp < 8`: `OK`
- `8 <= Kp < 9`: `MODERATE`
- `Kp >= 9`: `SEVERE`

For official ensemble forecasts, classify the ensemble median. Do not classify
the ensemble maximum as the primary state.

If the median is `OK` but the ensemble maximum is at least 8, add:

`Low-probability, high-impact ensemble scenario reaches Kp >= 8.`

This warning does not upgrade the primary state. The displayed `prob >= 8`
provides the quantitative uncertainty context; no new probability threshold is
invented for upgrading the category.

For historical observed outcomes, classify the actual observed Kp. Do not show
ensemble uncertainty fields because they do not apply.

## Data Boundaries

Add a dedicated Kp horizon evidence structure instead of mixing future rows
into the historical Kp DataFrame. Each row shall contain:

- `horizon_minutes`: `30` or `90`;
- `target_time`: exact AIDA horizon time;
- `interval_start`: mapped GFZ three-hour interval;
- `value`: observed Kp or ensemble median;
- `status`: `OK`, `MODERATE`, `SEVERE`, or `UNAVAILABLE`;
- `evidence_role`: `official_forecast`, `observed_backtesting`, or
  `unavailable`;
- `source`: explicit GFZ source label;
- `ensemble_maximum`: forecast-only numeric field;
- `probability_kp_ge_8`: forecast-only numeric field on `[0, 1]`;
- `data_status`: observed-only preliminary/definitive field;
- `issue_time`: forecast freshness time when supplied by HTTP metadata;
- `availability_reason`: controlled explanation for missing evidence.

This separation is required to prevent future outcome rows from influencing:

- Latest Kp;
- Max-3h Kp;
- the preceding-96-hour `Kp >= 6` PSD storm gate;
- any global nowcast graph.

## Dashboard Presentation

The main summary shall use general horizon wording so both roles remain honest:

- `+30 min assessment`
- `+90 min assessment`

For each horizon show:

- Kp value;
- risk category;
- evidence source/role.

For official forecasts, the API evidence section shall also show:

- ensemble maximum;
- `P(Kp >= 8)`;
- forecast freshness/issue time;
- the low-probability high-impact warning when applicable.

For historical outcomes, show:

`Observed outcome — backtesting only; not a forecast available at the selected analysis time.`

The current Latest and Max-3h columns remain observed GFZ Kp context.

## Caching and Requests

- Cache the latest PAGER/SWIFT JSON for one hour.
- Cache historical observed Kp by the existing index/range key.
- Resolve +30 and +90 together when one historical GFZ range request can cover
  both intervals.
- Do not send the SERENE token to either GFZ host.
- Preserve independent failure: a forecast failure must not remove observed Kp,
  SERENE AIDA, TEC, MUF3000F2, or PSD evidence.

## Verification

Automated tests shall cover:

- the exact `2024-09-28T00:00:00Z` analysis boundary;
- rejection of pre-boundary AIDA analysis;
- historical +30/+90 observed Backtesting at the archive boundary;
- historical +30/+90 observed Backtesting for `2026-07-01T05:55:00Z`;
- current/latest +30/+90 official PAGER/SWIFT predictions;
- three-hour interval mapping on both sides of a boundary;
- independent +30 and +90 availability;
- parser handling of GFZ dict-of-dicts forecast JSON;
- median classification and maximum/probability preservation;
- low-probability high-impact warning without category escalation;
- stale or unrelated `LAST` forecast rejection;
- malformed/non-finite/out-of-range forecast rejection;
- no future leakage into Latest, Max-3h, or the preceding-96-hour gate;
- no Authorization header sent to GFZ;
- unchanged SERENE AIDA product kinds and sources;
- complete Dashboard regression suite.

Live acceptance shall verify:

- `2024-09-28T00:00:00Z` produces observed +30/+90 Backtesting evidence;
- `2026-07-01T05:55:00Z` produces observed +30/+90 Backtesting evidence;
- Follow Latest uses the current GFZ official ensemble forecast where targets
  are genuinely in the future;
- source labels clearly distinguish forecast from Backtesting;
- SERENE remains the source for every AIDA analysis and AIDA forecast.

## Repository Scope

All implementation, tests, and documentation shall be committed and pushed
only to `ylianxin2003-droid/August-project-version`. The legacy repository
remains read-only.
