#!/usr/bin/env python3
"""ADAA v0.29 — source-faithful EAA reconstruction + performance-blind Pool A-2 selector.

This script deliberately never reads strategy returns, CAGR, Sharpe, drawdown, cost,
or other performance outputs. It reads only frozen adjusted prices and target weights.

EAA implementation basis
------------------------
- Keller & Butler (2014/2015), Elastic Asset Allocation.
- Ilya Kipnis IKTrading v1.0 EAA implementation used by the DB Financial Investment
  2022 operational recipe. Parameters are frozen to DB2022: wR=1, wV=0, wC=.5,
  wS=2, errorJitter=1e-6, cashAsset=IEF, bestN=1+ceil(sqrt(7)), crash protection on.
- A subtle implementation detail in IKTrading v1.0 increments wS by errorJitter inside
  each loop iteration. The primary reconstruction preserves that behavior exactly.
  A constant-exponent control is produced as a source-implementation sensitivity only.
"""
from pathlib import Path
import itertools, json, math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '03_Data_and_Code' / '04_Outputs'
MONTH_FILE = OUT / 'G5_FROZEN_MONTH_END_ADJUSTED_R_v0_15.csv'
MONTH_START = '2008-07'
MONTH_END = '2026-06'
TOL = 1e-10

EAA_ASSETS = ['VTI','VEA','VWO','QQQ','EWJ','HYG','IEF']

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
}

BUCKET = {
    'SPY':'US_BROAD_EQ','VTI':'US_BROAD_EQ','VFINX':'US_BROAD_EQ',
    'QQQ':'US_TECH_EQ','IWM':'US_SMALL_EQ','IWN':'US_SMALL_VALUE_EQ','IWD':'US_VALUE_EQ',
    'EFA':'DEV_EXUS_EQ','VEA':'DEV_EXUS_EQ','VGK':'EUROPE_EQ','EWJ':'JAPAN_EQ',
    'EEM':'EM_EQ','VWO':'EM_EQ','VEU':'GLOBAL_EXUS_EQ',
    'VINEX':'EXUS_SMALL_EQ','VSS':'EXUS_SMALL_EQ','OSMAX':'EXUS_SMALL_EQ',
    'VNQ':'US_REIT','RWX':'INTL_REIT','IYR':'US_REIT',
    'GLD':'GOLD','DBC':'COMMODITY','GSG':'COMMODITY',
    'HYG':'HY_BOND','LQD':'IG_CORP_BOND','TLT':'LONG_TSY','VUSTX':'LONG_TSY',
    'IEF':'INTERMEDIATE_TSY','SHY':'SHORT_TSY','BIL':'TBILL','AGG':'AGG_BOND','BND':'AGG_BOND',
    'TIP':'TIPS','CASH':'CASH'
}


def load_monthly_prices():
    d = pd.read_csv(MONTH_FILE)
    d['signal_month'] = d['signal_month'].astype(str)
    d = d.set_index('signal_month')
    x = d[EAA_ASSETS].astype(float).dropna()
    if x.index.min() > '2007-07':
        raise RuntimeError('EAA common input history unexpectedly shortened')
    return x


