#!/usr/bin/env python3
"""ADAA v0.27 - performance-blind Strategy Zoo common-data subset.

Purpose
-------
Reconstruct five additional public-rule implementations from the frozen daily price panel
using implementation recipes documented in the DB Financial Investment 2022 asset-allocation
reference, then combine them with six already-frozen public parent/control strategies.

CRITICAL: This script NEVER reads strategy-return, CAGR, Sharpe, drawdown or other performance
files. It uses only frozen prices and frozen target-weight files. The selector objective is
therefore performance-blind.

Pool A-1 is deliberately incomplete: strategies needing currently-unfrozen instruments or an
unfrozen external function/variant (DM/AAA/EAA/PAA/KDA) remain outside until their source and
input requirements are frozen. HAA is post-2023 and is also excluded.
"""
from pathlib import Path
import itertools
import json
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '03_Data_and_Code' / '04_Outputs'
SPEC = ROOT / '02_Strategy_Specification'

DAILY_FILE = OUT / 'G5_FROZEN_ADJUSTED_DAILY_LONG_R_v0_15.csv'
MONTH_START = '2008-07'
MONTH_END = '2026-06'
TOL = 1e-10

# ------------------------- helpers -------------------------
def load_daily():
    d = pd.read_csv(DAILY_FILE, parse_dates=['date'])
    p = d.pivot(index='date', columns='symbol', values='adjusted').sort_index()
    return p


def month_end_rows(df):
    # exact last available trading row in each calendar month
    return df.groupby(df.index.to_period('M')).tail(1)


def top_equal(score_row, n):
    s = score_row.dropna().sort_values(ascending=False, kind='mergesort')
    out = pd.Series(0.0, index=score_row.index)
    if len(s) == 0:
        return out
    k = min(n, len(s))
    chosen = s.index[:k]
    out.loc[chosen] = 1.0 / k
    return out


def finalize_monthly(weight_daily, extra_cash=False):
    w = month_end_rows(weight_daily)
    w.index = w.index.to_period('M').astype(str)
    w.index.name = 'signal_month'
    if extra_cash and 'CASH' not in w.columns:
        w['CASH'] = 1.0 - w.sum(axis=1)
    w = w.loc[(w.index >= MONTH_START) & (w.index <= MONTH_END)].copy()
    # normalize only tiny floating error; true residual cash should already be explicit
    sums = w.sum(axis=1)
    bad = sums.notna() & ((sums - 1.0).abs() > 1e-8)
    if bad.any():
        raise RuntimeError(f'weight sums not one: {w.loc[bad].head()}')
    return w.fillna(0.0)


# ------------------------- new rule reconstructions -------------------------
def gtAA(p):
    assets = ['SPY','EFA','DBC','VNQ','IEF']
    x = p[assets]
    sma200 = x.rolling(200, min_periods=200).mean()
    active = (x / sma200 - 1.0) > 0
    w = active.astype(float) / len(assets)
    w['CASH'] = 1.0 - w.sum(axis=1)
    return finalize_monthly(w)


def qsf(p):
    risk = ['SPY','QQQ','EFA','EEM','TLT']
    safe = 'IEF'
    x = p[risk + [safe]]
    score = x / x.shift(60) - 1.0
    rows = []
    for dt, r in score.iterrows():
        o = pd.Series(0.0, index=risk + [safe])
        rr = r[risk]
        if rr.notna().all():
            if (rr > 0).all():
                o.loc[rr.idxmax()] = 1.0
            else:
                o.loc[safe] = 1.0
        else:
            o[:] = np.nan
        rows.append(o)
    w = pd.DataFrame(rows, index=score.index)
    return finalize_monthly(w)


def weighted_13612(p):
    return ((p / p.shift(20) - 1.0) * 12.0 +
            (p / p.shift(60) - 1.0) * 4.0 +
            (p / p.shift(120) - 1.0) * 2.0 +
            (p / p.shift(240) - 1.0))


