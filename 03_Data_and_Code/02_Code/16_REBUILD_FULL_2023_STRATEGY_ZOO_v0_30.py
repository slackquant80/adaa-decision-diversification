#!/usr/bin/env python3
"""ADAA v0.30 — complete the historical 2023 Strategy Zoo, performance-blind.

Purpose
-------
Reconstruct the four remaining DB2022 operational strategies used in the user's 2023
candidate universe (DM, AAA, PAA, KDA) from frozen adjusted prices, combine them with the
12 already-frozen source/operational strategy rules, and rerun the *unchanged* v0.29
Decision-Space selector across the full 16-rule historical pool.

CRITICAL RESEARCH BOUNDARY
--------------------------
This script deliberately NEVER reads strategy returns, CAGR, Sharpe, drawdown, cost,
or any portfolio-performance output. It reads only frozen adjusted prices and frozen
target-weight files. The selector objective remains exactly the v0.29 return-free rule:
mean pairwise distance across (i) normalized target-weight L1, (ii) holdings disagreement,
and (iii) transition-timing disagreement, with equal component weights.

Operational specification basis
-------------------------------
The four new reconstructions follow the DB Financial Investment (2022) operational recipes
that were the working source used in the user's 2023 project. They are therefore labelled
DB2022 operational variants rather than claimed as unique canonical implementations of the
underlying published strategies.

- DM: 240-trading-day relative/absolute ranking of SPY, VEU, BIL; if BIL wins, hold AGG.
- AAA: 10-asset universe; top five by 120-trading-day momentum; long-only minimum-variance
  allocation from the last 60 daily log returns.
- PAA: 12 risky assets; 240-day SMA breadth; Top 6; protection parameter a=2; IEF defense.
- KDA: 10 investable assets + VWO/BND canaries; 13612F; top-five positive momentum;
  weighted multi-horizon correlation + one-month volatility long-only min-variance;
  canary-based 0/50/100% crash-protection allocation to IEF or cash.
"""
from pathlib import Path
import itertools
import json
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '03_Data_and_Code' / '04_Outputs'
BASE_DAILY = OUT / 'G5_FROZEN_ADJUSTED_DAILY_LONG_R_v0_15.csv'
EXACT_DAILY = ROOT / '03_Data_and_Code' / '01_Data' / 'raw_freeze_strategy_zoo_v0_29' / 'STRATEGY_ZOO_MISSING_ETF_ADJUSTED_DAILY_v0_29.csv'
MONTH_START = '2008-07'
MONTH_END = '2026-06'
TOL = 1e-10

# Existing 12-rule Pool A-2, unchanged from v0.29.
EXISTING = {
    'BAA_Aggressive': 'G5_BAA_AGGRESSIVE_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
    'BAA_Balanced': 'G5_BAA_BALANCED_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
    'ADM': 'G5_ADM_PARENT_VINEX_TARGET_WEIGHTS_R_v0_15.csv',
    'FAA': 'G5_FAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
    'LAA': 'G5_LAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
    'RAA': 'G5_RAA_PARENT_COMPARATOR_TARGET_WEIGHTS_R_v0_15.csv',
    'GTAA': 'G4_ZOO_GTAA_TARGET_WEIGHTS_DB2022_FROZEN_v0_27.csv',
    'QSF': 'G4_ZOO_QSF_TARGET_WEIGHTS_DB2022_FROZEN_v0_27.csv',
    'GPM': 'G4_ZOO_GPM_TARGET_WEIGHTS_DB2022_FROZEN_v0_27.csv',
    'VAA': 'G4_ZOO_VAA_TARGET_WEIGHTS_DB2022_FROZEN_v0_27.csv',
    'DAA': 'G4_ZOO_DAA_TARGET_WEIGHTS_DB2022_FROZEN_v0_27.csv',
    'EAA': 'G4_ZOO_EAA_TARGET_WEIGHTS_IKTRADING_V1_SOURCEFAITHFUL_v0_29.csv',
}

