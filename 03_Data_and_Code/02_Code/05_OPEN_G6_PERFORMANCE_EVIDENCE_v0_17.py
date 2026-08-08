#!/usr/bin/env python3
"""ADAA v0.17 — first formal performance/risk opening.

Design choices used here were frozen before formal performance interpretation:
- canonical FAA = peer-only correlation + deterministic exact-N (G3 v0.16);
- canonical LAA information-state continuation = carry latest actually released state;
- design-neutral ensemble = 20% each sleeve;
- historical successor ensemble = 25/15/17.5/17.5/25;
- final-account cross-netted turnover/cost ledger;
- transaction-cost grid = 0/5/10/25/50 bps per unit gross L1 turnover;
- historical dashboard 60/40 = SPY 60% / IEF 40%;
- primary ETF-only holding window = 2008-06 through 2026-07.

This script does not optimize any rule, universe, top-level weight, cost rate, or sample.
"""
from pathlib import Path
import json, math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '03_Data_and_Code' / '04_Outputs'
COST_BPS = [0, 5, 10, 25, 50]
TOL = 1e-10


def load_w(name):
    d = pd.read_csv(OUT / name)
    if 'signal_month' not in d.columns:
        raise RuntimeError(f'missing signal_month: {name}')
    d['signal_month'] = d['signal_month'].astype(str)
    d = d.set_index('signal_month').astype(float)
    if ((d.sum(axis=1) - 1.0).abs() > TOL).any():
        bad = d.index[(d.sum(axis=1)-1).abs() > TOL].tolist()[:5]
        raise RuntimeError(f'weight sum failure {name}: {bad}')
    return d


def common_months(weight_frames):
    return sorted(set.intersection(*[set(x.index) for x in weight_frames]))


def aggregate_weights(months, sleeve_frames, alphas):
    if abs(sum(alphas.values()) - 1.0) > 1e-12:
        raise RuntimeError('top-level alphas do not sum to one')
    assets = sorted(set().union(*[set(sleeve_frames[k].columns) for k in alphas]))
    rows=[]
    for sm in months:
        x = pd.Series(0.0, index=assets)
        for k,a in alphas.items():
            x = x.add(a*sleeve_frames[k].loc[sm].reindex(assets, fill_value=0.0), fill_value=0.0)
        if abs(float(x.sum())-1) > TOL:
            raise RuntimeError(f'aggregate sum failure {sm}')
        rows.append(x)
    return pd.DataFrame(rows,index=months)


def portfolio_path(targets, asset_returns):
    rows=[]; prev_eop=None
    for sm, targ in targets.iterrows():
        hm = str(pd.Period(sm, freq='M') + 1)
        if hm not in asset_returns.index:
            raise RuntimeError(f'missing holding return month {hm}')
        ar = asset_returns.loc[hm].reindex(targets.columns)
        used = targ.abs() > 1e-15
        if ar[used].isna().any():
            raise RuntimeError(f'missing used-asset return at {hm}: {list(ar.index[used & ar.isna()])}')
        ar = ar.fillna(0.0)
        gross = float((targ * ar).sum())
        turnover = 0.0 if prev_eop is None else float((targ - prev_eop).abs().sum())
        grown = targ * (1.0 + ar)
        den = 1.0 + gross
        if not np.isfinite(den) or den <= 0:
            raise RuntimeError(f'invalid portfolio denominator at {hm}')
        eop = grown / den
        rows.append({'signal_month':sm,'holding_month':hm,'gross_return':gross,'gross_L1_turnover':turnover})
        prev_eop = eop
    d=pd.DataFrame(rows).set_index('holding_month')
    for bps in COST_BPS:
        d[f'net_return_{bps}bps'] = d['gross_return'] - d['gross_L1_turnover']*(bps/10000.0)
    return d


def drawdown_stats(x):
    wealth=(1+x).cumprod(); peak=wealth.cummax(); dd=wealth/peak-1.0
    mdd=float(dd.min()); trough=str(dd.idxmin())
    under=(wealth < peak*(1-1e-14))
    max_run=cur=0
    for z in under.to_numpy():
        cur=cur+1 if z else 0; max_run=max(max_run,cur)
    # longest completed/ongoing underwater run is useful even if final recovery is absent
    return mdd,trough,int(max_run)