def eaa_weights(monthly_prices, preserve_loop_ws_drift=True):
    """Clean-room reproduction of the documented IKTrading v1.0 EAA implementation."""
    mp = monthly_prices.copy()
    rets = mp.pct_change(fill_method=None).iloc[1:]
    bestN = 1 + math.ceil(math.sqrt(mp.shape[1]))  # 4 for the DB2022 7-asset universe
    wR, wV, wC, wS, jitter = 1.0, 0.0, 0.5, 2.0, 1e-6
    rows = []
    current_wS = wS
    for i in range(0, len(rets)-11):
        rd = rets.iloc[i:i+12]
        cum3 = (1.0 + rd.iloc[9:12]).prod(axis=0) - 1.0
        cum6 = (1.0 + rd.iloc[6:12]).prod(axis=0) - 1.0
        cum12 = (1.0 + rd).prod(axis=0) - 1.0
        period_return = (rd.iloc[11] + cum3 + cum6 + cum12) / 22.0
        vols = rd.std(axis=0, ddof=1) * np.sqrt(12.0)
        market_index = rd.mean(axis=1, skipna=True)
        cors = rd.apply(lambda s: s.corr(market_index))
        weighted_rets = period_return ** wR
        weighted_cors = (1.0 - cors) ** wC
        weighted_vols = (vols + jitter) ** wV
        if preserve_loop_ws_drift:
            current_wS += jitter
        else:
            current_wS = wS + jitter
        base = weighted_rets * weighted_cors / weighted_vols
        with np.errstate(invalid='ignore'):
            z = pd.Series(np.power(base.astype(float), current_wS), index=period_return.index)
        z.loc[period_return < 0] = 0.0
        crash = float((z == 0).sum() / z.notna().sum())
        ordered = z.dropna().sort_values(ascending=False, kind='mergesort').values
        threshold = ordered[bestN-1]
        selected = z >= threshold
        pre = z * selected.astype(float)
        denom = float(pre.sum(skipna=True))
        if denom == 0 or not np.isfinite(denom):
            w = pd.Series(0.0, index=z.index)
        else:
            w = pre / denom
        w = w * (1.0 - crash)
        w = w.fillna(0.0)
        w.loc['IEF'] += 1.0 - float(w.sum())
        w.name = rd.index[-1]
        rows.append(w)
    ans = pd.DataFrame(rows)
    ans.index.name = 'signal_month'
    ans = ans.loc[(ans.index >= MONTH_START) & (ans.index <= MONTH_END)].copy()
    if ((ans.sum(axis=1)-1.0).abs() > 1e-8).any():
        raise RuntimeError('EAA target weights fail sum-to-one audit')
    return ans


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


