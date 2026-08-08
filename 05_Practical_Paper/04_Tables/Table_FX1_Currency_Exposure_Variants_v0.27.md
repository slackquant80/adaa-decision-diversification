# Appendix Table FX-1. Currency-exposure variants — v0.27

| Basis | Currency exposure | CAGR | Volatility | Zero-rate Sharpe | Max drawdown | Gain required to recover | Longest underwater run |
|---|---|---:|---:|---:|---:|---:|---:|
| Gross underlying | Hedged proxy | 10.80% | 8.97% | 1.19 | -10.34% | 11.53% | 18 |
| Gross underlying | Fixed 50% unhedged | 11.99% | 8.41% | 1.39 | -9.39% | 10.36% | 12 |
| Gross underlying | Fully unhedged | 12.79% | 11.57% | 1.10 | -14.32% | 16.71% | 12 |
| Gross underlying | Legacy dynamic 90/50/10 | 13.25% | 8.17% | 1.57 | -6.93% | 7.45% | 7 |
| 25 bp underlying cost | Hedged proxy | 9.36% | 8.97% | 1.05 | -10.75% | 12.05% | 23 |
| 25 bp underlying cost | Fixed 50% unhedged | 10.53% | 8.40% | 1.24 | -9.46% | 10.45% | 16 |
| 25 bp underlying cost | Fully unhedged | 11.32% | 11.56% | 0.99 | -14.49% | 16.95% | 16 |
| 25 bp underlying cost | Legacy dynamic 90/50/10 | 11.78% | 8.16% | 1.41 | -7.03% | 7.56% | 12 |

> **Interpretation limit.** “Hedged proxy” excludes forward/NDF carry, hedge transaction costs, collateral/funding, tax, and implementation frictions. The table is a currency-exposure illustration, not a complete executable KRW-hedged return study. Drawdown uses the v0.26/v0.27 standard definition with initial wealth W0=1 as a valid running peak.