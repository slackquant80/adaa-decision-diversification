#!/usr/bin/env python3
"""Build performance-blind ADAA ETF-only decision/target-weight panel from frozen inputs.

This independently reconstructs the dashboard-successor sleeve logic using only
frozen ETF prices and UNRATE. It DOES NOT compute portfolio returns or headline
performance. Output is provisional until R target-weight equivalence passes.
"""
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

ASSETS = ['SPY','QQQ','IWM','EFA','EEM','VNQ','DBC','IEF','TLT','EWY','GLD','BIL','TIP','AGG','LQD','VGK','HYG','SHY']

def load_audit_module(root: Path):
    p=root/'03_Data_and_Code'/'02_Code'/'independent_frozen_data_audit_v0_10.py'
    spec=importlib.util.spec_from_file_location('auditv010', p)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

def r_rank(s: pd.Series, ascending=True):
    return s.rank(method='average', ascending=ascending)

def month_end_prices(primary, audit):
    cols={k:audit.adjusted(v) for k,v in primary.items()}
    daily=pd.concat(cols,axis=1).sort_index()
    # R xts::to.monthly(indexAt='lastof', OHLC=FALSE): last available value in each calendar month,
    # labeled by calendar month end. pandas Period index avoids day-label ambiguity.
    out=daily.groupby(daily.index.to_period('M')).last()
    out.index.name='signal_month'
    return out

def ratio_avg(px, lags):
    return sum(px/px.shift(k) for k in lags)/len(lags)

def sma_ratio(px, k):
    return px/px.rolling(k).mean()

def choose_stronger_safe(monthly, assets=('SHY','BIL')):
    scores={a:sma_ratio(monthly[a],13) for a in assets}
    # dashboard: SHY if SH_avg > BI_avg; otherwise BIL (ties -> BIL)
    return pd.Series(np.where(scores[assets[0]]>scores[assets[1]],assets[0],assets[1]), index=monthly.index)

def make_weight_frame(index, assets):
    return pd.DataFrame(0.0,index=index,columns=assets)

def build_haa(m):
    risk=['SPY','QQQ','IWM','EFA','EEM','VNQ','DBC','IEF','TLT','EWY','GLD']; safe=['IEF','BIL']
    can=sum(m['TIP']/m['TIP'].shift(k)-1 for k in [1,3,6,12])
    regime=(can>0).astype(float); regime[can.isna()]=np.nan
    scores=pd.DataFrame({a:ratio_avg(m[a],[1,3,6,12]) for a in risk})
    safe_scores=pd.DataFrame({a:ratio_avg(m[a],[1,3,6,12]) for a in safe})
    idx=m.index
    w=make_weight_frame(idx, sorted(set(risk+safe)))
    tie_count=pd.Series(0,index=idx,dtype=int)
    for dt in idx:
        if pd.isna(regime.loc[dt]) or scores.loc[dt].isna().any() or safe_scores.loc[dt].isna().any(): continue
        if regime.loc[dt]==1:
            rr=r_rank(scores.loc[dt]); sel=rr[rr>=6].index.tolist(); tie_count.loc[dt]=len(sel)-6
            for a in sel: w.loc[dt,a]+=1/6
        else:
            rr=r_rank(safe_scores.loc[dt]); sel=rr[rr>=2].index.tolist(); tie_count.loc[dt]=len(sel)-1
            for a in sel: w.loc[dt,a]+=1.0
    meta=pd.DataFrame({'state':np.where(regime==1,'risk','defensive'),'rule_defensive_fraction':np.where(regime==1,0.0,1.0),'selection_count_anomaly':tie_count},index=idx)
    meta.loc[regime.isna(),['state','rule_defensive_fraction']]=[None,np.nan]
    return w,meta