# Same economic-bucket convention as v0.29, extended only for the exact newly frozen inputs.
# The distinction between VEU (broad ex-US incl. emerging markets) and EFA/VEA (developed ex-US)
# is deliberately retained rather than collapsed for convenience.
BUCKET = {
    'SPY':'US_BROAD_EQ','VTI':'US_BROAD_EQ','VFINX':'US_BROAD_EQ',
    'QQQ':'US_TECH_EQ','IWM':'US_SMALL_EQ','IWN':'US_SMALL_VALUE_EQ','IWD':'US_VALUE_EQ',
    'EFA':'DEV_EXUS_EQ','VEA':'DEV_EXUS_EQ','VGK':'EUROPE_EQ','EWJ':'JAPAN_EQ',
    'EEM':'EM_EQ','VWO':'EM_EQ','VEU':'GLOBAL_EXUS_EQ',
    'VINEX':'EXUS_SMALL_EQ','VSS':'EXUS_SMALL_EQ','OSMAX':'EXUS_SMALL_EQ',
    'VNQ':'US_REIT','IYR':'US_REIT','RWX':'INTL_REIT',
    'GLD':'GOLD','DBC':'COMMODITY','GSG':'COMMODITY',
    'HYG':'HY_BOND','LQD':'IG_CORP_BOND','TLT':'LONG_TSY','VUSTX':'LONG_TSY',
    'IEF':'INTERMEDIATE_TSY','SHY':'SHORT_TSY','BIL':'TBILL','AGG':'AGG_BOND','BND':'AGG_BOND',
    'TIP':'TIPS','CASH':'CASH'
}


def load_daily():
    base = pd.read_csv(BASE_DAILY, parse_dates=['date'])[['date','symbol','adjusted']]
    exact = pd.read_csv(EXACT_DAILY, parse_dates=['date'])[['date','symbol','adjusted']]
    if exact['symbol'].nunique() != 3 or set(exact['symbol']) != {'VEU','RWX','IYR'}:
        raise RuntimeError('Unexpected exact-input symbol set.')
    if exact['adjusted'].isna().any():
        raise RuntimeError('Exact-input freeze contains missing adjusted prices.')
    # Reject conflicting duplicate observations before pivoting.
    d = pd.concat([base, exact], ignore_index=True)
    dup = d.duplicated(['date','symbol'], keep=False)
    if dup.any():
        g = d.loc[dup].groupby(['date','symbol'])['adjusted'].agg(['min','max'])
        if ((g['max']-g['min']).abs() > 1e-12).any():
            raise RuntimeError('Conflicting duplicate frozen adjusted prices detected.')
        d = d.drop_duplicates(['date','symbol'], keep='first')
    p = d.pivot(index='date', columns='symbol', values='adjusted').sort_index()
    return p


def month_end_dates(index):
    s = pd.Series(index=index, data=np.arange(len(index)))
    return s.groupby(index.to_period('M')).tail(1).index


def month_end_frame(df):
    dates = month_end_dates(df.index)
    z = df.loc[dates].copy()
    z.index = z.index.to_period('M').astype(str)
    z.index.name = 'signal_month'
    return z


def finalize_monthly(w):
    w = w.copy()
    if isinstance(w.index, pd.DatetimeIndex):
        w = month_end_frame(w)
    else:
        w.index = w.index.astype(str)
        w.index.name = 'signal_month'
    w = w.loc[(w.index >= MONTH_START) & (w.index <= MONTH_END)].copy()
    w = w.fillna(0.0)
    sums = w.sum(axis=1)
    if ((sums - 1.0).abs() > 1e-8).any():
        bad = w.loc[(sums-1.0).abs() > 1e-8].head()
        raise RuntimeError(f'Weight sums not one. First failures:\n{bad}')
    return w


