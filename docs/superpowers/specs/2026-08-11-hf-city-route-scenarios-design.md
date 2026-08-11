# HF City-to-City Scenario Design

Date: 2026-08-11

## Purpose

Make the standalone HF communication study understandable to non-specialists by
allowing users to select named geographic endpoints such as Birmingham and New
York instead of entering latitude and longitude directly.

## Scientific Boundary

The endpoints are assumed geographic communication endpoints used for an
illustrative MUF-path assessment. They are not confirmed HF transmitter sites,
airport departure/destination pairs, or validated aircraft trajectories. The
existing great-circle route remains a reproducible engineering approximation.

## Interaction Design

The HF study provides three route modes:

1. **Preset scenario** — choose a named representative route.
2. **Custom city-to-city** — choose an origin city/region and target city/region
   from searchable Streamlit selectors.
3. **Advanced coordinates** — retain manual latitude/longitude inputs for
   scientific reproducibility.

The default preset is `Birmingham → New York`. The page shows the resolved
endpoint names and coordinates before calculating the route.

## Location Catalogue

Use a version-controlled offline catalogue rather than an external geocoding
API. This avoids network failures, rate limits, ambiguous addresses and privacy
issues. Initial locations cover representative North Atlantic and long-haul
cases:

- Birmingham, London, Reykjavik, Shannon and Madrid;
- New York, Gander, Toronto, Dubai, Singapore and Tokyo;
- North Atlantic corridor.

Each entry stores a display name, latitude, longitude and location type. The
catalogue may be expanded without changing the route engine.

## Preset Scenarios

- Birmingham → New York
- London → New York
- Birmingham → North Atlantic corridor
- London → Toronto
- London → Reykjavik
- London → Dubai
- London → Singapore
- London → Tokyo

These are demonstration scenarios, not operational route recommendations.

## Results

All existing route results remain available: distance, quiet/storm
availability, coverage reduction, degraded percentage, unavailable percentage,
longest degraded segment, maps, MUF profile and frequency sweep. Headings and
map legends use the selected endpoint names instead of a fixed UK–New York
label.

## Validation

- every catalogue entry has a unique name and valid coordinates;
- every preset resolves to two catalogue entries;
- custom city selection reaches the route engine with the correct coordinates;
- advanced coordinate mode remains available;
- Birmingham → New York is the default;
- UI and figures state the assumed/non-operational boundary;
- existing HF calculation tests remain green.
