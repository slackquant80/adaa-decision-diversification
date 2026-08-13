#!/usr/bin/env python3
"""ADAA v0.18.1 — moderate-optimization / broad-plateau robustness diagnostics.

Purpose
-------
Test the author's historical design recollection that ADAA was intended as a
moderately optimized, robust compromise rather than an ex-post maximum-backtest
portfolio. This script is diagnostic only. It MUST NOT be used to replace the
already-frozen canonical equal or historical ADAA top-level weights.

v0.18.1 hardens the historical v0.18 diagnostic without changing the
Sharpe/weight analysis: maximum drawdown includes initial wealth W0=1 and
used-asset return availability is checked before unused missing cells are
zero-filled.

Diagnostics
-----------
1) 100,000 deterministic feasible weight vectors with a 10% floor per sleeve
   (the same type of floor documented in the historical 2023 allocation search).
2) Full-sample constrained maximum gross Sharpe as an ex-post reference point.
3) Broad-plateau bands and local perturbations around the historical successor
   weights.
4) 60-month rolling optimal-weight instability.
5) 12-month moving-block bootstrap optimal-weight uncertainty.
6) A deployable 60-month rolling optimizer-chasing control versus fixed equal
   and historical weights on the same later-start sample, including 25bp costs.

No strategy rule, universe, sample start for the primary evidence, cost grid, or
canonical top-level weight is reselected from these results.
"""
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'03_Data_and_Code'/'04_Outputs'
SEED=20260807
RNG=np.random.default_rng(SEED)
SLEEVES=['HAA','BAA','ADM','FAA','LAA']
HIST=np.array([.25,.15,.175,.175,.25])
EQUAL=np.repeat(.2,5)
FLOOR=.10
N_SIMPLEX=100_000
N_LOCAL=10_000
N_BOOT=500
BOOT_BLOCK=12
ROLL=60
COSTS=[0,25,50]

# ---------- Frozen inputs ----------
px=pd.read_csv(OUT/'G5_FROZEN_MONTH_END_ADJUSTED_R_v0_15.csv')
px['signal_month']=px.signal_month.astype(str)
px=px.set_index('signal_month').astype(float)
asset_ret=px.pct_change(fill_method=None)
files={
'HAA':'G2_HAA_TARGET_WEIGHTS_R_v0_11_1.csv',
'BAA':'G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_R_v0_11_1.csv',
'ADM':'G2_ADM_TARGET_WEIGHTS_R_v0_11_1.csv',
'FAA':'G3_FAA_CANONICAL_PEER_ONLY_EXACTN_TARGET_WEIGHTS_R_v0_16.csv',
'LAA':'G2_LAA_CARRY_CALENDAR_TARGET_WEIGHTS_v0_11.csv',
}
W={}
for k,f in files.items():
    d=pd.read_csv(OUT/f); d['signal_month']=d.signal_month.astype(str)
    d=d.set_index('signal_month').astype(float)
    if ((d.sum(axis=1)-1).abs()>1e-10).any(): raise RuntimeError(f'weight-sum failure {k}')
    W[k]=d
months=sorted(set.intersection(*[set(x.index) for x in W.values()]))
holding=[str(pd.Period(m,'M')+1) for m in months]
if months[0]!='2008-05' or months[-1]!='2026-06' or len(months)!=218:
    raise RuntimeError('unexpected primary weight window')
rf=asset_ret.loc[holding,'BIL'].astype(float).to_numpy()

# sleeve gross returns and common underlying target tensor
assets=sorted(set().union(*[set(W[k].columns) for k in SLEEVES]))
WT=np.stack([W[k].loc[months].reindex(columns=assets,fill_value=0.0).to_numpy() for k in SLEEVES],axis=1) # t,s,a
AR_frame=asset_ret.loc[holding].reindex(columns=assets)
used_any=np.any(np.abs(WT)>1e-15,axis=1)
missing_used=used_any & AR_frame.isna().to_numpy()
if missing_used.any():
    t,a=np.argwhere(missing_used)[0]
    raise RuntimeError(f'missing used-asset return at {holding[t]}: {assets[a]}')
AR=AR_frame.fillna(0.0).to_numpy()
R=np.empty((len(months),len(SLEEVES)))
for s,k in enumerate(SLEEVES):
    R[:,s]=(WT[:,s,:]*AR).sum(axis=1)

# ---------- utility functions ----------
def sharpe_for(w, Rs=R, rfs=rf):
    ex=Rs@w-rfs
    sd=ex.std(ddof=1)
    return float(ex.mean()/sd*math.sqrt(12.0)) if sd>0 else -np.inf

