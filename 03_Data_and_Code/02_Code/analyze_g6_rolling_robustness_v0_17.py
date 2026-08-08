#!/usr/bin/env python3
"""Rolling-window robustness diagnostics for the formally opened v0.17 evidence.
No selection or re-optimization is performed. Rolling return/risk distributions were pre-registered in v0.4.
"""
from pathlib import Path
import numpy as np, pandas as pd, json
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'03_Data_and_Code'/'04_Outputs'
px=pd.read_csv(OUT/'G5_FROZEN_MONTH_END_ADJUSTED_R_v0_15.csv'); px['signal_month']=px['signal_month'].astype(str); px=px.set_index('signal_month').astype(float)
ret=px.pct_change(fill_method=None)
def load(f):
 d=pd.read_csv(OUT/f); d['signal_month']=d['signal_month'].astype(str); return d.set_index('signal_month').astype(float)
W={
'HAA':load('G2_HAA_TARGET_WEIGHTS_R_v0_11_1.csv'),
'BAA':load('G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_R_v0_11_1.csv'),
'ADM':load('G2_ADM_TARGET_WEIGHTS_R_v0_11_1.csv'),
'FAA':load('G3_FAA_CANONICAL_PEER_ONLY_EXACTN_TARGET_WEIGHTS_R_v0_16.csv'),
'LAA':load('G2_LAA_CARRY_CALENDAR_TARGET_WEIGHTS_v0_11.csv'),
}
months=list(W['HAA'].index)
def path(T):
 vals={}
 for sm,t in T.loc[months].iterrows():
  hm=str(pd.Period(sm,'M')+1); ar=ret.loc[hm].reindex(t.index).fillna(0.0); vals[hm]=float((t*ar).sum())
 return pd.Series(vals)
S=pd.DataFrame({k:path(v) for k,v in W.items()})
S['ADAA_equal']=S[['HAA','BAA','ADM','FAA','LAA']].mean(axis=1)
S['ADAA_historical']=S[['HAA','BAA','ADM','FAA','LAA']].mul([.25,.15,.175,.175,.25],axis=1).sum(axis=1)
rf=ret.loc[S.index,'BIL']
sl=['HAA','BAA','ADM','FAA','LAA']
rows=[]
for h in [12,36,60]:
 rr=(1+S).rolling(h).apply(np.prod,raw=True)**(12.0/h)-1
 ex=S.sub(rf,axis=0); sh=ex.rolling(h).mean()/ex.rolling(h).std(ddof=1)*np.sqrt(12)
 valid_r=rr[sl].notna().all(axis=1); valid_s=sh[sl].notna().all(axis=1)
 for port in ['ADAA_equal','ADAA_historical']:
  med=rr.loc[valid_r,sl].median(axis=1); ranks=rr.loc[valid_r,sl+[port]].rank(axis=1,ascending=False,method='average')[port]
  medsh=sh.loc[valid_s,sl].median(axis=1); ranksh=sh.loc[valid_s,sl+[port]].rank(axis=1,ascending=False,method='average')[port]
  rows.append({'window_months':h,'portfolio':port,
    'rolling_return_windows':int(valid_r.sum()),'fraction_annualized_return_above_median_sleeve':float((rr.loc[valid_r,port]>med).mean()),
    'mean_return_rank_among_5_sleeves_plus_portfolio':float(ranks.mean()),'fraction_return_rank_top2':float((ranks<=2).mean()),'fraction_return_rank_bottom2':float((ranks>=5).mean()),
    'rolling_sharpe_windows':int(valid_s.sum()),'fraction_Sharpe_above_median_sleeve':float((sh.loc[valid_s,port]>medsh).mean()),
    'mean_Sharpe_rank_among_5_sleeves_plus_portfolio':float(ranksh.mean()),'fraction_Sharpe_rank_top2':float((ranksh<=2).mean()),'fraction_Sharpe_rank_bottom2':float((ranksh>=5).mean())})
pd.DataFrame(rows).to_csv(OUT/'G6_ROLLING_ROBUSTNESS_RANKS_v0_17.csv',index=False)
# Which standalone sleeve is best through time (not used to select the ensemble).
bestrows=[]
for h in [12,36,60]:
 rr=(1+S[sl]).rolling(h).apply(np.prod,raw=True)**(12.0/h)-1
 sh=S[sl].sub(rf,axis=0).rolling(h).mean()/S[sl].sub(rf,axis=0).rolling(h).std(ddof=1)*np.sqrt(12)
 for metric,z in [('return',rr),('Sharpe',sh)]:
  valid=z.notna().all(axis=1); best=z.loc[valid].idxmax(axis=1)
  for sleeve,freq in best.value_counts(normalize=True).items():
   bestrows.append({'window_months':h,'metric':metric,'sleeve':sleeve,'fraction_best':float(freq),'n_windows':int(valid.sum())})
pd.DataFrame(bestrows).to_csv(OUT/'G6_ROLLING_BEST_SLEEVE_FREQUENCY_v0_17.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))