def build_baa(m):
    risk=['QQQ','EEM','EFA','AGG']; safe=['TIP','DBC','IEF','TLT','LQD','AGG','BIL']; cana=['SPY','EEM','EFA','AGG']
    can=pd.DataFrame({a:12*(m[a]/m[a].shift(1)-1)+4*(m[a]/m[a].shift(3)-1)+2*(m[a]/m[a].shift(6)-1)+(m[a]/m[a].shift(12)-1) for a in cana})
    regime=(can.ge(0).all(axis=1)).astype(float); regime[can.isna().any(axis=1)]=np.nan
    risk_s=pd.DataFrame({a:sma_ratio(m[a],13) for a in risk})
    safe_s=pd.DataFrame({a:sma_ratio(m[a],13) for a in safe})
    idx=m.index; w=make_weight_frame(idx,sorted(set(risk+safe))); anomalies=pd.Series(0,index=idx,dtype=int)
    for dt in idx:
        if pd.isna(regime.loc[dt]) or risk_s.loc[dt].isna().any() or safe_s.loc[dt].isna().any(): continue
        if regime.loc[dt]==1:
            rr=r_rank(risk_s.loc[dt]); sel=rr[rr==4].index.tolist(); anomalies.loc[dt]=len(sel)-1
            for a in sel:w.loc[dt,a]+=1.0
        else:
            rr=r_rank(safe_s.loc[dt]); sel=rr[rr>=5].index.tolist(); anomalies.loc[dt]=len(sel)-3
            # initial equal thirds per dashboard; ties can alter selected count and total before BIL fallback
            for a in sel:w.loc[dt,a]+=1/3
            bil_score=safe_s.loc[dt,'BIL']
            for a in [x for x in safe if x!='BIL']:
                if safe_s.loc[dt,a] <= bil_score: w.loc[dt,a]=0.0
            # dashboard fills all residual to BIL
            w.loc[dt,'BIL'] += 1.0-w.loc[dt].sum()
    meta=pd.DataFrame({'state':np.where(regime==1,'risk','defensive'),'rule_defensive_fraction':np.where(regime==1,0.0,1.0),'selection_count_anomaly':anomalies},index=idx)
    meta.loc[regime.isna(),['state','rule_defensive_fraction']]=[None,np.nan]
    return w,meta

def build_adm(m):
    risk=['SPY','QQQ','VGK','EWY','EEM','VNQ','DBC','GLD','TLT','HYG','LQD','TIP']; safe=['SHY','BIL']
    scores=pd.DataFrame({a:ratio_avg(m[a],[1,3,6]) for a in risk})
    safe_choice=choose_stronger_safe(m,safe)
    idx=m.index; w=make_weight_frame(idx,risk+safe); anomalies=pd.Series(0,index=idx,dtype=int); residual=pd.Series(np.nan,index=idx)
    for dt in idx:
        if scores.loc[dt].isna().any() or pd.isna(sma_ratio(m['SHY'],13).loc[dt]) or pd.isna(sma_ratio(m['BIL'],13).loc[dt]): continue
        rr=r_rank(scores.loc[dt]); sel=rr[rr>=7].index.tolist(); anomalies.loc[dt]=len(sel)-6
        for a in sel:
            if scores.loc[dt,a] >= 1: w.loc[dt,a]=1/6
        res=1.0-w.loc[dt,risk].sum(); residual.loc[dt]=res; w.loc[dt,safe_choice.loc[dt]]=res
    meta=pd.DataFrame(index=idx); meta['rule_defensive_fraction']=residual
    meta['state']=np.where(residual>=0.999999,'defensive',np.where(residual>1e-12,'mixed','risk'))
    meta.loc[residual.isna(),'state']=None; meta['selection_count_anomaly']=anomalies
    return w,meta

def rolling_corr_with_ew(ret: pd.DataFrame, width=6, self_exclude=False):
    out=pd.DataFrame(index=ret.index,columns=ret.columns,dtype=float)
    for i in range(width-1,len(ret)):
        x=ret.iloc[i-width+1:i+1]
        if x.isna().any().any(): continue
        for a in ret.columns:
            if self_exclude: ew=x.drop(columns=[a]).mean(axis=1)
            else: ew=x.mean(axis=1)
            out.iloc[i,out.columns.get_loc(a)]=x[a].corr(ew)
    return out