def optimize_sharpe(Rs,rfs,x0=None):
    if x0 is None: x0=EQUAL.copy()
    def obj(w):
        ex=Rs@w-rfs; sd=ex.std(ddof=1)
        return -(ex.mean()/sd*math.sqrt(12.0)) if sd>0 else 1e9
    res=minimize(obj,x0,bounds=[(FLOOR,.60)]*5,
                 constraints={'type':'eq','fun':lambda w:w.sum()-1.0},
                 method='SLSQP',options={'ftol':1e-12,'maxiter':1000})
    if not res.success:
        res=minimize(obj,HIST.copy(),bounds=[(FLOOR,.60)]*5,
                     constraints={'type':'eq','fun':lambda w:w.sum()-1.0},
                     method='SLSQP',options={'ftol':1e-12,'maxiter':2000})
    if not res.success: raise RuntimeError('Sharpe optimizer failed')
    return res.x.astype(float), float(-res.fun)

def gross_metrics_from_returns(pr):
    ex=pr-rf
    wealth=np.cumprod(1+pr)
    cagr=float(wealth[-1]**(12/len(pr))-1)
    vol=float(pr.std(ddof=1)*math.sqrt(12))
    sh=float(ex.mean()/ex.std(ddof=1)*math.sqrt(12))
    wealth_w0=np.concatenate(([1.0],wealth))
    mdd=float((wealth_w0/np.maximum.accumulate(wealth_w0)-1).min())
    return cagr,vol,sh,mdd

def candidate_gross_metrics(weights,batch=5000):
    out=[]
    for i in range(0,len(weights),batch):
        A=weights[i:i+batch]
        pr=R@A.T
        ex=pr-rf[:,None]
        sh=ex.mean(axis=0)/ex.std(axis=0,ddof=1)*math.sqrt(12)
        wealth=np.cumprod(1+pr,axis=0)
        cagr=wealth[-1]**(12/len(months))-1
        vol=pr.std(axis=0,ddof=1)*math.sqrt(12)
        wealth_w0=np.vstack([np.ones((1,wealth.shape[1])),wealth])
        mdd=(wealth_w0/np.maximum.accumulate(wealth_w0,axis=0)-1).min(axis=0)
        out.append(np.c_[cagr,vol,sh,mdd])
    return np.vstack(out)

def account_paths(alpha_matrix, idx=None):
    """Cross-netted final-account path. alpha_matrix rows correspond to idx months."""
    if idx is None: idx=np.arange(len(months))
    alpha_matrix=np.asarray(alpha_matrix,float)
    if len(alpha_matrix)!=len(idx): raise ValueError('alpha/index length mismatch')
    prev=None; gross=[]; turn=[]
    for j,t in enumerate(idx):
        target=alpha_matrix[j]@WT[t]
        ar=AR[t]
        g=float(target@ar)
        tr=0.0 if prev is None else float(np.abs(target-prev).sum())
        eop=target*(1+ar)/(1+g)
        gross.append(g); turn.append(tr); prev=eop
    return np.asarray(gross),np.asarray(turn)

def cost_metrics(gross,turn,rfs,bps):
    x=gross-turn*(bps/10000.0)
    wealth=np.cumprod(1+x); n=len(x)
    cagr=float(wealth[-1]**(12/n)-1)
    vol=float(x.std(ddof=1)*math.sqrt(12))
    ex=x-rfs; sh=float(ex.mean()/ex.std(ddof=1)*math.sqrt(12))
    wealth_w0=np.concatenate(([1.0],wealth))
    mdd=float((wealth_w0/np.maximum.accumulate(wealth_w0)-1).min())
    annual_turn=float(turn.mean()*12)
    return cagr,vol,sh,mdd,annual_turn

# ---------- full-sample ex-post reference optimum ----------
best_w,best_sh=optimize_sharpe(R,rf,EQUAL)
refs=[]
for name,w in [('historical_successor',HIST),('equal_20',EQUAL),('expost_max_sharpe_reference',best_w)]:
    c,v,s,m=gross_metrics_from_returns(R@w)
    refs.append({'reference':name,**{f'w_{k}':float(w[i]) for i,k in enumerate(SLEEVES)},
                 'gross_CAGR':c,'gross_volatility':v,'gross_Sharpe':s,'gross_MDD':m,
                 'Sharpe_as_fraction_of_expost_max':s/best_sh,
                 'L1_distance_to_expost_max':float(np.abs(w-best_w).sum())})
