# Public Input Acquisition

Raw Yahoo/FRED data are intentionally not redistributed in this package.

Start a clean reproduction from the package root, whose folder name must be `05_ADAA` when running the legacy research scripts. Run `03_Data_and_Code/02_Code/00_RUN_G2_FREEZE_PREP_v0_8.R` first to retrieve/freeze the main public inputs. Later R freeze steps retrieve additional parent/zoo inputs as documented in `RUN_ORDER_v0.2.md`.

The retrieval scripts create raw-freeze directories under this folder. Those downloaded files are local reproduction inputs and are not part of the redistribution ZIP.