def long_only_minvar(cov, labels, tol=1e-11):
    """Exact small-N active-set enumeration for long-only fully-invested GMV.

    Any optimum of the convex long-only GMV problem has an active support on which the
    unrestricted fully-invested GMV solution is positive. Enumerating all non-empty supports
    (N<=5 in these rules) therefore gives a deterministic solver independent of R packages.
    """
    cov = np.asarray(cov, dtype=float)
    n = cov.shape[0]
    if cov.shape != (n,n) or not np.isfinite(cov).all():
        raise RuntimeError('Non-finite covariance matrix in min-var solver.')
    cov = (cov + cov.T) / 2.0
    best = None
    one_full = np.ones(n)
    for mask in range(1, 1 << n):
        idx = [i for i in range(n) if mask & (1 << i)]
        S = cov[np.ix_(idx, idx)]
        one = np.ones(len(idx))
        try:
            x = np.linalg.solve(S, one)
        except np.linalg.LinAlgError:
            # A Moore-Penrose candidate is allowed only if the KKT residual is tiny.
            x = np.linalg.pinv(S, rcond=1e-12) @ one
        den = float(one @ x)
        if not np.isfinite(den) or den <= 0:
            continue
        ws = x / den
        if np.min(ws) < -tol:
            continue
        ws = np.where(ws < 0, 0.0, ws)
        if ws.sum() <= 0:
            continue
        ws = ws / ws.sum()
        w = np.zeros(n)
        w[idx] = ws
        var = float(w @ cov @ w)
        # Check inactive KKT gradient condition for true constrained optimum.
        grad = cov @ w
        lam = float(np.mean(grad[np.array(idx)]))
        inactive = [i for i in range(n) if i not in idx]
        if inactive and np.min(grad[inactive] - lam) < -1e-8:
            continue
        cand = (var, len(idx), tuple(idx), w)
        if best is None or cand[:3] < best[:3]:
            best = cand
    if best is None:
        raise RuntimeError('No feasible long-only min-variance solution found.')
    return pd.Series(best[3], index=labels, dtype=float)


def dm_weights(p):
    assets = ['SPY','VEU','BIL','AGG']
    x = p[assets].copy()
    score = x[['SPY','VEU','BIL']] / x[['SPY','VEU','BIL']].shift(240) - 1.0
    me = month_end_dates(x.index)
    rows=[]
    for dt in me:
        r = score.loc[dt]
        o = pd.Series(0.0, index=assets)
        if r.notna().all():
            win = r.sort_values(ascending=False, kind='mergesort').index[0]
            if win == 'BIL':
                o['AGG'] = 1.0
            else:
                o[win] = 1.0
        else:
            o[:] = np.nan
        o.name = dt.to_period('M').strftime('%Y-%m')
        rows.append(o)
    w = pd.DataFrame(rows); w.index.name='signal_month'
    return finalize_monthly(w)


def aaa_weights(p):
    assets = ['SPY','VGK','EWJ','VWO','VNQ','RWX','IEF','TLT','DBC','GLD']
    x = p[assets].dropna(how='any').copy()
    logret = np.log(x / x.shift(1))
    momentum = x / x.shift(120)
    me = month_end_dates(x.index)
    rows=[]
    for dt in me:
        o = pd.Series(0.0, index=assets)
        pos = x.index.get_loc(dt)
        m = momentum.loc[dt]
        if pos >= 59 and m.notna().all():
            chosen = m.sort_values(ascending=False, kind='mergesort').index[:5].tolist()
            hist = logret.iloc[pos-59:pos+1][chosen]
            full = [c for c in chosen if hist[c].notna().sum() == 60]
            if len(full) > 0:
                cov = hist[full].cov().values
                if len(full) == 1:
                    o[full[0]] = 1.0
                else:
                    mw = long_only_minvar(cov, full)
                    o.loc[full] = mw
            else:
                o[:] = np.nan
        else:
            o[:] = np.nan
        o.name = dt.to_period('M').strftime('%Y-%m')
        rows.append(o)
    w = pd.DataFrame(rows); w.index.name='signal_month'
    return finalize_monthly(w)


def paa_weights(p):
    risk = ['SPY','QQQ','IWM','VGK','EWJ','EEM','IYR','GSG','GLD','HYG','LQD','TLT']
    safe = 'IEF'
    x = p[risk + [safe]].copy()
    sma = x[risk].rolling(240, min_periods=240).mean()
    score = x[risk] / sma - 1.0
    me = month_end_dates(x.index)
    rows=[]
    n_risk = len(risk)
    topn = 6
    a = 2.0
    denom = n_risk - a*n_risk/4.0  # 6 for a=2 and 12 risky assets
    for dt in me:
        r = score.loc[dt]
        o = pd.Series(0.0, index=risk+[safe])
        if r.notna().all():
            chosen = r.sort_values(ascending=False, kind='mergesort').index[:topn]
            npos = int((r > 0).sum())
            bf = (n_risk - npos) / denom
            bf = min(1.0, max(0.0, float(bf)))
            o[safe] = bf
            if bf < 1.0:
                o.loc[chosen] = (1.0 - bf) / topn
        else:
            o[:] = np.nan
        o.name = dt.to_period('M').strftime('%Y-%m')
        rows.append(o)
    w = pd.DataFrame(rows); w.index.name='signal_month'
    return finalize_monthly(w)


