# ADAA Public Replication Package v1.0.2

**Status: PUBLIC RELEASE / CLEAN-RUN SCIENCE VALIDATED / FINAL PUBLIC-LINK METADATA SYNCHRONIZED.**

This repository accompanies the working paper *Diversify the Decisions, Not Just the Assets: A Practical Architecture for Dynamic Asset Allocation When Strategy Choice Is Uncertain*.

Version v1.0.2 is a **metadata-only final-release patch** on top of v1.0.1. Frozen research code, source data, derived exhibits, figure renders, validation results, and scientific conclusions are unchanged. The patch updates the public paper title/version and records the final dashboard and replication-repository URLs used by paper v1.16.

## Public resources

- Research dashboard: https://slackquant80.github.io/adaa-slackquant/
- Public replication repository: https://github.com/slackquant80/adaa-decision-diversification

The paper itself is distributed separately as `ADAA_SSRN_Working_Paper_v1.16_FINAL_PUBLIC_RELEASE.pdf` and contains both links under **Data and Code Availability**.

## What is included

- frozen R and Python research code;
- public source metadata and input contracts;
- derived figure/table source data;
- **12 active final-paper figure renders** synchronized to the frozen paper exhibit state;
- the prior v1.0 figure renders under `05_Practical_Paper/03_Figures/Archive_v1.0/`;
- nonprivate clean-run validation summaries;
- publication reconciliation and exhibit-to-source-data pointers;
- SHA-256 manifests and strict public-package validators.

The v1.16 paper differs from v1.15 only by adding the two final public-resource hyperlinks. Its scientific text, tables, figures, and embedded figure media are otherwise unchanged; accordingly, the v1.15-named final figure renders retained in this package remain the exact exhibit renders used by v1.16.

## What is deliberately not redistributed

- downloaded raw Yahoo Finance market data;
- locally retrieved FRED/Yahoo runtime objects;
- the private June 2023 university project report binary;
- proprietary research files;
- third-party article PDFs;
- the working-paper PDF/DOCX itself;
- credentials, local session files or private author notes.

The scripts retrieve required public-market inputs locally. Redistribution rights for upstream market data are not assumed merely because the data are publicly accessible.

## Important terminology note

Frozen code retains historical internal identifiers such as `ADAA_historical_weights_canonical` for reproducibility. In the final paper, the corresponding public comparison is described as **practitioner weights** in tables/figures and as the **later practitioner weights** in prose. These labels refer to the same 25/15/17.5/17.5/25 return path; they are not the June 2023 five-family weights. See `05_Practical_Paper/PUBLICATION_LABEL_MAP_v1.0.1.csv`.

## Reproduction

1. Obtain or clone this repository.
2. **For execution, the local project root must be named exactly `05_ADAA`.** With Git, use `git clone https://github.com/slackquant80/adaa-decision-diversification 05_ADAA` or rename the local clone to `05_ADAA` before running the frozen workflow.
3. Enter the `05_ADAA` root.
4. Run `python 00_VALIDATE_PUBLIC_PACKAGE_v1_0_2.py`.
5. Follow `RUN_ORDER_v1.0.1.md` exactly. v1.0.2 does not change execution order or science.
6. A full run will create local raw/runtime inputs. **Do not republish those inputs.** If re-zipping after a completed run, execute `python 01_PURGE_LOCAL_RUNTIME_INPUTS_FOR_REDISTRIBUTION_v1_0.py --confirm` and rerun the v1.0.2 validator.

## Validation records

Clean-run scientific validation remains recorded under `03_Data_and_Code/03_Validation/Release_Clean_Run/`. Scientific/exhibit publication reconciliation remains the v1.0.1 record because v1.0.2 changes metadata only. Final paper-link reconciliation is documented in `PUBLICATION_RECONCILIATION_v1.0.2.md`.

This package validates reproducibility of a retrospective research workflow. It is not a live track record, not historical preregistration, and not evidence that the current HAA/BAA/ADM/FAA/LAA implementation must remain optimal or effective indefinitely.
