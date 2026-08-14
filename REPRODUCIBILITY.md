# ADAA Reproducibility Guide

Run the frozen workflow from a local project root named exactly `05_ADAA`. Recommended environment: Windows with R/RStudio and Python. A complete run may take roughly 20–60 minutes.

R packages used by the frozen workflow include `quantmod`, `xts`, `zoo`, `digest`, and `quadprog`.

## 1. Acquire public inputs

```r
source("03_Data_and_Code/02_Code/00_RUN_G2_FREEZE_PREP_v0_8.R")
```

## 2. Reconstruct decision panels and target weights

```bash
python 03_Data_and_Code/02_Code/independent_frozen_data_audit_v0_10.py
```

```r
source("03_Data_and_Code/02_Code/01_EXPORT_G2_TARGET_WEIGHTS_ONLY_v0_11_1.R")
```

```bash
python 03_Data_and_Code/02_Code/build_independent_decision_panel_v0_11.py
python 03_Data_and_Code/02_Code/compare_r_python_target_weights_v0_11_1.py --project-root .
python 03_Data_and_Code/02_Code/analyze_decision_diversification_v0_12.py
python 03_Data_and_Code/02_Code/analyze_return_correlation_increment_v0_12.py
python 03_Data_and_Code/02_Code/audit_accounting_and_netting_v0_12.py
```

## 3. Source-parent and sleeve-engineering audit

```r
source("03_Data_and_Code/02_Code/02_FREEZE_PARENT_SOURCE_UNIVERSE_v0_14.R")
source("03_Data_and_Code/02_Code/03_EXPORT_PARENT_DECISION_PANELS_AND_AUDIT_DATA_v0_15_1.R")
```

```bash
python 03_Data_and_Code/02_Code/compare_parent_decision_panels_independent_v0_15_1.py
python 03_Data_and_Code/02_Code/analyze_parent_variants_and_p3_v0_16.py
```

```r
source("03_Data_and_Code/02_Code/04_EXPORT_G3_CANONICAL_FAA_ONLY_v0_16.R")
```

```bash
python 03_Data_and_Code/02_Code/compare_g3_canonical_faa_v0_16.py
```

## 4. Performance, costs, robustness, stress, and drawdown

```bash
python 03_Data_and_Code/02_Code/05_OPEN_G6_PERFORMANCE_EVIDENCE_v0_17.py
```

```r
source("03_Data_and_Code/02_Code/05_VALIDATE_G6_PERFORMANCE_ENGINE_R_v0_17_1.R")
```

```bash
python 03_Data_and_Code/02_Code/compare_g6_r_python_performance_v0_18.py
python 03_Data_and_Code/02_Code/analyze_g6_rolling_robustness_v0_17_1.py
python 03_Data_and_Code/02_Code/analyze_weight_robustness_plateau_v0_18_1.py
python 03_Data_and_Code/02_Code/06_G6_INFERENCE_STRESS_BENCHMARKS_v0_19.py
python 03_Data_and_Code/02_Code/09_ANALYZE_DRAWDOWN_AND_COMPOUNDING_v0_26.py
```

```r
source("03_Data_and_Code/02_Code/09_VALIDATE_DRAWDOWN_AND_COMPOUNDING_R_v0_26.R")
```

```bash
python 03_Data_and_Code/02_Code/10_G6_DRAWDOWN_CORRECTED_INFERENCE_v0_26.py
```

### Secondary hardening note

The `v0.17.1` and `v0.18.1` scripts are successor diagnostics on the current `main` branch. They do not alter the frozen Foundation headline science or the archived `v1.0.2` release. `v0.17.1` fails closed if a non-zero target weight would use a missing holding-period return. `v0.18.1` also corrects secondary weight-robustness MDD fields to the canonical `W0=1` drawdown convention already used by the paper-level drawdown analysis. Historical `v0.17`/`v0.18` scripts remain in the repository for provenance.

## 5. USD/KRW appendix

```r
source("03_Data_and_Code/02_Code/07_EXPORT_FX_EXTENSION_AUDIT_v0_19.R")
```

```bash
python 03_Data_and_Code/02_Code/08_G3_FX_EXTENSION_EVALUATION_v0_20.py
python 03_Data_and_Code/02_Code/12_G3_FX_DRAWDOWN_CORRECTION_AND_APPENDIX_v0_27.py
```

## 6. 2023 Strategy-Zoo structural challenge

```bash
python 03_Data_and_Code/02_Code/09_DECISION_SPACE_SELECTOR_PILOT_v0_24.py
python 03_Data_and_Code/02_Code/11_REBUILD_STRATEGY_ZOO_COMMON_SUBSET_v0_27.py
python 03_Data_and_Code/02_Code/13_G5_UNIVERSE_RULE_ENGINEERING_v0_28.py
python 03_Data_and_Code/02_Code/14_REBUILD_STRATEGY_ZOO_EAA_POOL_A2_v0_29.py
```

```r
source("03_Data_and_Code/02_Code/15_VALIDATE_EAA_AND_FREEZE_ZOO_INPUTS_R_v0_29.R")
```

```bash
python 03_Data_and_Code/02_Code/16_REBUILD_FULL_2023_STRATEGY_ZOO_v0_30.py
```

```r
source("03_Data_and_Code/02_Code/17_VALIDATE_FULL_2023_STRATEGY_ZOO_R_v0_30.R")
```

The final independent validation should report PASS and should not use strategy performance for Strategy-Zoo selection.

## 7. Regenerate the exact v1.24 publication exhibits

After the frozen source-data files are present, run:

```bash
python 03_Data_and_Code/02_Code/18_RENDER_PUBLICATION_EXHIBITS_v1_1_4.py
```

The active source-to-render map is `05_Practical_Paper/EXHIBIT_DATA_POINTERS_v1.1.4.csv`. Compare the regenerated PNG/SVG hashes with `05_Practical_Paper/03_Figures/EXACT_FIGURE_RENDER_MANIFEST_v1.1.4.csv`. The exact manuscript binding is recorded separately in `06_Public_Metadata/PUBLICATION_TARGET_v1.1.1.csv`.

Nonprivate validation outputs are retained under `03_Data_and_Code/03_Validation/Release_Clean_Run/`.

This workflow is retrospective. Reproduction does not convert the study into a live or prospective out-of-sample track record.
