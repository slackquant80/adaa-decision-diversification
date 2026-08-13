# Scientific Code Hardening Note — 2026-08-12

This note records a post-release reproducibility hardening of the ADAA Foundation research code.

## Scope

The archived public replication release `v1.0.2` remains immutable. The current `main` branch adds two versioned successor diagnostics after a retrospective Scientific Code Design Audit.

- `analyze_g6_rolling_robustness_v0_17_1.py`
  - adds a fail-closed check that no asset with a non-zero target weight has a missing holding-period return before unused missing cells are zero-filled;
  - recomputed rolling-robustness results are unchanged from the historical v0.17 diagnostic.

- `analyze_weight_robustness_plateau_v0_18_1.py`
  - applies the canonical `W0=1` maximum-drawdown convention to secondary weight-robustness MDD fields;
  - adds the same used-asset missing-return check;
  - leaves the manuscript-used Sharpe/weight-plateau, rolling-optimum, bootstrap-weight, near-optimal-band, and optimizer-chasing conclusions unchanged.

## Scientific impact

The audit found no headline numerical, inferential, or claim impact requiring reopening of the Foundation paper. The corrected MDD fields belong to a secondary diagnostic layer; the paper-level drawdown analysis already used the corrected `W0=1` convention.

The current working paper on `main` is SSRN v1.22. The archived `v1.0.2` replication release is preserved as the historical frozen public snapshot.