def cumulative_return(block):
    return (1.0 + block).prod(axis=0) - 1.0


def kda_weights(p):
    investable = ['SPY','VGK','EWJ','EEM','VNQ','RWX','TLT','DBC','GLD','IEF']
    canary = ['VWO','BND']
    assets = investable + canary
    x = p[assets].dropna(how='any').copy()
    ret = x.pct_change(fill_method=None)
    # Calendar-month endpoints exactly mirror the endpoint-block logic of the DB/Kipnis code.
    me = month_end_dates(x.index)
    me_pos = [x.index.get_loc(d) for d in me]
    rows=[]
    for j in range(len(me)):
        dt = me[j]
        o = pd.Series(0.0, index=investable+['CASH'])
        if j < 12:
            o[:] = np.nan
            o.name = dt.to_period('M').strftime('%Y-%m')
            rows.append(o); continue
        # retSubset from the day after the month-end 12 months ago through current month-end.
        start = me_pos[j-12] + 1
        end = me_pos[j]
        rd = ret.iloc[start:end+1][assets]
        if rd.isna().any().any() or len(rd) < 200:
            o[:] = np.nan
            o.name = dt.to_period('M').strftime('%Y-%m')
            rows.append(o); continue
        periods = rd.index.to_period('M')
        uniq = periods.unique()
        if len(uniq) != 12:
            raise RuntimeError(f'KDA expected 12 monthly blocks at {dt.date()}, got {len(uniq)}')
        def last_k_months(k):
            keep = set(uniq[-k:])
            return rd[[q in keep for q in periods]]
        one = last_k_months(1)
        three = last_k_months(3)
        six = last_k_months(6)
        twelve = rd
        moms = (cumulative_return(one)*12.0 + cumulative_return(three)*4.0 +
                cumulative_return(six)*2.0 + cumulative_return(twelve))
        asset_mom = moms[investable]
        cp_mom = moms[canary]
        ranks = asset_mom.rank(method='average', ascending=True)
        selected = (ranks >= 6.0) & (asset_mom > 0.0)
        sel = asset_mom.index[selected].tolist()
        risk_w = pd.Series(0.0, index=investable)
        if len(sel) == 1:
            risk_w[sel[0]] = 1.0
        elif len(sel) > 1:
            c1 = one[sel].corr().values
            c3 = three[sel].corr().values
            c6 = six[sel].corr().values
            c12 = twelve[sel].corr().values
            cors = (c1*12.0 + c3*4.0 + c6*2.0 + c12) / 19.0
            vols = one[sel].std(axis=0, ddof=1).values
            cov = np.outer(vols, vols) * cors
            mw = long_only_minvar(cov, sel)
            risk_w.loc[sel] = mw
        pct_aggressive = float((cp_mom > 0.0).mean())
        risk_w *= pct_aggressive
        o.loc[investable] = risk_w
        pct_cp = 1.0 - pct_aggressive
        if asset_mom['IEF'] > 0:
            o['IEF'] += pct_cp
        else:
            o['CASH'] += pct_cp
        # Exact residual cash, also protects against tiny optimizer round-off.
        o['CASH'] += 1.0 - float(o.sum())
        if o.min() < -1e-8:
            raise RuntimeError(f'KDA negative target at {dt}: {o[o<0]}')
        o[o.abs() < 1e-14] = 0.0
        o.name = dt.to_period('M').strftime('%Y-%m')
        rows.append(o)
    w = pd.DataFrame(rows); w.index.name='signal_month'
    return finalize_monthly(w)


