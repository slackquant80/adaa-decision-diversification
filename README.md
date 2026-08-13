# ADAA — Decision Diversification Replication Materials

Public research and replication materials for **“Diversify the Decisions, Not Just the Assets: A Practical Architecture for Dynamic Asset Allocation When Strategy Choice Is Uncertain.”**

The paper studies **Autonomous Dynamic Asset Allocation (ADAA)** as a rule-governed, modular dynamic-allocation architecture. The current five-sleeve configuration is a worked reference implementation, not a permanent definition of ADAA.

## Public resources

- **Working paper:** `paper/ADAA_SSRN_Working_Paper_v1.23_FINAL_PUBLIC_RELEASE.pdf`
- **Research dashboard:** https://slackquant80.github.io/adaa-slackquant/
- **Replication repository:** https://github.com/slackquant80/adaa-decision-diversification

The archived GitHub release `v1.0.2` remains the frozen replication snapshot. The current `main` branch is a curated reader-facing view of the same frozen Foundation science, with the current public working-paper PDF, simplified navigation, and non-headline reproducibility hardening introduced after the frozen release. The hardening does not rewrite or replace the archived `v1.0.2` release.

## Included

- frozen R and Python research code;
- public source metadata and input contracts;
- derived figure and table source data;
- active final-paper figure renders;
- nonprivate scientific validation outputs;
- source and rights documentation;
- the current public Foundation paper.

## Not redistributed

Downloaded raw Yahoo Finance or FRED market-data files, local runtime objects, private university material, proprietary research, third-party article files, credentials, and local session files are not redistributed.

## Scientific-code hardening

A retrospective scientific-code design audit found no headline-science error requiring reopening of the Foundation paper. Two versioned successor diagnostics are included on `main`: `analyze_g6_rolling_robustness_v0_17_1.py` adds a fail-closed used-asset return check, and `analyze_weight_robustness_plateau_v0_18_1.py` applies the already-canonical `W0=1` drawdown convention to secondary weight-robustness MDD fields. The archived `v1.0.2` release remains immutable. See `06_Public_Metadata/SCIENTIFIC_CODE_HARDENING_NOTE_2026-08-12.md`.

## Reproduction

The frozen workflow expects the local project root to be named exactly `05_ADAA`.

```bash
git clone https://github.com/slackquant80/adaa-decision-diversification 05_ADAA
cd 05_ADAA
```

Then follow `REPRODUCIBILITY.md`. A full mixed R/Python reproduction may take roughly 20–60 minutes depending on network access, package installation, and machine speed.

## Research boundary

This repository validates a retrospective historical research workflow. It is not a live track record, historical preregistration, or evidence that the current HAA / BAA / ADM / FAA / LAA implementation must remain optimal or effective indefinitely.

The broader ADAA principle is decision diversification inside a modular architecture whose components can be challenged or replaced.

## Data and rights

See `DATA_AND_RIGHTS.md` and the source metadata under `06_Public_Metadata/`.