def main():
    monthly = load_monthly_prices()
    eaa = eaa_weights(monthly, True)
    eaa_control = eaa_weights(monthly, False)
    eaa.reset_index().to_csv(OUT/'G4_ZOO_EAA_TARGET_WEIGHTS_IKTRADING_V1_SOURCEFAITHFUL_v0_29.csv',index=False)
    eaa_control.reset_index().to_csv(OUT/'G4_ZOO_EAA_TARGET_WEIGHTS_CONSTANT_WS_CONTROL_v0_29.csv',index=False)
    delta=(eaa-eaa_control).abs()
    pd.DataFrame([{
        'n_months':len(eaa),
        'max_abs_weight_difference':float(delta.max().max()),
        'months_any_cell_gt_1e_10':int((delta>1e-10).any(axis=1).sum()),
        'max_monthly_L1_difference':float(delta.sum(axis=1).max()),
        'interpretation':'IKTrading v1.0 loop-level wS increment has tiny numerical weight effects; selector robustness checked separately.'
    }]).to_csv(OUT/'G4_ZOO_EAA_IMPLEMENTATION_DETAIL_SENSITIVITY_v0_29.csv',index=False)

    mats={k:load_existing(v) for k,v in EXISTING.items()}
    mats['EAA']=eaa
    common=sorted(set.intersection(*[set(w.index) for w in mats.values()]))
    if (len(common),common[0],common[-1]) != (216,'2008-07','2026-06'):
        raise RuntimeError(f'unexpected common window: {len(common)}, {common[0]}, {common[-1]}')
    mats={k:w.loc[common] for k,w in mats.items()}

    audit=[]
    for name,w in mats.items():
        audit.append({'strategy':name,'n_months':len(w),'start':w.index.min(),'end':w.index.max(),
                      'max_abs_sum_minus_one':float((w.sum(axis=1)-1).abs().max()),
                      'mean_active_raw_tickers':float((w>TOL).sum(axis=1).mean())})
    pd.DataFrame(audit).to_csv(OUT/'G4_ZOO_POOL_A2_WEIGHT_AUDIT_v0_29.csv',index=False)

    pair=[]
    for a,b in itertools.combinations(sorted(mats),2):
        pair.append(pair_metrics(a,b,mats[a],mats[b]))
    pairdf=pd.DataFrame(pair)
    pairdf.to_csv(OUT/'G4_ZOO_POOL_A2_PAIRWISE_DECISION_SPACE_v0_29.csv',index=False)
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
    res.to_csv(OUT/'G4_ZOO_POOL_A2_FIVE_RULE_SELECTOR_v0_29.csv',index=False)
    histrow=res.loc[res.historical_2023_set].iloc[0]

    # Frozen return-free component-weight sensitivity.
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
                     'n_combinations':len(rr)})
    pd.DataFrame(sens).to_csv(OUT/'G4_ZOO_POOL_A2_SELECTOR_METRIC_SENSITIVITY_v0_29.csv',index=False)

    # Check whether the tiny EAA implementation detail changes the primary selector result.
    mats_ctrl={k:v.copy() for k,v in mats.items()}; mats_ctrl['EAA']=eaa_control.loc[common]
    pair_ctrl=[]
    for a,b in itertools.combinations(sorted(mats_ctrl),2):
        pair_ctrl.append(pair_metrics(a,b,mats_ctrl[a],mats_ctrl[b]))
    pc=pd.DataFrame(pair_ctrl); pmc={frozenset((r.strategy_a,r.strategy_b)):r for _,r in pc.iterrows()}
    def dc(a,b): return float(pmc[frozenset((a,b))].primary_decision_distance)
    ctr=[]
    for comb in itertools.combinations(names,5):
        ds=[dc(a,b) for a,b in itertools.combinations(comb,2)]
        ctr.append((' | '.join(comb),float(np.mean(ds)),float(np.min(ds))))
    ctr=sorted(ctr,key=lambda x:(-x[1],-x[2],x[0]))
    ctrl_rank={x[0]:i+1 for i,x in enumerate(ctr)}
    pd.DataFrame([{
        'primary_sourcefaithful_selected_set':res.iloc[0].combination,
        'constant_ws_control_selected_set':ctr[0][0],
        'selected_set_same':res.iloc[0].combination==ctr[0][0],
        'historical_rank_sourcefaithful':int(histrow['rank']),
        'historical_rank_constant_ws_control':int(ctrl_rank[hist]),
        'historical_rank_same':int(histrow['rank'])==int(ctrl_rank[hist])
    }]).to_csv(OUT/'G4_ZOO_EAA_SOURCE_DETAIL_SELECTOR_ROBUSTNESS_v0_29.csv',index=False)

    record={
        'version':'v0.29','status':'PERFORMANCE_BLIND_STRUCTURAL_CHALLENGE_PASS_R_VALIDATION_OPEN',
        'pool_name':'Pool A-2 common-data subset including source-faithful EAA operational implementation',
        'strategies':names,'n_strategies':len(names),'common_start':common[0],'common_end':common[-1],
        'n_common_months':len(common),'n_five_rule_combinations':len(res),
        'primary_selector':'mean of normalized target-weight L1, holdings disagreement, transition-timing disagreement; all equal weight',
        'selected_set':res.iloc[0].combination,'selected_score':float(res.iloc[0].mean_decision_distance),
        'historical_2023_set':hist,'historical_2023_rank':int(histrow['rank']),
        'historical_2023_score':float(histrow['mean_decision_distance']),
        'historical_2023_percentile':float(1-(int(histrow['rank'])-1)/(len(res)-1)),
        'performance_files_read':False,
        'new_in_v0_29':['EAA source code frozen from IKTrading v1.0 documentation/source and clean-room reconstructed'],
        'excluded_pending':['DM','AAA','PAA','KDA'],
        'missing_exact_inputs':['VEU','RWX','IYR'],
        'post_2023_excluded':['HAA'],
        'interpretation_boundary':'Structural validation only. No strategy performance was computed or used. Pool A remains incomplete until exact missing ETF inputs are frozen and the four pending rules are reconstructed.'
    }
    (OUT/'G4_ZOO_POOL_A2_RECORD_v0_29.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2))

if __name__=='__main__':
    main()