def load_existing(fn):
    d = pd.read_csv(OUT/fn)
    d['signal_month'] = d['signal_month'].astype(str)
    d = d.set_index('signal_month').astype(float)
    return d.loc[(d.index>=MONTH_START)&(d.index<=MONTH_END)]


def to_buckets(w):
    z = pd.DataFrame(index=w.index)
    for c in w.columns:
        b = BUCKET.get(c, c)
        if b not in z.columns:
            z[b] = 0.0
        z[b] = z[b] + w[c]
    return z


def pair_metrics(a,b,wa,wb):
    idx = wa.index.intersection(wb.index)
    A, B = to_buckets(wa.loc[idx]), to_buckets(wb.loc[idx])
    cols = sorted(set(A.columns)|set(B.columns))
    A = A.reindex(columns=cols,fill_value=0.0)
    B = B.reindex(columns=cols,fill_value=0.0)
    l1 = np.abs(A.values-B.values).sum(axis=1)
    holdings=[]
    for i in range(len(idx)):
        sa=set(np.array(cols)[A.iloc[i].values>TOL]); sb=set(np.array(cols)[B.iloc[i].values>TOL])
        holdings.append(len(sa&sb)/len(sa|sb) if (sa|sb) else 1.0)
    ca=np.abs(np.diff(A.values,axis=0)).sum(axis=1)>TOL
    cb=np.abs(np.diff(B.values,axis=0)).sum(axis=1)>TOL
    union=np.logical_or(ca,cb).sum(); inter=np.logical_and(ca,cb).sum()
    tj=inter/union if union else 1.0
    what=float(np.mean(l1)/2.0)
    hold=float(1.0-np.mean(holdings))
    when=float(1.0-tj)
    return {
        'strategy_a':a,'strategy_b':b,'n_months':len(idx),
        'mean_L1_target_weight_distance':float(np.mean(l1)),
        'normalized_L1_distance':what,
        'mean_holdings_jaccard':float(np.mean(holdings)),
        'holdings_disagreement':hold,
        'transition_jaccard':float(tj),
        'transition_timing_disagreement':when,
        'primary_decision_distance':float(np.mean([what,hold,when])),
        'change_rate_a':float(ca.mean()),'change_rate_b':float(cb.mean())
    }


