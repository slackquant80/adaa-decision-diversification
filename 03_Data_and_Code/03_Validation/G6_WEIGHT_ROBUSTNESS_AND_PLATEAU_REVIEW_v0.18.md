# G6 Weight Robustness / Broad-Plateau Review — v0.18

Status: **SUPPORTIVE ROBUSTNESS EVIDENCE — NOT A RESELECTION GATE**

This analysis was performed after formal performance opening solely to test the author's previously stated design philosophy: ADAA was intended as a moderately optimized robust architecture, not a maximum-backtest portfolio.

## 1. Ex-post optimum is deliberately treated as a control

Under the historically relevant 10% minimum weight per sleeve, the full-sample gross maximum-Sharpe reference is approximately:

- HAA 50.5%
- BAA 10.0%
- ADM 10.0%
- FAA 10.0%
- LAA 19.5%

Gross BIL-excess Sharpe: **1.086**.

This vector is **not** a candidate replacement for ADAA. It is an ex-post diagnostic showing where the current sample's sharpest estimated point lies.

The historical successor allocation (25/15/17.5/17.5/25) has gross Sharpe **1.049**, or **96.6% of the ex-post maximum**. Equal 20% has Sharpe **1.034**, or **95.2% of the ex-post maximum**.

## 2. The feasible surface is not narrowly concentrated around one point

A deterministic 100,000-draw feasible simplex scan with a 10% sleeve floor shows:

- historical successor Sharpe percentile: **83.2nd**;
- equal-weight Sharpe percentile: **63.6th**;
- **40.3%** of feasible draws achieve at least **95% of the ex-post maximum Sharpe**;
- **7.84%** achieve at least **97.5%** of the ex-post maximum.

This supports a broad-plateau interpretation more than a knife-edge optimum interpretation.

It does **not** prove future robustness. It shows only that the historical sample does not require a uniquely precise top-level weight vector to obtain broadly similar risk-adjusted performance.

## 3. Local perturbations around the historical allocation are stable

10,000 deterministic local perturbations were generated within total L1 weight distance 0.20 of the historical successor allocation while retaining the 10% sleeve floor.

At the frozen 25 bps transaction-cost assumption, the 5th–95th percentile Sharpe range is approximately:

> **0.884 to 0.915**

The historical point itself is approximately 0.902 on the same accounting basis. Small-to-moderate weight perturbations therefore do not produce a cliff-like collapse in the observed sample.

## 4. Estimated optimal weights are unstable across samples

Across 159 rolling 60-month optimization windows:

- HAA optimal weight ranges from 10% to 60%;
- BAA ranges from 10% to 60%;
- LAA ranges from 10% to about 51.8%;
- ADM and FAA sit at the imposed 10% floor in these rolling in-window Sharpe optima.

The identity and magnitude of the high-weight sleeve therefore vary materially with the estimation window.

A 500-replication 12-month moving-block bootstrap shows similarly wide uncertainty:

- HAA 2.5%–97.5% optimal-weight interval: roughly 10%–60%;
- BAA: roughly 10%–43.6%;
- LAA: roughly 10%–57.2%.

This is estimation-instability evidence, not a claim about the true future optimum.

## 5. Chasing the rolling optimum is not clearly superior

A diagnostic 60-month rolling max-Sharpe top-level optimizer was allowed to update monthly from 2013-06 through 2026-07. It is not a canonical strategy and was created only after performance opening as an adversarial robustness control.

Gross:

- rolling optimizer: CAGR **10.96%**, Sharpe **1.041**, annualized gross L1 turnover **7.03**;
- fixed historical weights: CAGR **10.72%**, Sharpe **1.052**, turnover **5.33**;
- fixed equal weights: CAGR **10.59%**, Sharpe **1.035**, turnover **5.83**.

At 25 bps:

- rolling optimizer: CAGR **9.05%**, Sharpe **0.845**;
- fixed historical weights: CAGR **9.27%**, Sharpe **0.898**;
- fixed equal weights: CAGR **9.01%**, Sharpe **0.866**.

The rolling optimizer achieves slightly higher gross CAGR than the fixed historical allocation but lower gross Sharpe and materially higher turnover. After the frozen 25 bps cost, the fixed historical allocation has both higher CAGR and higher Sharpe in this common later-start sample.

This supports — but does not prove — the practical case against continuously chasing the estimated peak.

## 6. Current interpretation

The v0.18 evidence is consistent with the author's recollection:

> **The goal was not to identify the highest point in the backtest, but to operate in a broad region of reasonable outcomes while preserving decision diversification.**

The strongest empirical statement currently permitted is that the historical/current ADAA top-level allocation lies in a broad high-Sharpe region of the observed surface and is not highly sensitive to moderate perturbations, while optimized weights themselves are sample-sensitive.

The paper must not claim that this proves superior future performance.
