# Table 2. Core Performance, Costs and Dependence-Aware Uncertainty — v0.26

## Panel A. Core observed performance and implementation costs

| Portfolio | Basis | CAGR | Volatility | BIL-excess Sharpe | Maximum drawdown |
|---|---|---:|---:|---:|---:|
| ADAA — historical weights | Gross | **10.80%** | **8.97%** | **1.05** | **-10.34%** |
| ADAA — historical weights | 25 bps one-way | **9.36%** | **8.97%** | **0.90** | **-10.75%** |
| ADAA — equal 20% | Gross | 10.66% | 8.97% | 1.03 | -10.00% |
| ADAA — equal 20% | 25 bps one-way | 9.07% | 8.97% | 0.87 | -10.43% |
| HAA — hindsight strongest sleeve | Gross | 12.97% | 10.70% | 1.07 | -11.68% |
| HAA — hindsight strongest sleeve | 25 bps one-way | 11.20% | 10.76% | 0.92 | -12.30% |
| 60/40 SPY/IEF | Gross | 8.44% | 9.72% | 0.75 | -27.55% |
| 60/40 SPY/IEF | 25 bps one-way | 8.38% | 9.71% | 0.75 | -27.61% |
| SPY | Gross | 11.68% | 15.73% | 0.70 | -46.32% |

**Definition note:** v0.26 corrects the drawdown layer so initial invested wealth `W0=1` is a valid peak. Returns, CAGR, volatility, Sharpe, turnover and cost paths are unchanged.

## Panel B. Dependence-aware uncertainty diagnostics

| Comparison | Basis | Annualized mean-return difference | HAC(12) p-value | Bootstrap P(mean-return advantage) | Bootstrap P(Sharpe advantage) | Bootstrap P(MDD advantage) |
|---|---|---:|---:|---:|---:|---:|
| ADAA vs 60/40 | Gross | +2.10 pp | 0.205 | 91.0% | 95.2% | 97.3% |
| ADAA vs 60/40 | 25 bps | +0.83 pp | 0.623 | 67.5% | 78.2% | 96.0% |
| ADAA vs HAA hindsight winner | Gross | -2.12 pp | 0.057 | 2.3% | 38.5% | 86.5% |
| ADAA vs HAA hindsight winner | 25 bps | -1.85 pp | 0.111 | 5.0% | 41.4% | 84.3% |
