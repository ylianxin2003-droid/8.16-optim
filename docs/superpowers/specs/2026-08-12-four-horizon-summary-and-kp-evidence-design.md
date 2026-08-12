# Four-Horizon Summary and Kp Evidence Design

## Goal

Restore a complete `+30 min`, `+90 min`, `+3 h`, and `+6 h` prediction surface
for Vertical TEC, Auroral Absorption (Kp proxy), and Post-Storm Depression while
preserving scientific provenance. The dashboard must use official or observed
evidence when it exists and must never turn missing evidence into a fabricated
`OK` result.

## Product Behaviour

The ICAO/PECASUS-style Summary Table always shows all four horizon groups. Each
group contains value, status, and source columns. The categorical map offers all
four horizons when the corresponding spatial product or explicitly labelled
dashboard fallback is available. The existing TEST advisory message remains
limited to `+30 min` and `+90 min`; expanding that message is outside this change.

For SERENE AIDA spatial indicators:

- Download requests remain `30`, `90`, `180`, and `360` minutes. This change does
  not add more AIDA requests; it starts decoding the already-requested 180- and
  360-minute files instead of retaining them only in the audit.
- Successfully decoded files are labelled `SERENE official forecast` and feed
  TEC and PSD values, statuses, table columns, and map choices.
- If a particular official AIDA horizon is missing, the existing trend or
  persistence fallback may fill TEC/PSD only when its prerequisites are valid.
  Its source must remain visibly labelled `Dashboard-generated ... forecast`.
- PSD forecasts continue to require the MUF baseline and the Kp storm-gate
  rules. A fallback must not bypass either rule.

For the global Kp auroral-absorption proxy:

- Extend Kp horizon resolution from `(30, 90)` to `(30, 90, 180, 360)` minutes.
- A future target uses the GFZ PAGER/SWIFT ensemble row whose three-hour
  `interval_start` contains the target. The ensemble median is the primary Kp;
  ensemble maximum and `P(Kp >= 8)` remain supporting uncertainty evidence.
- A past target uses the GFZ observed Kp value for its containing three-hour
  interval. It is labelled `GFZ observed outcome — backtesting only`, never as
  a historical forecast.
- Multiple horizons may legitimately share one Kp value when they fall in the
  same traditional three-hour Kp interval.
- A fresh, aligned cached GFZ forecast may survive a temporary request failure.
  Stale, misaligned, or absent evidence remains `UNAVAILABLE`; no local Kp
  extrapolation is introduced.

## Data Contracts and Flow

`IcaoProductBundle.kp_horizons` keeps its existing row-oriented schema and gains
rows for 180 and 360 minutes. The Summary Table gains these fields after the
existing 90-minute group:

- `+3h forecast`, `+3h status`, `+3h source`
- `+6h forecast`, `+6h status`, `+6h source`

The forecast audit continues to record request outcome and valid time for all
four AIDA periods, but 180 and 360 change from `audit_only` to primary display
inputs. Availability metadata reports all successfully decoded official periods
in display order.

The processed trial-cache schema and forecast-contract version are incremented.
All eight packaged Quick Demo and Full ICAO caches are regenerated so each
contains four Kp horizon rows and current-contract summary fields. A stale cache
is rejected rather than partially loaded.

## Availability Boundary

For dates in the SERENE archive, historical Kp target intervals are covered by
the longer-running GFZ observed index service under normal upstream operation.
For near-real-time analysis, the GFZ latest ensemble product currently covers
up to 72 hours, which is longer than the requested six-hour horizon. This makes
all four Kp horizons resolvable in normal operation.

Completeness cannot be promised during a third-party outage, malformed upstream
response, missing SERENE forecast file, or stale GFZ forecast. In those cases the
table remains structurally complete and shows the affected evidence as
`UNAVAILABLE` with a reason. This is preferable to presenting invented risk as
scientific output.

## Interface and Documentation

The table caption and Kp evidence panel explain the difference between official
future prediction and historical observed backtesting. Forecast-source fields
remain visible so assessors can trace every value. The API status panel reports
availability for each of the four AIDA horizons instead of describing 3 h and
6 h as audit-only. README and deployment guidance use the same terminology.

## Verification

Automated tests cover:

- Official AIDA 180/360 payloads are decoded and classified for TEC and PSD.
- Missing AIDA 180/360 files retain labelled fallback or `UNAVAILABLE` behaviour.
- GFZ future rows resolve all four horizons with correct three-hour alignment.
- Historical targets resolve all four observed outcomes and use backtesting
  provenance.
- Freshness, issue-time, missing-row, and GFZ outage guards do not fabricate Kp.
- The Summary Table always exposes four horizon groups and styles their statuses.
- Maps expose the available 3 h and 6 h spatial horizons; TEST messages remain
  30/90 only.
- Old trial-cache contracts are rejected; eight regenerated caches load with
  four Kp horizon rows and no credentials.

Acceptance requires the complete unit suite, cache-contract validation, secret
scan, and browser checks for one historical Full ICAO case and one current/live
case. The browser checks must confirm value/status/source fields, Kp provenance,
four horizon controls, no Streamlit exception, and no compatibility warning.

## Deployment

All implementation and regenerated outputs are committed only to
`August-project-version`. The legacy repository remains read-only. After push,
the Streamlit Cloud deployment can be rebooted or allowed to redeploy from the
August `main` branch.
