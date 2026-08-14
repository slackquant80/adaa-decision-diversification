# ADAA — Decision Diversification Replication Materials

Public research and replication materials for **“Diversify the Decisions, Not Just the Assets: A Practical Architecture for Dynamic Asset Allocation When Strategy Choice Is Uncertain.”**

The paper studies **Autonomous Dynamic Asset Allocation (ADAA)** as a rule-governed, modular dynamic-allocation architecture. The current five-sleeve configuration is a worked reference implementation, not a permanent definition of ADAA.

## Current public version

- **SSRN version:** v1.24
- **SSRN Abstract ID:** 7251518
- **Current public replication release:** v1.1.1
- **Historical frozen predecessor:** v1.0.2

## Public resources

- **Working paper:** `paper/ADAA_SSRN_Working_Paper_v1.24_FINAL_FREEZE.pdf`
- **Research dashboard:** https://slackquant80.github.io/adaa-slackquant/
- **Replication repository:** https://github.com/slackquant80/adaa-decision-diversification
- **GitHub release v1.1.1:** https://github.com/slackquant80/adaa-decision-diversification/releases/tag/v1.1.1
- **Archived release DOI (v1.1.1):** https://doi.org/10.5281/zenodo.21935901
- **Historical v1.0.2 DOI:** https://doi.org/10.5281/zenodo.21853534

Release `v1.1.1` is the reproducibility successor to the immutable `v1.0.2` snapshot. It binds the public replication surface to SSRN v1.24 and adds deterministic publication-figure rendering and exhibit-level provenance. It does **not** change the frozen strategy rules, empirical return paths, inference results, or substantive conclusions.

The v1.1.1 release is public on GitHub and archived at Zenodo DOI `10.5281/zenodo.21935901`. The uploaded replication asset SHA-256 is `9385704df7ab7f054a0cbf626b3289ddf5bc8ee818ee096fb4323973a196654e`.

## Included

- frozen R and Python research code;
- public source metadata and input contracts;
- derived figure and table source data;
- deterministic publication renderer `03_Data_and_Code/02_Code/18_RENDER_PUBLICATION_EXHIBITS_v1_1_4.py`;
- 12 exact v1.24 publication figure renders in PNG and SVG;
- exact figure-render and source-data manifests;
- nonprivate scientific validation outputs;
- source and rights documentation;
- the current public working paper.

## Not redistributed

Downloaded raw Yahoo Finance or FRED market-data files, local runtime objects, private university material, proprietary research, third-party article files, credentials, and local session files are not redistributed.

## Exact-exhibit reproducibility

The v1.24 publication layer adds an explicit chain from frozen source data to deterministic rendering code to the final publication figure. The active map is `05_Practical_Paper/EXHIBIT_DATA_POINTERS_v1.1.4.csv`, and the exact render hashes are recorded in `05_Practical_Paper/03_Figures/EXACT_FIGURE_RENDER_MANIFEST_v1.1.4.csv`.

The working-paper binding is recorded in `06_Public_Metadata/PUBLICATION_TARGET_v1.1.1.csv`. The manuscript PDF itself remains a separate public artifact; its SHA-256 is used to make the version relationship explicit.

## Reproduction

The frozen workflow expects the local project root to be named exactly `05_ADAA`.

```bash
git clone https://github.com/slackquant80/adaa-decision-diversification 05_ADAA
cd 05_ADAA
```

Then follow `REPRODUCIBILITY.md`. A full mixed R/Python reproduction may take roughly 20–60 minutes depending on network access, package installation, and machine speed.

To regenerate the publication figures after the frozen source-data files are present:

```bash
python 03_Data_and_Code/02_Code/18_RENDER_PUBLICATION_EXHIBITS_v1_1_4.py
```

Compare the outputs with `05_Practical_Paper/03_Figures/EXACT_FIGURE_RENDER_MANIFEST_v1.1.4.csv`.

## Research boundary

This repository validates a retrospective historical research workflow. It is not a live track record, historical preregistration, or evidence that the current HAA / BAA / ADM / FAA / LAA implementation must remain optimal or effective indefinitely.

The broader ADAA principle is decision diversification inside a modular architecture whose components can be challenged or replaced.

## Data and rights

See `DATA_AND_RIGHTS.md` and the source metadata under `06_Public_Metadata/`.