def vaa(p):
    risk = ['SPY','EFA','EEM','AGG']
    safe = ['SHY','IEF','LQD']
    score = weighted_13612(p[risk + safe])
    rows=[]
    for dt,r in score.iterrows():
        o=pd.Series(0.0,index=risk+safe)
        rr=r[risk]
        ss=r[safe]
        if rr.notna().all() and ss.notna().all():
            if (rr>0).all(): o.loc[rr.idxmax()]=1.0
            else: o.loc[ss.idxmax()]=1.0
        else: o[:]=np.nan
        rows.append(o)
    return finalize_monthly(pd.DataFrame(rows,index=score.index))


def daa(p):
    risk=['SPY','QQQ','IWM','VGK','EWJ','VWO','VNQ','GLD','GSG','HYG','LQD','TLT']
    safe=['SHY','IEF','LQD']
    cana=['VWO','BND']
    all_assets=list(dict.fromkeys(risk+safe+cana))
    score=weighted_13612(p[all_assets])
    rows=[]
    for dt,r in score.iterrows():
        o=pd.Series(0.0,index=all_assets)
        if r.notna().all():
            n_bad=int((r[cana] <= 0).sum())
            safe_frac=0.5*n_bad
            # top safe, top six risk. LQD can appear in both role sets but target weights aggregate.
            safe_pick=r[safe].idxmax()
            risk_pick=r[risk].sort_values(ascending=False,kind='mergesort').index[:6]
            if safe_frac>0:
                o.loc[safe_pick]+=safe_frac
            if safe_frac<1:
                o.loc[risk_pick]+=(1-safe_frac)/6.0
        else: o[:]=np.nan
        rows.append(o)
    return finalize_monthly(pd.DataFrame(rows,index=score.index))


def gpm(p):
    risk=['SPY','QQQ','IWM','VGK','EWJ','EEM','VNQ','DBC','GLD','HYG','LQD','TLT']
    safe=['BIL','IEF']
    assets=risk+safe
    x=p[assets]
    score=(x/x.shift(20)-1.0)+(x/x.shift(60)-1.0)+(x/x.shift(120)-1.0)+(x/x.shift(240)-1.0)
    ret=x.pct_change(fill_method=None)
    risk_port=ret[risk].mean(axis=1)
    corr=pd.DataFrame(index=x.index,columns=assets,dtype=float)
    for a in assets:
        corr[a]=ret[a].rolling(240,min_periods=240).corr(risk_port)
    prod=score*(1.0-corr)
    rows=[]
    for dt,r in prod.iterrows():
        o=pd.Series(0.0,index=assets)
        if r.notna().all():
            count=int((r[risk]>0).sum())
            safe_frac=1.0 if count <= 6 else (12.0-count)/6.0
            safe_pick=r[safe].idxmax()
            risk_pick=r[risk].sort_values(ascending=False,kind='mergesort').index[:3]
            o.loc[safe_pick]=safe_frac
            if safe_frac<1:
                o.loc[risk_pick]=(1-safe_frac)/3.0
        else: o[:]=np.nan
        rows.append(o)
    return finalize_monthly(pd.DataFrame(rows,index=prod.index))


# ------------------------- existing parent/control files -------------------------
EXISTING = {
    'BAA_Aggressive': 'G5_BAA_AGGRESSIVE_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
    'BAA_Balanced': 'G5_BAA_BALANCED_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
    'ADM': 'G5_ADM_PARENT_VINEX_TARGET_WEIGHTS_R_v0_15.csv',
    'FAA': 'G5_FAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
    'LAA': 'G5_LAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
    'RAA': 'G5_RAA_PARENT_COMPARATOR_TARGET_WEIGHTS_R_v0_15.csv',
}

