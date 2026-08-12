# Inline Standalone HF Study Design

## Purpose

Make the standalone HF communication engineering study part of the main
dashboard reading flow. The user should see the study controls, route map and
results without first opening an outer disclosure control.

## Scope

- Remove only the outer `Open standalone study details` expander.
- Render `render_hf_propagation_case_study(df)` directly below the standalone
  study introduction card.
- Retain the internal `How to interpret this HF case study` and `Trace
  integration status` expanders so supporting explanation does not make the
  main page unnecessarily long.
- Update README wording that currently describes the study entry as collapsed.
- Do not change the HF propagation calculations, scientific thresholds, data
  sources or standalone-study limitations as part of this layout change.

## Rendering and Data Flow

`_render_main()` continues to call `_render_standalone_hf_study(df)` only when
the loaded product frame is not empty. `_render_standalone_hf_study()` renders
its heading and scope card, then calls the existing HF case-study renderer
directly. The renderer continues to receive the same dataframe and owns all
route controls, calculations, figures and internal explanation panels.

## Error and Availability Behaviour

Existing empty-grid, missing-reference and assumed-PSD messages remain
unchanged. Removing the outer expander must not convert unavailable evidence to
`OK`, alter route results, or change any SERENE/GFZ availability decision.

## Verification

1. Add a Streamlit regression assertion that the standalone heading and study
   body are present while the removed outer expander label is absent.
2. Run the targeted Streamlit application test and the complete automated test
   suite.
3. Review the risk and HF calculation paths for internal consistency, including
   `OK`, `MODERATE`, `SEVERE` and `UNAVAILABLE`, PSD storm gating, displayed
   30/90-minute provenance, route sampling and missing-data behaviour.
4. Start the local Streamlit app and inspect the rendered page in a browser:
   the study body must be visible immediately; both internal explanation
   expanders must remain; controls and route graphics must render without an
   application exception.

Any unrelated logic defect found during review will be reported with evidence.
It will not be silently combined with this presentation-only change.