def perf_metrics(x, rf):
    x=x.astype(float).dropna(); rf=rf.reindex(x.index).astype(float)
    if rf.isna().any():
        raise RuntimeError('risk-free BIL return missing in performance window')
    n=len(x); wealth=(1+x).cumprod(); cagr=float(wealth.iloc[-1]**(12.0/n)-1.0)
    ann_mean=float(x.mean()*12.0); vol=float(x.std(ddof=1)*math.sqrt(12.0))
    ex=x-rf; exsd=float(ex.std(ddof=1)); sharpe=float(ex.mean()/exsd*math.sqrt(12.0)) if exsd>0 else np.nan
    mdd,trough,maxuw=drawdown_stats(x); calmar=float(cagr/abs(mdd)) if mdd<0 else np.nan
    downside=float(math.sqrt(float(np.mean(np.minimum(x.to_numpy(),0.0)**2)))*math.sqrt(12.0))
    out={
        'months':n,'CAGR':cagr,'annualized_arithmetic_mean':ann_mean,'annualized_volatility':vol,
        'BIL_excess_Sharpe':sharpe,'max_drawdown':mdd,'max_drawdown_trough_month':trough,
        'Calmar':calmar,'downside_deviation':downside,'max_time_under_water_months':maxuw,
        'ending_growth_of_1':float(wealth.iloc[-1]),
    }
    for h in [1,3,12,36]:
        rr=(1+x).rolling(h).apply(np.prod,raw=True)-1.0
        out[f'worst_{h}m_return']=float(rr.min())
        if rr.notna().any(): out[f'worst_{h}m_end_month']=str(rr.idxmin())
    return out


def metric_rows(name, path, rf):
    rows=[]
    for bps in COST_BPS:
        m=perf_metrics(path[f'net_return_{bps}bps'],rf)
        m.update({
            'portfolio':name,'cost_bps':bps,
            'total_gross_L1_turnover':float(path.gross_L1_turnover.sum()),
            'annualized_mean_gross_L1_turnover':float(path.gross_L1_turnover.mean()*12.0),
        })
        rows.append(m)
    return rows

# Frozen month-end adjusted ETF/fund prices exported by local R before performance opening.
px=pd.read_csv(OUT/'G5_FROZEN_MONTH_END_ADJUSTED_R_v0_15.csv')
px['signal_month']=px['signal_month'].astype(str); px=px.set_index('signal_month').astype(float)
ret=px.pct_change(fill_method=None)

# Gate close: canonical FAA must already match R and independent implementation.
eq_file=OUT/'G3_FAA_CANONICAL_R_PYTHON_EQUIVALENCE_RECORD_v0_16.json'
if not eq_file.exists(): raise RuntimeError('canonical FAA equivalence record missing; run compare_g3_canonical_faa_v0_16.py first')
eq=json.loads(eq_file.read_text(encoding='utf-8'))
if eq.get('status')!='PASS': raise RuntimeError('canonical FAA equivalence is not PASS')

W={
 'HAA':load_w('G2_HAA_TARGET_WEIGHTS_R_v0_11_1.csv'),
 'BAA':load_w('G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_R_v0_11_1.csv'),
 'ADM':load_w('G2_ADM_TARGET_WEIGHTS_R_v0_11_1.csv'),
 'FAA':load_w('G3_FAA_CANONICAL_PEER_ONLY_EXACTN_TARGET_WEIGHTS_R_v0_16.csv'),
 'FAA_legacy':load_w('G2_FAA_LEGACY_TARGET_WEIGHTS_R_v0_11_1.csv'),
 'LAA':load_w('G2_LAA_CARRY_CALENDAR_TARGET_WEIGHTS_v0_11.csv'),
 'Static_LAA':load_w('G5_STATIC_ADAA_LAA_RISKY_CORE_TARGET_WEIGHTS_R_v0_15.csv'),
 'RAA':load_w('G5_RAA_PARENT_COMPARATOR_TARGET_WEIGHTS_R_v0_15.csv'),
 'BAA_Balanced_proxy':load_w('G5_BAA_BALANCED_ADAA_PROXY_EXPRESSION_TARGET_WEIGHTS_R_v0_15.csv'),
}
months=common_months([W[k] for k in ['HAA','BAA','ADM','FAA','LAA']])
if months[0]!='2008-05' or months[-1]!='2026-06' or len(months)!=218:
    raise RuntimeError(f'unexpected primary signal window {months[0]}..{months[-1]} n={len(months)}')
