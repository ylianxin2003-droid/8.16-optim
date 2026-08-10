# Near-Real-Time Verification Record — 2026-08-10

## Scope and operating definition

The dashboard is an academic research prototype that provides on-demand or
optionally scheduled **near-real-time** monitoring. It is not a zero-latency
or operational aviation service.

For follow-latest use, the safe analysis anchor is current UTC minus **15
minutes**, floored to the five-minute AIDA cadence. The interface exposes the
requested analysis time, the actual returned AIDA time, data age, last
successful refresh, and the next scheduled-refresh status.

## Refresh controls and request limits

- **Follow latest near-real-time** is enabled by default for a new session.
  It derives the date/time from the safe anchor. Turning it off restores manual
  historical date/time selection.
- **Manual Load / Refresh** is available in both modes. It recalculates the
  safe anchor before loading in follow-latest mode and preserves the selected
  analysis time in historical mode.
- **Auto-refresh every 15 minutes** is optional and disabled by default. It is
  eligible only for **Live SERENE API** + **Quick Demo** + **Follow latest
  near-real-time**.
- A scheduled load is attempted only when the safe five-minute anchor differs
  from the last successful automatic-refresh anchor.
- **Full ICAO-style mode** is manual-only. A single load can request 37 rolling
  states, up to 30 baseline states, and three forecasts, so automatic refresh
  is deliberately prohibited.

## Browser observations before the forecast-request fix

The following were browser-test observations collected before this change was
deployed. They establish the fault pattern, but they do **not** validate a new
deployment.

| Analysis time | Observation states | Official forecast states | Rows | Observation |
|---|---:|---:|---:|---|
| 2026-08-10 08:50 UTC | 1 | 0 | 1,300 | Observation succeeded; forecasts failed |
| 2026-08-09 08:50 UTC | 1 | 3 | 3,250 | Observation and forecasts succeeded |
| 2026-08-08 08:50 UTC | 1 | 3 | 3,250 | Observation and forecasts succeeded |
| 2026-08-07 08:50 UTC | 1 | 3 | 3,250 | Observation and forecasts succeeded |

The root cause was a current-day forecast request using the future valid time
as API `file_time`. SERENE rejected it because `file_time` must not be in the
future. The corrected request sends the normalized **analysis time** as
`file_time` and sends 90, 180, or 360 minutes as `period`; valid time is derived
and displayed as `analysis time + period`. Audit metadata keeps analysis time
and valid time separate. A forecast-specific failure must not remove a
successful analysis observation.

## Official Kp/ap freshness and PSD/HF boundary

On 2026-08-10, the official Kp/ap CSV observed by this project ended at
`2026-07-07T03:00:00Z`. When the requested interval lacks sufficient official
history, the dashboard reports the source freshness and retains unavailable
Kp/ap-dependent PSD and HF COM outputs. It must not fabricate real-time Kp,
ap, PSD, or HF risk values.

The optional HF slider is only an **Assumed PSD demonstration**. It is not a
live scientific PSD result, and the dashboard does not claim an integrated HF
ray-tracing implementation.

## Required live deployment acceptance

After deploying the new revision, test with real authorised access before
claiming operational behaviour:

1. In **Live SERENE API** + **Quick Demo** + **Follow latest near-real-time**,
   load the safe analysis anchor and confirm the recorded forecast request uses
   a non-future analysis `file_time` for all horizons.
2. Confirm the returned observation remains visible if any forecast horizon
   fails, with a forecast-specific warning.
3. Confirm **Auto-refresh every 15 minutes** is disabled by default and cannot
   be enabled outside the three eligible controls; verify Full ICAO-style mode
   cannot schedule automatic scientific loads.
4. Confirm the status panel shows requested/returned times, data age, refresh
   status, and official Kp/ap freshness. If the official history is incomplete,
   verify PSD/HF stays unavailable rather than becoming a generated value.
5. Record the deployment revision, test UTC time, authorised tester, and
   observed outcomes separately. Do not place credentials or tokens in this
   record.

This record deliberately separates pre-fix browser observations, implemented
request/refresh controls, and the acceptance test still required after
deployment.
