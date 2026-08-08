#!/usr/bin/env python3
"""ADAA v0.18 — reconcile user-local base-R v0.17.1 performance/accounting outputs
against the independently opened Python v0.17 evidence.

This is a validation script only. It does not optimize, reselect, or modify any
strategy, universe, sample window, weight vector, cost assumption, or benchmark.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'03_Data_and_Code'/'04_Outputs'
R_PERF=OUT/'G6_PRIMARY_PERFORMANCE_R_VALIDATION_v0_17_1.csv'
PY_PERF=OUT/'G6_PRIMARY_PERFORMANCE_AND_COST_GRID_v0_17.csv'
R_PATH=OUT/'G6_PRIMARY_MONTHLY_RETURN_TURNOVER_R_VALIDATION_v0_17_1.csv'
PY_PATH=OUT/'G6_PRIMARY_MONTHLY_RETURN_TURNOVER_PATHS_v0_17.csv'
for f in [R_PERF,PY_PERF,R_PATH,PY_PATH]:
    if not f.exists(): raise FileNotFoundError(f)

ports=['ADAA_equal20_canonical','ADAA_historical_weights_canonical','Benchmark_60_40_SPY_IEF',
       'Sleeve_HAA','Sleeve_BAA','Sleeve_ADM','Sleeve_FAA','Sleeve_LAA']
metric_cols=['CAGR','annualized_arithmetic_mean','annualized_volatility','BIL_excess_Sharpe',
             'max_drawdown','Calmar','downside_deviation','max_time_under_water_months',
             'worst_1m_return','worst_3m_return','worst_12m_return','worst_36m_return',
             'ending_growth_of_1','total_gross_L1_turnover','annualized_mean_gross_L1_turnover']

r=pd.read_csv(R_PERF); p=pd.read_csv(PY_PERF)
rows=[]
for port in ports:
    for bps in [0,5,10,25,50]:
        a=r[(r.portfolio==port)&(r.cost_bps==bps)]
        b=p[(p.portfolio==port)&(p.cost_bps==bps)]
        if len(a)!=1 or len(b)!=1: raise RuntimeError(f'missing metric row {port} {bps}')
        diffs={c:abs(float(a.iloc[0][c])-float(b.iloc[0][c])) for c in metric_cols}
        rows.append({'portfolio':port,'cost_bps':bps,'max_abs_diff':max(diffs.values()),
                     'cells_gt_1e-10':sum(v>1e-10 for v in diffs.values()),
                     **{f'diff_{k}':v for k,v in diffs.items()}})
metric_diff=pd.DataFrame(rows)
metric_diff.to_csv(OUT/'G6_R_PYTHON_PERFORMANCE_EQUIVALENCE_v0_18.csv',index=False)

rp=pd.read_csv(R_PATH); pp=pd.read_csv(PY_PATH)
keys=['portfolio','signal_month','holding_month']
if rp.duplicated(keys).any() or pp.duplicated(keys).any(): raise RuntimeError('duplicate monthly path keys')
m=pp.merge(rp,on=keys,how='outer',suffixes=('_py','_r'),indicator=True)
if not (m['_merge']=='both').all():
    bad=m[m['_merge']!='both'][keys+['_merge']]
    bad.to_csv(OUT/'G6_R_PYTHON_MONTHLY_KEY_MISMATCH_v0_18.csv',index=False)
    raise RuntimeError('R/Python monthly key mismatch')
for c in ['gross_return','gross_L1_turnover']:
    m[f'diff_{c}']=(m[f'{c}_py']-m[f'{c}_r']).abs()
m[keys+['diff_gross_return','diff_gross_L1_turnover']].to_csv(
    OUT/'G6_R_PYTHON_MONTHLY_PATH_EQUIVALENCE_v0_18.csv',index=False)

max_metric=float(metric_diff.max_abs_diff.max())
metric_cells=int(metric_diff['cells_gt_1e-10'].sum())
max_ret=float(m.diff_gross_return.max())
max_turn=float(m.diff_gross_L1_turnover.max())
status='PASS' if metric_cells==0 and max_ret<=1e-10 and max_turn<=1e-10 else 'MISMATCH'
record={
    'version':'v0.18','status':status,
    'metric_rows_compared':int(len(metric_diff)),
    'monthly_rows_compared':int(len(m)),
    'max_metric_abs_diff':max_metric,
    'metric_cells_gt_1e-10':metric_cells,
    'max_monthly_gross_return_abs_diff':max_ret,
    'max_monthly_gross_turnover_abs_diff':max_turn,
    'r_input':'G6_PRIMARY_PERFORMANCE_R_VALIDATION_v0_17_1.csv',
    'python_input':'G6_PRIMARY_PERFORMANCE_AND_COST_GRID_v0_17.csv',
    'interpretation':'Independent R/Python performance and cross-netted turnover/accounting reconciliation only; no strategy reselection or optimization.'
}
(OUT/'G6_R_PYTHON_PERFORMANCE_EQUIVALENCE_RECORD_v0_18.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
if status!='PASS': raise SystemExit('R/Python performance reconciliation mismatch')