holding=[str(pd.Period(m,'M')+1) for m in months]
if holding[0]!='2008-06' or holding[-1]!='2026-07': raise RuntimeError('unexpected primary holding window')

# Primary and pre-specified diagnostic ensembles.
alpha_equal={'HAA':.2,'BAA':.2,'ADM':.2,'FAA':.2,'LAA':.2}
alpha_hist={'HAA':.25,'BAA':.15,'ADM':.175,'FAA':.175,'LAA':.25}
variants={
 'ADAA_equal20_canonical': aggregate_weights(months,W,alpha_equal),
 'ADAA_historical_weights_canonical': aggregate_weights(months,W,alpha_hist),
 'ADAA_equal20_legacy_FAA': aggregate_weights(months,W,{'HAA':.2,'BAA':.2,'ADM':.2,'FAA_legacy':.2,'LAA':.2}),
 'ADAA_historical_weights_legacy_FAA': aggregate_weights(months,W,{'HAA':.25,'BAA':.15,'ADM':.175,'FAA_legacy':.175,'LAA':.25}),
 'ADAA_equal_no_LAA_rescaled': aggregate_weights(months,W,{'HAA':.25,'BAA':.25,'ADM':.25,'FAA':.25}),
 'ADAA_hist_no_LAA_rescaled': aggregate_weights(months,W,{'HAA':1/3,'BAA':.20,'ADM':7/30,'FAA':7/30}),
 'ADAA_equal_static_LAA_replacement': aggregate_weights(months,W,{'HAA':.2,'BAA':.2,'ADM':.2,'FAA':.2,'Static_LAA':.2}),
 'ADAA_hist_static_LAA_replacement': aggregate_weights(months,W,{'HAA':.25,'BAA':.15,'ADM':.175,'FAA':.175,'Static_LAA':.25}),
 'ADAA_equal_RAA_replacement': aggregate_weights(months,W,{'HAA':.2,'BAA':.2,'ADM':.2,'FAA':.2,'RAA':.2}),
 'ADAA_hist_RAA_replacement': aggregate_weights(months,W,{'HAA':.25,'BAA':.15,'ADM':.175,'FAA':.175,'RAA':.25}),
 'ADAA_equal_BAA_Balanced_for_HAA': aggregate_weights(months,W,{'BAA_Balanced_proxy':.2,'BAA':.2,'ADM':.2,'FAA':.2,'LAA':.2}),
 'ADAA_hist_BAA_Balanced_for_HAA': aggregate_weights(months,W,{'BAA_Balanced_proxy':.25,'BAA':.15,'ADM':.175,'FAA':.175,'LAA':.25}),
}
# Historical dashboard benchmark definition was already coded before this research rebuild.
variants['Benchmark_60_40_SPY_IEF']=pd.DataFrame({'SPY':.6,'IEF':.4},index=months)

# Standalone current sleeves on same primary window.
for k in ['HAA','BAA','ADM','FAA','LAA']:
    variants[f'Sleeve_{k}']=W[k].loc[months]

paths={}; rows=[]
rf=ret.loc[holding,'BIL']
for name,T in variants.items():
    p=portfolio_path(T,ret); paths[name]=p
    rows.extend(metric_rows(name,p,rf))

metrics=pd.DataFrame(rows)
lead=['portfolio','cost_bps','months','CAGR','annualized_arithmetic_mean','annualized_volatility','BIL_excess_Sharpe','max_drawdown','max_drawdown_trough_month','Calmar','downside_deviation','max_time_under_water_months','worst_1m_return','worst_1m_end_month','worst_3m_return','worst_3m_end_month','worst_12m_return','worst_12m_end_month','worst_36m_return','worst_36m_end_month','total_gross_L1_turnover','annualized_mean_gross_L1_turnover','ending_growth_of_1']
metrics=metrics[lead]
metrics.to_csv(OUT/'G6_PRIMARY_PERFORMANCE_AND_COST_GRID_v0_17.csv',index=False)

