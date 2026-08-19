# Figure Provenance Map — SSRN v1.34

Date: 2026-08-19
Status: PASS

All 12 empirical figures in the SSRN v1.34 upload-ready manuscript are bound to the deterministic publication renderer v1.1.6 and the existing frozen source-data layer.

Validation requirements closed for this candidate:
- source-data -> renderer -> PNG/SVG chain recorded in `EXACT_FIGURE_RENDER_MANIFEST_v1.1.6.csv`;
- 12/12 rendered PNG files match the images embedded in the canonical v1.34 DOCX byte-for-byte;
- same-environment repeat render is byte-identical for all 12 PNG/SVG pairs;
- presentation-label changes do not alter source data or plotted values.

No conceptual-only manuscript figures are used in the v1.34 publication set.
