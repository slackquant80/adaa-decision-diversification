# Publication Reconciliation v1.0

**Verdict: PASS at publication precision.**

The completed user-local clean run was reconciled against the final public working paper. Fresh public-data retrieval can create tiny full-precision differences relative to the frozen publication source files, but the displayed performance, inference, drawdown, robustness and FX values remain invariant at the precision used in the paper.

Automated checks are recorded in `PUBLICATION_RECONCILIATION_CHECKS_v1.0.csv`.

## Final consistency corrections made before SSRN v1.0 freeze

1. **FX threshold-grid count:** the corrected source shows that **15 of 16** predeclared threshold cells have a shallower maximum drawdown than the fixed-50% unhedged comparator. An earlier draft said fourteen; the final paper says fifteen.
2. **FX bootstrap MDD wording:** the corrected block-bootstrap probability is 0.8323, so the final paper reports **about 83.2%** rather than carrying unnecessary second-decimal precision.
3. **Strategy-Zoo floating-point wording:** final independent R validation produced a maximum cell difference of 1.332e-15 across DM/AAA/PAA/KDA. The paper therefore uses the environment-robust wording **below 3e-15** rather than anchoring the prose to one machine's last floating-point digit.
4. **Figures:** all 11 embedded manuscript images are byte-identical to the 11 active PNG exhibits in this release package.

These are reconciliation/presentation corrections. They do not alter strategy rules, universes, target-weight histories, return paths, sample, top-level weights, transaction-cost grid, benchmarks, selector definition or scientific conclusions.
