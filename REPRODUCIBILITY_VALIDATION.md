# Reproducibility Validation Summary

A separate clean reproduction of the frozen ADAA Foundation workflow was completed before public release.

The validation covered independent R/Python reconstruction of target weights, source-parent and counterfactual decision panels, canonical FAA, performance/accounting reconciliation, robustness diagnostics, stress and dependence-aware inference, drawdown calculations, the USD/KRW appendix, and the completed 2023 Strategy-Zoo reconstruction.

Cross-language differences in the principal weight and performance checks were at floating-point scale or below the stated numerical tolerances.

This establishes reproducibility of the frozen retrospective workflow. It does not establish a live track record, preregistration, or permanent optimality of the current sleeve set.

## Post-release scientific-code hardening

A retrospective Scientific Code Design Audit completed after the frozen `v1.0.2` release classified the findings as one no-science-impact hardening item and one secondary-only diagnostic correction, with no headline numerical, inferential, or claim impact. The current public line retains the versioned `v0.17.1` and `v0.18.1` successors without altering the archived `v1.0.2` release or the Foundation headline results.

## v1.1.1 exact-exhibit validation

The v1.1.1 successor binds the public replication surface to SSRN v1.24. All 12 empirical publication figures have frozen source-data pointers, a deterministic rendering path through `18_RENDER_PUBLICATION_EXHIBITS_v1_1_4.py`, and PNG/SVG SHA-256 records in `EXACT_FIGURE_RENDER_MANIFEST_v1.1.4.csv`.

The v1.24 publication-table reconciliation records 40 checks with 0 failures. The exhibit-layer upgrade changes presentation provenance and reproducibility, not the frozen strategy rules, empirical return paths, inference results, or substantive conclusions.
