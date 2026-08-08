#!/usr/bin/env python3
"""ADAA v0.19: dependence-aware inference, stress/failure decomposition, and benchmark expansion.

Frozen inputs only. No rule/universe/weight reselection. No parameter optimization.
Main inference uses circular moving-block bootstrap with 12-month blocks; 6/24-month
block-length sensitivity is reported. HAC mean-return-difference tests use Newey-West
lags 6 and 12. External benchmark family is pre-defined and intentionally simple.
"""
from pathlib import Path
from itertools import combinations
import argparse, json, math
import numpy as np
import pandas as pd
import statsmodels.api as sm

TOL=1e-12
SEED=20260807
B_MAIN=10000
B_SENS=5000

WFILES={
    'HAA':'G2_HAA_TARGET_WEIGHTS_R_v0_11_1.csv',
    'BAA':'G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_R_v0_11_1.csv',
    'ADM':'G2_ADM_TARGET_WEIGHTS_R_v0_11_1.csv',
    'FAA':'G3_FAA_CANONICAL_PEER_ONLY_EXACTN_TARGET_WEIGHTS_R_v0_16.csv',
    'LAA':'G2_LAA_CARRY_CALENDAR_TARGET_WEIGHTS_v0_11.csv',
    'RAA':'G5_RAA_PARENT_COMPARATOR_TARGET_WEIGHTS_R_v0_15.csv',
    'STATIC_LAA_CORE':'G5_STATIC_ADAA_LAA_RISKY_CORE_TARGET_WEIGHTS_R_v0_15.csv',
}
ALPHA_HIST={'HAA':.25,'BAA':.15,'ADM':.175,'FAA':.175,'LAA':.25}
ALPHA_EQUAL={'HAA':.2,'BAA':.2,'ADM':.2,'FAA':.2,'LAA':.2}

PREDEFINED_EPISODES=[
    ('GFC_sample_onset','2008-06','2009-03','Predeclared recognizable stress window; sample begins 2008-06'),
    ('2011_Euro_US_downgrade','2011-05','2011-10','Predeclared 2011 risk-off window'),
    ('2018_Q4','2018-10','2018-12','Predeclared Q4 2018 selloff'),
    ('COVID_crash','2020-02','2020-03','Predeclared COVID crash window'),
    ('COVID_rebound','2020-04','2020-08','Predeclared rapid rebound window'),
    ('2022_stock_bond_stress','2022-01','2022-10','Predeclared 2022 joint stock-bond stress window'),
]


def read_weights(out, f):
    d=pd.read_csv(out/f, index_col=0).astype(float); d.index=d.index.astype(str); return d

def next_month(m):
    return (pd.Period(m,freq='M')+1).strftime('%Y-%m')

def prev_month(m):
    return (pd.Period(m,freq='M')-1).strftime('%Y-%m')

def aggregate_weights(W, alphas, months):
    assets=sorted(set().union(*[set(W[k].columns) for k in alphas]))
    z=pd.DataFrame(0.0,index=months,columns=assets)
    for k,a in alphas.items():
        z=z.add(W[k].reindex(months).reindex(columns=assets,fill_value=0.0)*a,fill_value=0.0)
    if (z.sum(axis=1).sub(1).abs()>1e-10).any(): raise RuntimeError('aggregate weight sum failure')
    return z

def constant_weights(months, weights):
    return pd.DataFrame([weights]*len(months),index=months).fillna(0.0)

def portfolio_path(T, rmat):
    assets=list(T.columns); rows=[]; prev_eop=None
    for sm,row in T.iterrows():
        hm=next_month(sm)
        ar=rmat.loc[hm,assets].copy(); t=row.astype(float).copy()
        used=t.abs()>1e-15
        if ar[used].isna().any(): raise RuntimeError(f'missing used return {hm} {list(ar[used & ar.isna()].index)}')
        ar=ar.fillna(0.0)
        gross=float((t*ar).sum())
        turn=0.0 if prev_eop is None else float((t-prev_eop).abs().sum())
        prev_eop=t*(1+ar)/(1+gross)
        rows.append((sm,hm,gross,turn))
    return pd.DataFrame(rows,columns=['signal_month','holding_month','gross_return','gross_L1_turnover']).set_index('holding_month')

