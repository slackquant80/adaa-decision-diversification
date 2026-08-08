from __future__ import annotations

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '03_Data_and_Code' / '04_Outputs'
SRC = OUT / 'G6_ALL_MONTHLY_PATHS_FOR_INFERENCE_v0_19.csv'
LEGACY = OUT / 'G6_PRIMARY_PERFORMANCE_AND_COST_GRID_v0_17.csv'

TOL = 1e-12


def _month(x):
    return pd.PeriodIndex(x.astype(str), freq='M')


def standard_drawdown_series(r: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """End-of-month wealth and drawdown, with initial wealth W0=1 included as a valid peak."""
    x = r.astype(float).to_numpy()
    wealth = np.cumprod(1.0 + x)
    peak = np.maximum.accumulate(np.r_[1.0, wealth])[1:]
    dd = wealth / peak - 1.0
    return wealth, dd


def legacy_drawdown_series(r: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Legacy v0.17 implementation retained only for audit comparison."""
    x = r.astype(float).to_numpy()
    wealth = np.cumprod(1.0 + x)
    peak = np.maximum.accumulate(wealth)
    dd = wealth / peak - 1.0
    return wealth, dd


def drawdown_episodes(months: list[pd.Period], wealth: np.ndarray, dd: np.ndarray, portfolio: str, basis: str):
    # A drawdown episode is a consecutive run of month-end observations below the running peak.
    underwater = dd < -1e-14
    episodes = []
    i = 0
    ep = 0
    while i < len(dd):
        if not underwater[i]:
            i += 1
            continue
        start = i
        while i < len(dd) and underwater[i]:
            i += 1
        end = i - 1
        recovery_index = i if i < len(dd) else None
        trough_local = start + int(np.argmin(dd[start:end+1]))

        # peak observation immediately preceding the underwater run; if start==0 it is pre-sample W0=1.
        peak_month = 'PRE_SAMPLE_START' if start == 0 else str(months[start - 1])
        peak_value = 1.0 if start == 0 else float(wealth[start - 1])
        recovery_month = str(months[recovery_index]) if recovery_index is not None else 'NOT_RECOVERED'
        ep += 1
        episodes.append({
            'portfolio': portfolio,
            'basis': basis,
            'episode_id': ep,
            'peak_month': peak_month,
            'first_underwater_month': str(months[start]),
            'trough_month': str(months[trough_local]),
            'recovery_month': recovery_month,
            'underwater_months': int(end - start + 1),
            'months_peak_to_trough': int(trough_local - start + 1),
            'peak_value': peak_value,
            'trough_value': float(wealth[trough_local]),
            'episode_max_drawdown': float(dd[trough_local]),
            'recovery_return_required_at_trough': float(1.0 / (1.0 + dd[trough_local]) - 1.0),
            'drawdown_area_decimal_months': float(np.sum(-np.minimum(dd[start:end+1], 0.0))),
            'completed': recovery_index is not None,
        })
    return episodes


def diagnostics(g: pd.DataFrame, portfolio: str, basis: str, retcol: str):
    g = g.sort_values('holding_month').copy()
    months = list(_month(g['holding_month']))
    r = g[retcol].astype(float).reset_index(drop=True)
    wealth, dd = standard_drawdown_series(r)
    _, dd_legacy = legacy_drawdown_series(r)

    trough = int(np.argmin(dd))
    mdd = float(dd[trough])
    legacy_mdd = float(np.min(dd_legacy))
    underwater = dd < -1e-14
    eps = drawdown_episodes(months, wealth, dd, portfolio, basis)
    max_under = max((e['underwater_months'] for e in eps), default=0)
    completed = sum(bool(e['completed']) for e in eps)

    # Identify MDD episode.
    mdd_ep = min(eps, key=lambda e: e['episode_max_drawdown']) if eps else None
    n = len(r)
    cagr = float(wealth[-1] ** (12.0 / n) - 1.0)
    calmar = float(cagr / abs(mdd)) if mdd < 0 else np.nan
    pain = float(np.mean(-np.minimum(dd, 0.0)))
    ulcer = float(np.sqrt(np.mean(np.minimum(dd, 0.0) ** 2)))
    mean_under = float(np.mean(-dd[underwater])) if underwater.any() else 0.0

    return ({
        'portfolio': portfolio,
        'basis': basis,
        'months': n,
        'CAGR_unchanged': cagr,
        'standard_max_drawdown': mdd,
        'legacy_v0_17_style_max_drawdown': legacy_mdd,
        'MDD_correction_pp': (mdd - legacy_mdd) * 100.0,
        'standard_Calmar': calmar,
        'mdd_peak_month': mdd_ep['peak_month'] if mdd_ep else '',
        'mdd_trough_month': mdd_ep['trough_month'] if mdd_ep else '',
        'mdd_recovery_month': mdd_ep['recovery_month'] if mdd_ep else '',
        'mdd_underwater_months': mdd_ep['underwater_months'] if mdd_ep else 0,
        'mdd_months_peak_to_trough': mdd_ep['months_peak_to_trough'] if mdd_ep else 0,
        'recovery_return_required_from_MDD': float(1.0 / (1.0 + mdd) - 1.0) if mdd < 0 else 0.0,
        'fraction_months_underwater': float(np.mean(underwater)),
        'max_underwater_spell_months': int(max_under),
        'mean_drawdown_all_months': pain,
        'mean_drawdown_conditional_underwater': mean_under,
        'ulcer_index': ulcer,
        'drawdown_area_decimal_months': float(np.sum(-np.minimum(dd, 0.0))),
        'drawdown_episode_count': int(len(eps)),
        'completed_drawdown_episode_count': int(completed),
        'ending_growth_of_1_unchanged': float(wealth[-1]),
    }, eps)


def main():
    d = pd.read_csv(SRC)
    required = {'portfolio','holding_month','gross_return','net_return_25bps'}
    if not required.issubset(d.columns):
        raise RuntimeError(f'missing required columns: {sorted(required - set(d.columns))}')

    summary_rows = []
    episode_rows = []
    for portfolio, g in d.groupby('portfolio', sort=False):
        for basis, col in [('gross','gross_return'),('net25','net_return_25bps')]:
            s, eps = diagnostics(g, portfolio, basis, col)
            summary_rows.append(s)
            episode_rows.extend(eps)

    summary = pd.DataFrame(summary_rows)
    episodes = pd.DataFrame(episode_rows)
    summary.to_csv(OUT / 'G6_DRAWDOWN_COMPOUNDING_DIAGNOSTICS_v0_26.csv', index=False)
    episodes.to_csv(OUT / 'G6_DRAWDOWN_EPISODES_v0_26.csv', index=False)

    # Reconcile current v0.17 legacy MDD outputs where a direct label mapping exists.
    old = pd.read_csv(LEGACY)
    oldmap = {
        'ADAA_equal20_canonical':'ADAA_equal20',
        'ADAA_historical_weights_canonical':'ADAA_historical',
        'ADAA_equal_no_LAA_rescaled':'ADAA_no_LAA_rescaled',
        'ADAA_equal_RAA_replacement':'ADAA_equal_RAA_replacement',
        'ADAA_hist_RAA_replacement':'ADAA_hist_RAA_replacement',
        'Benchmark_60_40_SPY_IEF':'Benchmark_60_40_SPY_IEF',
        'Sleeve_HAA':'Sleeve_HAA','Sleeve_BAA':'Sleeve_BAA','Sleeve_ADM':'Sleeve_ADM',
        'Sleeve_FAA':'Sleeve_FAA','Sleeve_LAA':'Sleeve_LAA',
    }
    rec = []
    for _, row in old.iterrows():
        if row['portfolio'] not in oldmap or int(row['cost_bps']) not in (0,25):
            continue
        p = oldmap[row['portfolio']]
        basis = 'gross' if int(row['cost_bps']) == 0 else 'net25'
        hit = summary[(summary.portfolio == p) & (summary.basis == basis)]
        if len(hit) != 1:
            continue
        h = hit.iloc[0]
        rec.append({
            'legacy_portfolio_label':row['portfolio'],
            'canonical_path_label':p,
            'basis':basis,
            'legacy_reported_MDD':float(row['max_drawdown']),
            'legacy_recomputed_MDD':float(h['legacy_v0_17_style_max_drawdown']),
            'legacy_reproduction_abs_diff':abs(float(row['max_drawdown']) - float(h['legacy_v0_17_style_max_drawdown'])),
            'corrected_standard_MDD':float(h['standard_max_drawdown']),
            'corrected_minus_legacy_pp':(float(h['standard_max_drawdown']) - float(row['max_drawdown']))*100,
            'legacy_reported_max_TUW':int(row['max_time_under_water_months']),
            'corrected_max_underwater_spell_months':int(h['max_underwater_spell_months']),
            'legacy_Calmar':float(row['Calmar']),
            'corrected_standard_Calmar':float(h['standard_Calmar']),
        })
    reconciliation = pd.DataFrame(rec)
    reconciliation.to_csv(OUT / 'G6_DRAWDOWN_DEFINITION_RECONCILIATION_v0_26.csv', index=False)
    if len(reconciliation) and reconciliation['legacy_reproduction_abs_diff'].max() > TOL:
        raise RuntimeError('legacy drawdown reproduction failed')

    # Pure arithmetic recovery asymmetry table for book/practitioner explanation.
    losses = np.array([.05,.10,.20,.30,.40,.50,.60,.70,.80], dtype=float)
    recovery = pd.DataFrame({
        'loss_fraction': losses,
        'loss_percent': losses*100,
        'gain_required_to_recover_fraction': losses/(1-losses),
        'gain_required_to_recover_percent': losses/(1-losses)*100,
    })
    recovery.to_csv(OUT / 'BOOK_DRAWDOWN_RECOVERY_ASYMMETRY_v0_26.csv', index=False)

    # Publication-facing compact table (labels deliberately plain-English).
    primary = [
        ('ADAA historical','ADAA_historical'),
        ('ADAA equal 20%','ADAA_equal20'),
        ('HAA hindsight strongest sleeve','Sleeve_HAA'),
        ('60/40 SPY/IEF','Benchmark_60_40_SPY_IEF'),
        ('SPY','Benchmark_SPY'),
    ]
    pub_rows=[]
    for label,p in primary:
        for basis in ['gross','net25']:
            h=summary[(summary.portfolio==p)&(summary.basis==basis)]
            if len(h)!=1: continue
            z=h.iloc[0]
            pub_rows.append({
                'portfolio':label,'basis':basis,
                'MDD':z.standard_max_drawdown,
                'recovery_gain_required_from_MDD':z.recovery_return_required_from_MDD,
                'max_underwater_months':z.max_underwater_spell_months,
                'fraction_months_underwater':z.fraction_months_underwater,
                'mean_drawdown_all_months':z.mean_drawdown_all_months,
                'ulcer_index':z.ulcer_index,
                'MDD_trough_month':z.mdd_trough_month,
                'MDD_recovery_month':z.mdd_recovery_month,
            })
    pd.DataFrame(pub_rows).to_csv(OUT / 'G6_PUBLIC_DRAWDOWN_ANATOMY_TABLE_v0_26.csv', index=False)

    record = {
        'version':'v0.26',
        'status':'PYTHON_ANALYSIS_PASS_R_INDEPENDENT_VALIDATION_PENDING',
        'definition':'Drawdown is measured from running portfolio wealth peak with pre-sample initial wealth W0=1 included as a valid peak.',
        'legacy_issue':'v0.17/Python and R engines initialized running peak at first end-of-month wealth, which can omit a drawdown from initial capital when the sample starts with losses.',
        'return_path_changes':'NONE',
        'strategy_rule_changes':'NONE',
        'sample_changes':'NONE',
        'impacted_public_metrics':['maximum drawdown','Calmar','maximum time under water / underwater spell'],
        'unimpacted_public_metrics':['monthly returns','CAGR','volatility','BIL-excess Sharpe','turnover','cost paths','stress-window cumulative returns'],
        'legacy_reproduction_max_abs_diff':float(reconciliation.legacy_reproduction_abs_diff.max()) if len(reconciliation) else None,
        'primary_gross':{},
    }
    for label,p in primary:
        h=summary[(summary.portfolio==p)&(summary.basis=='gross')]
        if len(h)==1:
            z=h.iloc[0]
            record['primary_gross'][label]={
                'MDD':float(z.standard_max_drawdown),
                'recovery_required':float(z.recovery_return_required_from_MDD),
                'max_underwater_months':int(z.max_underwater_spell_months),
                'fraction_underwater':float(z.fraction_months_underwater),
                'ulcer_index':float(z.ulcer_index),
            }
    (OUT / 'G6_DRAWDOWN_COMPOUNDING_RECORD_v0_26.json').write_text(json.dumps(record, indent=2), encoding='utf-8')

    print('PASS: v0.26 drawdown/compounding diagnostics generated.')
    print(f'Legacy MDD reproduction max abs diff: {record["legacy_reproduction_max_abs_diff"]:.3e}')
    print('IMPORTANT: standard MDD now includes initial wealth W0=1 as a valid running peak.')
    print('No returns, strategies, weights, samples, costs or selection rules were changed.')

if __name__ == '__main__':
    main()
