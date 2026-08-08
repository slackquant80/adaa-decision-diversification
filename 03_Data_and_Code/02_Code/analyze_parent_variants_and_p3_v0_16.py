#!/usr/bin/env python3
"""ADAA v0.16 performance-blind parent/variant and P3 decision-structure analysis.

Purpose
-------
1) Audit whether parent-to-ADAA modifications preserve or change decision behavior.
2) Test whether the What / When / How-much decision fingerprint generalizes beyond
   the exact current ADAA five-sleeve set.
3) Test whether persistence is broader than LAA alone using RAA/static controls.

This script does NOT calculate strategy returns, portfolio returns, CAGR, Sharpe,
MDD, Calmar, or optimize any strategy or universe.
"""
from __future__ import annotations
from pathlib import Path
from itertools import combinations
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '03_Data_and_Code' / '04_Outputs'
TOL = 1e-12
COMMON_START, COMMON_END = '2008-07', '2026-06'

# ---------- utilities ----------
def read_w(name: str) -> pd.DataFrame:
    p = OUT / name
    d = pd.read_csv(p)
    d['signal_month'] = d['signal_month'].astype(str)
    return d.set_index('signal_month').astype(float).sort_index()

def slice_common(d: pd.DataFrame, start=COMMON_START, end=COMMON_END) -> pd.DataFrame:
    return d.loc[(d.index >= start) & (d.index <= end)].copy()

def align(a,b,start=COMMON_START,end=COMMON_END):
    a,b=slice_common(a,start,end),slice_common(b,start,end)
    idx=a.index.intersection(b.index)
    cols=sorted(set(a.columns)|set(b.columns))
    return a.reindex(index=idx,columns=cols,fill_value=0.0), b.reindex(index=idx,columns=cols,fill_value=0.0)

def change_indicator(d: pd.DataFrame) -> pd.Series:
    x=d.round(12)
    ch=x.diff().abs().sum(axis=1)>TOL
    if len(ch): ch.iloc[0]=False
    return ch

def transition_jaccard(a,b):
    ca,cb=change_indicator(a),change_indicator(b)
    idx=ca.index.intersection(cb.index); ca,cb=ca.loc[idx],cb.loc[idx]
    u=int((ca|cb).sum()); i=int((ca&cb).sum())
    return i/u if u else np.nan

def run_lengths(d):
    ch=change_indicator(d); g=ch.cumsum(); lens=g.value_counts().sort_index().to_numpy()
    return lens

def fingerprint(d: pd.DataFrame):
    d=slice_common(d)
    if d.empty: return {}
    ch=change_indicator(d); lens=run_lengths(d)
    active=(d.abs()>TOL).sum(axis=1)
    hhi=(d*d).sum(axis=1)
    effn=1/hhi.replace(0,np.nan)
    tv=0.5*d.diff().abs().sum(axis=1)
    tv_changed=tv[ch]
    return {
        'months':len(d),
        'change_rate':float(ch.iloc[1:].mean()) if len(d)>1 else np.nan,
        'transition_months':int(ch.sum()),
        'mean_constant_weight_run_months':float(lens.mean()) if len(lens) else np.nan,
        'max_constant_weight_run_months':int(lens.max()) if len(lens) else 0,
        'mean_active_assets':float(active.mean()),
        'median_active_assets':float(active.median()),
        'mean_hhi':float(hhi.mean()),
        'mean_effective_n':float(effn.mean()),
        'mean_target_turnover_all_months':float(tv.iloc[1:].mean()) if len(tv)>1 else np.nan,
        'mean_target_turnover_changed_months':float(tv_changed.mean()) if len(tv_changed) else 0.0,
    }

# semantic exposure aliases only where economic-expression comparison is intended.
ALIASES={
    'VEA':'DEV_EXUS','EFA':'DEV_EXUS',
    'VWO':'EM_EQ','EEM':'EM_EQ',
    'BND':'US_AGG_BOND','AGG':'US_AGG_BOND',
    'GSG':'BROAD_COMMODITY','DBC':'BROAD_COMMODITY',
    'VINEX':'EXUS_SMALL','VSS':'EXUS_SMALL','OSMAX':'EXUS_SMALL',
}
def semantic(d):
    z={}
    for c in d.columns:
        k=ALIASES.get(c,c)
        z[k]=z.get(k,0)+d[c]
    return pd.DataFrame(z,index=d.index)