# Monthly audit paths for the two primary ADAA specs and 60/40.
monthly=[]
for name in ['ADAA_equal20_canonical','ADAA_historical_weights_canonical','Benchmark_60_40_SPY_IEF']:
    q=paths[name].reset_index(); q.insert(0,'portfolio',name); monthly.append(q)
pd.concat(monthly,ignore_index=True).to_csv(OUT/'G6_PRIMARY_MONTHLY_RETURN_TURNOVER_PATHS_v0_17.csv',index=False)

# Parent / ADAA-variant performance on the pre-frozen P3 common window (gross only; decision-first audit already completed).
parent_files={
 'HAA_parent':'G5_HAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
 'HAA_parentRule_ADAAuniverse':'G5_HAA_PARENT_RULE_ADAA_UNIVERSE_TARGET_WEIGHTS_R_v0_15.csv',
 'HAA_ADAArule_parentUniverse':'G5_HAA_ADAA_RULE_PARENT_UNIVERSE_TARGET_WEIGHTS_R_v0_15.csv',
 'HAA_ADAA_current':'G2_HAA_TARGET_WEIGHTS_R_v0_11_1.csv',
 'BAA_Agg_parent':'G5_BAA_AGGRESSIVE_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
 'BAA_Agg_parentRule_ADAAexpression':'G5_BAA_AGGRESSIVE_PARENT_RULE_ADAA_PROXY_TARGET_WEIGHTS_R_v0_15.csv',
 'BAA_Agg_ADAA_current':'G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_R_v0_11_1.csv',
 'BAA_Balanced_parent':'G5_BAA_BALANCED_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
 'BAA_Balanced_ADAAexpression':'G5_BAA_BALANCED_ADAA_PROXY_EXPRESSION_TARGET_WEIGHTS_R_v0_15.csv',
 'ADM_parent_VINEX':'G5_ADM_PARENT_VINEX_TARGET_WEIGHTS_R_v0_15.csv',
 'ADM_parent_OSMAX_control':'G5_ADM_PARENT_OSMAX_CONTROL_TARGET_WEIGHTS_R_v0_15.csv',
 'ADM_ADAA_current':'G2_ADM_TARGET_WEIGHTS_R_v0_11_1.csv',
 'FAA_parent':'G5_FAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
 'FAA_parentRule_ADAAuniverse':'G5_FAA_PARENT_RULE_ADAA_UNIVERSE_TARGET_WEIGHTS_R_v0_15.csv',
 'FAA_ADAA_legacy':'G2_FAA_LEGACY_TARGET_WEIGHTS_R_v0_11_1.csv',
 'FAA_ADAA_canonical':'G3_FAA_CANONICAL_PEER_ONLY_EXACTN_TARGET_WEIGHTS_R_v0_16.csv',
 'LAA_parent':'G5_LAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv',
 'LAA_parentRule_ADAAequityExpression':'G5_LAA_PARENT_RULE_ADAA_EQUITY_EXPRESSION_TARGET_WEIGHTS_R_v0_15.csv',
 'LAA_ADAAtiming_parentUniverse':'G5_LAA_ADAA_TIMING_PARENT_UNIVERSE_TARGET_WEIGHTS_R_v0_15.csv',
 'LAA_ADAA_current_infoState':'G2_LAA_CARRY_CALENDAR_TARGET_WEIGHTS_v0_11.csv',
 'RAA_parent_comparator':'G5_RAA_PARENT_COMPARATOR_TARGET_WEIGHTS_R_v0_15.csv',
 'Static_ADAA_LAA_core':'G5_STATIC_ADAA_LAA_RISKY_CORE_TARGET_WEIGHTS_R_v0_15.csv',
}
P={k:load_w(f) for k,f in parent_files.items()}
p3_months=[str(p) for p in pd.period_range('2008-07','2026-06',freq='M')]
p3_hold=[str(pd.Period(m,'M')+1) for m in p3_months]
p3_rf=ret.loc[p3_hold,'BIL']
p3rows=[]
for name,T in P.items():
    missing=[m for m in p3_months if m not in T.index]
    if missing: raise RuntimeError(f'{name} missing P3 months: {missing[:5]}')
    path=portfolio_path(T.loc[p3_months],ret)
    m=perf_metrics(path['gross_return'],p3_rf)
    m.update({'variant':name,'cost_bps':0,'total_gross_L1_turnover':float(path.gross_L1_turnover.sum()),'annualized_mean_gross_L1_turnover':float(path.gross_L1_turnover.mean()*12)})
    p3rows.append(m)