def selector(mats, tag='FULL'):
    common=sorted(set.intersection(*[set(w.index) for w in mats.values()]))
    if (len(common),common[0],common[-1]) != (216,'2008-07','2026-06'):
        raise RuntimeError(f'Unexpected full-pool common window: {len(common)}, {common[0]}, {common[-1]}')
    mats={k:w.loc[common] for k,w in mats.items()}

    audit=[]
    for name,w in mats.items():
        audit.append({'strategy':name,'n_months':len(w),'start':w.index.min(),'end':w.index.max(),
                      'max_abs_sum_minus_one':float((w.sum(axis=1)-1).abs().max()),
                      'mean_active_raw_tickers':float((w>TOL).sum(axis=1).mean())})
    pd.DataFrame(audit).to_csv(OUT/'G4_ZOO_FULL_2023_WEIGHT_AUDIT_v0_30.csv',index=False)

    pair=[]
    for a,b in itertools.combinations(sorted(mats),2):
        pair.append(pair_metrics(a,b,mats[a],mats[b]))
    pairdf=pd.DataFrame(pair)
    pairdf.to_csv(OUT/'G4_ZOO_FULL_2023_PAIRWISE_DECISION_SPACE_v0_30.csv',index=False)
    pmap={frozenset((r.strategy_a,r.strategy_b)):r for _,r in pairdf.iterrows()}
    def dist(a,b): return float(pmap[frozenset((a,b))].primary_decision_distance)

    names=sorted(mats)
    rows=[]
    for comb in itertools.combinations(names,5):
        ds=[dist(a,b) for a,b in itertools.combinations(comb,2)]
        rows.append({'combination':' | '.join(comb),'mean_decision_distance':float(np.mean(ds)),
                     'min_pair_distance':float(np.min(ds)),'max_pair_distance':float(np.max(ds))})
    res=pd.DataFrame(rows).sort_values(['mean_decision_distance','min_pair_distance','combination'],ascending=[False,False,True]).reset_index(drop=True)
    res.insert(0,'rank',np.arange(1,len(res)+1))
    hist=' | '.join(sorted(['BAA_Aggressive','BAA_Balanced','ADM','FAA','LAA']))
    res['historical_2023_set']=res['combination'].eq(hist)
    res.to_csv(OUT/'G4_ZOO_FULL_2023_FIVE_RULE_SELECTOR_v0_30.csv',index=False)
    histrow=res.loc[res.historical_2023_set].iloc[0]

    # Same frozen, performance-blind component-weight sensitivity as v0.29.
    weight_specs={
        'equal_1_1_1':(1,1,1),'L1_only':(1,0,0),'holdings_only':(0,1,0),'timing_only':(0,0,1),
        'what_heavy_2_1_1':(2,1,1),'when_heavy_1_1_2':(1,1,2),'holdings_heavy_1_2_1':(1,2,1)
    }
    sens=[]
    for label,ww in weight_specs.items():
        s=sum(ww)
        def wd(a,b):
            r=pmap[frozenset((a,b))]
            vals=[float(r.normalized_L1_distance),float(r.holdings_disagreement),float(r.transition_timing_disagreement)]
            return sum(w*v for w,v in zip(ww,vals))/s
        rr=[]
        for comb in itertools.combinations(names,5):
            ds=[wd(a,b) for a,b in itertools.combinations(comb,2)]
            rr.append((' | '.join(comb),float(np.mean(ds)),float(np.min(ds))))
        rr=sorted(rr,key=lambda x:(-x[1],-x[2],x[0]))
        ranks={x[0]:i+1 for i,x in enumerate(rr)}
        sens.append({'metric_spec':label,'selected_set':rr[0][0],
                     'selected_mean_distance':rr[0][1],
                     'historical_2023_rank':ranks[hist],
                     'historical_2023_percentile':1-(ranks[hist]-1)/(len(rr)-1),
                     'n_combinations':len(rr)})
    pd.DataFrame(sens).to_csv(OUT/'G4_ZOO_FULL_2023_SELECTOR_METRIC_SENSITIVITY_v0_30.csv',index=False)

    # Random-set distribution is structural only; deterministic enumeration makes this exact, not Monte Carlo.
    vals=res['mean_decision_distance'].to_numpy()
    distribution=pd.DataFrame([{
        'n_combinations':len(res),
        'mean_score_all_sets':float(np.mean(vals)),
        'median_score_all_sets':float(np.median(vals)),
        'p10_score':float(np.quantile(vals,.10)),
        'p25_score':float(np.quantile(vals,.25)),
        'p75_score':float(np.quantile(vals,.75)),
        'p90_score':float(np.quantile(vals,.90)),
        'selected_score':float(res.iloc[0].mean_decision_distance),
        'historical_score':float(histrow.mean_decision_distance),
        'historical_rank':int(histrow['rank']),
        'historical_percentile':float(1-(int(histrow['rank'])-1)/(len(res)-1)),
    }])
    distribution.to_csv(OUT/'G4_ZOO_FULL_2023_SET_SCORE_DISTRIBUTION_v0_30.csv',index=False)

    closest=pairdf.sort_values(['primary_decision_distance','strategy_a','strategy_b']).head(10)
    closest.to_csv(OUT/'G4_ZOO_FULL_2023_CLOSEST_PAIRS_v0_30.csv',index=False)
    farthest=pairdf.sort_values(['primary_decision_distance','strategy_a','strategy_b'],ascending=[False,True,True]).head(10)
    farthest.to_csv(OUT/'G4_ZOO_FULL_2023_FARTHEST_PAIRS_v0_30.csv',index=False)

    return common,mats,pairdf,res,histrow,sens


