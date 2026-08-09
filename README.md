# ADAA — Decision Diversification Replication Materials

Public research and replication materials for **“Diversify the Decisions, Not Just the Assets: A Practical Architecture for Dynamic Asset Allocation When Strategy Choice Is Uncertain.”**

The paper studies **Autonomous Dynamic Asset Allocation (ADAA)** as a rule-governed, modular dynamic-allocation architecture. The current five-sleeve configuration is a worked reference implementation, not a permanent definition of ADAA.

## Public resources

- **Working paper:** `paper/ADAA_SSRN_Working_Paper_v1.21_FINAL_PUBLIC_RELEASE.pdf`
- **Research dashboard:** https://slackquant80.github.io/adaa-slackquant/
- **Replication repository:** https://github.com/slackquant80/adaa-decision-diversification

The archived GitHub release `v1.0.2` remains the frozen replication snapshot. The current `main` branch is a curated reader-facing view of the same frozen Foundation science, with the current public working-paper PDF and simplified navigation.

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