def max_dd(x):
    w=np.cumprod(1+np.asarray(x,float)); peak=np.maximum.accumulate(w); dd=w/peak-1
    return float(np.min(dd))

def perf(x,rf=None):
    x=np.asarray(x,float); n=len(x); wealth=np.cumprod(1+x)
    if rf is None: rf=np.zeros(n)
    rf=np.asarray(rf,float); ex=x-rf
    cagr=float(wealth[-1]**(12/n)-1)
    vol=float(np.std(x,ddof=1)*np.sqrt(12))
    sh=float(np.mean(ex)/np.std(ex,ddof=1)*np.sqrt(12)) if np.std(ex,ddof=1)>0 else np.nan
    return {'CAGR':cagr,'ann_mean':float(np.mean(x)*12),'vol':vol,'Sharpe':sh,'MDD':max_dd(x),'ending_wealth':float(wealth[-1])}

def circular_block_indices(n, block, rng):
    idx=[]
    while len(idx)<n:
        s=int(rng.integers(0,n)); idx.extend([(s+j)%n for j in range(block)])
    return np.array(idx[:n],dtype=int)

def bootstrap_pair(a,b,rf,block,B,seed):
    a=np.asarray(a,float); b=np.asarray(b,float); rf=np.asarray(rf,float); n=len(a)
    rng=np.random.default_rng(seed)
    # Build circular moving-block indices deterministically.
    nb=int(np.ceil(n/block))
    starts=rng.integers(0,n,size=(B,nb))
    offs=np.arange(block)
    idx=(starts[:,:,None]+offs[None,None,:])%n
    idx=idx.reshape(B,nb*block)[:,:n]
    A=a[idx]; C=b[idx]; R=rf[idx]
    annA=A.mean(axis=1)*12; annB=C.mean(axis=1)*12
    sdA=A.std(axis=1,ddof=1); sdB=C.std(axis=1,ddof=1)
    exA=A-R; exB=C-R
    shA=exA.mean(axis=1)/exA.std(axis=1,ddof=1)*np.sqrt(12)
    shB=exB.mean(axis=1)/exB.std(axis=1,ddof=1)*np.sqrt(12)
    cagrA=np.prod(1+A,axis=1)**(12/n)-1; cagrB=np.prod(1+C,axis=1)**(12/n)-1
    volA=sdA*np.sqrt(12); volB=sdB*np.sqrt(12)
    wealthA=np.cumprod(1+A,axis=1); wealthB=np.cumprod(1+C,axis=1)
    ddA=wealthA/np.maximum.accumulate(wealthA,axis=1)-1; ddB=wealthB/np.maximum.accumulate(wealthB,axis=1)-1
    mddA=ddA.min(axis=1); mddB=ddB.min(axis=1)
    return np.column_stack([annA-annB,shA-shB,cagrA-cagrB,volB-volA,mddA-mddB])

def summarize_boot(vals):
    names=['delta_ann_mean','delta_Sharpe','delta_CAGR','vol_advantage_B_minus_A','MDD_advantage_A_minus_B']
    out={}
    for i,nm in enumerate(names):
        v=vals[:,i]
        out[f'{nm}_p025']=float(np.quantile(v,.025)); out[f'{nm}_median']=float(np.quantile(v,.5)); out[f'{nm}_p975']=float(np.quantile(v,.975)); out[f'{nm}_prob_gt0']=float(np.mean(v>0))
    return out

def hac_mean_test(diff,lag):
    y=np.asarray(diff,float); X=np.ones((len(y),1)); fit=sm.OLS(y,X).fit(cov_type='HAC',cov_kwds={'maxlags':lag,'use_correction':True})
    return float(fit.params[0]*12),float(fit.tvalues[0]),float(fit.pvalues[0])

def cumret(s): return float(np.prod(1+np.asarray(s,float))-1)
def episode_mdd(s): return max_dd(np.asarray(s,float))

def rolling_worst(series,h):
    s=pd.Series(series).dropna(); vals=[]
    for i in range(h-1,len(s)):
        sub=s.iloc[i-h+1:i+1]; vals.append((cumret(sub.values),sub.index[0],sub.index[-1]))
    return min(vals,key=lambda x:x[0])

