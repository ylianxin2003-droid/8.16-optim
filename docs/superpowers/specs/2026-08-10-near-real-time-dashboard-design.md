# Near-Real-Time Dashboard and August Repository Design

Date: 2026-08-10

## Purpose

Create a new August development line in `ylianxin2003-droid/August-project-version` without modifying `ylianxin2003-droid/primay-test-frist-version`. The new version must preserve the existing project and Git history, correct the live forecast request, and make near-real-time behaviour explicit, safe, traceable, and testable.

## Repository Isolation

- The legacy repository remains fixed at `951c1cf79adc3d66e7aaf62baa472853ba3f8b87` unless the user changes it independently.
- The August repository inherits the complete legacy `main` history and all tracked files.
- Local development takes place only in `/Users/a123/Desktop/August-project-version`.
- `origin` points to `https://github.com/ylianxin2003-droid/August-project-version.git`.
- `legacy-source` is fetch-only; its push URL is deliberately invalid to prevent accidental writes.
- `.env`, API tokens, Streamlit Secrets, credentials, and local caches are never copied or committed.

## Observed Behaviour and Root Cause

Live browser tests on 2026-08-10 established the following:

| Analysis time | Observation states | Official forecast states | Rows | Result |
|---|---:|---:|---:|---|
| 2026-08-10 08:50 UTC | 1 | 0 | 1,300 | Observation succeeded; forecasts failed |
| 2026-08-09 08:50 UTC | 1 | 3 | 3,250 | Observation and forecasts succeeded |
| 2026-08-08 08:50 UTC | 1 | 3 | 3,250 | Observation and forecasts succeeded |
| 2026-08-07 08:50 UTC | 1 | 3 | 3,250 | Observation and forecasts succeeded |

For current-day requests, `data_loader.py` adds the forecast period to the analysis time and passes the resulting future valid time as the forecast API `file_time`. SERENE rejects that value with `File time must not be in the future`. The API contract requires the analysis time as `file_time` and the horizon as `period`; the valid time is derived locally as `analysis time + period`.

The official public Kp/ap CSV currently ends at `2026-07-07T03:00:00Z`. Therefore Kp-dependent products for August correctly remain unavailable. The application must expose this source-freshness limitation and must not replace missing official data with invented real-time Kp, PSD, or HF risk values.

## Near-Real-Time Definition

The dashboard provides on-demand or optionally scheduled **near-real-time** monitoring. It is not a zero-latency operational service.

- The safe analysis anchor is current UTC minus 15 minutes, floored to a five-minute boundary.
- The interface displays the requested analysis time, actual returned AIDA time, data age, last successful refresh, and next scheduled refresh.
- All near-real-time wording retains the academic research-prototype disclaimer.

## User Controls

### Follow latest near-real-time

- Enabled by default for a new session.
- When enabled, date and time are derived from the safe analysis anchor instead of stale widget values.
- Manual date/time inputs are disabled or hidden while following latest.
- Disabling the option restores historical date/time selection.

### Automatic refresh every 15 minutes

- Disabled by default.
- Available only when all three conditions are true: `Live SERENE API`, `Quick Demo`, and `Follow latest near-real-time`.
- The application recomputes the safe five-minute anchor on each scheduled rerun.
- A scientific reload occurs only when the safe anchor differs from the last successfully loaded automatic-refresh anchor.
- Full ICAO-style mode cannot enable automatic refresh because one load may request 37 rolling states, up to 30 baseline states, and three forecasts.

### Manual Load / Refresh

- The existing button remains available.
- When following latest, the button first recalculates the safe anchor and then loads it.
- In historical mode, the button loads the user-selected analysis time unchanged.

## Forecast Request Correction

For each period in `(90, 180, 360)`:

1. Call `download_aida_forecast(analysis.isoformat(), latency, period)`.
2. Send the normalized analysis time as API `file_time`.
3. Send 90, 180, or 360 as API `period`.
4. Store and display the valid time as `analysis + period`.
5. Preserve the analysis observation if any forecast request fails.

Forecast audit metadata records both `analysis_time` and `valid_time` so the request and displayed horizon remain independently traceable.

## Kp/ap Freshness and PSD Safety

- Parse the complete official public CSV as before.
- Record the newest source timestamp even when filtering produces no rows for the requested interval.
- If the latest official Kp timestamp is older than the requested interval, show a concise stale-source warning including that timestamp.
- Keep `kp_ap_status`, PSD, and HF COM risk unavailable when the required preceding 96-hour history is incomplete.
- The HF manual slider remains an explicitly labelled `Assumed PSD demonstration`; it is never presented as live scientific data.

## Failure Handling

- Observation succeeds, forecast fails: retain observation maps, tables, and GNSS results; show forecast-specific warnings.
- Authentication fails: show a sanitized authentication message and do not fall back to fabricated scientific values.
- Scheduled refresh fails: retain the last successful dataset, mark it stale, and show the failed attempt time.
- Kp/ap is stale or incomplete: show official source freshness and keep dependent products unavailable.
- Automatic refresh never runs in Full ICAO-style mode.

## Testing Strategy

Automated tests must cover:

- forecast `file_time` equals analysis time for all three horizons;
- valid time equals analysis time plus the forecast period;
- a current-day analysis no longer generates a future `file_time`;
- safe analysis time is UTC minus 15 minutes and floored to five minutes;
- automatic refresh eligibility requires Live API, Quick Demo, and Follow latest;
- repeated reruns for the same safe anchor do not trigger duplicate scientific loads;
- observations survive forecast failures;
- stale Kp/ap metadata produces an unavailable, source-dated result;
- secrets and tokens are absent from errors and tracked files.

The full existing `unittest` suite must pass after focused tests pass.

## Documentation and Deployment

README and deployment documentation will explain:

- near-real-time versus continuous operational real time;
- the 15-minute publication allowance and five-minute AIDA cadence;
- manual and optional automatic refresh behaviour;
- API request controls and the Full Mode restriction;
- forecast request provenance;
- Kp/ap freshness limitations;
- Streamlit Community Cloud configuration without real secret values.

Deployment uses `streamlit_cloud_github/app.py`, Python 3.11, and Streamlit Secrets. The August repository must be deployed as a separate app or explicitly repointed only after the new repository has passed verification.

## Acceptance Criteria

1. The legacy remote still resolves to commit `951c1cf79adc3d66e7aaf62baa472853ba3f8b87` after publication.
2. The August repository contains the complete tracked legacy project plus the new design, implementation, tests, and documentation.
3. Today’s observation and official forecast requests use a non-future analysis `file_time`.
4. Yesterday, two-days-prior, and 72-hour historical requests continue to work.
5. Optional 15-minute refresh cannot cause repeated Full Mode downloads.
6. Missing or stale Kp/ap never produces fabricated PSD or HF risk.
7. The complete automated test suite passes.
8. Repository scanning finds no committed API token, `.env`, or Streamlit Secrets.