def pair_metrics(a,b, semantic_alias=False):
    if semantic_alias: a,b=semantic(a),semantic(b)
    aa,bb=align(a,b)
    l1=(aa-bb).abs().sum(axis=1)
    # holdings overlap
    jac=[]
    for m in aa.index:
        sa=set(aa.columns[aa.loc[m].abs()>TOL]); sb=set(bb.columns[bb.loc[m].abs()>TOL])
        jac.append(len(sa&sb)/len(sa|sb) if sa|sb else 1.0)
    return {
      'common_months':len(aa),
      'mean_L1':float(l1.mean()),
      'median_L1':float(l1.median()),
      'identical_weight_rate':float((l1<=TOL).mean()),
      'mean_holdings_jaccard':float(np.mean(jac)),
      'transition_jaccard':float(transition_jaccard(aa,bb)),
      'change_rate_a':fingerprint(aa)['change_rate'],
      'change_rate_b':fingerprint(bb)['change_rate'],
      'mean_effective_n_a':fingerprint(aa)['mean_effective_n'],
      'mean_effective_n_b':fingerprint(bb)['mean_effective_n'],
    }

def state_agreement(trace_a,trace_b,col_a,col_b):
    a=pd.read_csv(OUT/trace_a); b=pd.read_csv(OUT/trace_b)
    a['signal_month']=a['signal_month'].astype(str); b['signal_month']=b['signal_month'].astype(str)
    x=a[['signal_month',col_a]].merge(b[['signal_month',col_b]],on='signal_month',suffixes=('_a','_b'))
    x=x[(x.signal_month>=COMMON_START)&(x.signal_month<=COMMON_END)]
    return float((x[f'{col_a}_a']==x[f'{col_b}_b']).mean()), len(x)

# ---------- load independently verified current ADAA ----------
current={
 'ADAA_HAA':read_w('G2_HAA_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv'),
 'ADAA_BAA_Aggressive':read_w('G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv'),
 'ADAA_ADM':read_w('G2_ADM_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv'),
 'ADAA_FAA_legacy':read_w('G2_FAA_LEGACY_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv'),
 # Information-state policy frozen in G3; identical to legacy on overlap and continues through missing observation window.
 'ADAA_LAA_info_state':read_w('G2_LAA_CARRY_CALENDAR_TARGET_WEIGHTS_v0_11.csv'),
}
parent={
 'HAA_parent':read_w('G5_HAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv'),
 'HAA_parent_rule_ADAA_universe':read_w('G5_HAA_PARENT_RULE_ADAA_UNIVERSE_TARGET_WEIGHTS_R_v0_15.csv'),
 'HAA_ADAA_rule_parent_universe':read_w('G5_HAA_ADAA_RULE_PARENT_UNIVERSE_TARGET_WEIGHTS_R_v0_15.csv'),
 'BAA_Agg_parent':read_w('G5_BAA_AGGRESSIVE_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv'),
 'BAA_Agg_parent_rule_ADAA_proxy':read_w('G5_BAA_AGGRESSIVE_PARENT_RULE_ADAA_PROXY_TARGET_WEIGHTS_R_v0_15.csv'),
 'BAA_Balanced_parent':read_w('G5_BAA_BALANCED_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv'),
 'BAA_Balanced_ADAA_proxy':read_w('G5_BAA_BALANCED_ADAA_PROXY_EXPRESSION_TARGET_WEIGHTS_R_v0_15.csv'),
 'ADM_parent_VINEX':read_w('G5_ADM_PARENT_VINEX_TARGET_WEIGHTS_R_v0_15.csv'),
 'ADM_parent_VSS':read_w('G5_ADM_PARENT_VSS_CONTROL_TARGET_WEIGHTS_R_v0_15.csv'),
 'ADM_parent_OSMAX':read_w('G5_ADM_PARENT_OSMAX_CONTROL_TARGET_WEIGHTS_R_v0_15.csv'),
 'FAA_parent':read_w('G5_FAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv'),
 'FAA_parent_rule_ADAA_universe':read_w('G5_FAA_PARENT_RULE_ADAA_UNIVERSE_TARGET_WEIGHTS_R_v0_15.csv'),
 'LAA_parent':read_w('G5_LAA_PARENT_PP_TARGET_WEIGHTS_R_v0_15.csv'),
 'LAA_parent_rule_ADAA_equity':read_w('G5_LAA_PARENT_RULE_ADAA_EQUITY_EXPRESSION_TARGET_WEIGHTS_R_v0_15.csv'),
 'LAA_ADAA_timing_parent_universe':read_w('G5_LAA_ADAA_TIMING_PARENT_UNIVERSE_TARGET_WEIGHTS_R_v0_15.csv'),
 'RAA_parent':read_w('G5_RAA_PARENT_COMPARATOR_TARGET_WEIGHTS_R_v0_15.csv'),
 'Static_LAA_parent_core':read_w('G5_STATIC_LAA_PARENT_RISKY_CORE_TARGET_WEIGHTS_R_v0_15.csv'),
 'Static_ADAA_LAA_core':read_w('G5_STATIC_ADAA_LAA_RISKY_CORE_TARGET_WEIGHTS_R_v0_15.csv'),
}

