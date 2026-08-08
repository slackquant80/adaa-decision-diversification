"""ADAA v0.15.1 independent parent-decision reconstruction and R↔Python equivalence.

This script is deliberately performance-blind. It reads only frozen adjusted prices,
UNRATE information-state exports, and R target-weight exports created by the local v0.15 R script.
It does NOT calculate strategy returns, portfolio returns, CAGR, Sharpe, drawdown, Calmar,
or optimize any rule.
"""
from __future__ import annotations
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "03_Data_and_Code" / "04_Outputs"
SIGNAL_START, SIGNAL_END = "2008-05", "2026-06"
TOL = 1e-10

MONTHLY_FILE = OUT / "G5_FROZEN_MONTH_END_ADJUSTED_R_v0_15.csv"
DAILY_FILE = OUT / "G5_FROZEN_ADJUSTED_DAILY_LONG_R_v0_15.csv"
UIS_FILE = OUT / "G5_UNRATE_INFORMATION_STATE_R_v0_15.csv"
for f in [MONTHLY_FILE, DAILY_FILE, UIS_FILE]:
    if not f.exists():
        raise FileNotFoundError(f"Missing local-R v0.15 export: {f}")

monthly = pd.read_csv(MONTHLY_FILE)
monthly["signal_month"] = monthly["signal_month"].astype(str)
monthly = monthly.set_index("signal_month").sort_index()

daily_long = pd.read_csv(DAILY_FILE, parse_dates=["date"])
daily = daily_long.pivot(index="date", columns="symbol", values="adjusted").sort_index()
uis = pd.read_csv(UIS_FILE)
uis["calendar_month"] = uis["calendar_month"].astype(str)
uis = uis.set_index("calendar_month")

months = monthly.index.tolist()
month_pos = {m:i for i,m in enumerate(months)}

def val(sym, m):
    return float(monthly.loc[m, sym])

def prior_month(m: str, k: int) -> str:
    p = pd.Period(m, freq="M") - k
    return str(p)

def has(m, syms, lags):
    try:
        for k in [0, *lags]:
            mm = prior_month(m, k)
            if mm not in monthly.index:
                return False
            if not np.isfinite(monthly.loc[mm, syms].to_numpy(dtype=float)).all():
                return False
        return True
    except KeyError:
        return False

def mom_ret(sym, m, lags):
    p0=val(sym,m)
    return float(np.mean([p0/val(sym,prior_month(m,k))-1 for k in lags]))

def mom_sum(sym,m,lags):
    p0=val(sym,m)
    return float(np.sum([p0/val(sym,prior_month(m,k))-1 for k in lags]))

def baa_fast(sym,m):
    p=val(sym,m)
    return (12*(p/val(sym,prior_month(m,1))-1)+4*(p/val(sym,prior_month(m,3))-1)
            +2*(p/val(sym,prior_month(m,6))-1)+(p/val(sym,prior_month(m,12))-1))

def sma13(sym,m):
    xs=[val(sym,prior_month(m,k)) for k in range(13)]
    return val(sym,m)/float(np.mean(xs))

def pick(scores: dict[str,float], n: int, high=True):
    items=[(k,v) for k,v in scores.items() if np.isfinite(v)]
    items=sorted(items, key=lambda kv: ((-kv[1] if high else kv[1]), kv[0]))
    return [k for k,_ in items[:n]]

def frame(rows, cols):
    if not rows:
        return pd.DataFrame(columns=["signal_month",*cols])
    d=pd.DataFrame(rows).set_index("signal_month")
    for c in cols:
        if c not in d: d[c]=0.0
    d=d[cols].fillna(0.0)
    d.index.name="signal_month"
    return d.reset_index()

def in_window(m): return SIGNAL_START <= m <= SIGNAL_END