refdf=pd.DataFrame(refs)
# Add cost-aware reference metrics using the frozen final-account cross-netted ledger.
for i,row in refdf.iterrows():
    w=np.array([row[f'w_{k}'] for k in SLEEVES],dtype=float)
    g,t=account_paths(np.tile(w,(len(months),1)))
    for bps in [25,50]:
        c,v,s,m,tr=cost_metrics(g,t,rf,bps)
        refdf.loc[i,f'CAGR_{bps}bps']=c
        refdf.loc[i,f'volatility_{bps}bps']=v
        refdf.loc[i,f'Sharpe_{bps}bps']=s
        refdf.loc[i,f'MDD_{bps}bps']=m
        refdf.loc[i,f'annualized_turnover_{bps}bps']=tr

# ---------- 100k feasible broad simplex ----------
# floor 10% consumes 50%; remaining 50% is Dirichlet-distributed.
simplex=FLOOR+(1-5*FLOOR)*RNG.dirichlet(np.ones(5),size=N_SIMPLEX)
M=candidate_gross_metrics(simplex)
# percentiles for reference points among feasible random vectors
for i,row in refdf.iterrows():
    refdf.loc[i,'Sharpe_percentile_in_100k']=float(np.mean(M[:,2] <= row.gross_Sharpe))
    refdf.loc[i,'CAGR_percentile_in_100k']=float(np.mean(M[:,0] <= row.gross_CAGR))
    refdf.loc[i,'MDD_percentile_in_100k']=float(np.mean(M[:,3] <= row.gross_MDD)) # larger (less negative) is better
refdf.to_csv(OUT/'G6_WEIGHT_PLATEAU_REFERENCE_POINTS_v0_18_1.csv',index=False)

# summary distribution and near-optimal breadth
summary=[]
for j,name in enumerate(['gross_CAGR','gross_volatility','gross_Sharpe','gross_MDD']):
    q=np.quantile(M[:,j],[0,.01,.05,.25,.5,.75,.95,.99,1])
    summary.append({'metric':name,**{f'q_{p}':float(v) for p,v in zip(['0','01','05','25','50','75','95','99','100'],q)}})
pd.DataFrame(summary).to_csv(OUT/'G6_WEIGHT_SIMPLEX_100K_DISTRIBUTION_v0_18_1.csv',index=False)

bands=[]
for frac in [.99,.975,.95,.90]:
    mask=M[:,2]>=best_sh*frac
    rec={'band':f'>={frac:.3f}_of_max_Sharpe','threshold':best_sh*frac,'count':int(mask.sum()),'fraction_of_100k':float(mask.mean())}
    for i,k in enumerate(SLEEVES):
        rec[f'{k}_min']=float(simplex[mask,i].min()) if mask.any() else np.nan
        rec[f'{k}_max']=float(simplex[mask,i].max()) if mask.any() else np.nan
    bands.append(rec)
for gap in [.01,.025,.05,.10]:
    mask=M[:,2]>=best_sh-gap
    rec={'band':f'within_{gap:.3f}_Sharpe_of_max','threshold':best_sh-gap,'count':int(mask.sum()),'fraction_of_100k':float(mask.mean())}
    for i,k in enumerate(SLEEVES):
        rec[f'{k}_min']=float(simplex[mask,i].min()) if mask.any() else np.nan
        rec[f'{k}_max']=float(simplex[mask,i].max()) if mask.any() else np.nan
    bands.append(rec)
pd.DataFrame(bands).to_csv(OUT/'G6_WEIGHT_NEAR_OPTIMAL_BANDS_v0_18_1.csv',index=False)

# ---------- deliberately local perturbations around historical weights ----------
local=[]
while sum(len(x) for x in local)<N_LOCAL:
    z=RNG.normal(size=(N_LOCAL,5)); z=z-z.mean(axis=1,keepdims=True)
    l1=np.abs(z).sum(axis=1,keepdims=True); z=z/np.where(l1==0,1,l1)
    radius=RNG.uniform(0,.20,size=(N_LOCAL,1))
    a=HIST+z*radius
    ok=(a>=FLOOR-1e-12).all(axis=1)&(a<=.60+1e-12).all(axis=1)&(np.abs(a.sum(axis=1)-1)<1e-10)
    local.append(a[ok])