# ---------- fingerprint table ----------
all_panels={**current,**parent}
fp=[]
for name,d in all_panels.items():
    r={'panel':name,**fingerprint(d)}
    fp.append(r)
fpdf=pd.DataFrame(fp)
fpdf.to_csv(OUT/'G5_P3_DECISION_FINGERPRINTS_v0_16.csv',index=False)

# ---------- parent -> ADAA decomposition ----------
comparisons=[
 ('HAA_universe_effect_parent_rule','HAA_parent','HAA_parent_rule_ADAA_universe',True,'universe'),
 ('HAA_rule_effect_parent_universe','HAA_parent','HAA_ADAA_rule_parent_universe',False,'rule'),
 ('HAA_rule_effect_ADAA_universe','HAA_parent_rule_ADAA_universe','ADAA_HAA',False,'rule'),
 ('HAA_full_parent_to_ADAA','HAA_parent','ADAA_HAA',True,'rule+universe'),
 ('BAA_Agg_proxy_expression','BAA_Agg_parent','BAA_Agg_parent_rule_ADAA_proxy',True,'investable_expression'),
 ('BAA_Agg_current_vs_parent_rule_proxy','BAA_Agg_parent_rule_ADAA_proxy','ADAA_BAA_Aggressive',False,'residual_rule_check'),
 ('BAA_Balanced_proxy_expression','BAA_Balanced_parent','BAA_Balanced_ADAA_proxy',True,'investable_expression'),
 ('ADM_parent_to_ADAA','ADM_parent_VINEX','ADAA_ADM',False,'major_rule+universe_variant'),
 ('FAA_universe_effect_parent_rule','FAA_parent','FAA_parent_rule_ADAA_universe',True,'universe'),
 ('FAA_rule_effect_ADAA_universe','FAA_parent_rule_ADAA_universe','ADAA_FAA_legacy',False,'rule'),
 ('FAA_full_parent_to_ADAA','FAA_parent','ADAA_FAA_legacy',True,'rule+universe'),
 ('LAA_equity_expression_parent_rule','LAA_parent','LAA_parent_rule_ADAA_equity',False,'persistent_equity_expression'),
 ('LAA_timing_effect_parent_universe','LAA_parent','LAA_ADAA_timing_parent_universe',False,'timing_information_rule'),
 ('LAA_timing_effect_ADAA_equity','LAA_parent_rule_ADAA_equity','ADAA_LAA_info_state',False,'timing_information_rule'),
 ('LAA_full_parent_to_ADAA','LAA_parent','ADAA_LAA_info_state',False,'rule+universe'),
]
rows=[]
for exp,a,b,use_alias,dim in comparisons:
    A=all_panels[a]; B=all_panels[b]
    raw=pair_metrics(A,B,False); sem=pair_metrics(A,B,use_alias) if use_alias else raw
    row={'experiment':exp,'panel_a':a,'panel_b':b,'dimension':dim,'semantic_alias_applied':use_alias}
    row.update({f'raw_{k}':v for k,v in raw.items()})
    row.update({f'semantic_{k}':v for k,v in sem.items()})
    rows.append(row)
pv=pd.DataFrame(rows)
pv.to_csv(OUT/'G5_PARENT_VARIANT_DECISION_EFFECTS_v0_16.csv',index=False)

