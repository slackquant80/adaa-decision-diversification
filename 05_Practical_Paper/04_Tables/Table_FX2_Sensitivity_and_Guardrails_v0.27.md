# Appendix Table FX-2. Sensitivity and guardrails — v0.27

| Diagnostic | Result | Interpretation |
|---|---|---|
| Predeclared threshold grid | CAGR 12.22%–13.51%; corrected MDD -9.39% to -6.93% | Legacy -0.5/+2.0 is not the ex-post CAGR maximum; no threshold is reselected. |
| Threshold grid vs fixed 50% | 16/16 cells have higher CAGR; 14/16 have shallower MDD | Evidence is not confined to one threshold pair, but this is one historical sample. |
| Window sensitivity (756/1306/1827 days, common sample) | CAGR 12.45%–12.59%; MDD -6.93% to -6.93% | Long-horizon lookback result is not visibly knife-edge across the frozen window set. |
| Legacy dynamic vs fixed 50% (gross) | CAGR difference +1.26 pp; MDD difference +2.46 pp | Historical application evidence only; not a causal claim or a forward-hedging implementation study. |

> **Guardrail.** Historical thresholds have outcome-linked provenance. The sensitivity grid is used to diagnose fragility, not to promote a new best threshold.