def main():
    p=load_daily()
    required=['SPY','VEU','BIL','AGG','VGK','EWJ','VWO','VNQ','RWX','IEF','TLT','DBC','GLD',
              'QQQ','IWM','EEM','IYR','GSG','HYG','LQD','BND']
    miss=[c for c in required if c not in p.columns]
    if miss: raise RuntimeError(f'Missing required frozen symbols: {miss}')

    rebuilt={
        'DM':dm_weights(p),
        'AAA':aaa_weights(p),
        'PAA':paa_weights(p),
        'KDA':kda_weights(p),
    }
    outfiles={
        'DM':'G4_ZOO_DM_TARGET_WEIGHTS_DB2022_FROZEN_v0_30.csv',
        'AAA':'G4_ZOO_AAA_TARGET_WEIGHTS_DB2022_FROZEN_v0_30.csv',
        'PAA':'G4_ZOO_PAA_TARGET_WEIGHTS_DB2022_FROZEN_v0_30.csv',
        'KDA':'G4_ZOO_KDA_TARGET_WEIGHTS_DB2022_FROZEN_v0_30.csv',
    }
    for name,w in rebuilt.items():
        w.reset_index().to_csv(OUT/outfiles[name],index=False)

    mats={k:load_existing(v) for k,v in EXISTING.items()}
    mats.update(rebuilt)
    common,mats,pairdf,res,histrow,sens=selector(mats)

    # Verify that all v0.29 pairwise distances among the original 12 strategies are unchanged.
    old=pd.read_csv(OUT/'G4_ZOO_POOL_A2_PAIRWISE_DECISION_SPACE_v0_29.csv')
    key=lambda a,b:'|'.join(sorted((a,b)))
    old['key']=[key(a,b) for a,b in zip(old.strategy_a,old.strategy_b)]
    new12=pairdf[pairdf.strategy_a.isin(EXISTING)&pairdf.strategy_b.isin(EXISTING)].copy()
    new12['key']=[key(a,b) for a,b in zip(new12.strategy_a,new12.strategy_b)]
    z=old[['key','primary_decision_distance']].merge(new12[['key','primary_decision_distance']],on='key',suffixes=('_v029','_v030'))
    max_existing_delta=float((z.primary_decision_distance_v029-z.primary_decision_distance_v030).abs().max())
    if len(z)!=66 or max_existing_delta>1e-12:
        raise RuntimeError(f'v0.29 existing-pair drift detected: n={len(z)}, max={max_existing_delta}')
    pd.DataFrame([{'n_existing_pairs':len(z),'max_abs_primary_distance_delta':max_existing_delta,
                   'verdict':'PASS'}]).to_csv(OUT/'G4_ZOO_V029_TO_V030_EXISTING_PAIR_INVARIANCE_v0_30.csv',index=False)

    hist=' | '.join(sorted(['BAA_Aggressive','BAA_Balanced','ADM','FAA','LAA']))
    selected=res.iloc[0]
    record={
        'version':'v0.30',
        'status':'FULL_2023_STRATEGY_ZOO_STRUCTURAL_RECONSTRUCTION_PASS_R_VALIDATION_OPEN',
        'pool_name':'Full historical 2023 strategy candidate pool — performance-blind Decision Space',
        'strategies':sorted(mats),'n_strategies':len(mats),
        'common_start':common[0],'common_end':common[-1],'n_common_months':len(common),
        'n_five_rule_combinations':len(res),
        'primary_selector':'UNCHANGED from v0.29: mean of normalized target-weight L1, holdings disagreement, transition-timing disagreement; equal component weights',
        'selected_set':selected.combination,'selected_score':float(selected.mean_decision_distance),
        'historical_2023_set':hist,'historical_2023_rank':int(histrow['rank']),
        'historical_2023_score':float(histrow.mean_decision_distance),
        'historical_2023_percentile':float(1-(int(histrow['rank'])-1)/(len(res)-1)),
        'performance_files_read':False,'performance_used_for_selection':False,
        'new_rules_v0_30':['DM','AAA','PAA','KDA'],
        'new_rule_basis':'DB Financial Investment 2022 operational recipes used by the 2023 project; exact VEU/RWX/IYR adjusted prices frozen in user-local v0.29 runtime',
        'post_2023_excluded':['HAA'],
        'existing_12_pairwise_invariance_max_abs_delta':max_existing_delta,
        'interpretation_boundary':'Structural challenge only. Historical ADAA was practitioner-selected and is not retroactively described as algorithm-selected. New four-rule target weights remain independently R-validation-open; no strategy performance was computed or used.'
    }
    (OUT/'G4_ZOO_FULL_2023_RECORD_v0_30.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2))

if __name__=='__main__':
    main()
