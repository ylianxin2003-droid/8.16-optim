# GFZ Kp/ap Data Source Design

## Objective

Replace only the dashboard's stale SERENE-distributed Kp/ap input with the
public GFZ Helmholtz Centre for Geosciences Kp/ap nowcast file. Preserve all
other SERENE AIDA downloads, calculations, forecasts, risk thresholds, labels,
maps, exports, and user workflows.

## Scope

The dashboard shall obtain Kp and ap from:

`https://kp.gfz.de/fileadmin/files_for_gfz_cms/Kp_ap_nowcast.txt`

This public HTTPS resource requires no API token or additional Streamlit
secret. It provides one Kp/ap record per three-hour interval for the latest 30
days. GFZ is the original provider identified on the SERENE Indices page.

No NOAA source, Kp forecast, multi-source fallback, new credential, regional
Kp layer, or unrelated refactor is included.

## Architecture and Data Flow

`SereneClient.fetch_kp_ap_indices()` remains the compatibility boundary used by
the existing loader. Its implementation will download and cache the GFZ text
resource, parse it into the existing long-form DataFrame schema, and filter it
to the requested UTC interval.

The returned schema remains compatible with downstream code:

- `time`: UTC interval start time
- `lat`, `lon`, `alt`: null because Kp/ap are planetary indices
- `variable`: `Kp` or `ap`
- `value`: numeric GFZ value
- `model`: `GFZ Geomagnetic Indices`
- `source`: `GFZ Kp/ap nowcast`
- `data_status`: `preliminary` when GFZ `D=0`, otherwise `definitive`

The existing `data_loader` continues to select the preceding 96 hours, check
history completeness, calculate whether Kp reached 6, and pass that gate to
the existing PSD logic. Kp/ap remain excluded from regional map cells.

## Parsing Rules

The parser shall:

1. Ignore blank lines and GFZ comment lines beginning with `#`.
2. Read the documented columns `YYYY MM DD hh.h hh._m days days_m Kp ap D`.
3. Construct the timestamp from the UTC date and interval start hour `hh.h`.
4. Treat `Kp=-1.000` and `ap=-1` as missing values, not real measurements.
5. Convert `D=0` to `preliminary` and `D=1` to `definitive`.
6. Apply inclusive start/end filters and preserve the source maximum timestamp
   before filtering for freshness reporting.

Malformed or empty input shall return no rows and a controlled unavailable
message rather than raising into the Streamlit page.

## User Interface and Provenance

The connection panel shall label the index source as GFZ, show its latest
official timestamp, and state whether the loaded range contains preliminary or
definitive values. CSV exports shall carry `GFZ Kp/ap nowcast` in the source
field. The existing thresholds and risk labels are unchanged.

The documentation shall state:

- SERENE remains the source for AIDA observations and forecasts.
- GFZ is used only for Kp/ap.
- GFZ preliminary nowcast values may later be revised.
- Missing or incomplete Kp history remains `Unavailable`, never `OK`.

## Failure Behaviour

If the GFZ request fails, times out, returns malformed text, or does not cover
the selected 96-hour window:

- AIDA products remain available.
- Kp/ap status becomes `unavailable`.
- Kp-dependent PSD remains `Unavailable` when the 96-hour gate cannot be
  evaluated.
- The status panel reports a concise GFZ-specific reason without exposing any
  token or secret.

## Compatibility Guarantees

The following behaviour shall not change:

- SERENE authentication and AIDA endpoints
- follow-latest AIDA cycle selection
- TEC and MUF3000F2 calculations
- official +30 minute and +90 minute forecast presentation
- +3 hour and +6 hour audit-only treatment
- TEC, PSD, and Kp risk thresholds
- route selection and HF communication coverage
- map construction and the exclusion of Kp/ap from regional cells
- Streamlit Cloud secret names and deployment entry point

## Verification

Automated tests shall cover GFZ parsing, time filtering, missing-value handling,
preliminary/definitive provenance, caching, no-token requests, malformed input,
and downstream 96-hour Kp gating. Existing tests shall continue to pass.

A live acceptance check shall confirm that the GFZ source returns current Kp/ap
rows, that the latest timestamp is recorded, that no token is needed, and that
the SERENE AIDA path still loads its existing products independently.
