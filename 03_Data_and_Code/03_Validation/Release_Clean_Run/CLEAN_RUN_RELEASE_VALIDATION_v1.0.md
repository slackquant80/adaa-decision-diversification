# Clean-Run Release Validation v1.0

**Release gate: CLOSED PASS.**

A full mixed R/Python clean reproduction was executed in a separate user-local temporary project copy on 2026-08-08. Public-market inputs were retrieved locally; downloaded raw inputs were removed before the completed tree was returned for release reconciliation.

## Closed gates

- Public-package static validation: PASS before the run and PASS after local runtime inputs were purged.
- Frozen-input audit: performance blind; manifest hash checks PASS; no headline strategy performance computed before structural gates.
- Five-sleeve target weights: independent R/Python comparison PASS. Maximum absolute cell differences were floating-point scale (HAA/BAA/ADM/FAA about 3-4e-16; LAA exactly zero in that gate).
- Parent/source and counterfactual decision panels: independent comparison PASS.
- Canonical FAA: independent R/Python target-weight comparison PASS; 218 common months; maximum absolute difference 3.89e-16.
- Performance/accounting engine: independent R/Python reconciliation PASS; 40 metric rows and 654 monthly rows compared; no metric cell exceeded 1e-10.
- Weight robustness / broad plateau diagnostics: PASS; diagnostic only, with no reselection.
- Stress / dependence-aware inference: PASS.
- Standard drawdown definition: independent R/Python validation PASS. Initial wealth W0=1 is a valid running peak; no strategy rule, return path, weight, cost or sample was changed.
- KRW/USD appendix: signal replication and corrected drawdown appendix PASS / conditional historical-application interpretation; no FX rule was reselected.
- Completed 2023 Strategy-Zoo: 16 rules and 4,368 five-rule combinations rebuilt performance-blind. Final independent R validation PASS for DM / AAA / PAA / KDA: DM 0, AAA 1.332e-15, PAA 0, KDA 1.055e-15 maximum absolute cell difference. The frozen v0.29 Decision-Space selector definition was unchanged.

## Interpretation boundary

The clean run verifies reproducibility of the frozen research workflow. It does not convert retrospective simulations into live or prospective out-of-sample evidence, does not establish that any current sleeve will work indefinitely, and does not turn a structural diagnostic into a historically algorithm-selected portfolio.