p3=pd.DataFrame(p3rows)
p3.to_csv(OUT/'G6_PARENT_VARIANT_PERFORMANCE_COMMON_WINDOW_v0_17.csv',index=False)

# ADM VSS begins later (2009-10 signal); keep it as a separate inception-matched robustness rather than forcing it into the P3 common window.
adm_expr={
 'ADM_parent_VINEX': load_w('G5_ADM_PARENT_VINEX_TARGET_WEIGHTS_R_v0_15.csv'),
 'ADM_parent_VSS': load_w('G5_ADM_PARENT_VSS_CONTROL_TARGET_WEIGHTS_R_v0_15.csv'),
 'ADM_parent_OSMAX': load_w('G5_ADM_PARENT_OSMAX_CONTROL_TARGET_WEIGHTS_R_v0_15.csv'),
}
adm_common=common_months(list(adm_expr.values()))
adm_hold=[str(pd.Period(m,'M')+1) for m in adm_common]
adm_rf=ret.loc[adm_hold,'BIL']
admrows=[]
for name,T in adm_expr.items():
    path=portfolio_path(T.loc[adm_common],ret)
    m=perf_metrics(path['gross_return'],adm_rf)
    m.update({'variant':name,'signal_start':adm_common[0],'signal_end':adm_common[-1],
              'holding_start':adm_hold[0],'holding_end':adm_hold[-1],
              'total_gross_L1_turnover':float(path.gross_L1_turnover.sum()),
              'annualized_mean_gross_L1_turnover':float(path.gross_L1_turnover.mean()*12)})
    admrows.append(m)
pd.DataFrame(admrows).to_csv(OUT/'G6_ADM_EXPRESSION_PERFORMANCE_MATCHED_WINDOW_v0_17.csv',index=False)

# Compact deltas that directly address universe/rule adaptation questions.
M=p3.set_index('variant')
def delta(label,a,b):
    return {'comparison':label,'from_variant':a,'to_variant':b,
            'delta_CAGR':float(M.loc[b,'CAGR']-M.loc[a,'CAGR']),
            'delta_volatility':float(M.loc[b,'annualized_volatility']-M.loc[a,'annualized_volatility']),
            'delta_Sharpe':float(M.loc[b,'BIL_excess_Sharpe']-M.loc[a,'BIL_excess_Sharpe']),
            'delta_max_drawdown_abs':float(abs(M.loc[b,'max_drawdown'])-abs(M.loc[a,'max_drawdown'])),
            'delta_annualized_turnover':float(M.loc[b,'annualized_mean_gross_L1_turnover']-M.loc[a,'annualized_mean_gross_L1_turnover'])}
deltas=[
 delta('HAA universe change under parent rule','HAA_parent','HAA_parentRule_ADAAuniverse'),
 delta('HAA rule+selection change from parent-rule ADAA universe to current','HAA_parentRule_ADAAuniverse','HAA_ADAA_current'),
 delta('BAA Aggressive investable-expression change','BAA_Agg_parent','BAA_Agg_parentRule_ADAAexpression'),
 delta('FAA universe change under parent rule','FAA_parent','FAA_parentRule_ADAAuniverse'),
 delta('FAA parent-rule ADAA universe to ADAA canonical','FAA_parentRule_ADAAuniverse','FAA_ADAA_canonical'),
 delta('LAA equity-expression change under parent rule','LAA_parent','LAA_parentRule_ADAAequityExpression'),
 delta('LAA timing change on parent universe','LAA_parent','LAA_ADAAtiming_parentUniverse'),
]
pd.DataFrame(deltas).to_csv(OUT/'G6_PARENT_VARIANT_PERFORMANCE_DELTAS_v0_17.csv',index=False)