# State/regime comparisons where state variable is genuinely commensurable.
state_rows=[]
state_specs=[
 ('HAA_parent_vs_parent_rule_ADAA_universe','G5_HAA_PARENT_PP_TRACE_R_v0_15.csv','G5_HAA_PARENT_RULE_ADAA_UNIVERSE_TRACE_R_v0_15.csv','regime','regime'),
 ('HAA_parent_vs_ADAA_rule_parent_universe','G5_HAA_PARENT_PP_TRACE_R_v0_15.csv','G5_HAA_ADAA_RULE_PARENT_UNIVERSE_TRACE_R_v0_15.csv','regime','regime'),
 ('BAA_Agg_parent_vs_proxy','G5_BAA_AGGRESSIVE_PARENT_PP_TRACE_R_v0_15.csv','G5_BAA_AGGRESSIVE_PARENT_RULE_ADAA_PROXY_TRACE_R_v0_15.csv','regime','regime'),
 ('BAA_Balanced_parent_vs_proxy','G5_BAA_BALANCED_PARENT_PP_TRACE_R_v0_15.csv','G5_BAA_BALANCED_ADAA_PROXY_EXPRESSION_TRACE_R_v0_15.csv','regime','regime'),
 ('LAA_parent_vs_equity_expression','G5_LAA_PARENT_PP_TRACE_R_v0_15.csv','G5_LAA_PARENT_RULE_ADAA_EQUITY_EXPRESSION_TRACE_R_v0_15.csv','riskoff','riskoff'),
 ('LAA_parent_vs_ADAA_timing','G5_LAA_PARENT_PP_TRACE_R_v0_15.csv','G5_LAA_ADAA_TIMING_PARENT_UNIVERSE_TRACE_R_v0_15.csv','riskoff','riskoff'),
]
for name,fa,fb,ca,cb in state_specs:
    agr,n=state_agreement(fa,fb,ca,cb); state_rows.append({'comparison':name,'months':n,'state_agreement_rate':agr})
# Current ADAA HAA uses the same TIP canary state variable as parent HAA.
hp=pd.read_csv(OUT/'G5_HAA_PARENT_PP_TRACE_R_v0_15.csv')[['signal_month','regime']]
hc=pd.read_csv(OUT/'G2_DECISION_PANEL_INDEPENDENT_v0_11.csv')
hc=hc[hc['sleeve']=='HAA'][['signal_month','state']].copy(); hc['regime_current']=(hc['state']=='risk').astype(int)
hx=hp.merge(hc[['signal_month','regime_current']],on='signal_month'); hx=hx[(hx.signal_month>=COMMON_START)&(hx.signal_month<=COMMON_END)]
state_rows.append({'comparison':'HAA_parent_vs_current_ADAA_regime','months':len(hx),'state_agreement_rate':float((hx.regime==hx.regime_current).mean())})
# Current information-state LAA versus parent-rule ADAA-equity expression: isolates timing/information policy.
lp=pd.read_csv(OUT/'G5_LAA_PARENT_RULE_ADAA_EQUITY_EXPRESSION_TRACE_R_v0_15.csv')[['signal_month','riskoff']]
lc=pd.read_csv(OUT/'G2_LAA_CARRY_CALENDAR_DECISION_CONTROL_v0_11.csv')[['signal_month','state']].copy(); lc['riskoff_current']=(lc['state']=='defensive').astype(int)
lx=lp.merge(lc[['signal_month','riskoff_current']],on='signal_month'); lx=lx[(lx.signal_month>=COMMON_START)&(lx.signal_month<=COMMON_END)]
state_rows.append({'comparison':'LAA_parent_rule_ADAA_equity_vs_current_info_state','months':len(lx),'state_agreement_rate':float((lx.riskoff==lx.riskoff_current).mean())})
pd.DataFrame(state_rows).to_csv(OUT/'G5_PARENT_VARIANT_STATE_AGREEMENT_v0_16.csv',index=False)

# ADM expression robustness: map VINEX/VSS/OSMAX to common EXUS_SMALL role and compare selections.
adm_controls={'VINEX':parent['ADM_parent_VINEX'],'VSS':parent['ADM_parent_VSS'],'OSMAX':parent['ADM_parent_OSMAX']}
adm_rows=[]
for (na,a),(nb,b) in combinations(adm_controls.items(),2):
    pm=pair_metrics(a,b,True)
    adm_rows.append({'vehicle_a':na,'vehicle_b':nb,**pm})
pd.DataFrame(adm_rows).to_csv(OUT/'G5_ADM_EXPRESSION_ROBUSTNESS_v0_16.csv',index=False)

# ---------- P3 generalization ----------
# Main source-faithful/generalization set. Current ADAA variants are retained as reference,
# while parent/RAA/static controls establish that the dimensions are not unique to exact ADAA five.
p3_names=[
 'ADAA_HAA','ADAA_BAA_Aggressive','ADAA_ADM','ADAA_FAA_legacy','ADAA_LAA_info_state',
 'HAA_parent','BAA_Agg_parent','BAA_Balanced_parent','ADM_parent_VINEX','FAA_parent','LAA_parent','RAA_parent','Static_LAA_parent_core'
]
p3={k:all_panels[k] for k in p3_names}