def build_faa(m, self_exclude=False, exact_n=False):
    risk=['SPY','QQQ','VGK','EWY','EEM','VNQ','DBC','GLD','TLT','HYG','LQD','TIP']; safe=['SHY','BIL']
    mom=pd.DataFrame({a:ratio_avg(m[a],[3,6,12]) for a in risk})
    ret=m[risk].pct_change(fill_method=None).dropna(how='any')
    vol=ret.rolling(6).std(ddof=1)
    corr=rolling_corr_with_ew(ret,6,self_exclude=self_exclude)
    # align to m index
    vol=vol.reindex(m.index); corr=corr.reindex(m.index)
    safe_choice=choose_stronger_safe(m,safe)
    idx=m.index; w=make_weight_frame(idx,risk+safe); anomalies=pd.Series(0,index=idx,dtype=int); residual=pd.Series(np.nan,index=idx)
    for dt in idx:
        if mom.loc[dt].isna().any() or vol.loc[dt].isna().any() or corr.loc[dt].isna().any(): continue
        # R momentum: -mom then ascending rank => highest mom gets rank 1
        M=r_rank(-mom.loc[dt]); V=r_rank(vol.loc[dt]); C=r_rank(corr.loc[dt]); agg=M+0.5*V+0.5*C
        if exact_n:
            # deterministic publication candidate: stable secondary ordering by asset name
            order=sorted(risk,key=lambda a:(agg[a],a)); sel=order[:6]
        else:
            R=r_rank(agg); sel=R[R<=6].index.tolist()
        anomalies.loc[dt]=len(sel)-6
        denom=len(sel)
        if denom==0: continue
        for a in sel:
            if mom.loc[dt,a] >=1: w.loc[dt,a]=1/denom
        res=1.0-w.loc[dt,risk].sum(); residual.loc[dt]=res
        # require safe scores available
        sh=sma_ratio(m['SHY'],13).loc[dt]; bi=sma_ratio(m['BIL'],13).loc[dt]
        if pd.isna(sh) or pd.isna(bi): w.loc[dt,:]=0; residual.loc[dt]=np.nan; continue
        w.loc[dt,'SHY' if sh>bi else 'BIL']=res
    meta=pd.DataFrame(index=idx); meta['rule_defensive_fraction']=residual
    meta['state']=np.where(residual>=0.999999,'defensive',np.where(residual>1e-12,'mixed','risk'))
    meta.loc[residual.isna(),'state']=None; meta['selection_count_anomaly']=anomalies
    return w,meta

def build_laa(m,unrate,audit):
    assets=['SPY','QQQ','EEM','EWY','IEF','GLD','SHY']; idx=m.index
    # Proven v0.10 chronology: observation month t -> signal/weight month t+1 -> effective holding month t+2.
    u=unrate.iloc[:,0].copy(); u.index=u.index.to_period('M')
    obs_aligned=pd.Series(index=idx,dtype=float)
    for sm in idx:
        om=sm-1
        if om in u.index:
            obs_aligned.loc[sm]=u.loc[om]
    x=m.loc[idx,assets].copy(); x['UNRATE']=obs_aligned
    sp_score=x['SPY']/x['SPY'].rolling(11).mean(); un_score=x['UNRATE']/x['UNRATE'].rolling(13).mean()
    valid=sp_score.notna()&un_score.notna()&x[assets].notna().all(axis=1)
    w=make_weight_frame(idx,assets); state=pd.Series(None,index=idx,dtype=object); dfrac=pd.Series(np.nan,index=idx)
    for dt in idx[valid]:
        w.loc[dt,['SPY','EEM','EWY','IEF','GLD']]=[0.175,0.05,0.025,0.25,0.25]
        risk_on=(sp_score.loc[dt]>1) or (un_score.loc[dt]<1)
        if risk_on: w.loc[dt,'QQQ']=0.25; state.loc[dt]='risk'; dfrac.loc[dt]=0.0
        else: w.loc[dt,'SHY']=0.25; state.loc[dt]='defensive'; dfrac.loc[dt]=0.25
    meta=pd.DataFrame({'state':state,'rule_defensive_fraction':dfrac,'selection_count_anomaly':0},index=idx)
    return w,meta

