# ADAA Public Replication Package v1.0.1

**Status: PUBLIC RELEASE CANDIDATE / CLEAN-RUN SCIENCE VALIDATED / PAPER-v1.15 PUBLICATION-SYNC VALIDATED.**

This repository accompanies the working paper *Diversify the Decisions, Not Just the Assets: Autonomous Dynamic Asset Allocation as a Practical Multi-Rule Framework*.

Version v1.0.1 is a publication-synchronization patch to the clean-run validated v1.0 package. The frozen research code and scientific results are unchanged. The patch aligns the public exhibit set and presentation labels with working paper v1.15.

## What is included

- frozen R and Python research code;
- public source metadata and input contracts;
- derived figure/table source data;
- **12 active final-paper figure renders synchronized to paper v1.15**;
- the prior v1.0 figure renders under `05_Practical_Paper/03_Figures/Archive_v1.0/`;
- nonprivate clean-run validation summaries;
- publication reconciliation and exhibit-to-source-data pointers;
- SHA-256 manifest and a strict public-package validator.

## What is deliberately not redistributed

- downloaded raw Yahoo Finance market data;
- locally retrieved FRED/Yahoo runtime objects;
- the private June 2023 university project report binary;
- proprietary research files;
- third-party article PDFs;
- the working-paper PDF/DOCX itself (its expected v1.15 hashes are recorded, but the paper is distributed separately);
- credentials, local session files or private author notes.

The scripts retrieve the required public-market inputs locally. Redistribution rights for upstream market data are not assumed merely because the data are publicly accessible.

## Important terminology note

Frozen code retains historical internal identifiers such as `ADAA_historical_weights_canonical` for reproducibility. In paper v1.15 the corresponding public comparison is described as **practitioner weights** in tables/figures and as the **later practitioner weights** in prose. These labels refer to the same 25/15/17.5/17.5/25 return path; they are not the June 2023 five-family weights. See `05_Practical_Paper/PUBLICATION_LABEL_MAP_v1.0.1.csv`.

## Reproduction

1. Obtain or clone this repository.
2. **For execution, the local project root must be named exactly `05_ADAA`.** With Git, either use `git clone <repository-url> 05_ADAA` or rename the local clone to `05_ADAA` before running the frozen workflow.
3. Enter the `05_ADAA` root.
4. Run `python 00_VALIDATE_PUBLIC_PACKAGE_v1_0_1.py`.
5. Follow `RUN_ORDER_v1.0.1.md` exactly. The workflow intentionally keeps structural selection gates performance-blind until the prescribed performance-opening stage.
6. A full run will create local raw/runtime inputs. **Do not republish those inputs.** If re-zipping after a completed run, execute `python 01_PURGE_LOCAL_RUNTIME_INPUTS_FOR_REDISTRIBUTION_v1_0.py --confirm` and rerun the v1.0.1 validator.

## Validation records

Clean-run scientific validation remains recorded under `03_Data_and_Code/03_Validation/Release_Clean_Run/`. The v1.0.1 publication-sync reconciliation is:

- `PUBLICATION_RECONCILIATION_v1.0.1.md`
- `PUBLICATION_RECONCILIATION_CHECKS_v1.0.1.csv`

The package validates reproducibility of a retrospective research workflow. It is not a live track record, not historical preregistration, and not evidence that the current HAA/BAA/ADM/FAA/LAA implementation must remain optimal or effective indefinitely.
