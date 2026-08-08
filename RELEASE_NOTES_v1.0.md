# ADAA Public Replication Package v1.0 - Release Notes

- Promoted the rights-safe release candidate to public v1.0 after a complete mixed R/Python clean run.
- Added sanitized release-validation summaries and automated publication reconciliation checks.
- Added canonical source data for the active full-2023 Strategy-Zoo and FX appendix figures.
- Removed the obsolete provisional Z1 source pointer and added `EXHIBIT_DATA_POINTERS_v1.0.csv`.
- Added a stricter validator that rejects raw/near-raw runtime market-data paths, including CSV artifacts inside `raw_freeze*` folders.
- Added an explicit post-run purge utility for users who need to redistribute a clean-run tree.
- Scientific content remains frozen; no strategy rule, universe, target-weight history, return path, sample, top-level weight, cost grid, benchmark or selector definition was changed for this release.
