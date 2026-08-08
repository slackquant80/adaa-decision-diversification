#!/usr/bin/env python3
"""ADAA v0.24 exploratory decision-space selector pilot.

IMPORTANT: This pilot is NOT confirmatory evidence. The distance formula was frozen only
after headline performance had already been opened. It exists to test the mechanics and
to motivate a future broad-pool, pre-registered selector. No return/performance column is read.
"""
from pathlib import Path
import itertools
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'03_Data_and_Code'/'04_Outputs'
pair=pd.read_csv(OUT/'G5_P3_PAIRWISE_DECISION_GEOMETRY_v0_16.csv')
pmap={frozenset((r.panel_a,r.panel_b)):r for _,r in pair.iterrows()}
cands=['HAA_parent','BAA_Agg_parent','BAA_Balanced_parent','ADM_parent_VINEX','FAA_parent','LAA_parent','RAA_parent']

def distance(a,b):
    r=pmap[frozenset((a,b))]
    what=float(r.mean_L1)/2.0
    holdings=1.0-float(r.mean_holdings_jaccard)
    timing=1.0-float(r.transition_jaccard)
    return (what+holdings+timing)/3.0

rows=[]
for comb in itertools.combinations(cands,5):
    ds=[distance(a,b) for a,b in itertools.combinations(comb,2)]
    rows.append({'combination':' | '.join(comb),'mean_decision_distance':np.mean(ds),'min_pair_distance':np.min(ds)})
res=pd.DataFrame(rows).sort_values(['mean_decision_distance','min_pair_distance'],ascending=False).reset_index(drop=True)
res.insert(0,'rank',np.arange(1,len(res)+1))
res.to_csv(OUT/'G4_DECISION_SPACE_SELECTOR_PILOT_REBUILT_v0_24.csv',index=False)
print(res.head(10).to_string(index=False))
print('No return or performance data were used.')
