#!/usr/bin/env python3
from pathlib import Path
import json, numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'03_Data_and_Code'/'04_Outputs'
rfile=OUT/'G6_PRIMARY_PERFORMANCE_R_VALIDATION_v0_17.csv'; pfile=OUT/'G6_PRIMARY_PERFORMANCE_AND_COST_GRID_v0_17.csv'
if not rfile.exists(): raise FileNotFoundError(rfile)
r=pd.read_csv(rfile); p=pd.read_csv(pfile)
ports=['ADAA_equal20_canonical','ADAA_historical_weights_canonical','Benchmark_60_40_SPY_IEF','Sleeve_HAA','Sleeve_BAA','Sleeve_ADM','Sleeve_FAA','Sleeve_LAA']
cols=['CAGR','annualized_arithmetic_mean','annualized_volatility','BIL_excess_Sharpe','max_drawdown','Calmar','downside_deviation','max_time_under_water_months','worst_1m_return','worst_3m_return','worst_12m_return','worst_36m_return','ending_growth_of_1','total_gross_L1_turnover','annualized_mean_gross_L1_turnover']
rows=[]
for port in ports:
 for bps in [0,5,10,25,50]:
  a=r[(r.portfolio==port)&(r.cost_bps==bps)]; b=p[(p.portfolio==port)&(p.cost_bps==bps)]
  if len(a)!=1 or len(b)!=1: raise RuntimeError(f'missing row {port} {bps}')
  diffs=[abs(float(a.iloc[0][c])-float(b.iloc[0][c])) for c in cols]
  rows.append({'portfolio':port,'cost_bps':bps,'max_abs_diff':max(diffs),'cells_gt_1e-9':sum(d>1e-9 for d in diffs)})
d=pd.DataFrame(rows); d.to_csv(OUT/'G6_R_PYTHON_PERFORMANCE_EQUIVALENCE_v0_17.csv',index=False)
status='PASS' if int(d['cells_gt_1e-9'].sum())==0 else 'MISMATCH'
rec={'version':'v0.17','status':status,'rows_compared':len(d),'max_abs_diff':float(d.max_abs_diff.max()),'cells_gt_1e-9':int(d['cells_gt_1e-9'].sum())}
(OUT/'G6_R_PYTHON_PERFORMANCE_EQUIVALENCE_RECORD_v0_17.json').write_text(json.dumps(rec,indent=2),encoding='utf-8')
print(json.dumps(rec,indent=2))
if status!='PASS': raise SystemExit('R/Python performance mismatch')
