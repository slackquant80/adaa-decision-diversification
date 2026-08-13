# G6 Secondary Robustness Hardening Review — v0.18.1

Status: **POST-RELEASE SECONDARY HARDENING / NO HEADLINE SCIENCE CHANGE**

The historical v0.17 and v0.18 diagnostic scripts remain available for provenance. The current `main` branch adds versioned successors rather than overwriting those historical layers.

## v0.17.1

`analyze_g6_rolling_robustness_v0_17_1.py` adds a fail-closed check for missing returns on assets with non-zero target weights. The diagnostic values are unchanged from v0.17.

## v0.18.1

`analyze_weight_robustness_plateau_v0_18_1.py` corrects maximum drawdown in secondary weight-robustness diagnostics by prepending initial wealth `W0=1`, matching the canonical drawdown convention already used by the Foundation paper-level drawdown analysis. It also adds the used-asset missing-return assertion.

The correction does not alter the manuscript-used Sharpe plateau, feasible-weight breadth, rolling-optimum instability, bootstrap-weight uncertainty, near-optimal bands, or optimizer-chasing results.

The archived public replication release `v1.0.2` is not modified by this hardening.
