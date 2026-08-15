# ADAA Public Replication Run Order v1.0

**Release status: CLEAN-RUN VALIDATED. Follow this order without reselection or optimization.**


## Environment and expected runtime
Run from the package/project root renamed exactly to `05_ADAA` because the frozen scripts fail closed on another root name.

Recommended environment: Windows + R/RStudio and Python. The first data retrieval typically takes 3-10 minutes; later parent/Strategy-Zoo retrieval steps usually take several additional minutes. The full mixed R/Python chain can take roughly 20-60 minutes depending on network, package installation and machine speed. Yahoo retrieval can be silent for 1-2 minutes; investigate if a retrieval step produces no progress for more than about 10 minutes.

R packages used by the frozen pipeline include `quantmod`, `xts`, `zoo`, `digest`, and `quadprog` for the final independent minimum-variance validation.

## Phase 0 - package self-check
`python 00_VALIDATE_PUBLIC_PACKAGE_v1_0.py`

## Phase 1 - acquire and freeze public inputs (no headline performance)
In R, from the `05_ADAA` root:
`source("03_Data_and_Code/02_Code/00_RUN_G2_FREEZE_PREP_v0_8.R")`

## Phase 2 - decision-panel and target-weight reconstruction
1. `python 03_Data_and_Code/02_Code/independent_frozen_data_audit_v0_10.py`
2. R: `source("03_Data_and_Code/02_Code/01_EXPORT_G2_TARGET_WEIGHTS_ONLY_v0_11_1.R")`
3. `python 03_Data_and_Code/02_Code/build_independent_decision_panel_v0_11.py`
4. `python 03_Data_and_Code/02_Code/compare_r_python_target_weights_v0_11_1.py --project-root .`
5. `python 03_Data_and_Code/02_Code/analyze_decision_diversification_v0_12.py`
6. `python 03_Data_and_Code/02_Code/analyze_return_correlation_increment_v0_12.py`
7. `python 03_Data_and_Code/02_Code/audit_accounting_and_netting_v0_12.py`

## Phase 3 - source-parent / sleeve engineering audit
1. R: `source("03_Data_and_Code/02_Code/02_FREEZE_PARENT_SOURCE_UNIVERSE_v0_14.R")`
2. R: `source("03_Data_and_Code/02_Code/03_EXPORT_PARENT_DECISION_PANELS_AND_AUDIT_DATA_v0_15_1.R")`
3. `python 03_Data_and_Code/02_Code/compare_parent_decision_panels_independent_v0_15_1.py`
4. `python 03_Data_and_Code/02_Code/analyze_parent_variants_and_p3_v0_16.py`
5. R: `source("03_Data_and_Code/02_Code/04_EXPORT_G3_CANONICAL_FAA_ONLY_v0_16.R")`
6. `python 03_Data_and_Code/02_Code/compare_g3_canonical_faa_v0_16.py`

## Phase 4 - performance, costs, robustness, stress and drawdown
1. `python 03_Data_and_Code/02_Code/05_OPEN_G6_PERFORMANCE_EVIDENCE_v0_17.py`
2. R: `source("03_Data_and_Code/02_Code/05_VALIDATE_G6_PERFORMANCE_ENGINE_R_v0_17_1.R")`
3. `python 03_Data_and_Code/02_Code/compare_g6_r_python_performance_v0_18.py`
4. `python 03_Data_and_Code/02_Code/analyze_g6_rolling_robustness_v0_17.py`
5. `python 03_Data_and_Code/02_Code/analyze_weight_robustness_plateau_v0_18.py`
6. `python 03_Data_and_Code/02_Code/06_G6_INFERENCE_STRESS_BENCHMARKS_v0_19.py`
7. `python 03_Data_and_Code/02_Code/09_ANALYZE_DRAWDOWN_AND_COMPOUNDING_v0_26.py`
8. R: `source("03_Data_and_Code/02_Code/09_VALIDATE_DRAWDOWN_AND_COMPOUNDING_R_v0_26.R")`
9. `python 03_Data_and_Code/02_Code/10_G6_DRAWDOWN_CORRECTED_INFERENCE_v0_26.py`

## Phase 5 - KRW/USD currency-exposure appendix
1. R: `source("03_Data_and_Code/02_Code/07_EXPORT_FX_EXTENSION_AUDIT_v0_19.R")`
2. `python 03_Data_and_Code/02_Code/08_G3_FX_EXTENSION_EVALUATION_v0_20.py`
3. `python 03_Data_and_Code/02_Code/12_G3_FX_DRAWDOWN_CORRECTION_AND_APPENDIX_v0_27.py`

## Phase 6 - completed 2023 Strategy-Zoo structural challenge
1. `python 03_Data_and_Code/02_Code/09_DECISION_SPACE_SELECTOR_PILOT_v0_24.py`
2. `python 03_Data_and_Code/02_Code/11_REBUILD_STRATEGY_ZOO_COMMON_SUBSET_v0_27.py`
3. `python 03_Data_and_Code/02_Code/13_G5_UNIVERSE_RULE_ENGINEERING_v0_28.py`
4. `python 03_Data_and_Code/02_Code/14_REBUILD_STRATEGY_ZOO_EAA_POOL_A2_v0_29.py`
5. R: `source("03_Data_and_Code/02_Code/15_VALIDATE_EAA_AND_FREEZE_ZOO_INPUTS_R_v0_29.R")`
6. `python 03_Data_and_Code/02_Code/16_REBUILD_FULL_2023_STRATEGY_ZOO_v0_30.py`
7. R: `source("03_Data_and_Code/02_Code/17_VALIDATE_FULL_2023_STRATEGY_ZOO_R_v0_30.R")`

The final R validation must report PASS and must not calculate or use strategy performance for selection.

## Release gate after the local clean run
Reconcile regenerated headline metrics, tables and 11 active exhibits against the frozen public paper. Then rerun the package validator, scan generated content for raw/private files, and freeze the final redistribution manifest/checksum.