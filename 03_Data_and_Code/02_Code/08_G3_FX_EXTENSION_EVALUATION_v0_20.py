#!/usr/bin/env python3
"""ADAA v0.20 — KRW/USD extension evaluation.

Frozen inputs only. Reproduces the legacy 1306-day USD/KRW z-score signal independently,
then evaluates the historical currency-exposure overlay without reselecting thresholds.
The analysis is an application-layer diagnostic, not a claim that the legacy hedge rule is optimal.

Important limitation: the "fully hedged" leg is the legacy dashboard proxy (USD portfolio return
without FX translation). Forward carry, forward/NDF transaction costs, collateral and tax are not
modeled. Therefore results are currency-exposure illustrations, not a complete executable hedge P&L.
"""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd

SEED=20260807
B=10000
BLOCK=12


def max_dd(x):
    x=np.asarray(x,float)
    w=np.cumprod(1+x)
    return float(np.min(w/np.maximum.accumulate(w)-1))


def perf(x):
    x=np.asarray(x,float); x=x[np.isfinite(x)]; n=len(x)
    growth=float(np.prod(1+x))
    cagr=float(growth**(12/n)-1)
    vol=float(np.std(x,ddof=1)*np.sqrt(12))
    ann=float(np.mean(x)*12)
    zero_sharpe=float(ann/vol) if vol>0 else np.nan
    return dict(months=n,CAGR=cagr,annualized_arithmetic_mean=ann,
                annualized_volatility=vol,zero_rate_Sharpe=zero_sharpe,
                max_drawdown=max_dd(x),ending_growth_of_1=growth)


def overlay_return(base,fx,u):
    base=np.asarray(base,float); fx=np.asarray(fx,float); u=np.asarray(u,float)
    # (1-u) * legacy fully-hedged proxy + u * KRW-unhedged return
    krw=(1+base)*(1+fx)-1
    return (1-u)*base + u*krw


def weight_from_z(z,lo=-0.5,hi=2.0):
    z=np.asarray(z,float); w=np.full(len(z),np.nan); ok=np.isfinite(z)
    w[ok & (z>hi)]=0.10
    w[ok & (z<lo)]=0.90
    w[ok & (z>=lo) & (z<=hi)]=0.50
    return w


def circular_boot(a,b,block=12,B=10000,seed=SEED):
    a=np.asarray(a,float); b=np.asarray(b,float); n=len(a)
    rng=np.random.default_rng(seed); nb=int(np.ceil(n/block))
    starts=rng.integers(0,n,size=(B,nb)); offs=np.arange(block)
    idx=(starts[:,:,None]+offs[None,None,:])%n
    idx=idx.reshape(B,nb*block)[:,:n]
    A=a[idx]; C=b[idx]
    ann=(A.mean(1)-C.mean(1))*12
    cagr=np.prod(1+A,axis=1)**(12/n)-np.prod(1+C,axis=1)**(12/n)
    vol=C.std(1,ddof=1)*np.sqrt(12)-A.std(1,ddof=1)*np.sqrt(12)
    wa=np.cumprod(1+A,axis=1); wc=np.cumprod(1+C,axis=1)
    dda=(wa/np.maximum.accumulate(wa,axis=1)-1).min(1)
    ddc=(wc/np.maximum.accumulate(wc,axis=1)-1).min(1)
    return pd.DataFrame(dict(delta_ann_mean=ann,delta_CAGR=cagr,
                             vol_advantage_fixed50_minus_dynamic=vol,
                             MDD_advantage_dynamic_minus_fixed50=dda-ddc))


