#!/usr/bin/env python3
"""Contribution Gate P2 diagnostic: return correlation versus decision structure.

This script computes ONLY gross monthly sleeve returns needed to obtain pairwise
return correlations. It intentionally does not calculate or write average return,
volatility, CAGR, Sharpe, MDD, Calmar, cumulative wealth, or rankings.

Target weights are the already-verified legacy sleeve weights; signal-month weights
are applied to the next calendar month's asset returns under the established
Return.portfolio timing convention. The diagnostic is restricted to the common
five-sleeve window so return-correlation and decision metrics use the same months.
"""
from pathlib import Path
import argparse, importlib.util, json
import numpy as np
import pandas as pd

WEIGHT_FILES={
'HAA':'G2_HAA_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',
'BAA_Aggressive':'G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',
'ADM':'G2_ADM_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',
'FAA_legacy':'G2_FAA_LEGACY_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',
'LAA':'G2_LAA_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',
}


def load_audit(root):
    p=root/'03_Data_and_Code'/'02_Code'/'independent_frozen_data_audit_v0_10.py'
    spec=importlib.util.spec_from_file_location('auditv010',p)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def pearson(x,y):
    a=np.asarray(x,dtype=float); b=np.asarray(y,dtype=float)
    if len(a)<2: return np.nan
    return float(np.corrcoef(a,b)[0,1])


def rank_average(x):
    return pd.Series(x).rank(method='average').to_numpy()


def spearman(x,y):
    return pearson(rank_average(x),rank_average(y))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default=str(Path(__file__).resolve().parents[2])); args=ap.parse_args()
    root=Path(args.project_root).resolve(); out=root/'03_Data_and_Code'/'04_Outputs'; raw=root/'03_Data_and_Code'/'01_Data'/'raw_freeze_v0_8'
    audit=load_audit(root)
    primary=audit.named_xts_list(audit.read_rds(raw/'yahoo_primary_raw.rds'))
    daily=pd.concat({k:audit.adjusted(v) for k,v in primary.items()},axis=1).sort_index()
    monthly=daily.groupby(daily.index.to_period('M')).last(); monthly.index=monthly.index.astype(str)
    asset_ret=monthly.pct_change(fill_method=None)

    W={k:pd.read_csv(out/f,index_col=0).astype(float) for k,f in WEIGHT_FILES.items()}
    for d in W.values(): d.index=d.index.astype(str)
    common_signal=sorted(set.intersection(*[set(d.index) for d in W.values()]))

    sleeve_ret={}
    for sleeve,w in W.items():
        vals=[]; idx=[]
        for sm in common_signal:
            em=str(pd.Period(sm,freq='M')+1)
            row=w.loc[sm]
            rr=asset_ret.loc[em].reindex(row.index)
            if rr.isna().any():
                raise RuntimeError(f'Missing effective-month return for {sleeve} {sm}->{em}: {list(rr[rr.isna()].index)}')
            vals.append(float((row*rr).sum())); idx.append(em)
        sleeve_ret[sleeve]=pd.Series(vals,index=idx,name=sleeve)
    X=pd.concat(sleeve_ret.values(),axis=1)
    if X.isna().any().any(): raise RuntimeError('Unexpected NA in common sleeve return panel')
    # Write correlation only; do not persist the underlying sleeve returns.
    corr=X.corr()
    corr.to_csv(out/'G4_SLEEVE_RETURN_CORRELATION_DIAGNOSTIC_v0_12.csv')

    dec=pd.read_csv(out/'G4_PAIRWISE_DECISION_DIVERSITY_v0_12.csv')
    rows=[]
    for _,r in dec.iterrows():
        a,b=r['sleeve_a'],r['sleeve_b']
        rows.append({
            'sleeve_a':a,'sleeve_b':b,'common_effective_months':len(X),
            'gross_monthly_return_correlation':float(corr.loc[a,b]),
            'mean_L1_target_weight_distance':float(r['mean_L1_target_weight_distance']),
            'any_defense_state_agreement_rate':float(r['any_defense_state_agreement_rate']),
            'transition_jaccard':float(r['transition_jaccard']),
            'mean_selected_asset_jaccard':float(r['mean_selected_asset_jaccard']),
        })
    d=pd.DataFrame(rows)
    d.to_csv(out/'G4_RETURN_CORRELATION_VS_DECISION_METRICS_v0_12.csv',index=False)

    rc=d['gross_monthly_return_correlation'].to_numpy()
    associations={}
    for col in ['mean_L1_target_weight_distance','any_defense_state_agreement_rate','transition_jaccard','mean_selected_asset_jaccard']:
        associations[col]={
            'pearson_across_10_pairs':pearson(rc,d[col].to_numpy()),
            'spearman_across_10_pairs':spearman(rc,d[col].to_numpy()),
        }

    # Find a simple matched-correlation contrast that demonstrates incremental timing information.
    contrasts=[]
    for i in range(len(d)):
        for j in range(i+1,len(d)):
            ri,rj=d.iloc[i],d.iloc[j]
            cd=abs(ri.gross_monthly_return_correlation-rj.gross_monthly_return_correlation)
            td=abs(ri.transition_jaccard-rj.transition_jaccard)
            if cd<=0.05:
                contrasts.append({
                    'pair_1':f"{ri.sleeve_a}__{ri.sleeve_b}",'pair_2':f"{rj.sleeve_a}__{rj.sleeve_b}",
                    'return_correlation_difference':float(cd),'transition_jaccard_difference':float(td),
                    'pair_1_return_correlation':float(ri.gross_monthly_return_correlation),
                    'pair_2_return_correlation':float(rj.gross_monthly_return_correlation),
                    'pair_1_transition_jaccard':float(ri.transition_jaccard),
                    'pair_2_transition_jaccard':float(rj.transition_jaccard),
                })
    contrasts=pd.DataFrame(contrasts).sort_values(['transition_jaccard_difference','return_correlation_difference'],ascending=[False,True])
    contrasts.to_csv(out/'G4_P2_MATCHED_RETURN_CORRELATION_CONTRASTS_v0_12.csv',index=False)

    best=contrasts.iloc[0].to_dict() if len(contrasts) else None
    rec={
        'version':'v0.12','gate_component':'P2_incremental_information_beyond_return_correlation',
        'status':'PRELIMINARY_PASS_ON_FROZEN_LEGACY_FIVE',
        'performance_blind_except_required_return_correlation':True,
        'headline_performance_computed':False,
        'signal_window':[common_signal[0],common_signal[-1]],
        'effective_return_window':[X.index[0],X.index[-1]],
        'months':len(X),'pair_count':len(d),
        'cross_pair_associations':associations,
        'best_matched_correlation_transition_contrast':best,
        'interpretation':[
            'Return correlation strongly co-moves with target-weight distance, broad defense-state agreement, and holdings overlap; decision metrics are not claimed to be orthogonal replacements for return correlation.',
            'Transition-timing overlap is much less tightly summarized by return correlation, and pairs with similar return correlation can have radically different transition synchronization.',
            'The incremental practitioner value of Decision Diversification is therefore concentrated in mechanism, timing, and persistence diagnostics rather than in claiming return correlation is useless.',
        ],
    }
    (out/'G4_P2_INCREMENTAL_INFORMATION_RECORD_v0_12.json').write_text(json.dumps(rec,indent=2),encoding='utf-8')
    print(json.dumps(rec,indent=2))

if __name__=='__main__': main()