local=np.vstack(local)[:N_LOCAL]
local_dist=np.abs(local-HIST).sum(axis=1)
local_rows=[]
# cost-aware cross-netting in batches to limit memory
for bps in COSTS:
    vals=[]
    for i in range(0,N_LOCAL,500):
        A=local[i:i+500]; C=len(A); prev=None
        gr=np.empty((len(months),C)); tr=np.empty_like(gr)
        for t in range(len(months)):
            targets=A@WT[t]
            gross=targets@AR[t]
            turnover=np.zeros(C) if prev is None else np.abs(targets-prev).sum(axis=1)
            eop=targets*(1+AR[t])/(1+gross)[:,None]
            gr[t]=gross; tr[t]=turnover; prev=eop
        x=gr-tr*(bps/10000.0); wealth=np.cumprod(1+x,axis=0)
        cagr=wealth[-1]**(12/len(months))-1
        vol=x.std(axis=0,ddof=1)*math.sqrt(12)
        ex=x-rf[:,None]; sh=ex.mean(axis=0)/ex.std(axis=0,ddof=1)*math.sqrt(12)
        wealth_w0=np.vstack([np.ones((1,wealth.shape[1])),wealth])
        mdd=(wealth_w0/np.maximum.accumulate(wealth_w0,axis=0)-1).min(axis=0)
        turnover=tr.mean(axis=0)*12
        vals.append(np.c_[cagr,vol,sh,mdd,turnover])
    V=np.vstack(vals)
    for radius in [.05,.10,.20]:
        mask=local_dist<=radius
        for j,mname in enumerate(['CAGR','volatility','Sharpe','MDD','annualized_gross_L1_turnover']):
            q=np.quantile(V[mask,j],[.05,.25,.5,.75,.95])
            local_rows.append({'cost_bps':bps,'max_L1_radius':radius,'metric':mname,'n':int(mask.sum()),
                               'q05':float(q[0]),'q25':float(q[1]),'median':float(q[2]),'q75':float(q[3]),'q95':float(q[4])})
pd.DataFrame(local_rows).to_csv(OUT/'G6_HISTORICAL_WEIGHT_LOCAL_PERTURBATION_v0_18_1.csv',index=False)

# ---------- 60m rolling optimum instability ----------
roll=[]; x0=EQUAL.copy()
for st in range(0,len(R)-ROLL+1):
    w,s=optimize_sharpe(R[st:st+ROLL],rf[st:st+ROLL],x0)
    roll.append({'window_start_holding_month':holding[st],
                 'window_end_holding_month':holding[st+ROLL-1],
                 **{f'w_{k}':float(w[i]) for i,k in enumerate(SLEEVES)},
                 'in_window_max_Sharpe':s,
                 'L1_distance_to_historical':float(np.abs(w-HIST).sum()),
                 'L1_distance_to_equal':float(np.abs(w-EQUAL).sum())})
    x0=w
rolldf=pd.DataFrame(roll)
rolldf.to_csv(OUT/'G6_ROLLING_60M_OPTIMAL_WEIGHT_PATH_v0_18_1.csv',index=False)

rsummary=[]
for k in SLEEVES:
    x=rolldf[f'w_{k}']
    rsummary.append({'sleeve':k,'min':float(x.min()),'q25':float(x.quantile(.25)),'median':float(x.median()),
                     'q75':float(x.quantile(.75)),'max':float(x.max()),'std':float(x.std(ddof=0)),
                     'floor_frequency':float((x<=FLOOR+1e-8).mean())})
pd.DataFrame(rsummary).to_csv(OUT/'G6_ROLLING_60M_OPTIMAL_WEIGHT_SUMMARY_v0_18_1.csv',index=False)

# ---------- moving-block bootstrap optimum uncertainty ----------
starts=np.arange(0,len(R)-BOOT_BLOCK+1)
boot=[]; x0=EQUAL.copy()
for b in range(N_BOOT):
    idx=[]
    while len(idx)<len(R):
        st=int(RNG.choice(starts)); idx.extend(range(st,st+BOOT_BLOCK))
    idx=np.asarray(idx[:len(R)])
    w,s=optimize_sharpe(R[idx],rf[idx],EQUAL if b%10==0 else x0)
    boot.append({'bootstrap_id':b+1,**{f'w_{k}':float(w[i]) for i,k in enumerate(SLEEVES)},
                 'bootstrap_max_Sharpe':s,
                 'L1_distance_to_historical':float(np.abs(w-HIST).sum()),
                 'L1_distance_to_equal':float(np.abs(w-EQUAL).sum())})
    x0=w
bootdf=pd.DataFrame(boot); bootdf.to_csv(OUT/'G6_BLOCK_BOOTSTRAP_OPTIMAL_WEIGHTS_v0_18_1.csv',index=False)
bsummary=[]
for k in SLEEVES:
    x=bootdf[f'w_{k}']
    q=x.quantile([.025,.25,.5,.75,.975]).to_numpy()
    bsummary.append({'sleeve':k,'q025':float(q[0]),'q25':float(q[1]),'median':float(q[2]),'q75':float(q[3]),'q975':float(q[4]),
                     'std':float(x.std(ddof=0)),'floor_frequency':float((x<=FLOOR+1e-5).mean()),
                     'largest_weight_frequency':float(np.mean(bootdf[[f'w_{j}' for j in SLEEVES]].idxmax(axis=1)==f'w_{k}'))})
