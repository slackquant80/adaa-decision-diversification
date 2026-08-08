# Table 2 — Core Performance, Costs and Uncertainty

## Panel A — Observed performance and implementation costs

| Portfolio | Cost basis | CAGR | Volatility | Sharpe | Maximum drawdown | Annualized L1 turnover |
| --- | --- | --- | --- | --- | --- | --- |
| ADAA — equal 20% | Gross | 10.66% | 8.97% | 1.03 | -10.00% | 5.81 |
| ADAA — equal 20% | 25 bps one-way | 9.07% | 8.97% | 0.87 | -10.43% | 5.81 |
| ADAA — historical weights | Gross | 10.80% | 8.97% | 1.05 | -10.16% | 5.28 |
| ADAA — historical weights | 25 bps one-way | 9.36% | 8.97% | 0.90 | -10.58% | 5.28 |
| SPY | Gross | 11.68% | 15.73% | 0.70 | -41.80% | 0.00 |
| SPY | 25 bps one-way | 11.68% | 15.73% | 0.70 | -41.80% | 0.00 |
| 60/40 SPY/IEF | Gross | 8.44% | 9.72% | 0.75 | -25.06% | 0.22 |
| 60/40 SPY/IEF | 25 bps one-way | 8.38% | 9.71% | 0.75 | -25.10% | 0.22 |
| HAA — hindsight strongest sleeve | Gross | 12.97% | 10.70% | 1.07 | -9.97% | 6.34 |
| HAA — hindsight strongest sleeve | 25 bps one-way | 11.20% | 10.76% | 0.92 | -10.29% | 6.34 |

## Panel B — Dependence-aware uncertainty diagnostics

| Comparison | Basis | Annualized mean-return difference | HAC(12) p-value | Bootstrap P(mean return advantage) | Bootstrap P(Sharpe advantage) | Bootstrap P(MDD advantage) |
| --- | --- | --- | --- | --- | --- | --- |
| ADAA vs 60/40 | Gross | +2.10 pp | 0.205 | 91.0% | 95.2% | 97.2% |
| ADAA vs 60/40 | 25 bps | +0.83 pp | 0.623 | 67.5% | 78.2% | 95.9% |
| ADAA vs HAA hindsight winner | Gross | -2.12 pp | 0.057 | 2.3% | 38.5% | 86.4% |
| ADAA vs HAA hindsight winner | 25 bps | -1.85 pp | 0.111 | 5.0% | 41.4% | 84.3% |

**Interpretation.** Panel A reports the frozen ETF-only sample. Panel B deliberately separates observed performance from inferential strength. The 60/40 comparison is stronger for Sharpe and drawdown than for average return; HAA remains the hindsight full-sample winner, which the paper treats as an ex-post diagnostic rather than a fair ex-ante selector.