# HAA
def build_haa(risk, topn=4, replace_bad=True):
    safe=["IEF","BIL"]; rows=[]
    for m in months:
        if not in_window(m) or not has(m, list(dict.fromkeys(risk+safe+["TIP"])), [1,3,6,12]): continue
        tip=mom_ret("TIP",m,[1,3,6,12]); regime=tip>0
        ss={a:mom_ret(a,m,[1,3,6,12]) for a in safe}; best=pick(ss,1,True)[0]
        rs={a:mom_ret(a,m,[1,3,6,12]) for a in risk}
        w={a:0.0 for a in list(dict.fromkeys(risk+safe))}
        if not regime: w[best]=1.0
        else:
            for a in pick(rs,topn,True):
                if replace_bad and rs[a] <= 0: w[best]+=1/topn
                else: w[a]+=1/topn
        rows.append({"signal_month":m,**w})
    return frame(rows,list(dict.fromkeys(risk+safe)))

# BAA
def build_baa(offensive, top_off, canary, defensive):
    cols=list(dict.fromkeys(offensive+defensive)); rows=[]
    for m in months:
        req=list(dict.fromkeys(offensive+canary+defensive))
        if not in_window(m) or not has(m,req,[1,3,6,12]): continue
        can={a:baa_fast(a,m) for a in canary}; regime=all(v>=0 for v in can.values())
        off={a:sma13(a,m) for a in offensive}; de={a:sma13(a,m) for a in defensive}
        w={a:0.0 for a in cols}
        if regime:
            for a in pick(off,top_off,True): w[a]+=1/top_off
        else:
            bil=de["BIL"]
            for a in pick(de,3,True):
                if a!="BIL" and de[a] <= bil: w["BIL"]+=1/3
                else: w[a]+=1/3
        rows.append({"signal_month":m,**w})
    return frame(rows,cols)

# ADM parent
def build_adm(exus):
    risk=["VFINX",exus]; safe="VUSTX"; rows=[]
    for m in months:
        if not in_window(m) or not has(m,risk+[safe],[1,3,6]): continue
        sc={a:mom_sum(a,m,[1,3,6]) for a in risk}; best=pick(sc,1,True)[0]
        w={a:0.0 for a in risk+[safe]}; w[best if max(sc.values())>0 else safe]=1.0
        rows.append({"signal_month":m,**w})
    return frame(rows,risk+[safe])

# FAA parent
def build_faa(universe, cash="SHY", topn=3):
    rows=[]
    for m in months:
        if not in_window(m) or not has(m,universe,[4]): continue
        mom={a:val(a,m)/val(a,prior_month(m,4))-1 for a in universe}
        end=(pd.Period(m,"M").end_time).normalize()
        dr=daily.loc[:end,universe].pct_change(fill_method=None).dropna(how="any").tail(84)
        if len(dr)<84: continue
        vol=dr.std(ddof=1).to_dict(); corv={}
        for a in universe:
            others=[b for b in universe if b!=a]
            peer=dr[others].mean(axis=1) if others else pd.Series(0.0,index=dr.index)
            corv[a]=float(dr[a].corr(peer)) if others else 0.0
        if not np.isfinite(list(mom.values())+list(vol.values())+list(corv.values())).all(): continue
        rR=pd.Series(mom).rank(ascending=False,method="average")
        rV=pd.Series(vol).rank(ascending=True,method="average")
        rC=pd.Series(corv).rank(ascending=True,method="average")
        L=(rR+.5*rV+.5*rC).to_dict(); sel=pick(L,topn,False)
        w={a:0.0 for a in universe}
        for a in sel:
            if mom[a] > 0: w[a]+=1/topn
            else: w[cash]+=1/topn
        rows.append({"signal_month":m,**w})
    return frame(rows,universe)

# UNRATE / LAA

def ue_ratio(m, n):
    om=prior_month(m,1)
    if om not in uis.index: return np.nan
    j=uis.index.get_loc(om)
    if not isinstance(j,(int,np.integer)) or j < n-1: return np.nan
    vals=uis.iloc[j-n+1:j+1]["value"].to_numpy(float)
    if not np.isfinite(vals).all(): return np.nan
    return float(vals[-1]/vals.mean())

def spy_ratio(m,n):
    xs=[]
    for k in range(n):
        mm=prior_month(m,k)
        if mm not in monthly.index: return np.nan
        x=val("SPY",mm)
        if not np.isfinite(x): return np.nan
        xs.append(x)
    return float(xs[0]/np.mean(xs))