# Canonical exposure buckets. This mapping is intentionally return-free and only collapses
# obvious fund/proxy aliases; distinct styles/regions remain distinct where economically useful.
BUCKET = {
    'SPY':'US_BROAD_EQ','VTI':'US_BROAD_EQ','VFINX':'US_BROAD_EQ',
    'QQQ':'US_TECH_EQ','IWM':'US_SMALL_EQ','IWN':'US_SMALL_VALUE_EQ','IWD':'US_VALUE_EQ',
    'EFA':'DEV_EXUS_EQ','VEA':'DEV_EXUS_EQ','VGK':'EUROPE_EQ','EWJ':'JAPAN_EQ',
    'EEM':'EM_EQ','VWO':'EM_EQ','VINEX':'EXUS_SMALL_EQ','VSS':'EXUS_SMALL_EQ','OSMAX':'EXUS_SMALL_EQ',
    'VNQ':'US_REIT','GLD':'GOLD','DBC':'COMMODITY','GSG':'COMMODITY',
    'HYG':'HY_BOND','LQD':'IG_CORP_BOND','TLT':'LONG_TSY','VUSTX':'LONG_TSY',
    'IEF':'INTERMEDIATE_TSY','SHY':'SHORT_TSY','BIL':'TBILL','AGG':'AGG_BOND','BND':'AGG_BOND',
    'TIP':'TIPS','CASH':'CASH'
}


def load_existing(name, fn):
    d=pd.read_csv(OUT/fn)
    d['signal_month']=d['signal_month'].astype(str)
    d=d.set_index('signal_month').astype(float)
    d=d.loc[(d.index>=MONTH_START)&(d.index<=MONTH_END)]
    return d


def to_buckets(w):
    cols={}
    for c in w.columns:
        b=BUCKET.get(c,c)
        cols.setdefault(b,[]).append(c)
    z=pd.DataFrame(index=w.index)
    for b,cs in cols.items(): z[b]=w[cs].sum(axis=1)
    return z


def pair_metrics(a,b,wa,wb):
    idx=wa.index.intersection(wb.index)
    A=to_buckets(wa.loc[idx]); B=to_buckets(wb.loc[idx])
    cols=sorted(set(A.columns)|set(B.columns))
    A=A.reindex(columns=cols,fill_value=0.0); B=B.reindex(columns=cols,fill_value=0.0)
    l1=np.abs(A.values-B.values).sum(axis=1)
    h=[]
    for i in range(len(idx)):
        sa=set(np.array(cols)[A.iloc[i].values>TOL]); sb=set(np.array(cols)[B.iloc[i].values>TOL])
        h.append(len(sa&sb)/len(sa|sb) if sa|sb else 1.0)
    ca=np.abs(np.diff(A.values,axis=0)).sum(axis=1)>TOL
    cb=np.abs(np.diff(B.values,axis=0)).sum(axis=1)>TOL
    union=np.logical_or(ca,cb).sum(); inter=np.logical_and(ca,cb).sum()
    tj=inter/union if union else 1.0
    what_l1=float(np.mean(l1)/2.0)
    holdings_dis=float(1.0-np.mean(h))
    timing_dis=float(1.0-tj)
    primary=float(np.mean([what_l1,holdings_dis,timing_dis]))
    return {
        'strategy_a':a,'strategy_b':b,'n_months':len(idx),
        'mean_L1_target_weight_distance':float(np.mean(l1)),
        'normalized_L1_distance':what_l1,
        'mean_holdings_jaccard':float(np.mean(h)),
        'holdings_disagreement':holdings_dis,
        'transition_jaccard':float(tj),
        'transition_timing_disagreement':timing_dis,
        'primary_decision_distance':primary,
        'change_rate_a':float(ca.mean()),'change_rate_b':float(cb.mean())
    }


