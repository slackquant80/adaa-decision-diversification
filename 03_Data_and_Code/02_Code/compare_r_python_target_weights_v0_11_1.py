#!/usr/bin/env python3
"""Cell-by-cell R vs independent Python target-weight equivalence for ADAA G2 v0.11."""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd

MAP={
'HAA':('G2_HAA_TARGET_WEIGHTS_R_v0_11_1.csv','G2_HAA_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv'),
'BAA_Aggressive':('G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_R_v0_11_1.csv','G2_BAA_AGGRESSIVE_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv'),
'ADM':('G2_ADM_TARGET_WEIGHTS_R_v0_11_1.csv','G2_ADM_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv'),
'FAA_legacy':('G2_FAA_LEGACY_TARGET_WEIGHTS_R_v0_11_1.csv','G2_FAA_LEGACY_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv'),
'LAA':('G2_LAA_TARGET_WEIGHTS_R_v0_11_1.csv','G2_LAA_TARGET_WEIGHTS_INDEPENDENT_v0_11.csv')}

def read_r(path):
    d=pd.read_csv(path); d=d.set_index('signal_month'); return d.astype(float)
def read_py(path):
    d=pd.read_csv(path,index_col=0); d.index=d.index.astype(str); return d.astype(float)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default=str(Path(__file__).resolve().parents[2])); args=ap.parse_args()
    root=Path(args.project_root).resolve(); out=root/'03_Data_and_Code'/'04_Outputs'
    rows=[]; diffs=[]
    for sleeve,(rf,pf) in MAP.items():
        rp=out/rf; pp=out/pf
        if not rp.exists(): raise FileNotFoundError(f'Missing R export: {rp}')
        r=read_r(rp); p=read_py(pp)
        idx=r.index.intersection(p.index); cols=sorted(set(r.columns)|set(p.columns))
        rr=r.reindex(index=idx,columns=cols,fill_value=0); py=p.reindex(index=idx,columns=cols,fill_value=0)
        delta=(rr-py).abs(); maxd=float(delta.to_numpy().max()) if delta.size else np.nan
        nd=int((delta>1e-12).to_numpy().sum()); month_set_match=set(r.index)==set(p.index)
        rows.append({'sleeve':sleeve,'r_months':len(r),'python_months':len(p),'common_months':len(idx),'month_set_match':month_set_match,'max_abs_weight_diff':maxd,'n_cells_diff_gt_1e_12':nd,'pass':bool(month_set_match and maxd<=1e-12)})
        if nd:
            st=delta.stack(); st=st[st>1e-12].sort_values(ascending=False).head(50)
            for (m,a),v in st.items(): diffs.append({'sleeve':sleeve,'signal_month':m,'asset':a,'abs_diff':v,'R':rr.loc[m,a],'Python':py.loc[m,a]})
    summary=pd.DataFrame(rows); summary.to_csv(out/'G2_R_PYTHON_TARGET_WEIGHT_EQUIVALENCE_v0_11_1.csv',index=False)
    pd.DataFrame(diffs).to_csv(out/'G2_R_PYTHON_TARGET_WEIGHT_DIFF_DETAIL_v0_11_1.csv',index=False)
    rec={'version':'v0.11.1','all_pass':bool(summary['pass'].all()),'performance_blind':True,'headline_performance_computed':False,'sleeves':rows}
    (out/'G2_R_PYTHON_TARGET_WEIGHT_EQUIVALENCE_RECORD_v0_11_1.json').write_text(json.dumps(rec,indent=2),encoding='utf-8')
    print(summary.to_string(index=False)); print('ALL_PASS=',rec['all_pass'])

if __name__=='__main__': main()