def build_laa_missing_observation_controls(m,unrate):
    """Two non-promoted controls for structurally missing UNRATE months.
    carry_calendar: carry latest observation into the missing calendar month then 13-calendar-month SMA.
    last13_available: compare latest released observation with mean of latest 13 nonmissing observations.
    """
    assets=['SPY','QQQ','EEM','EWY','IEF','GLD','SHY']; idx=m.index
    u=unrate.iloc[:,0].copy(); u.index=u.index.to_period('M')
    outs={}
    for mode in ['carry_calendar','last13_available']:
        w=make_weight_frame(idx,assets); state=pd.Series(None,index=idx,dtype=object); dfrac=pd.Series(np.nan,index=idx)
        ua=u.copy()
        if mode=='carry_calendar': ua=ua.ffill()
        sp=m['SPY']; sp_score=sp/sp.rolling(11).mean()
        for sm in idx:
            om=sm-1
            if om not in ua.index or pd.isna(sp_score.loc[sm]) or m.loc[sm,assets].isna().any(): continue
            if mode=='carry_calendar':
                hist=ua.loc[:om].tail(13)
            else:
                hist=ua.loc[:om].dropna().tail(13)
            if len(hist)<13 or pd.isna(ua.loc[om]):
                if mode=='last13_available' and om in u.index and pd.isna(u.loc[om]):
                    latest=u.loc[:om].dropna()
                    if len(latest)<13: continue
                    current=latest.iloc[-1]; hist=latest.tail(13)
                else:
                    continue
            else:
                current=ua.loc[om]
            un_score=current/hist.mean()
            w.loc[sm,['SPY','EEM','EWY','IEF','GLD']]=[0.175,0.05,0.025,0.25,0.25]
            risk_on=(sp_score.loc[sm]>1) or (un_score<1)
            if risk_on: w.loc[sm,'QQQ']=0.25; state.loc[sm]='risk'; dfrac.loc[sm]=0.0
            else: w.loc[sm,'SHY']=0.25; state.loc[sm]='defensive'; dfrac.loc[sm]=0.25
        outs[mode]=(w,pd.DataFrame({'state':state,'rule_defensive_fraction':dfrac,'selection_count_anomaly':0},index=idx))
    return outs

def canonicalize_weights(w):
    # drop all-unavailable rows (sum 0), keep true 0 only after availability cannot be distinguished; use sum>0 criterion.
    return w[w.sum(axis=1)>0].copy()