def boot_summary(b):
    rows=[]
    for c in b.columns:
        v=b[c].to_numpy(float)
        rows.append(dict(metric=c,p025=np.quantile(v,.025),median=np.quantile(v,.5),
                         p975=np.quantile(v,.975),probability_gt_zero=np.mean(v>0)))
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default=str(Path(__file__).resolve().parents[2]))
    args=ap.parse_args(); root=Path(args.project_root).resolve(); out=root/'03_Data_and_Code'/'04_Outputs'

    daily=pd.read_csv(out/'G3_FX_DAILY_MISSING_AND_LOCF_AUDIT_R_v0_19.csv',parse_dates=['date'])
    rmon=pd.read_csv(out/'G3_FX_MONTHLY_SIGNAL_AND_RETURNS_R_v0_19.csv')
    rmon['month']=pd.PeriodIndex(rmon['month'],freq='M')
    thr=pd.read_csv(out/'G3_FX_THRESHOLD_GRID_WEIGHTS_R_v0_19.csv'); thr['month']=pd.PeriodIndex(thr['month'],freq='M')
    win=pd.read_csv(out/'G3_FX_WINDOW_SENSITIVITY_R_v0_19.csv'); win['month']=pd.PeriodIndex(win['month'],freq='M')
    valid=pd.read_csv(out/'G3_FX_VALID_OBSERVATION_CONTROL_R_v0_19.csv'); valid['month']=pd.PeriodIndex(valid['month'],freq='M')
    paths=pd.read_csv(out/'G6_PRIMARY_MONTHLY_RETURN_TURNOVER_PATHS_v0_17.csv')
    paths=paths[paths['portfolio']=='ADAA_historical_weights_canonical'].copy()
    paths['holding_month']=pd.PeriodIndex(paths['holding_month'],freq='M')
    if len(paths)!=218 or paths['holding_month'].iloc[0]!=pd.Period('2008-06','M') or paths['holding_month'].iloc[-1]!=pd.Period('2026-07','M'):
        raise RuntimeError('primary ADAA holding window drift')

    # Independent Python replication of R legacy FX signal.
    s=pd.Series(daily['locf_close'].to_numpy(float),index=pd.DatetimeIndex(daily['date']))
    z=(s-s.rolling(1306,min_periods=1306).mean())/s.rolling(1306,min_periods=1306).std(ddof=1)
    z_m=z.groupby(z.index.to_period('M')).last()
    c_m=s.groupby(s.index.to_period('M')).last()
    fx_m=c_m.pct_change()
    comp=rmon.set_index('month').join(pd.DataFrame({'z_python':z_m,'fx_return_python':fx_m}),how='left')
    comp['strict_weight_python']=weight_from_z(comp['z_python'])
    zmask=np.isfinite(comp['z1306_strict']) & np.isfinite(comp['z_python'])
    max_z=float(np.max(np.abs(comp.loc[zmask,'z1306_strict']-comp.loc[zmask,'z_python'])))
    max_fx=float(np.nanmax(np.abs(comp['fx_return']-comp['fx_return_python'])))
    r_w=comp['strict_unhedged_weight'].fillna(-9).to_numpy(); p_w=comp['strict_weight_python'].fillna(-9).to_numpy()
    w_mismatch=int(np.sum(np.abs(r_w-p_w)>1e-12))
    if max_z>1e-10 or max_fx>1e-12 or w_mismatch:
        raise RuntimeError(f'R/Python FX replication failed: z={max_z}, fx={max_fx}, weights={w_mismatch}')

    # Align prior-month signal to current holding-month FX return.
    fx_current=rmon[['month','fx_return']].rename(columns={'month':'holding_month'})
    fx_signal=rmon[['month','legacy_unhedged_weight','strict_unhedged_weight','z1306_strict','z1306_legacy_fill1']].copy()
    fx_signal['holding_month']=fx_signal['month']+1; fx_signal=fx_signal.drop(columns='month')
    m=paths.merge(fx_current,on='holding_month',how='left').merge(fx_signal,on='holding_month',how='left')
    if m[['fx_return','legacy_unhedged_weight']].isna().any().any(): raise RuntimeError('primary FX merge missing')

    # Main fixed/dynamic comparison. Both gross and existing 25bp underlying path are shown.
    variant_rows=[]; path_frames=[]
    for base_col,base_label in [('gross_return','gross_underlying'),('net_return_25bps','net25_underlying')]:
        base=m[base_col].to_numpy(float); fxr=m['fx_return'].to_numpy(float)
        specs={'fully_hedged_proxy':np.zeros(len(m)),
               'fixed_50_unhedged':np.full(len(m),.5),
               'fully_unhedged':np.ones(len(m)),
               'legacy_dynamic_90_50_10':m['legacy_unhedged_weight'].to_numpy(float)}
        for nm,u in specs.items():
            rr=overlay_return(base,fxr,u); d=perf(rr)
            d.update(base_return_path=base_label,variant=nm,average_unhedged_weight=float(np.mean(u)),
                     state_changes=int(np.sum(np.abs(np.diff(u))>1e-12)))
            variant_rows.append(d)
            path_frames.append(pd.DataFrame({'holding_month':m['holding_month'].astype(str),'base_return_path':base_label,
                                             'variant':nm,'unhedged_weight':u,'portfolio_return':rr}))
    variants=pd.DataFrame(variant_rows)
    variants.to_csv(out/'G3_FX_EXTENSION_VARIANT_PERFORMANCE_v0_20.csv',index=False)
    pd.concat(path_frames,ignore_index=True).to_csv(out/'G3_FX_EXTENSION_MONTHLY_PATHS_v0_20.csv',index=False)

    # Threshold surface. No selection/promotion is performed.
    threshold_rows=[]
    for (lo,hi),g in thr.groupby(['low_threshold','high_threshold']):
        gg=g[['month','unhedged_weight']].copy(); gg['holding_month']=gg['month']+1
        mm=m.merge(gg[['holding_month','unhedged_weight']],on='holding_month',how='left')
        if mm['unhedged_weight'].isna().any(): raise RuntimeError('threshold path missing')
        for base_col,base_label in [('gross_return','gross_underlying'),('net_return_25bps','net25_underlying')]:
            rr=overlay_return(mm[base_col],mm['fx_return'],mm['unhedged_weight']); d=perf(rr)
            d.update(low_threshold=float(lo),high_threshold=float(hi),base_return_path=base_label,
                     is_legacy_rule=bool(abs(lo+.5)<1e-12 and abs(hi-2)<1e-12),
                     average_unhedged_weight=float(mm['unhedged_weight'].mean()),
                     state_changes=int(np.sum(np.abs(np.diff(mm['unhedged_weight']))>1e-12)))
            threshold_rows.append(d)
    threshold_perf=pd.DataFrame(threshold_rows)
    threshold_perf.to_csv(out/'G3_FX_THRESHOLD_PERFORMANCE_SURFACE_v0_20.csv',index=False)

    # Window-length sensitivity on a common post-warm-up sample.
    first=win.dropna(subset=['unhedged_weight']).groupby('window_days')['month'].min()
    common_holding=max(first)+1
    window_rows=[]
    for ww,g in win.groupby('window_days'):
        gg=g[['month','unhedged_weight']].copy(); gg['holding_month']=gg['month']+1
        mm=m[m['holding_month']>=common_holding].merge(gg[['holding_month','unhedged_weight']],on='holding_month',how='left').dropna(subset=['unhedged_weight'])
        for base_col,base_label in [('gross_return','gross_underlying'),('net_return_25bps','net25_underlying')]:
            rr=overlay_return(mm[base_col],mm['fx_return'],mm['unhedged_weight']); d=perf(rr)
            d.update(window_days=int(ww),base_return_path=base_label,common_start=str(common_holding),
                     first_holding_month=str(mm['holding_month'].iloc[0]),last_holding_month=str(mm['holding_month'].iloc[-1]),
                     average_unhedged_weight=float(mm['unhedged_weight'].mean()))
            window_rows.append(d)
    pd.DataFrame(window_rows).to_csv(out/'G3_FX_WINDOW_PERFORMANCE_COMMON_SAMPLE_v0_20.csv',index=False)

    # LOCF versus valid-observation-only control.
    miss=rmon[['month','z1306_strict','strict_unhedged_weight']].merge(valid,on='month',how='inner')
    ok=miss['z1306_strict'].notna() & miss['z1306_valid_observations_only'].notna()
    miss_rec=pd.DataFrame([{
        'comparable_months':int(ok.sum()),
        'max_abs_z_difference':float(np.max(np.abs(miss.loc[ok,'z1306_strict']-miss.loc[ok,'z1306_valid_observations_only']))),
        'unhedged_weight_state_mismatches':int(np.sum(np.abs(miss.loc[ok,'strict_unhedged_weight']-miss.loc[ok,'unhedged_weight_valid_observations_only'])>1e-12)),
        'daily_raw_missing_rows':int(daily['raw_close_missing'].sum()),
        'daily_locf_imputed_rows':int(daily['locf_imputed'].sum())
    }])
    miss_rec.to_csv(out/'G3_FX_MISSINGNESS_CONTROL_SUMMARY_v0_20.csv',index=False)

    # State diagnostics and high/low-side decomposition. Descriptive only.
    state=m.groupby('legacy_unhedged_weight')['fx_return'].agg(['count','mean','median','std']).reset_index()
    state['annualized_arithmetic_mean_fx_return']=state['mean']*12
    state.to_csv(out/'G3_FX_STATE_CONDITIONAL_NEXT_MONTH_RETURN_v0_20.csv',index=False)
    z=m['z1306_legacy_fill1'].to_numpy(float)
    specs={'fixed_50':np.full(len(m),.5),
           'high_side_only':np.where(z>2,.1,.5),
           'low_side_only':np.where(z<-.5,.9,.5),
           'full_legacy':m['legacy_unhedged_weight'].to_numpy(float)}
    decomp=[]
    for nm,u in specs.items():
        rr=overlay_return(m['net_return_25bps'],m['fx_return'],u); d=perf(rr)
        d.update(component=nm,average_unhedged_weight=float(np.mean(u)),state_changes=int(np.sum(np.abs(np.diff(u))>1e-12)))
        decomp.append(d)
    pd.DataFrame(decomp).to_csv(out/'G3_FX_LEGACY_COMPONENT_DECOMPOSITION_v0_20.csv',index=False)

    # Paired dependence-aware diagnostic versus fixed 50%, using the existing net-25bp underlying path.
    fixed=overlay_return(m['net_return_25bps'],m['fx_return'],np.full(len(m),.5))
    dyn=overlay_return(m['net_return_25bps'],m['fx_return'],m['legacy_unhedged_weight'])
    boot=circular_boot(dyn,fixed,B=B,block=BLOCK); boot.to_csv(out/'G3_FX_LEGACY_VS_FIXED50_BLOCK_BOOTSTRAP_DRAWS_v0_20.csv',index=False)
    bs=boot_summary(boot); bs.to_csv(out/'G3_FX_LEGACY_VS_FIXED50_BLOCK_BOOTSTRAP_SUMMARY_v0_20.csv',index=False)

    # Core evaluation record.
    gross_thr=threshold_perf[threshold_perf['base_return_path']=='gross_underlying']
    legacy_thr=gross_thr[gross_thr['is_legacy_rule']].iloc[0]
    fixed50=variants[(variants['base_return_path']=='gross_underlying')&(variants['variant']=='fixed_50_unhedged')].iloc[0]
    dynamic=variants[(variants['base_return_path']=='gross_underlying')&(variants['variant']=='legacy_dynamic_90_50_10')].iloc[0]
    primary_sig=m['legacy_unhedged_weight']
    record={
        'version':'v0.20','verdict':'CONDITIONAL PASS FOR APPENDIX / HISTORICAL APPLICATION ONLY',
        'r_python_signal_replication':{'max_abs_z_diff':max_z,'max_abs_fx_return_diff':max_fx,'weight_mismatches':w_mismatch},
        'primary_sample':{'holding_start':str(m['holding_month'].iloc[0]),'holding_end':str(m['holding_month'].iloc[-1]),'months':len(m)},
        'legacy_state_counts':{str(k):int(v) for k,v in primary_sig.value_counts().sort_index().items()},
        'legacy_average_unhedged_weight':float(primary_sig.mean()),
        'legacy_state_changes':int(np.sum(np.abs(np.diff(primary_sig))>1e-12)),
        'gross_legacy_vs_fixed50':{'legacy_CAGR':float(dynamic['CAGR']),'fixed50_CAGR':float(fixed50['CAGR']),
                                   'legacy_vol':float(dynamic['annualized_volatility']),'fixed50_vol':float(fixed50['annualized_volatility']),
                                   'legacy_MDD':float(dynamic['max_drawdown']),'fixed50_MDD':float(fixed50['max_drawdown'])},
        'threshold_surface_gross':{'cells':int(len(gross_thr)),'CAGR_min':float(gross_thr['CAGR'].min()),
                                   'CAGR_median':float(gross_thr['CAGR'].median()),'CAGR_max':float(gross_thr['CAGR'].max()),
                                   'legacy_CAGR':float(legacy_thr['CAGR']),
                                   'cells_CAGR_above_fixed50':int(np.sum(gross_thr['CAGR']>fixed50['CAGR'])),
                                   'cells_vol_below_fixed50':int(np.sum(gross_thr['annualized_volatility']<fixed50['annualized_volatility'])),
                                   'cells_MDD_shallower_than_fixed50':int(np.sum(gross_thr['max_drawdown']>fixed50['max_drawdown']))},
        'missingness_control':miss_rec.iloc[0].to_dict(),
        'limitations':['legacy thresholds have outcome-linked historical provenance and are not treated as ex-ante optimal',
                       'fully hedged leg is a zero-carry/zero-hedge-cost proxy; forward points, hedge transaction costs, collateral and tax are not modeled',
                       'zero-rate Sharpe is diagnostic only and is not proposed as a Korean-investor risk-adjusted benchmark',
                       'FX extension is separate from the global Decision Diversification contribution']
    }
    (out/'G3_FX_EXTENSION_EVALUATION_RECORD_v0_20.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
    print('PASS: v0.20 independent FX signal replication and application-layer evaluation complete.')
    print('Verdict: CONDITIONAL PASS for appendix / historical application; no FX rule was reselected.')

if __name__=='__main__': main()