# Pairwise structural geometry on common window. Raw ticker geometry is used as a literal portfolio-decision comparison;
# no return information enters this table.
pair=[]
for a,b in combinations(p3_names,2):
    m=pair_metrics(p3[a],p3[b],False)
    pair.append({'panel_a':a,'panel_b':b,**m})
p3pair=pd.DataFrame(pair)
p3pair.to_csv(OUT/'G5_P3_PAIRWISE_DECISION_GEOMETRY_v0_16.csv',index=False)

# Persistence-specific comparison: is slow clock unique to LAA?
persist_names=['ADAA_LAA_info_state','LAA_parent','RAA_parent','Static_LAA_parent_core','ADAA_HAA','ADAA_BAA_Aggressive','ADAA_ADM','ADAA_FAA_legacy','HAA_parent','BAA_Agg_parent','BAA_Balanced_parent','ADM_parent_VINEX','FAA_parent']
persist=fpdf.set_index('panel').loc[persist_names].reset_index()
persist.to_csv(OUT/'G5_P3_PERSISTENCE_GENERALIZATION_v0_16.csv',index=False)

# Dimension-spread record: demonstrate that What/When/How-much are empirically non-degenerate across non-ADAA controls.
controls=['HAA_parent','BAA_Agg_parent','BAA_Balanced_parent','ADM_parent_VINEX','FAA_parent','LAA_parent','RAA_parent','Static_LAA_parent_core']
c=fpdf.set_index('panel').loc[controls]
spread=[]
for dim in ['change_rate','mean_active_assets','mean_effective_n','mean_target_turnover_changed_months']:
    vals=c[dim]
    spread.append({'dimension_metric':dim,'n_controls':len(vals),'min':float(vals.min()),'max':float(vals.max()),'range':float(vals.max()-vals.min()),'std':float(vals.std(ddof=0))})
pd.DataFrame(spread).to_csv(OUT/'G5_P3_DIMENSION_SPREAD_v0_16.csv',index=False)

# Key deterministic conclusions, phrased as gate evidence not marketing claims.
def getfp(name,col): return float(fpdf.set_index('panel').loc[name,col])
def getpv(exp,col): return float(pv.set_index('experiment').loc[exp,col])
rec={
 'version':'v0.16',
 'performance_blind':True,
 'headline_performance_computed':False,
 'p3_common_signal_window':[COMMON_START,COMMON_END],
 'parent_r_python_equivalence_required':True,
 'key_evidence':{
   'BAA_Agg_current_vs_parent_rule_proxy_mean_L1':getpv('BAA_Agg_current_vs_parent_rule_proxy','raw_mean_L1'),
   'BAA_Agg_current_vs_parent_rule_proxy_identical_rate':getpv('BAA_Agg_current_vs_parent_rule_proxy','raw_identical_weight_rate'),
   'LAA_parent_change_rate':getfp('LAA_parent','change_rate'),
   'ADAA_LAA_change_rate':getfp('ADAA_LAA_info_state','change_rate'),
   'RAA_change_rate':getfp('RAA_parent','change_rate'),
   'Static_control_change_rate':getfp('Static_LAA_parent_core','change_rate'),
   'ADM_parent_change_rate':getfp('ADM_parent_VINEX','change_rate'),
   'ADAA_ADM_change_rate':getfp('ADAA_ADM','change_rate'),
   'FAA_parent_change_rate':getfp('FAA_parent','change_rate'),
   'ADAA_FAA_change_rate':getfp('ADAA_FAA_legacy','change_rate'),
 },
 'gate_interpretation':{
   'P3_generalization_beyond_exact_five':'TESTED_STRUCTURALLY',
   'parent_variant_rationale':'DECISION_EFFECTS_QUANTIFIED_BEFORE_PERFORMANCE',
   'persistence_generalization':'TESTED_WITH_LAA_PARENT_RAA_AND_STATIC_CONTROL',
 },
}
(OUT/'G5_P3_AND_PARENT_VARIANT_RECORD_v0_16.json').write_text(json.dumps(rec,indent=2),encoding='utf-8')
print('PASS: v0.16 performance-blind parent/variant and P3 structural analysis written.')
print('No strategy or portfolio performance was calculated.')
