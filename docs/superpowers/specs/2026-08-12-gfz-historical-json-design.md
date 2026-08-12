# GFZ Historical JSON and SERENE Time Alignment Design

## Objective

Support Kp/ap-backed dashboard analysis for every selectable SERENE AIDA time
from `2024-09-28T00:00:00Z` through the latest available SERENE cycle. Replace
the GFZ 30-day nowcast-file dependency with the official GFZ JSON web service.

This specification supersedes the 30-day GFZ nowcast design in
`2026-08-12-gfz-kp-ap-source-design.md`.

## Supported Time Range

The combined dashboard range begins at the SERENE AIDA archive boundary:

`2024-09-28T00:00:00Z`

GFZ supplies older Kp/ap data, but the dashboard does not claim a complete
AIDA/Kp analysis before this boundary. The upper boundary is not the user's
computer clock. In Follow Latest mode it is the authoritative UTC cycle read
from the latest SERENE AIDA HDF5 state.

## Query Strategy

For each analysis cycle, the dashboard requests from the GFZ JSON service:

- Kp from `analysis_time - 96 hours` through `analysis_time`
- ap from `analysis_time - 96 hours` through `analysis_time`

The service endpoint is:

`https://kp.gfz.de/app/json/`

with URL parameters `start`, `end`, and `index`. It is public and requires no
token or Streamlit secret.

The dashboard deliberately does not pass the complete two-year Kp archive into
the current risk engine. Doing so could allow an old storm to influence a later
analysis. Instead, any analysis time in the supported range can be queried, but
only its relevant preceding 96-hour window is returned downstream.

## SERENE Alignment

In Follow Latest mode:

1. Download the latest SERENE Ultra AIDA HDF5 file.
2. Read its authoritative `analysis_time` from the file.
3. Use exactly that time as the GFZ query end.
4. Use exactly `analysis_time - 96 hours` as the GFZ query start.
5. Use the same `analysis_time` as the AIDA forecast `file_time`.

In manual historical mode, the user-selected normalized AIDA analysis time is
used for both the AIDA cycle and GFZ query end.

GFZ values occur at three-hour interval starts. The latest valid GFZ value may
therefore precede the AIDA cycle by up to approximately three hours. Future or
missing GFZ slots must not be treated as data.

## JSON Parsing and Merge

Kp and ap are requested independently because GFZ's documented interface takes
one `index` per request. Each response must contain compatible `datetime`,
index-value, and `status` arrays.

The parser shall:

- parse all timestamps as UTC;
- map `pre` to `preliminary` and `def` to `definitive`;
- reject non-finite and sentinel values;
- merge Kp and ap rows into the existing long-form dashboard schema;
- preserve the source label `GFZ Kp/ap JSON service`;
- record the last valid timestamp at or before the SERENE analysis time.

If Kp succeeds and ap fails, Kp-backed HF risk may still be evaluated and ap is
reported unavailable. If Kp fails or its preceding 96-hour coverage is
incomplete, Auroral Absorption and Kp-gated PSD remain `Unavailable`.

## Caching

Cache GFZ responses by `(index, normalized start, normalized end)` for one hour.
This prevents duplicate Kp/ap requests during Streamlit reruns without allowing
one analysis cycle's data to leak into another cycle.

## Unchanged Behaviour

Only the Kp/ap acquisition mechanism changes. The following remain unchanged:

- SERENE token and AIDA endpoints;
- AIDA analysis, rolling, baseline, and forecast downloads;
- TEC and MUF3000F2 calculations;
- +30/+90 minute primary forecast display;
- +3/+6 hour audit-only handling;
- Kp, TEC, and PSD thresholds;
- route and HF communication coverage logic;
- Kp/ap exclusion from regional maps;
- missing evidence never becoming `OK`.

## Verification

Automated tests shall cover:

- July 2026 historical Kp/ap retrieval outside the former 30-day file;
- a 2024 analysis near the AIDA archive start;
- a current Follow Latest cycle aligned to the SERENE HDF5 time;
- Kp/ap JSON parsing and status mapping;
- independent Kp/ap partial failure;
- incomplete 96-hour Kp coverage;
- cache isolation by index and time range;
- unchanged AIDA product kinds and source labels;
- complete dashboard regression suite.

Live acceptance shall query both a historical July 2026 cycle and the current
SERENE cycle, verifying that Kp/ap load from GFZ while AIDA analysis and
+30/+90 minute forecasts remain sourced from SERENE.