def panel_long(sleeve, w, meta, start_signal, end_signal):
    w=canonicalize_weights(w).loc[start_signal:end_signal]
    meta=meta.reindex(w.index)
    rec=[]
    for dt,row in w.iterrows():
        selected=[a for a,v in row.items() if abs(v)>1e-12]
        rec.append({'sleeve':sleeve,'signal_month':str(dt),'effective_holding_month':str(dt+1),'state':meta.loc[dt,'state'],
                    'rule_defensive_fraction':meta.loc[dt,'rule_defensive_fraction'],'selection_count_anomaly':int(meta.loc[dt,'selection_count_anomaly']),
                    'selected_assets':'|'.join(selected),'n_selected_assets':len(selected),'weight_sum':row.sum()})
    return pd.DataFrame(rec),w

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default=str(Path(__file__).resolve().parents[2])); args=ap.parse_args()
    root=Path(args.project_root).resolve(); raw=root/'03_Data_and_Code'/'01_Data'/'raw_freeze_v0_8'; out=root/'03_Data_and_Code'/'04_Outputs'; out.mkdir(parents=True,exist_ok=True)
    audit=load_audit_module(root); primary=audit.named_xts_list(audit.read_rds(raw/'yahoo_primary_raw.rds')); unrate=audit.xts_to_df(audit.read_rds(raw/'fred_UNRATE_current_vintage_raw.rds'))
    m=month_end_prices(primary,audit)
    # Freeze primary ETF-only evidence window from v0.10 contract: signal 2008-05 through 2026-06, effective holdings 2008-06 through 2026-07.
    start=pd.Period('2008-05',freq='M'); end=pd.Period('2026-06',freq='M')
    builders={'HAA':build_haa,'BAA_Aggressive':build_baa,'ADM':build_adm,'FAA_legacy':lambda x:build_faa(x,False,False),'LAA':lambda x:build_laa(x,unrate,audit)}
    all_meta=[]; weight_tables={}
    for name,b in builders.items():
        w,meta=b(m); pm,wsub=panel_long(name,w,meta,start,end); all_meta.append(pm); weight_tables[name]=wsub
        wsub.to_csv(out/f'G2_{name.upper()}_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv')
    panel=pd.concat(all_meta,ignore_index=True)
    panel.to_csv(out/'G2_DECISION_PANEL_INDEPENDENT_v0_11.csv',index=False)
    # LAA missing-observation operational controls (not promoted).
    for tag,(w,meta) in build_laa_missing_observation_controls(m,unrate).items():
        pm,wsub=panel_long('LAA_'+tag,w,meta,start,end); pm.to_csv(out/f'G2_LAA_{tag.upper()}_DECISION_CONTROL_v0_11.csv',index=False); wsub.to_csv(out/f'G2_LAA_{tag.upper()}_TARGET_WEIGHTS_v0_11.csv')
    # FAA control variants: do not promote; only measure implementation sensitivity at the decision level.
    for tag,kwargs in [('peer_only',dict(self_exclude=True,exact_n=False)),('peer_only_exactN',dict(self_exclude=True,exact_n=True))]:
        w,meta=build_faa(m,**kwargs); pm,wsub=panel_long('FAA_'+tag,w,meta,start,end); pm.to_csv(out/f'G2_FAA_{tag.upper()}_DECISION_CONTROL_v0_11.csv',index=False); wsub.to_csv(out/f'G2_FAA_{tag.upper()}_TARGET_WEIGHTS_v0_11.csv')
    # preliminary non-performance diagnostics only.
    summary=[]
    for name,w in weight_tables.items():
        mta=panel[panel.sleeve==name].set_index('signal_month')
        changes=(w.round(12).diff().abs().sum(axis=1)>1e-12)
        summary.append({'sleeve':name,'months':len(w),'weight_sum_min':float(w.sum(axis=1).min()),'weight_sum_max':float(w.sum(axis=1).max()),
                        'months_with_weight_change':int(changes.iloc[1:].sum()),'change_rate':float(changes.iloc[1:].mean()),
                        'mean_rule_defensive_fraction':float(pd.to_numeric(mta.rule_defensive_fraction,errors='coerce').mean()),
                        'selection_count_anomaly_months':int((mta.selection_count_anomaly!=0).sum())})
    pd.DataFrame(summary).to_csv(out/'G2_DECISION_PANEL_STRUCTURAL_SUMMARY_v0_11.csv',index=False)
    # pairwise target-weight L1 distance on union of asset columns for months common to each pair.
    names=list(weight_tables); rows=[]
    for i,a in enumerate(names):
        for b in names[i+1:]:
            wa,wb=weight_tables[a],weight_tables[b]; idx=wa.index.intersection(wb.index); cols=sorted(set(wa.columns)|set(wb.columns))
            aa=wa.reindex(index=idx,columns=cols,fill_value=0); bb=wb.reindex(index=idx,columns=cols,fill_value=0)
            l1=(aa-bb).abs().sum(axis=1); rows.append({'sleeve_a':a,'sleeve_b':b,'common_months':len(idx),'mean_L1_target_weight_distance':float(l1.mean()),'median_L1_target_weight_distance':float(l1.median()),'identical_target_weight_months':int((l1<1e-12).sum())})
    pd.DataFrame(rows).to_csv(out/'G2_PAIRWISE_TARGET_WEIGHT_DISTANCE_PRELIM_v0_11.csv',index=False)
    record={'version':'v0.11','performance_blind':True,'status':'PROVISIONAL_PENDING_R_EQUIVALENCE','signal_window':[str(start),str(end)],'effective_window':[str(start+1),str(end+1)],'sleeves':list(builders),'output_rows':int(len(panel)),'headline_performance_computed':False}
    (out/'G2_INDEPENDENT_DECISION_PANEL_RECORD_v0_11.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2))

if __name__=='__main__': main()
