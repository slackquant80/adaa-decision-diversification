# ADAA Public Replication Package v1.1.3

**Status: VERSIONED RELEASE CANDIDATE / SSRN v1.28 FINAL-PUBLIC COMPANION / NO SCIENCE CHANGE.**

This package accompanies the working paper *Diversify the Decisions, Not Just the Assets: A Practical Architecture for Dynamic Asset Allocation When Strategy Choice Is Uncertain*.

Version v1.1.3 is a metadata-only paper-binding successor to public v1.1.2. It binds the unchanged replication payload to the final 25-page SSRN v1.28 manuscript after byte-for-byte live verification. The scientific workflow, empirical results, source data, tables, and all 12 publication figures are unchanged.

## Public resources

- Research dashboard: https://slackquant80.github.io/adaa-slackquant/
- Public replication repository: https://github.com/slackquant80/adaa-decision-diversification

The working-paper PDF is distributed separately. Its exact filename and SHA-256 binding are recorded in `06_Public_Metadata/PUBLICATION_TARGET_v1.1.3.csv`.

## What changed from v1.1.1

- paper binding advanced from SSRN v1.24 (26 pages) to the final house-reviewed SSRN v1.25 artifact (25 pages);
- current publication renderer advanced to `18_RENDER_PUBLICATION_EXHIBITS_v1_1_6.py`;
- active figure outputs use the v1.25 publication layer;
- Figure 7 uses the manuscript term `Longest underwater spell (months)`;
- Figure 8 explicitly separates stress-window cumulative return differences from the exploratory mean one-month rapid-reversal diagnostic;
- appendix display labels are synchronized to Figure A1/A2 and Figure B1/B2; frozen Z/FX source-data identifiers remain unchanged for provenance;
- Figure B2 threshold tick labels use the final house-paper formatting;
- release metadata, manifest, validation record, and paper-binding notes were updated.

## What is included

- frozen R and Python research code;
- public source metadata and input contracts;
- derived figure/table source data;
- deterministic publication renderer `18_RENDER_PUBLICATION_EXHIBITS_v1_1_6.py`;
- 12 active v1.25 publication figure renders in PNG and SVG;
- exact current render manifest and source-data hashes;
- nonprivate clean-run validation summaries;
- publication reconciliation and exhibit-to-source-data pointers;
- SHA-256 release manifest and validation records.

## What is deliberately not redistributed

- downloaded raw Yahoo Finance or FRED market data;
- locally retrieved runtime objects;
- the private June 2023 university project report binary;
- proprietary research files;
- third-party article PDFs;
- the working-paper PDF/DOCX itself;
- credentials, local session files, or private author notes.

Public scripts retrieve required public-market inputs locally. Redistribution rights for upstream market data are not assumed merely because the data are publicly accessible.

## Terminology and provenance

Frozen code and source-data filenames retain historical internal identifiers where changing them would weaken reproducibility. The public exhibit crosswalk in `05_Practical_Paper/EXHIBIT_DATA_POINTERS_v1.1.6.csv` maps those identifiers to the final paper's Figure A1/A2/B1/B2 labels. This is a presentation-layer synchronization only.

## Reproduction

1. Obtain or clone the repository.
2. For execution, use a local project root named `05_ADAA` because frozen workflow paths assume that project-root name.
3. Enter the `05_ADAA` root.
4. Follow `RUN_ORDER_v1.0.1.md` for the frozen scientific workflow.
5. Use `03_Data_and_Code/02_Code/18_RENDER_PUBLICATION_EXHIBITS_v1_1_6.py` to regenerate the current v1.25 publication figures from frozen source-data files.
6. Compare generated hashes with `05_Practical_Paper/03_Figures/EXACT_FIGURE_RENDER_MANIFEST_v1.1.6.csv`.
7. A full run may create local raw/runtime inputs. Do not republish them. Before redistributing a locally executed copy, purge restricted runtime inputs and rerun package validation.

## Release status

Version v1.1.3 is the metadata-only replication successor bound to the public final SSRN v1.28 manuscript artifact. Public v1.1.1 remains an immutable historical predecessor. This package intentionally does not pre-claim a downstream DOI; the DOI and public-release URLs are recorded by the external release services after publication, so the scientific payload does not need to be rebuilt.

This package validates reproducibility of a retrospective research workflow. It is not a live track record, not historical preregistration, and not evidence that the current HAA/BAA/ADM/FAA/LAA implementation must remain optimal or effective indefinitely.
