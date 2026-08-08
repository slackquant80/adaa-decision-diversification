# G6 Dependence-Aware Inference / Stress / Benchmark Review — v0.19

Status: **SUPPORTIVE BUT MIXED — CLAIMS MUST REMAIN PRACTITIONER-SCALED**

No strategy rule, universe, sample, cost grid, or top-level weight was reselected in v0.19. The v0.19 reconstruction of ADAA equal-weight, historical-weight and 60/40 monthly paths matches the already R↔Python-reconciled v0.17 paths to below 1e-12.

## 1. Dependence-aware inference

Primary uncertainty analysis uses a circular moving-block bootstrap with a 12-month block, 10,000 replications, and 6/12/24-month block-length sensitivity. Mean-return differences are also checked with Newey-West HAC lags 6 and 12.

### Historical ADAA vs 60/40 SPY/IEF

Gross observed differences favor ADAA on risk-adjusted and drawdown dimensions, but the mean-return advantage is not conventionally statistically precise:

- HAC(12) annualized mean-return difference: **2.10%**, two-sided p **0.205**;
- 12-month-block bootstrap probability that annualized mean difference is positive: **91.0%**;
- bootstrap Sharpe-difference median: **0.282**, 95% interval **[-0.053, 0.573]**, probability positive **95.2%**;
- probability that ADAA has the shallower bootstrap MDD: **97.2%**.

At the deliberately harsh frozen 25 bps one-way cost assumption, evidence narrows materially:

- HAC(12) annualized mean-return difference: **0.83%**, p **0.623**;
- bootstrap probability positive mean difference: **67.5%**;
- bootstrap probability positive Sharpe difference: **78.2%**.

Therefore the paper may say that the observed ETF-only sample shows a materially better drawdown/risk-adjusted profile than the primary static 60/40 benchmark, while dependence-aware uncertainty is too wide to claim a precisely estimated mean-return premium. Trading costs meaningfully weaken the superiority claim and must remain visible.

### Historical ADAA vs SPY

SPY has the higher observed CAGR/mean return. ADAA's case is risk control, not equity-return dominance. Gross bootstrap probability of a positive Sharpe difference is **97.3%**, while the annualized mean-return difference is negative in the observed sample. ADAA has lower volatility in essentially all bootstrap replications and a shallower MDD in essentially all replications. Do not claim ADAA beats equities on return.

### Historical ADAA vs HAA

HAA is the ex-post strongest constituent. ADAA's annualized mean return is lower; HAC(12) p is **0.057** and only **38.5%** of block-bootstrap replications favor ADAA on Sharpe. ADAA is consistently lower-volatility. This reinforces the intended argument: the ensemble is not designed to beat the hindsight winner.

### LAA / persistence control

Removing LAA and rescaling the four dynamic sleeves leaves gross mean return essentially unchanged, while ADAA-with-LAA has a positive Sharpe difference in **81.4%** of gross bootstrap replications and **96.7%** at 25 bps. The MDD advantage is not supported. The evidence therefore supports **persistence / lower turnover / lower volatility / cost-aware behavior**, not a generic claim that LAA reduces drawdowns.

Replacing LAA with RAA tends to reduce volatility and drawdown further; the Sharpe ordering is not decisive. This supports the broader claim that the choice of slow/quasi-static anchor changes portfolio geometry, rather than a claim that LAA is uniquely optimal.

## 2. External benchmark family

The pre-defined simple benchmark family is SPY, 60/40 SPY/IEF, 60/40 VTI/BND, 60/40 SPY/AGG and BIL. No benchmark was added or removed after seeing results.

Gross primary-window results:

| Portfolio | CAGR | Vol | BIL-excess Sharpe | MDD |
|---|---:|---:|---:|---:|
| ADAA historical | 10.80% | 8.97% | 1.05 | -10.16% |
| SPY | 11.68% | 15.73% | 0.70 | -41.80% |
| 60/40 SPY/IEF | 8.44% | 9.72% | 0.75 | -25.06% |
| 60/40 VTI/BND | 8.29% | 10.40% | 0.70 | -26.77% |
| 60/40 SPY/AGG | 8.34% | 10.11% | 0.72 | -26.54% |

The benchmark conclusion is not sensitive to which ordinary 60/40 implementation is used, although precise inference varies with costs and block length.

## 3. Stress and failure evidence

Predeclared named windows were fixed before the analysis: sample-onset GFC, 2011 Euro/US downgrade stress, 2018 Q4, COVID crash, COVID rebound and 2022 stock-bond stress. Data-defined worst 1/3/12-month windows for SPY, 60/40 and ADAA are reported separately to avoid relying only on hand-picked episodes.

| Episode | ADAA historical gross | 60/40 gross | SPY gross |
|---|---:|---:|---:|
| GFC sample onset | -4.45% | -22.97% | -41.85% |
| 2011 | -1.97% | 0.26% | -7.08% |
| 2018 Q4 | -3.59% | -6.74% | -13.53% |
| COVID crash | -3.92% | -9.35% | -19.42% |
| COVID rebound | 21.26% | 20.92% | 36.12% |
| 2022 stock-bond stress | -6.92% | -17.09% | -17.74% |

Key failure findings:

1. ADAA materially limited losses relative to 60/40 in the sample-onset GFC, 2018 Q4, COVID crash and 2022 stock-bond stress.
2. ADAA did **not** dominate in every stress episode: in the fixed 2011 window it lost about 2% while 60/40 was roughly flat.
3. The slow LAA sleeve was a major drag in 2022 (about **-19.6%** gross) while HAA/BAA were much more defensive. Persistence is therefore not synonymous with downside protection.
4. Among the ten worst one-month ADAA active returns versus 60/40, **7/10** occur in months where SPY rises more than 3% after a negative prior three-month SPY return. This identifies **rapid reversal / re-entry lag** as an important empirical failure mode of momentum-heavy dynamic allocation.
5. All five sleeves never changed simultaneously in any of the predeclared named stress windows. Stress performance therefore cannot be reduced to a story of complete decision synchronization.

## 4. Claim discipline

Allowed wording after v0.19:

- decision diversification is real and measurable in the frozen architecture;
- ADAA's observed sample has substantially shallower drawdowns than simple equity/60-40 benchmarks;
- risk-adjusted evidence is supportive, especially gross, but uncertainty is meaningful and costs weaken the result;
- the ensemble does not beat the hindsight-best rule and is not designed to;
- rapid reversals are a recurring relative weakness;
- a slow anchor changes turnover/volatility/cost behavior but is not guaranteed to improve MDD.

Not allowed:

- statistically proven return alpha;
- guaranteed future generalization;
- “ADAA always protects in crises”;
- “LAA reduces drawdowns” as a general claim;
- “ADAA beats the best constituent”;
- any selection of a benchmark, block length, cost, FX threshold, or stress window because it makes ADAA look better.