# Gate / summary record. This is descriptive evidence, not optimization.
def row(port,bps):
    z=metrics[(metrics.portfolio==port)&(metrics.cost_bps==bps)]
    if len(z)!=1: raise RuntimeError(f'missing metric row {port} {bps}')
    return z.iloc[0]
eq0=row('ADAA_equal20_canonical',0); eq25=row('ADAA_equal20_canonical',25)
h0=row('ADAA_historical_weights_canonical',0); h25=row('ADAA_historical_weights_canonical',25)
b0=row('Benchmark_60_40_SPY_IEF',0); b25=row('Benchmark_60_40_SPY_IEF',25)
no=row('ADAA_equal_no_LAA_rescaled',0); st=row('ADAA_equal_static_LAA_replacement',0); raa=row('ADAA_equal_RAA_replacement',0)
record={
 'version':'v0.17','formal_performance_opened':True,'performance_selection_performed':False,
 'primary_signal_window':[months[0],months[-1]],'primary_holding_window':[holding[0],holding[-1]],
 'canonical_faa_r_python_equivalence':'PASS','canonical_laa_information_state':'latest released state carried with true source-month metadata',
 'primary_specs':{'design_neutral':'20% each sleeve','historical_successor':'25/15/17.5/17.5/25'},
 'cost_grid_bps':COST_BPS,'historical_dashboard_cost_bps':25,'risk_free_for_sharpe':'BIL monthly total return',
 'key_descriptive_results':{
    'equal_gross_CAGR':float(eq0.CAGR),'equal_gross_vol':float(eq0.annualized_volatility),'equal_gross_MDD':float(eq0.max_drawdown),'equal_gross_Sharpe':float(eq0.BIL_excess_Sharpe),
    'equal_25bps_CAGR':float(eq25.CAGR),'equal_25bps_MDD':float(eq25.max_drawdown),'equal_25bps_Sharpe':float(eq25.BIL_excess_Sharpe),
    'historical_gross_CAGR':float(h0.CAGR),'historical_gross_vol':float(h0.annualized_volatility),'historical_gross_MDD':float(h0.max_drawdown),'historical_gross_Sharpe':float(h0.BIL_excess_Sharpe),
    'historical_25bps_CAGR':float(h25.CAGR),'historical_25bps_MDD':float(h25.max_drawdown),'historical_25bps_Sharpe':float(h25.BIL_excess_Sharpe),
    'benchmark_60_40_gross_CAGR':float(b0.CAGR),'benchmark_60_40_gross_MDD':float(b0.max_drawdown),'benchmark_60_40_gross_Sharpe':float(b0.BIL_excess_Sharpe),
    'benchmark_60_40_25bps_CAGR':float(b25.CAGR),
    'equal_no_LAA_gross_CAGR':float(no.CAGR),'equal_no_LAA_gross_vol':float(no.annualized_volatility),'equal_no_LAA_gross_MDD':float(no.max_drawdown),'equal_no_LAA_annualized_turnover':float(no.annualized_mean_gross_L1_turnover),
    'equal_with_LAA_annualized_turnover':float(eq0.annualized_mean_gross_L1_turnover),
    'equal_static_LAA_replacement_MDD':float(st.max_drawdown),'equal_RAA_replacement_MDD':float(raa.max_drawdown),
 },
 'interpretation_constraints':[
    'HAA is a strong standalone strategy in this sample; ADAA is not presented as an ex-post return-maximizing combination.',
    'LAA persistence reduces turnover and volatility in the equal-sleeve ensemble but does not mechanically improve every drawdown statistic.',
    'RAA replacement provides evidence that a slow/quasi-static anchor can materially alter drawdown geometry; this does not prove LAA is uniquely optimal.',
    'Parent/variant performance differences are descriptive consequences of previously frozen modifications, not justifications retrofitted from performance.',
    'All headline figures remain provisional until independent R performance/accounting reconciliation passes.'
 ]
}
(OUT/'G6_PERFORMANCE_OPENING_RECORD_v0_17.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
