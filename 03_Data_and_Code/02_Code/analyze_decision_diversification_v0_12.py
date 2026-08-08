#!/usr/bin/env python3
"""Performance-blind structural diagnostics for ADAA Decision Diversification, v0.12.

Reads the already-verified independent target-weight panels produced in v0.11 and
computes only decision-structure diagnostics. It DOES NOT compute sleeve or
portfolio returns, CAGR, Sharpe, MDD, Calmar, or any headline performance metric.

Primary structural comparison uses the legacy-reproduced common window shared by
all five sleeves. LAA missing-observation controls and FAA implementation variants
are reported separately and are not silently promoted to canonical status.
"""
from pathlib import Path
from itertools import combinations
import argparse, json
import numpy as np
import pandas as pd

LEGACY_FILES = {
    'HAA':'G2_HAA_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',
    'BAA_Aggressive':'G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',
    'ADM':'G2_ADM_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',
    'FAA_legacy':'G2_FAA_LEGACY_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',
    'LAA':'G2_LAA_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',
}
FAA_VARIANTS = {
    'FAA_legacy':'G2_FAA_LEGACY_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',
    'FAA_peer_only':'G2_FAA_PEER_ONLY_TARGET_WEIGHTS_v0_11.csv',
    'FAA_peer_only_exactN':'G2_FAA_PEER_ONLY_EXACTN_TARGET_WEIGHTS_v0_11.csv',
}
LAA_CONTROLS = {
    'LAA_legacy':'G2_LAA_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',
    'LAA_carry_calendar':'G2_LAA_CARRY_CALENDAR_TARGET_WEIGHTS_v0_11.csv',
    'LAA_last13_available':'G2_LAA_LAST13_AVAILABLE_TARGET_WEIGHTS_v0_11.csv',
}
TOL=1e-12


def read_weights(path: Path) -> pd.DataFrame:
    d=pd.read_csv(path,index_col=0).astype(float)
    d.index=d.index.astype(str)
    return d


def align(a: pd.DataFrame,b: pd.DataFrame,months=None):
    if months is None:
        months=sorted(set(a.index)&set(b.index))
    cols=sorted(set(a.columns)|set(b.columns))
    aa=a.reindex(index=months,columns=cols,fill_value=0.0)
    bb=b.reindex(index=months,columns=cols,fill_value=0.0)
    return aa,bb


def change_indicator(d: pd.DataFrame, months):
    x=d.reindex(months).round(12)
    ch=x.diff().abs().sum(axis=1)>TOL
    if len(ch): ch.iloc[0]=False
    return ch


def run_stats(d: pd.DataFrame, months):
    ch=change_indicator(d,months)
    grp=ch.cumsum()
    lens=grp.value_counts().sort_index().to_numpy()
    return {
        'months':len(months),
        'change_months_excluding_first':int(ch.iloc[1:].sum()) if len(ch)>1 else 0,
        'change_rate_excluding_first':float(ch.iloc[1:].mean()) if len(ch)>1 else np.nan,
        'n_constant_weight_runs':int(len(lens)),
        'mean_constant_weight_run_months':float(np.mean(lens)) if len(lens) else np.nan,
        'median_constant_weight_run_months':float(np.median(lens)) if len(lens) else np.nan,
        'max_constant_weight_run_months':int(np.max(lens)) if len(lens) else 0,
    }