def main():
    p=load_daily()
    rebuilt={
        'GTAA': gtAA(p),
        'QSF': qsf(p),
        'GPM': gpm(p),
        'VAA': vaa(p),
        'DAA': daa(p),
    }
    for name,w in rebuilt.items():
        f=OUT/f'G4_ZOO_{name}_TARGET_WEIGHTS_DB2022_FROZEN_v0_27.csv'
        w.reset_index().to_csv(f,index=False)

    mats={**{k:load_existing(k,v) for k,v in EXISTING.items()},**rebuilt}
    common=set.intersection(*[set(w.index) for w in mats.values()])
    common=sorted(x for x in common if MONTH_START<=x<=MONTH_END)
    if len(common)<200: raise RuntimeError(f'common months too short: {len(common)}')
    mats={k:w.loc[common] for k,w in mats.items()}

    # Audit target sums before any distance computation.
    aud=[]
    for name,w in mats.items():
        sums=w.sum(axis=1)
        aud.append({'strategy':name,'n_months':len(w),'start':w.index.min(),'end':w.index.max(),
                    'max_abs_sum_minus_one':float((sums-1).abs().max()),
                    'mean_active_raw_tickers':float((w>TOL).sum(axis=1).mean())})
    pd.DataFrame(aud).to_csv(OUT/'G4_ZOO_COMMON_SUBSET_WEIGHT_AUDIT_v0_27.csv',index=False)

    pair=[]
    for a,b in itertools.combinations(sorted(mats),2):
        pair.append(pair_metrics(a,b,mats[a],mats[b]))
    pairdf=pd.DataFrame(pair)
    pairdf.to_csv(OUT/'G4_ZOO_COMMON_SUBSET_PAIRWISE_DECISION_SPACE_v0_27.csv',index=False)
    pmap={frozenset((r.strategy_a,r.strategy_b)):r for _,r in pairdf.iterrows()}

    def dist(a,b): return float(pmap[frozenset((a,b))].primary_decision_distance)
    rows=[]
    names=sorted(mats)
    for comb in itertools.combinations(names,5):
        ds=[dist(a,b) for a,b in itertools.combinations(comb,2)]
        rows.append({'combination':' | '.join(comb),'mean_decision_distance':float(np.mean(ds)),
                     'min_pair_distance':float(np.min(ds)),'max_pair_distance':float(np.max(ds))})
    res=pd.DataFrame(rows).sort_values(['mean_decision_distance','min_pair_distance','combination'],ascending=[False,False,True]).reset_index(drop=True)
    res.insert(0,'rank',np.arange(1,len(res)+1))
    hist=' | '.join(sorted(['BAA_Aggressive','BAA_Balanced','ADM','FAA','LAA']))
    res['historical_2023_set']=res['combination'].eq(hist)
    res.to_csv(OUT/'G4_ZOO_COMMON_SUBSET_FIVE_RULE_SELECTOR_v0_27.csv',index=False)
    histrow=res.loc[res.historical_2023_set].iloc[0]

    # metric-weight sensitivity is frozen without performance: each component alone and simple equal-weight pairs.
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
        rank={x[0]:i+1 for i,x in enumerate(rr)}
        sens.append({'metric_spec':label,'selected_set':rr[0][0],'historical_2023_rank':rank[hist],
                     'historical_2023_percentile':1-(rank[hist]-1)/(len(rr)-1),
                     'n_combinations':len(rr)})
    pd.DataFrame(sens).to_csv(OUT/'G4_ZOO_COMMON_SUBSET_SELECTOR_METRIC_SENSITIVITY_v0_27.csv',index=False)

    record={
        'version':'v0.27','status':'PERFORMANCE_BLIND_STRUCTURAL_CHALLENGE_PASS',
        'pool_name':'Pool A-1 common-data subset','strategies':names,'n_strategies':len(names),
        'common_start':common[0],'common_end':common[-1],'n_common_months':len(common),
        'n_five_rule_combinations':len(res),
        'primary_selector':'mean of normalized target-weight L1, holdings disagreement, transition-timing disagreement; all equal weight',
        'selected_set':res.iloc[0].combination,'selected_score':float(res.iloc[0].mean_decision_distance),
        'historical_2023_set':hist,'historical_2023_rank':int(histrow['rank']),
        'historical_2023_score':float(histrow.mean_decision_distance),
        'historical_2023_percentile':float(1-(int(histrow['rank'])-1)/(len(res)-1)),
        'performance_files_read':False,
        'excluded_pending':['DM','AAA','EAA','PAA','KDA'],
        'post_2023_excluded':['HAA'],
        'interpretation_boundary':'Structural validation only. No strategy performance was computed or used. Pool A is not yet complete.'
    }
    (OUT/'G4_ZOO_COMMON_SUBSET_RECORD_v0_27.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2))

if __name__=='__main__': main()
