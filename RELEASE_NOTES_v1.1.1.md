# Release Notes v1.1.1 — exact exhibit reproducibility and final-paper binding

This is the fresh successor to public replication v1.0.2. The earlier local v1.1.0 release candidate was never published and is superseded.

- Binds the replication release to the SSRN v1.24 final-freeze manuscript submitted through the SSRN revise workflow on 2026-08-14.
- Final manuscript SHA-256: `1ddf4f8eb1078791e7dba91a76a006638086c954182170ec04d87f6d86d64fad` (26 pages).
- Uses exact publication renderer `18_RENDER_PUBLICATION_EXHIBITS_v1_1_4.py`.
- Includes deterministic source-data-to-render chains for all 12 empirical figures, with PNG and SVG companions and SHA-256 manifesting.
- Includes publication-layer source files and the existing 40-check numeric table reconciliation.
- Preserves all frozen strategy rules, return paths, inference results, and substantive conclusions from public v1.0.2.
- Presentation refinements reflected in v1.24 include the Figure 5 Monte Carlo-range wording, Figure 7 axis reconciliation, Figure 8 exploratory-bar distinction, Z1/Z2 readability improvements, and the FX2 threshold-sensitivity heatmap.
- The manuscript PDF is distributed separately and is not bundled into this package; `06_Public_Metadata/PUBLICATION_TARGET_v1.1.1.csv` records the exact binding hash.