def safe_corr(a,b):
    x=pd.concat([pd.Series(a),pd.Series(b)],axis=1).dropna()
    if len(x)<2 or x.iloc[:,0].nunique()<2 or x.iloc[:,1].nunique()<2:
        return np.nan
    return float(x.iloc[:,0].corr(x.iloc[:,1]))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project-root', default=str(Path(__file__).resolve().parents[2]))
    args=ap.parse_args()
    root=Path(args.project_root).resolve()
    out=root/'03_Data_and_Code'/'04_Outputs'; out.mkdir(parents=True,exist_ok=True)

    W={k:read_weights(out/f) for k,f in LEGACY_FILES.items()}
    panel=pd.read_csv(out/'G2_DECISION_PANEL_INDEPENDENT_v0_11.csv')
    panel['signal_month']=panel['signal_month'].astype(str)
    meta={k:panel[panel.sleeve==k].set_index('signal_month') for k in LEGACY_FILES}

    common=sorted(set.intersection(*[set(d.index) for d in W.values()]))
    if not common:
        raise RuntimeError('No common five-sleeve window')

    # Sleeve persistence.
    persistence=[]
    changes={}
    for k,d in W.items():
        st=run_stats(d,common); st['sleeve']=k; st['window']='legacy_common_five_sleeve'
        persistence.append(st); changes[k]=change_indicator(d,common)

    # Full-sample LAA information-state controls.
    for tag,f in LAA_CONTROLS.items():
        d=read_weights(out/f)
        months=sorted(d.index)
        st=run_stats(d,months); st['sleeve']=tag; st['window']='available_for_variant'
        persistence.append(st)
    pd.DataFrame(persistence).to_csv(out/'G4_SLEEVE_PERSISTENCE_v0_12.csv',index=False)

    # Pairwise decision diagnostics on the common legacy window.
    pair=[]
    for a,b in combinations(W.keys(),2):
        aa,bb=align(W[a],W[b],common)
        l1=(aa-bb).abs().sum(axis=1)
        ma=meta[a].reindex(common); mb=meta[b].reindex(common)
        da=pd.to_numeric(ma.rule_defensive_fraction,errors='coerce')
        db=pd.to_numeric(mb.rule_defensive_fraction,errors='coerce')
        anya=da>TOL; anyb=db>TOL
        ca=changes[a]; cb=changes[b]
        union=int((ca|cb).sum()); inter=int((ca&cb).sum())
        js=[]
        for m in common:
            sa={x for x in str(ma.loc[m,'selected_assets']).split('|') if x and x!='nan'}
            sb={x for x in str(mb.loc[m,'selected_assets']).split('|') if x and x!='nan'}
            js.append(len(sa&sb)/len(sa|sb) if (sa|sb) else 1.0)
        pair.append({
            'sleeve_a':a,'sleeve_b':b,'common_months':len(common),
            'mean_L1_target_weight_distance':float(l1.mean()),
            'median_L1_target_weight_distance':float(l1.median()),
            'identical_target_weight_months':int((l1<=TOL).sum()),
            'identical_target_weight_rate':float((l1<=TOL).mean()),
            'any_defense_state_agreement_rate':float((anya==anyb).mean()),
            'defensive_fraction_correlation':safe_corr(da,db),
            'transition_month_intersection':inter,
            'transition_month_union':union,
            'transition_jaccard':float(inter/union) if union else np.nan,
            'transition_indicator_correlation':safe_corr(ca.astype(int),cb.astype(int)),
            'mean_selected_asset_jaccard':float(np.mean(js)),
        })
    pairdf=pd.DataFrame(pair)
    pairdf.to_csv(out/'G4_PAIRWISE_DECISION_DIVERSITY_v0_12.csv',index=False)

    # Leave-one-out structural contribution. This does not assess performance; it asks
    # which sleeve contributes to allocation dispersion versus transition desynchronization.
    def avg_pair_metric(subset, metric):
        vals=[]
        for a,b in combinations(subset,2):
            q=pairdf[((pairdf.sleeve_a==a)&(pairdf.sleeve_b==b))|((pairdf.sleeve_a==b)&(pairdf.sleeve_b==a))]
            vals.append(float(q.iloc[0][metric]))
        return float(np.mean(vals))
    base=list(W.keys())
    base_metrics={m:avg_pair_metric(base,m) for m in ['mean_L1_target_weight_distance','transition_jaccard','mean_selected_asset_jaccard','any_defense_state_agreement_rate']}
    loo=[]
    for leave in base:
        sub=[x for x in base if x!=leave]
        row={'removed_sleeve':leave,'remaining_sleeves':'|'.join(sub)}
        for m,bv in base_metrics.items():
            val=avg_pair_metric(sub,m); row[m]=val; row['relative_change_'+m]=val/bv-1 if abs(bv)>1e-15 else np.nan
        loo.append(row)
    pd.DataFrame(loo).to_csv(out/'G4_LEAVE_ONE_OUT_STRUCTURAL_DIVERSITY_v0_12.csv',index=False)

    # Monthly ensemble synchronization and dispersion: four dynamic sleeves vs all five.
    D=pd.DataFrame({k:pd.to_numeric(meta[k].reindex(common).rule_defensive_fraction,errors='coerce') for k in W},index=common)
    C=pd.DataFrame({k:changes[k] for k in W},index=common)

    def monthly_avg_pair_l1(subset):
        vals=[]
        for m in common:
            ds=[]
            for a,b in combinations(subset,2):
                aa,bb=align(W[a],W[b],[m]); ds.append(float((aa-bb).abs().sum(axis=1).iloc[0]))
            vals.append(np.mean(ds))
        return pd.Series(vals,index=common,dtype=float)

    monthly_rows=[]; ensemble_rows=[]
    subsets={
        'dynamic_four':['HAA','BAA_Aggressive','ADM','FAA_legacy'],
        'all_five':['HAA','BAA_Aggressive','ADM','FAA_legacy','LAA'],
    }
    for label,subset in subsets.items():
        l1=monthly_avg_pair_l1(subset)
        anydef=D[subset]>TOL
        disagree=[]
        for _,r in anydef.iterrows():
            v=r.astype(int).to_numpy(); n=len(v)
            disagree.append(sum(v[i]!=v[j] for i in range(n) for j in range(i+1,n))/(n*(n-1)/2))
        disagree=pd.Series(disagree,index=common,dtype=float)
        dstd=D[subset].std(axis=1,ddof=0)
        changed_fraction=C[subset].mean(axis=1)
        all_changed=C[subset].all(axis=1)
        none_changed=(~C[subset]).all(axis=1)
        for m in common:
            monthly_rows.append({
                'group':label,'signal_month':m,
                'avg_pairwise_L1_target_weight_distance':float(l1.loc[m]),
                'pairwise_any_defense_disagreement_rate':float(disagree.loc[m]),
                'cross_sectional_defensive_fraction_std':float(dstd.loc[m]),
                'fraction_sleeves_changing_target_weights':float(changed_fraction.loc[m]),
                'all_sleeves_changed':bool(all_changed.loc[m]),
                'no_sleeve_changed':bool(none_changed.loc[m]),
            })
        ensemble_rows.append({
            'group':label,'months':len(common),
            'mean_avg_pairwise_L1_target_weight_distance':float(l1.mean()),
            'median_avg_pairwise_L1_target_weight_distance':float(l1.median()),
            'mean_pairwise_any_defense_disagreement_rate':float(disagree.mean()),
            'median_pairwise_any_defense_disagreement_rate':float(disagree.median()),
            'mean_cross_sectional_defensive_fraction_std':float(dstd.mean()),
            'mean_fraction_sleeves_changing_target_weights':float(changed_fraction.mean()),
            'all_sleeves_changed_months':int(all_changed.sum()),
            'no_sleeve_changed_months':int(none_changed.sum()),
        })
    pd.DataFrame(monthly_rows).to_csv(out/'G4_MONTHLY_DECISION_SYNCHRONIZATION_v0_12.csv',index=False)
    ens=pd.DataFrame(ensemble_rows)
    ens.to_csv(out/'G4_ENSEMBLE_DECISION_DIVERSITY_SUMMARY_v0_12.csv',index=False)

    # LAA contribution as a structural, not performance, comparison.
    d4=ens.set_index('group').loc['dynamic_four']; a5=ens.set_index('group').loc['all_five']
    laa_effect=pd.DataFrame([{
        'common_months':len(common),
        'dynamic_four_mean_pairwise_L1':d4['mean_avg_pairwise_L1_target_weight_distance'],
        'all_five_mean_pairwise_L1':a5['mean_avg_pairwise_L1_target_weight_distance'],
        'relative_change_pairwise_L1':a5['mean_avg_pairwise_L1_target_weight_distance']/d4['mean_avg_pairwise_L1_target_weight_distance']-1,
        'dynamic_four_any_defense_disagreement':d4['mean_pairwise_any_defense_disagreement_rate'],
        'all_five_any_defense_disagreement':a5['mean_pairwise_any_defense_disagreement_rate'],
        'relative_change_any_defense_disagreement':a5['mean_pairwise_any_defense_disagreement_rate']/d4['mean_pairwise_any_defense_disagreement_rate']-1,
        'dynamic_four_defensive_fraction_std':d4['mean_cross_sectional_defensive_fraction_std'],
        'all_five_defensive_fraction_std':a5['mean_cross_sectional_defensive_fraction_std'],
        'relative_change_defensive_fraction_std':a5['mean_cross_sectional_defensive_fraction_std']/d4['mean_cross_sectional_defensive_fraction_std']-1,
        'dynamic_four_mean_fraction_changing':d4['mean_fraction_sleeves_changing_target_weights'],
        'all_five_mean_fraction_changing':a5['mean_fraction_sleeves_changing_target_weights'],
        'dynamic_four_all_changed_months':int(d4['all_sleeves_changed_months']),
        'all_five_all_changed_months':int(a5['all_sleeves_changed_months']),
    }])
    laa_effect.to_csv(out/'G4_LAA_STRUCTURAL_CONTRIBUTION_v0_12.csv',index=False)

    # FAA implementation sensitivity; do not select a branch based on these results.
    F={k:read_weights(out/f) for k,f in FAA_VARIANTS.items()}
    faa_rows=[]
    legacy=F['FAA_legacy']
    for tag,d in F.items():
        months=sorted(set(legacy.index)&set(d.index))
        aa,bb=align(legacy,d,months); dl=(aa-bb).abs().sum(axis=1)
        adm_a,adm_b=align(W['ADM'],d,sorted(set(W['ADM'].index)&set(d.index)))
        adm_l1=(adm_a-adm_b).abs().sum(axis=1)
        st=run_stats(d,sorted(d.index))
        faa_rows.append({
            'variant':tag,'months':len(d),
            'months_different_from_legacy':int((dl>TOL).sum()),
            'identical_to_legacy_months':int((dl<=TOL).sum()),
            'mean_L1_vs_legacy':float(dl.mean()),'max_L1_vs_legacy':float(dl.max()),
            'mean_L1_vs_ADM':float(adm_l1.mean()),
            'identical_target_weight_rate_vs_ADM':float((adm_l1<=TOL).mean()),
            'change_rate_excluding_first':st['change_rate_excluding_first'],
            'max_constant_weight_run_months':st['max_constant_weight_run_months'],
        })
    pd.DataFrame(faa_rows).to_csv(out/'G4_FAA_VARIANT_STRUCTURAL_SENSITIVITY_v0_12.csv',index=False)

    # LAA missing-observation controls: exact overlap and continuation months.
    L={k:read_weights(out/f) for k,f in LAA_CONTROLS.items()}
    lrows=[]
    leg=L['LAA_legacy']
    for tag,d in L.items():
        idx=sorted(set(leg.index)&set(d.index)); aa,bb=align(leg,d,idx); dl=(aa-bb).abs().sum(axis=1)
        extra=sorted(set(d.index)-set(leg.index)); st=run_stats(d,sorted(d.index))
        lrows.append({
            'variant':tag,'months':len(d),'overlap_months_with_legacy':len(idx),
            'max_L1_on_legacy_overlap':float(dl.max()) if len(dl) else np.nan,
            'different_overlap_months':int((dl>TOL).sum()) if len(dl) else 0,
            'extra_months_after_legacy_missing_window':len(extra),
            'extra_month_list':'|'.join(extra),
            'change_rate_excluding_first':st['change_rate_excluding_first'],
            'mean_constant_weight_run_months':st['mean_constant_weight_run_months'],
            'median_constant_weight_run_months':st['median_constant_weight_run_months'],
            'max_constant_weight_run_months':st['max_constant_weight_run_months'],
        })
    pd.DataFrame(lrows).to_csv(out/'G4_LAA_INFORMATION_STATE_CONTROL_v0_12.csv',index=False)

    # HAA R trace exact regime check.
    rtrace=pd.read_csv(out/'G2_HAA_CANARY_TRACE_R_v0_11_1.csv')
    hp=meta['HAA'].reset_index()[['signal_month','state']].copy()
    hp['python_regime']=hp['state'].map({'risk':1,'defensive':0})
    hm=rtrace.merge(hp[['signal_month','python_regime']],on='signal_month',how='inner')
    hpass=bool(len(hm)==218 and (hm['regime']==hm['python_regime']).all())

    # Direction record. P1/P4 only preliminary; P2/P3 remain closed until their planned tests.
    p=pairdf.set_index(['sleeve_a','sleeve_b'])
    def row_for(a,b):
        if (a,b) in p.index: return p.loc[(a,b)]
        return p.loc[(b,a)]
    hb=row_for('HAA','BAA_Aggressive'); af=row_for('ADM','FAA_legacy')
    record={
        'version':'v0.12',
        'performance_blind':True,
        'headline_performance_computed':False,
        'legacy_common_window':[common[0],common[-1]],
        'legacy_common_months':len(common),
        'haa_r_python_regime_trace_exact_match':hpass,
        'g2_target_weight_equivalence_all_five':'PASS',
        'preliminary_positioning':{
            'P1_beyond_simple_combination':'PRELIMINARY_SUPPORT',
            'P2_incremental_beyond_return_correlation':'PRELIMINARY_PASS_SEE_P2_RECORD',
            'P3_generalization_beyond_exact_five':'OPEN_NOT_TESTED',
            'P4_persistence_hypothesis':'PRELIMINARY_STRUCTURAL_SUPPORT',
            'P5_practitioner_usefulness':'CONCEPTUALLY_SUPPORTED_NOT_FINAL',
        },
        'key_structural_findings':{
            'HAA_vs_BAA_any_defense_agreement_rate':float(hb['any_defense_state_agreement_rate']),
            'HAA_vs_BAA_mean_L1':float(hb['mean_L1_target_weight_distance']),
            'ADM_vs_FAA_any_defense_agreement_rate':float(af['any_defense_state_agreement_rate']),
            'ADM_vs_FAA_defensive_fraction_correlation':float(af['defensive_fraction_correlation']),
            'ADM_vs_FAA_mean_L1':float(af['mean_L1_target_weight_distance']),
            'LAA_legacy_change_rate':float(pd.DataFrame(persistence).query("sleeve=='LAA' and window=='legacy_common_five_sleeve'").iloc[0]['change_rate_excluding_first']),
            'dynamic_four_mean_pairwise_L1':float(d4['mean_avg_pairwise_L1_target_weight_distance']),
            'all_five_mean_pairwise_L1':float(a5['mean_avg_pairwise_L1_target_weight_distance']),
            'dynamic_four_all_changed_months':int(d4['all_sleeves_changed_months']),
            'all_five_all_changed_months':int(a5['all_sleeves_changed_months']),
        },
        'interpretation_limits':[
            'These are decision-structure diagnostics, not evidence of superior investment performance.',
            'The reduction in all-sleeve simultaneous changes after adding a persistent LAA sleeve is partly mechanical and must not be marketed as a return benefit.',
            'P2 has a preliminary pass on the frozen legacy five and must be replicated after final branch freeze; candidate-set generalization P3 remains required.',
            'FAA branch selection remains governed by source/implementation logic, not by which branch appears more diverse from ADM.',
        ],
    }
    (out/'G4_DECISION_DIVERSIFICATION_PRELIM_RECORD_v0_12.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2))

if __name__=='__main__':
    main()
