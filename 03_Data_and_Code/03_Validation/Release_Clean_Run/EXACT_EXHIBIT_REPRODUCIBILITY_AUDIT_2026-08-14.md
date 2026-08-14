# ADAA Exact Exhibit Reproducibility Audit — 2026-08-14

Status: **INFRASTRUCTURE PASS / FINAL SSRN PDF BINDING PENDING**

Policy basis: common `Exhibit Provenance and Reproducibility Policy v1.1` under Research Governance v1.13.2.

## Scope

- 12 empirical publication figures: Figures 1–8, Appendix Figures Z1–Z2, Appendix FX Figures 1–2.
- Numeric/publication tables: Table 1, Table 1B, Table 2A, Table 2B, Table 3, Table 4, Appendix Table FX-1.
- Current working manuscript inspected: `ADAA_SSRN_Working_Paper_v1.24_PUBLIC_LANGUAGE_REVISION_CANDIDATE.pdf`.
- Working-PDF SHA-256 at audit time: `23a44eed727f6a16e0ed41f27867fcdcd43b060b37e2d95151cadfc6b1035347`.

## Figure result

All 12 figures now have an explicit chain:

`upstream analysis code -> frozen/publication source data -> deterministic render code -> PNG/SVG publication render -> SHA-256 manifest`.

The render program is `03_Data_and_Code/02_Code/18_RENDER_PUBLICATION_EXHIBITS_v1_1.py`.
A double render in the same pinned reference environment produced identical PNG SHA-256 values for all 12 figures.

The new render layer is title-free by design because the manuscript caption is the authoritative title/caption surface.
No strategy rule, return series, statistical result, table value, or figure data geometry was changed.

## Presentation mismatches detected and resolved in the render specification

1. **Figure 7 axis/caption mismatch.** The current v1.24 working PDF caption says the horizontal axis is underwater duration and the vertical axis is maximum drawdown, while the previously stored plot had those axes reversed. The exact-render specification follows the caption: x = longest underwater run, y = maximum drawdown depth.
2. **Figure 5 marker-language mismatch.** The manuscript text describes circles-and-whiskers for the near-optimal region and square-and-whisker bootstrap ranges. The exact-render specification now implements those marker roles explicitly while retaining the later practitioner weights, full-sample ex-post optimum, and rolling optimum range.
3. **Figure 6/7 public label cleanup.** The publication render uses `ADAA practitioner weights` rather than internal/historical `successor` or `historical` labels. Numeric paths are unchanged.
4. **Appendix FX Figure 2 marker-size provenance.** A v1.1 source-data successor explicitly records CAGR improvement versus the fixed-50%-unhedged gross baseline, so marker area no longer depends on an implicit plotting-time reference.

Because the manuscript is still undergoing prose review, these corrected exact renders are **not yet declared bound to the final SSRN PDF**. The final v1.24/v-next PDF must be rebuilt with the exact-render files and then hash-bound under the Policy-to-Artifact Compliance Evidence Gate before SSRN revise.

## Table result

The numeric-table audit required no new general table framework. Existing analytical source CSVs already cover the quantitative tables. Two publication-layer source files were added because their prose was editorially revised:

- `TABLE_1_PUBLICATION_SOURCE_v1.1.csv`
- `TABLE_1B_PUBLICATION_SOURCE_v1.1.csv`

A 40-check reconciliation against the current v1.24 PDF text returned **40 PASS / 0 FAIL** across Table 1/1B, Table 2A/2B, Table 3, Table 4, and Appendix Table FX-1.

## Release boundary

- Public replication v1.0.2 remains immutable historical provenance.
- Local v1.0.3 remains a superseded local hygiene candidate; it is not published automatically.
- A new local v1.1.0 exact-exhibit replication candidate may be used with the next natural SSRN/public-replication release after final manuscript binding and exact-artifact QA.
- FAJ v0.66.5 submitted files and submitted replication state are not modified. Apply the new exhibit policy only to a future FAJ revision successor if the journal opens a revision gate.
