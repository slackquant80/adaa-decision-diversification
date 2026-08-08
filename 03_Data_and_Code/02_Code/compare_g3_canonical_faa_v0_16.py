#!/usr/bin/env python3
"""Compare local-R G3 canonical FAA candidate with frozen independent v0.11 control.
Performance-blind: target weights only.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'03_Data_and_Code'/'04_Outputs'
rfile=OUT/'G3_FAA_CANONICAL_PEER_ONLY_EXACTN_TARGET_WEIGHTS_R_v0_16.csv'
pfile=OUT/'G2_FAA_PEER_ONLY_EXACTN_TARGET_WEIGHTS_v0_11.csv'
if not rfile.exists(): raise FileNotFoundError(rfile)
if not pfile.exists(): raise FileNotFoundError(pfile)
r=pd.read_csv(rfile); p=pd.read_csv(pfile)
for d in (r,p): d['signal_month']=d['signal_month'].astype(str)
cols=sorted(set(r.columns[1:])|set(p.columns[1:]))
a=r.set_index('signal_month').reindex(columns=cols,fill_value=0.0)
b=p.set_index('signal_month').reindex(columns=cols,fill_value=0.0)
idx=a.index.intersection(b.index); onlyr=a.index.difference(b.index); onlyp=b.index.difference(a.index)
d=(a.loc[idx].fillna(0)-b.loc[idx].fillna(0)).abs()
mx=float(d.to_numpy().max()) if len(d) else np.nan; bad=int((d.to_numpy()>1e-10).sum()) if len(d) else 0
status='PASS' if len(onlyr)==0 and len(onlyp)==0 and bad==0 else 'MISMATCH'
rec={'version':'v0.16','status':status,'r_rows':len(r),'independent_rows':len(p),'common_rows':len(idx),'r_only_rows':len(onlyr),'independent_only_rows':len(onlyp),'max_abs_diff':mx,'cells_gt_1e-10':bad,'headline_performance_computed':False}
(OUT/'G3_FAA_CANONICAL_R_PYTHON_EQUIVALENCE_RECORD_v0_16.json').write_text(json.dumps(rec,indent=2),encoding='utf-8')
pd.DataFrame([rec]).to_csv(OUT/'G3_FAA_CANONICAL_R_PYTHON_EQUIVALENCE_v0_16.csv',index=False)
print(pd.DataFrame([rec]).to_string(index=False))
if status!='PASS': raise SystemExit('Canonical FAA R/Python mismatch')
print('PASS: canonical FAA candidate R↔independent target weights match. No performance calculated.')