def build_laa(eq: dict[str,float], parent_spy=True, parent_ue=True):
    cols=list(dict.fromkeys(list(eq)+["GLD","IEF","QQQ","SHY"])); rows=[]
    for m in months:
        if not in_window(m): continue
        req=list(dict.fromkeys(list(eq)+["GLD","IEF","QQQ","SHY","SPY"]))
        if any(a not in monthly.columns or not np.isfinite(val(a,m)) for a in req): continue
        sp=spy_ratio(m,10 if parent_spy else 11); ue=ue_ratio(m,12 if parent_ue else 13)
        if not np.isfinite(sp) or not np.isfinite(ue): continue
        w={a:0.0 for a in cols}
        w.update(eq); w["GLD"]+=.25; w["IEF"]+=.25
        w["SHY" if (sp<=1 and ue>=1) else "QQQ"]+=.25
        rows.append({"signal_month":m,**w})
    return frame(rows,cols)

def build_static(weights):
    rows=[]; cols=list(weights)
    for m in months:
        if not in_window(m): continue
        if all(a in monthly.columns and np.isfinite(val(a,m)) for a in cols): rows.append({"signal_month":m,**weights})
    return frame(rows,cols)

# RAA
def build_raa():
    risky=["QQQ","IWN","IEF","TLT","GLD"]; safe=["IEF","TLT"]; cana=["VWO","BND"]
    cols=list(dict.fromkeys(risky+safe)); rows=[]
    for m in months:
        if not in_window(m) or not has(m,list(dict.fromkeys(risky+safe+cana)),[1,3,6,12]): continue
        market_bear=any(baa_fast(a,m)<0 for a in cana)
        om=prior_month(m,1)
        if om not in uis.index: continue
        j=uis.index.get_loc(om)
        if not isinstance(j,(int,np.integer)) or j<12: continue
        now=float(uis.iloc[j]["value"]); old=float(uis.iloc[j-12]["value"])
        if not np.isfinite([now,old]).all(): continue
        riskoff=market_bear and now>old
        w={a:0.0 for a in cols}
        if riskoff:
            for a in safe:w[a]=.5
        else:
            for a in risky:w[a]=.2
        rows.append({"signal_month":m,**w})
    return frame(rows,cols)

builders={
 "HAA_PARENT_PP": lambda: build_haa(["SPY","IWM","VEA","VWO","VNQ","DBC","IEF","TLT"],4,True),
 "HAA_PARENT_RULE_ADAA_UNIVERSE": lambda: build_haa(["SPY","QQQ","IWM","EFA","EEM","VNQ","DBC","IEF","TLT","EWY","GLD"],4,True),
 "HAA_ADAA_RULE_PARENT_UNIVERSE": lambda: build_haa(["SPY","IWM","VEA","VWO","VNQ","DBC","IEF","TLT"],6,False),
 "BAA_AGGRESSIVE_PARENT_PP": lambda: build_baa(["QQQ","VWO","VEA","BND"],1,["SPY","VWO","VEA","BND"],["TIP","DBC","BIL","IEF","TLT","LQD","BND"]),
 "BAA_AGGRESSIVE_PARENT_RULE_ADAA_PROXY": lambda: build_baa(["QQQ","EEM","EFA","AGG"],1,["SPY","EEM","EFA","AGG"],["TIP","DBC","BIL","IEF","TLT","LQD","AGG"]),
 "BAA_BALANCED_PARENT_PP": lambda: build_baa(["SPY","QQQ","IWM","VGK","EWJ","VWO","VNQ","DBC","GLD","TLT","HYG","LQD"],6,["SPY","VWO","VEA","BND"],["TIP","DBC","BIL","IEF","TLT","LQD","BND"]),
 "BAA_BALANCED_ADAA_PROXY_EXPRESSION": lambda: build_baa(["SPY","QQQ","IWM","VGK","EWJ","EEM","VNQ","DBC","GLD","TLT","HYG","LQD"],6,["SPY","EEM","EFA","AGG"],["TIP","DBC","BIL","IEF","TLT","LQD","AGG"]),
 "ADM_PARENT_VINEX": lambda: build_adm("VINEX"),
 "ADM_PARENT_VSS_CONTROL": lambda: build_adm("VSS"),
 "ADM_PARENT_OSMAX_CONTROL": lambda: build_adm("OSMAX"),
 "FAA_PARENT_PP": lambda: build_faa(["VTI","VEA","VWO","SHY","BND","GSG","VNQ"],"SHY",3),
 "FAA_PARENT_RULE_ADAA_UNIVERSE": lambda: build_faa(["SPY","QQQ","VGK","EWY","EEM","VNQ","DBC","GLD","TLT","HYG","LQD","TIP","SHY"],"SHY",3),
 "LAA_PARENT_PP": lambda: build_laa({"IWD":.25},True,True),
 "LAA_PARENT_RULE_ADAA_EQUITY_EXPRESSION": lambda: build_laa({"SPY":.175,"EEM":.05,"EWY":.025},True,True),
 "LAA_ADAA_TIMING_PARENT_UNIVERSE": lambda: build_laa({"IWD":.25},False,False),
 "STATIC_LAA_PARENT_RISKY_CORE": lambda: build_static({"IWD":.25,"GLD":.25,"IEF":.25,"QQQ":.25}),
 "STATIC_ADAA_LAA_RISKY_CORE": lambda: build_static({"SPY":.175,"EEM":.05,"EWY":.025,"GLD":.25,"IEF":.25,"QQQ":.25}),
 "RAA_PARENT_COMPARATOR": build_raa,
}