pd.DataFrame(bsummary).to_csv(OUT/'G6_BLOCK_BOOTSTRAP_OPTIMAL_WEIGHT_SUMMARY_v0_18_1.csv',index=False)

# ---------- optimizer-chasing control ----------
# For signal month i, use the 60 completed holding returns ending in signal month i,
# then apply the estimated top-level weights to holding month i+1.
idxs=np.arange(ROLL,len(months))
alphas=[]; x0=EQUAL.copy()
for i in idxs:
    w,_=optimize_sharpe(R[i-ROLL:i],rf[i-ROLL:i],x0)
    alphas.append(w); x0=w
alphas=np.asarray(alphas)
controls={
    'rolling_60m_max_sharpe_control':alphas,
    'fixed_historical_successor':np.tile(HIST,(len(idxs),1)),
    'fixed_equal_20':np.tile(EQUAL,(len(idxs),1)),
}
control_rows=[]
for name,A in controls.items():
    g,t=account_paths(A,idx=idxs)
    for bps in [0,25]:
        c,v,s,m,tr=cost_metrics(g,t,rf[idxs],bps)
        control_rows.append({'control':name,'cost_bps':bps,'holding_start':holding[idxs[0]],'holding_end':holding[idxs[-1]],
                             'months':int(len(idxs)),'CAGR':c,'volatility':v,'Sharpe':s,'MDD':m,
                             'annualized_gross_L1_turnover':tr})
pd.DataFrame(control_rows).to_csv(OUT/'G6_ROLLING_OPTIMIZER_CHASING_CONTROL_v0_18_1.csv',index=False)

# ---------- compact evidence record ----------
hist_ref=refdf[refdf.reference=='historical_successor'].iloc[0]
eq_ref=refdf[refdf.reference=='equal_20'].iloc[0]
near95=pd.DataFrame(bands).query("band == '>=0.950_of_max_Sharpe'").iloc[0]
# local radius 20 / 25bps Sharpe row
locdf=pd.DataFrame(local_rows)
locsh=locdf[(locdf.cost_bps==25)&(locdf.max_L1_radius==.20)&(locdf.metric=='Sharpe')].iloc[0]
ctrl=pd.read_csv(OUT/'G6_ROLLING_OPTIMIZER_CHASING_CONTROL_v0_18_1.csv')
record={
    'version':'v0.18.1','status':'SUPPORTIVE_ROBUSTNESS_EVIDENCE',
    'author_recollection_tested':'ADAA was intended as moderate/limited optimization and robust architecture, not maximum historical backtest fit.',
    'diagnostic_only_no_reselection':True,
    'simplex_draws':N_SIMPLEX,'min_weight_per_sleeve':FLOOR,'random_seed':SEED,
    'expost_max_gross_sharpe':best_sh,
    'expost_max_weights':{k:float(best_w[i]) for i,k in enumerate(SLEEVES)},
    'historical_gross_sharpe':float(hist_ref.gross_Sharpe),
    'historical_fraction_of_expost_max_sharpe':float(hist_ref.Sharpe_as_fraction_of_expost_max),
    'historical_sharpe_percentile_of_100k':float(hist_ref.Sharpe_percentile_in_100k),
    'equal_fraction_of_expost_max_sharpe':float(eq_ref.Sharpe_as_fraction_of_expost_max),
    'fraction_of_feasible_100k_at_least_95pct_of_max_sharpe':float(near95.fraction_of_100k),
    'local_historical_L1_0_20_25bps_Sharpe_q05_q95':[float(locsh.q05),float(locsh.q95)],
    'rolling_60m_optimum_windows':int(len(rolldf)),
    'block_bootstrap_replications':N_BOOT,'block_months':BOOT_BLOCK,
    'rolling_optimizer_control_note':'Post-opening robustness diagnostic; not a pre-registered strategy and not a candidate canonical replacement.',
    'interpretation_constraints':[
        'The ex-post optimum is a diagnostic reference, not a strategy recommendation.',
        'Broad-plateau language is permitted only as a robustness interpretation, not proof of future performance.',
        'Bootstrap/rolling-optimum dispersion measures estimation instability; it does not identify the true future optimum.',
        'Historical and equal weights remain frozen canonical/reference specifications regardless of these results.'
    ]
}
(OUT/'G6_ROBUST_ARCHITECTURE_WEIGHT_PLATEAU_RECORD_v0_18_1.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
