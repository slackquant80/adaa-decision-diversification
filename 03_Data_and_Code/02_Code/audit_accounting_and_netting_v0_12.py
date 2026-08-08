#!/usr/bin/env python3
"""Performance-blind G3 accounting/netting audit for the historical ADAA successor.

Uses verified monthly target weights and frozen ETF returns only to reconstruct
end-of-period weight drift and rebalancing turnover. It does NOT compute, rank,
or write portfolio return/performance metrics.

Comparison:
- legacy_sleeve_internal_gross_turnover: weighted sum of each sleeve's gross L1
  rebalance turnover, analogous to charging costs inside sleeves before combination;
- final_account_cross_netted_gross_turnover: gross L1 turnover after aggregating
  the five sleeve targets into the final underlying-account target, so opposing
  trades can net and top-level monthly reset is represented at the asset level.

Historical top-level sleeve weights are used as a frozen diagnostic candidate,
not promoted as the canonical paper allocation.
"""
from pathlib import Path
import argparse, importlib.util, json
import numpy as np
import pandas as pd

WEIGHTS={
'HAA':('G2_HAA_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',0.25),
'BAA_Aggressive':('G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',0.15),
'ADM':('G2_ADM_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',0.175),
'FAA_legacy':('G2_FAA_LEGACY_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv',0.175),
# Latest-known information-state continuation; identical to legacy LAA on overlap.
'LAA_info_state':('G2_LAA_CARRY_CALENDAR_TARGET_WEIGHTS_v0_11.csv',0.25),
}


def load_audit(root):
    p=root/'03_Data_and_Code'/'02_Code'/'independent_frozen_data_audit_v0_10.py'
    spec=importlib.util.spec_from_file_location('auditv010',p)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def eop_weights(target, asset_ret):
    grown=target*(1.0+asset_ret)
    denom=float(grown.sum())
    if not np.isfinite(denom) or denom<=0: raise RuntimeError('Invalid EOP denominator')
    return grown/denom


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default=str(Path(__file__).resolve().parents[2])); args=ap.parse_args()
    root=Path(args.project_root).resolve(); out=root/'03_Data_and_Code'/'04_Outputs'; raw=root/'03_Data_and_Code'/'01_Data'/'raw_freeze_v0_8'
    audit=load_audit(root)
    primary=audit.named_xts_list(audit.read_rds(raw/'yahoo_primary_raw.rds'))
    daily=pd.concat({k:audit.adjusted(v) for k,v in primary.items()},axis=1).sort_index()
    monthly=daily.groupby(daily.index.to_period('M')).last(); monthly.index=monthly.index.astype(str)
    ret=monthly.pct_change(fill_method=None)

    W={}; alpha={}
    for sleeve,(f,a) in WEIGHTS.items():
        d=pd.read_csv(out/f,index_col=0).astype(float); d.index=d.index.astype(str); W[sleeve]=d; alpha[sleeve]=a
    if abs(sum(alpha.values())-1)>1e-12: raise RuntimeError('Top-level weights do not sum to 1')
    months=sorted(set.intersection(*[set(d.index) for d in W.values()]))
    assets=sorted(set().union(*[set(d.columns) for d in W.values()]))

    rows=[]; prev_eop_s=None; prev_eop_agg=None; prev_target_agg=None
    for j,sm in enumerate(months):
        em=str(pd.Period(sm,freq='M')+1)
        ar=ret.loc[em].reindex(assets)
        targets={k:W[k].loc[sm].reindex(assets,fill_value=0.0) for k in W}
        # Missing return is acceptable only for an asset with zero target in every sleeve.
        used=pd.Series(False,index=assets)
        for t in targets.values(): used |= (t.abs()>1e-15)
        if ar[used].isna().any():
            raise RuntimeError(f'Missing used-asset return at {em}: {list(ar[used & ar.isna()].index)}')
        ar=ar.fillna(0.0)
        agg=sum(alpha[k]*targets[k] for k in W)
        if abs(float(agg.sum())-1)>1e-10: raise RuntimeError(f'Aggregate target does not sum to 1 at {sm}')
        if j>0:
            legacy=sum(alpha[k]*float((targets[k]-prev_eop_s[k]).abs().sum()) for k in W)
            cross=float((agg-prev_eop_agg).abs().sum())
            target_only=float((agg-prev_target_agg).abs().sum())
            rows.append({
                'signal_month':sm,'effective_holding_month':em,
                'legacy_sleeve_internal_gross_turnover':legacy,
                'final_account_cross_netted_gross_turnover':cross,
                'cross_netted_minus_legacy':cross-legacy,
                'aggregate_target_only_gross_L1_change':target_only,
                'cross_net_lower_than_legacy':bool(cross<legacy),
            })
        prev_eop_s={k:eop_weights(targets[k],ar) for k in W}
        prev_eop_agg=eop_weights(agg,ar)
        prev_target_agg=agg

    d=pd.DataFrame(rows)
    d.to_csv(out/'G3_ACCOUNTING_NETTING_MONTHLY_AUDIT_v0_12.csv',index=False)
    legacy_total=float(d.legacy_sleeve_internal_gross_turnover.sum()); cross_total=float(d.final_account_cross_netted_gross_turnover.sum())
    rec={
        'version':'v0.12','performance_blind':True,'headline_performance_computed':False,
        'historical_top_level_weights':alpha,
        'turnover_convention':'gross_L1_traded_notional_consistent_with_legacy_dashboard_cost_ledger',
        'rebalance_months':int(len(d)),
        'legacy_total_gross_turnover':legacy_total,
        'cross_netted_total_gross_turnover':cross_total,
        'relative_cross_netted_reduction_vs_legacy':float(1-cross_total/legacy_total),
        'mean_legacy_monthly_gross_turnover':float(d.legacy_sleeve_internal_gross_turnover.mean()),
        'mean_cross_netted_monthly_gross_turnover':float(d.final_account_cross_netted_gross_turnover.mean()),
        'months_cross_net_lower':int(d.cross_net_lower_than_legacy.sum()),
        'months_cross_net_higher_or_equal':int((~d.cross_net_lower_than_legacy).sum()),
        'interpretation':[
            'The legacy dashboard charges turnover inside sleeves before combining sleeve returns, so opposing underlying trades cannot net.',
            'A final-account underlying ledger reduces total gross turnover by the reported amount under the frozen historical top-level weights.',
            'This is an implementation/accounting result only; no transaction-cost rate or portfolio performance is evaluated here.',
            'The exact turnover level will be recomputed after final canonical FAA and top-level allocation policies are frozen.',
        ],
    }
    (out/'G3_ACCOUNTING_NETTING_AUDIT_RECORD_v0_12.json').write_text(json.dumps(rec,indent=2),encoding='utf-8')
    print(json.dumps(rec,indent=2))

if __name__=='__main__': main()