summary=[]; detail=[]
for tag,fn in builders.items():
    py=fn(); py.to_csv(OUT/f"G5_{tag}_TARGET_WEIGHTS_INDEPENDENT_v0_15.csv",index=False)
    rf=OUT/f"G5_{tag}_TARGET_WEIGHTS_R_v0_15.csv"
    if not rf.exists():
        summary.append({"panel":tag,"status":"R_FILE_MISSING"}); continue
    r=pd.read_csv(rf); r["signal_month"]=r["signal_month"].astype(str); py["signal_month"]=py["signal_month"].astype(str)
    cols=sorted(set(r.columns[1:])|set(py.columns[1:]))
    a=r.set_index("signal_month").reindex(columns=cols,fill_value=0.0)
    b=py.set_index("signal_month").reindex(columns=cols,fill_value=0.0)
    common=a.index.intersection(b.index); only_r=a.index.difference(b.index); only_p=b.index.difference(a.index)
    if len(common):
        d=(a.loc[common].fillna(0)-b.loc[common].fillna(0)).abs()
        mx=float(d.to_numpy().max()); bad=int((d.to_numpy()>TOL).sum())
        for m,c in zip(*np.where(d.to_numpy()>TOL)):
            detail.append({"panel":tag,"signal_month":common[m],"asset":cols[c],"r":float(a.loc[common[m],cols[c]]),"python":float(b.loc[common[m],cols[c]]),"abs_diff":float(d.iloc[m,c])})
    else: mx=np.nan; bad=0
    status="PASS" if len(only_r)==0 and len(only_p)==0 and bad==0 else "MISMATCH"
    summary.append({"panel":tag,"r_rows":len(r),"python_rows":len(py),"common_rows":len(common),"r_only_rows":len(only_r),"python_only_rows":len(only_p),"max_abs_diff":mx,"cells_gt_tol":bad,"status":status})

sdf=pd.DataFrame(summary); ddf=pd.DataFrame(detail)
sdf.to_csv(OUT/"G5_PARENT_R_PYTHON_EQUIVALENCE_v0_15.csv",index=False)
ddf.to_csv(OUT/"G5_PARENT_R_PYTHON_DIFF_DETAIL_v0_15.csv",index=False)
record={
 "version":"v0.15","performance_blind":True,"tolerance":TOL,
 "panels":summary,
 "all_available_panels_pass": bool(len(sdf) and (sdf["status"]=="PASS").all()),
 "headline_performance_computed":False,
}
(OUT/"G5_PARENT_R_PYTHON_EQUIVALENCE_RECORD_v0_15.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
print(sdf.to_string(index=False))
if not record["all_available_panels_pass"]:
    raise SystemExit("Parent R↔Python equivalence has mismatches; inspect G5_PARENT_R_PYTHON_DIFF_DETAIL_v0_15.csv")
print("PASS: all v0.15 parent/counterfactual decision panels match independently. No portfolio performance calculated.")