def change_indicator(W, months):
    x=W.reindex(months).fillna(0).round(12); ch=x.diff().abs().sum(axis=1)>TOL
    if len(ch): ch.iloc[0]=False
    return ch

def avg_pair_l1(Wdict,sm):
    ds=[]
    for a,b in combinations(Wdict,2):
        A=Wdict[a].reindex([sm]).fillna(0); B=Wdict[b].reindex([sm]).fillna(0)
        cols=sorted(set(A.columns)|set(B.columns)); ds.append(float((A.reindex(columns=cols,fill_value=0)-B.reindex(columns=cols,fill_value=0)).abs().sum(axis=1).iloc[0]))
    return float(np.mean(ds))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default=str(Path(__file__).resolve().parents[2])); args=ap.parse_args()
    root=Path(args.project_root).resolve(); out=root/'03_Data_and_Code'/'04_Outputs'; out.mkdir(exist_ok=True,parents=True)
    px=pd.read_csv(out/'G5_FROZEN_MONTH_END_ADJUSTED_R_v0_15.csv').set_index('signal_month'); px.index=px.index.astype(str)
    rmat=px.pct_change(fill_method=None).iloc[1:]; rmat.index=rmat.index.astype(str)
    W={k:read_weights(out,f) for k,f in WFILES.items()}
    months=sorted(set.intersection(*[set(W[k].index) for k in ['HAA','BAA','ADM','FAA','LAA']]))
    if len(months)!=218 or months[0]!='2008-05' or months[-1]!='2026-06': raise RuntimeError('primary window drift')
    holding=[next_month(m) for m in months]
    rf=rmat.loc[holding,'BIL'].astype(float)

    # Core and mechanism portfolios.
    T={}
    T['ADAA_equal20']=aggregate_weights(W,ALPHA_EQUAL,months)
    T['ADAA_historical']=aggregate_weights(W,ALPHA_HIST,months)
    no_laa={'HAA':.25,'BAA':.25,'ADM':.25,'FAA':.25}
    T['ADAA_no_LAA_rescaled']=aggregate_weights(W,no_laa,months)
    hist_raa={'HAA':.25,'BAA':.15,'ADM':.175,'FAA':.175,'RAA':.25}
    T['ADAA_hist_RAA_replacement']=aggregate_weights(W,hist_raa,months)
    hist_static={'HAA':.25,'BAA':.15,'ADM':.175,'FAA':.175,'STATIC_LAA_CORE':.25}
    T['ADAA_hist_static_anchor']=aggregate_weights(W,hist_static,months)
    for k in ['HAA','BAA','ADM','FAA','LAA','RAA']:
        T[f'Sleeve_{k}']=W[k].reindex(months)

    # Pre-defined simple external benchmark family; no benchmark shopping.
    T['Benchmark_SPY']=constant_weights(months,{'SPY':1.0})
    T['Benchmark_60_40_SPY_IEF']=constant_weights(months,{'SPY':.6,'IEF':.4})
    T['Benchmark_60_40_VTI_BND']=constant_weights(months,{'VTI':.6,'BND':.4})
    T['Benchmark_60_40_SPY_AGG']=constant_weights(months,{'SPY':.6,'AGG':.4})
    T['Benchmark_BIL']=constant_weights(months,{'BIL':1.0})

    P={k:portfolio_path(v,rmat) for k,v in T.items()}
    # Export all monthly paths, including 25-bps net.
    allpaths=[]
    for k,p in P.items():
        q=p.reset_index().copy(); q['portfolio']=k; q['net_return_25bps']=q['gross_return']-q['gross_L1_turnover']*.0025
        allpaths.append(q[['portfolio','signal_month','holding_month','gross_return','gross_L1_turnover','net_return_25bps']])
    pd.concat(allpaths,ignore_index=True).to_csv(out/'G6_ALL_MONTHLY_PATHS_FOR_INFERENCE_v0_19.csv',index=False)

    # Reconcile reconstructed core paths to the already R↔Python-validated v0.17 paths before inference.
    old=pd.read_csv(out/'G6_PRIMARY_MONTHLY_RETURN_TURNOVER_PATHS_v0_17.csv')
    mapping={'ADAA_equal20':'ADAA_equal20_canonical','ADAA_historical':'ADAA_historical_weights_canonical','Benchmark_60_40_SPY_IEF':'Benchmark_60_40_SPY_IEF'}
    rec=[]
    for nk,ok in mapping.items():
        o=old[old.portfolio==ok].set_index('holding_month'); q=P[nk]
        common=sorted(set(o.index)&set(q.index));
        dr=float(np.max(np.abs(o.loc[common,'gross_return'].to_numpy()-q.loc[common,'gross_return'].to_numpy())))
        dt=float(np.max(np.abs(o.loc[common,'gross_L1_turnover'].to_numpy()-q.loc[common,'gross_L1_turnover'].to_numpy())))
        rec.append({'reconstructed':nk,'v0_17_reference':ok,'months':len(common),'max_abs_return_diff':dr,'max_abs_turnover_diff':dt,'pass_1e_12':bool(max(dr,dt)<=1e-12)})
    rdf=pd.DataFrame(rec); rdf.to_csv(out/'G6_V019_PATH_RECONCILIATION_v0_19.csv',index=False)
    if not rdf.pass_1e_12.all(): raise RuntimeError('v0.19 reconstructed path does not match reconciled v0.17 path')

    # Benchmark performance family at gross and 25 bps.
    bench=[]
    for k in ['ADAA_equal20','ADAA_historical','Benchmark_SPY','Benchmark_60_40_SPY_IEF','Benchmark_60_40_VTI_BND','Benchmark_60_40_SPY_AGG','Benchmark_BIL','Sleeve_HAA']:
        p=P[k]
        for bps in [0,25]:
            x=p['gross_return']-p['gross_L1_turnover']*(bps/10000)
            m=perf(x.values,rf.values); m.update({'portfolio':k,'cost_bps':bps,'annualized_turnover':float(p.gross_L1_turnover.mean()*12)})
            bench.append(m)
    pd.DataFrame(bench).to_csv(out/'G6_EXTERNAL_BENCHMARK_FAMILY_v0_19.csv',index=False)

    # HAC + dependence-aware block-bootstrap comparisons.
    comps=[
        ('ADAA_historical','Benchmark_60_40_SPY_IEF','primary benchmark'),
        ('ADAA_historical','Benchmark_60_40_VTI_BND','broad-market 60/40 robustness'),
        ('ADAA_historical','Benchmark_SPY','equity benchmark'),
        ('ADAA_historical','Sleeve_HAA','ex-post strongest constituent diagnostic; not a fair ex-ante selector'),
        ('ADAA_historical','ADAA_no_LAA_rescaled','persistence-anchor mechanism control'),
        ('ADAA_historical','ADAA_hist_RAA_replacement','quasi-static-anchor replacement control'),
        ('ADAA_historical','ADAA_equal20','top-level weight robustness control'),
    ]
    inf=[]; sens=[]
    for ci,(a,b,role) in enumerate(comps):
        for basis,bps in [('gross',0),('net25',25)]:
            A=P[a]['gross_return']-P[a]['gross_L1_turnover']*(bps/10000)
            B=P[b]['gross_return']-P[b]['gross_L1_turnover']*(bps/10000)
            diff=A.values-B.values
            row={'portfolio_A':a,'portfolio_B':b,'comparison_role':role,'return_basis':basis,'cost_bps':bps,'months':len(diff)}
            for lag in [6,12]:
                am,t,pv=hac_mean_test(diff,lag); row[f'HAC{lag}_delta_ann_mean']=am; row[f'HAC{lag}_t']=t; row[f'HAC{lag}_p_two_sided']=pv
            vals=bootstrap_pair(A.values,B.values,rf.values,12,B_MAIN,SEED+ci*202+bps)
            row.update(summarize_boot(vals)); row['bootstrap_block_months']=12; row['bootstrap_reps']=B_MAIN
            inf.append(row)
            for block in [6,12,24]:
                vv=bootstrap_pair(A.values,B.values,rf.values,block,B_SENS,SEED+9000+ci*202+bps+block)
                ss=summarize_boot(vv)
                sens.append({'portfolio_A':a,'portfolio_B':b,'comparison_role':role,'return_basis':basis,'cost_bps':bps,'block_months':block,'bootstrap_reps':B_SENS,
                             'delta_Sharpe_p025':ss['delta_Sharpe_p025'],'delta_Sharpe_median':ss['delta_Sharpe_median'],'delta_Sharpe_p975':ss['delta_Sharpe_p975'],'delta_Sharpe_prob_gt0':ss['delta_Sharpe_prob_gt0'],
                             'delta_ann_mean_p025':ss['delta_ann_mean_p025'],'delta_ann_mean_p975':ss['delta_ann_mean_p975'],'delta_ann_mean_prob_gt0':ss['delta_ann_mean_prob_gt0']})
    pd.DataFrame(inf).to_csv(out/'G6_DEPENDENCE_AWARE_INFERENCE_v0_19.csv',index=False)
    pd.DataFrame(sens).to_csv(out/'G6_BLOCK_LENGTH_SENSITIVITY_v0_19.csv',index=False)

    # Stress episodes: predeclared named windows + data-defined worst windows.
    episodes=list(PREDEFINED_EPISODES)
    for src in ['Benchmark_SPY','Benchmark_60_40_SPY_IEF','ADAA_historical']:
        s=P[src]['gross_return']
        for h in [1,3,12]:
            v,st,en=rolling_worst(s,h)
            episodes.append((f'data_defined_{src}_worst_{h}m',st,en,f'Data-defined worst {h}-month window for {src}; not hand-picked'))
    # deduplicate exact names only
    erows=[]
    pnames=['ADAA_historical','ADAA_equal20','Benchmark_60_40_SPY_IEF','Benchmark_SPY','Sleeve_HAA','Sleeve_BAA','Sleeve_ADM','Sleeve_FAA','Sleeve_LAA']
    for eid,st,en,basis in episodes:
        for k in pnames:
            sub=P[k].loc[(P[k].index>=st)&(P[k].index<=en)]
            if sub.empty: continue
            gross=sub.gross_return; net=gross-sub.gross_L1_turnover*.0025
            erows.append({'episode':eid,'start':st,'end':en,'selection_basis':basis,'portfolio':k,'months':len(sub),
                          'gross_cumulative_return':cumret(gross),'net25_cumulative_return':cumret(net),'gross_episode_MDD':episode_mdd(gross),
                          'mean_monthly_turnover':float(sub.gross_L1_turnover.mean()),'total_turnover':float(sub.gross_L1_turnover.sum())})
    pd.DataFrame(erows).to_csv(out/'G6_STRESS_EPISODE_PERFORMANCE_v0_19.csv',index=False)

    # Canonical decision synchronization during episodes and worst active-return windows.
    coreW={k:W[k].reindex(months).fillna(0) for k in ['HAA','BAA','ADM','FAA','LAA']}
    changes={k:change_indicator(v,months) for k,v in coreW.items()}
    sync=[]
    for eid,st,en,basis in episodes:
        sms=[prev_month(h) for h in holding if st<=h<=en and prev_month(h) in months]
        if not sms: continue
        fr=[]; l1=[]
        for sm in sms:
            fr.append(np.mean([changes[k].loc[sm] for k in coreW])); l1.append(avg_pair_l1(coreW,sm))
        sync.append({'episode':eid,'start':st,'end':en,'signal_months':len(sms),'mean_fraction_sleeves_changing':float(np.mean(fr)),
                     'fraction_months_all_five_change':float(np.mean(np.array(fr)==1.0)),'mean_pairwise_L1_target_distance':float(np.mean(l1))})
    pd.DataFrame(sync).to_csv(out/'G6_STRESS_DECISION_SYNCHRONIZATION_v0_19.csv',index=False)

    # Sleeve arithmetic contribution attribution for historical ADAA in predeclared episodes only.
    contrib=[]
    for eid,st,en,basis in PREDEFINED_EPISODES:
        for k,a in ALPHA_HIST.items():
            sub=P[f'Sleeve_{k}'].loc[(P[f'Sleeve_{k}'].index>=st)&(P[f'Sleeve_{k}'].index<=en)]
            contrib.append({'episode':eid,'sleeve':k,'top_level_weight':a,'sleeve_cumulative_return':cumret(sub.gross_return),
                            'arithmetic_monthly_contribution_sum':float((a*sub.gross_return).sum()),'note':'Arithmetic contribution sums exactly by month but does not compound additively across an episode.'})
    pd.DataFrame(contrib).to_csv(out/'G6_STRESS_SLEEVE_ATTRIBUTION_v0_19.csv',index=False)

    # Failure diagnostics: worst active months and 3-month windows vs 60/40.
    act=P['ADAA_historical'].gross_return-P['Benchmark_60_40_SPY_IEF'].gross_return
    rows=[]
    for hm,val in act.nsmallest(10).items():
        sm=prev_month(hm); row={'type':'worst_active_1m','start':hm,'end':hm,'active_return':float(val),'ADAA_return':float(P['ADAA_historical'].loc[hm,'gross_return']),'benchmark_return':float(P['Benchmark_60_40_SPY_IEF'].loc[hm,'gross_return'])}
        row['fraction_sleeves_changing_signal_month']=float(np.mean([changes[k].loc[sm] for k in coreW])) if sm in months else np.nan
        row['avg_pairwise_L1_signal_month']=avg_pair_l1(coreW,sm) if sm in months else np.nan
        loc=list(P['Benchmark_SPY'].index).index(hm)
        prior=P['Benchmark_SPY'].gross_return.iloc[max(0,loc-3):loc]
        row['SPY_current_month_return']=float(P['Benchmark_SPY'].loc[hm,'gross_return'])
        row['SPY_prior_3m_return']=cumret(prior) if len(prior) else np.nan
        row['rebound_after_negative_prior3m']=bool(len(prior)==3 and row['SPY_prior_3m_return']<0 and row['SPY_current_month_return']>0.03)
        rows.append(row)
    rv=[]
    for i in range(2,len(act)):
        sub=act.iloc[i-2:i+1]; rv.append((cumret(P['ADAA_historical'].gross_return.iloc[i-2:i+1])-cumret(P['Benchmark_60_40_SPY_IEF'].gross_return.iloc[i-2:i+1]),sub.index[0],sub.index[-1]))
    for val,st,en in sorted(rv,key=lambda z:z[0])[:10]:
        sms=[prev_month(h) for h in act.loc[st:en].index if prev_month(h) in months]
        rows.append({'type':'worst_active_3m','start':st,'end':en,'active_return':float(val),'ADAA_return':cumret(P['ADAA_historical'].loc[st:en,'gross_return']),'benchmark_return':cumret(P['Benchmark_60_40_SPY_IEF'].loc[st:en,'gross_return']),
                     'fraction_sleeves_changing_signal_month':float(np.mean([[changes[k].loc[sm] for k in coreW] for sm in sms])) if sms else np.nan,
                     'avg_pairwise_L1_signal_month':float(np.mean([avg_pair_l1(coreW,sm) for sm in sms])) if sms else np.nan})
    pd.DataFrame(rows).to_csv(out/'G6_DATA_DEFINED_FAILURE_WINDOWS_v0_19.csv',index=False)

    # Evidence record.
    record={
        'version':'v0.19','primary_holding_window':[holding[0],holding[-1]],'rules_reselected':False,'weights_reselected':False,'benchmark_shopping':False,
        'bootstrap':{'method':'circular moving-block','main_block_months':12,'main_reps':B_MAIN,'sensitivity_blocks_months':[6,12,24],'sensitivity_reps':B_SENS,'seed':SEED},
        'HAC_lags_months':[6,12],
        'external_benchmarks':['SPY','60/40 SPY-IEF','60/40 VTI-BND','60/40 SPY-AGG','BIL'],
        'named_stress_windows':[x[0] for x in PREDEFINED_EPISODES],
        'interpretation_guardrail':'Inference quantifies sample uncertainty under dependence-aware resampling; it does not prove future outperformance or structural causality.'
    }
    (out/'G6_INFERENCE_STRESS_BENCHMARK_RECORD_v0_19.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('PASS: v0.19 dependence-aware inference, stress/failure decomposition, and benchmark expansion complete.')

if __name__=='__main__': main()
