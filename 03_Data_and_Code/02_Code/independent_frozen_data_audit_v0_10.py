#!/usr/bin/env python3
"""Independent, performance-blind audit of ADAA v0.8 frozen RDS inputs.

Purpose
-------
- verify raw-file SHA-256 integrity;
- inspect missingness without filling values;
- audit legacy ETF/proxy row alignment and overlap quality;
- audit LAA UNRATE observation/weight/effective-month alignment;
- identify the earliest fully ETF-only signal month for the five-sleeve design.

This script does NOT compute ADAA/strategy performance, Sharpe, CAGR, MDD, or
select a strategy based on returns.

The RDS reader implements only the subset of R serialization needed by the
frozen objects in this project (numeric xts objects and named lists thereof).
"""
from __future__ import annotations
import argparse, calendar, csv, hashlib, json, lzma, math, os, struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

TYPES={0:'NIL',1:'SYM',2:'LIST',3:'CLO',4:'ENV',5:'PROM',6:'LANG',7:'SPECIAL',8:'BUILTIN',9:'CHAR',10:'LGL',11:'INT?',12:'?',13:'INT',14:'REAL',15:'CPLX',16:'STR',17:'DOTS',18:'ANY',19:'VEC',20:'EXPR',21:'BCODE',22:'EXTPTR',23:'WEAKREF',24:'RAW',25:'S4'}
NILVALUE_SXP=254; REFSXP=255

class Node:
    def __init__(self,t,val=None,attr=None,tag=None,flags=None,offset=None):
        self.t=t; self.val=val; self.attr=attr; self.tag=tag; self.flags=flags; self.offset=offset

class RDSParser:
    def __init__(self,b:bytes): self.b=b; self.o=0; self.refs=[]
    def u32(self): x=struct.unpack('>I',self.b[self.o:self.o+4])[0]; self.o+=4; return x
    def i32(self): x=struct.unpack('>i',self.b[self.o:self.o+4])[0]; self.o+=4; return x
    def f64(self): x=struct.unpack('>d',self.b[self.o:self.o+8])[0]; self.o+=8; return x
    def length(self):
        n=self.i32()
        if n>=0:return n
        hi=self.u32(); lo=self.u32(); return (hi<<32)|lo
    def read_header(self):
        fmt=self.b[:2]; self.o=2
        ver=self.u32(); writer=self.u32(); minr=self.u32(); enc=None
        if ver>=3:
            n=self.u32(); enc=self.b[self.o:self.o+n].decode(); self.o+=n
        return fmt,ver,writer,minr,enc
    def addref(self,node): self.refs.append(node); return node
    def parse(self):
        off=self.o; flags=self.u32(); typ=flags&255
        if flags==NILVALUE_SXP or typ==NILVALUE_SXP: return Node('NIL',None,flags=flags,offset=off)
        if typ==REFSXP:
            idx=flags>>8
            if idx==0: idx=self.u32()
            if idx<1 or idx>len(self.refs): raise RuntimeError(f'bad RDS reference {idx}')
            return self.refs[idx-1]
        has_attr=bool(flags&0x200); has_tag=bool(flags&0x400)
        if typ==9:
            n=self.length(); raw=self.b[self.o:self.o+n]; self.o+=n
            val=None if n==-1 else raw.decode('utf-8',errors='replace')
            node=Node('CHAR',val,flags=flags,offset=off)
        elif typ==1:
            node=Node('SYM',self.parse(),flags=flags,offset=off); self.addref(node)
        elif typ in (2,6,17):
            tag=self.parse() if has_tag else None; car=self.parse(); cdr=self.parse()
            node=Node(TYPES.get(typ,str(typ)),(car,cdr),tag=tag,flags=flags,offset=off)
        elif typ in (10,13):
            n=self.length(); node=Node(TYPES[typ],[self.i32() for _ in range(n)],flags=flags,offset=off)
        elif typ==14:
            n=self.length(); node=Node('REAL',[self.f64() for _ in range(n)],flags=flags,offset=off)
        elif typ==15:
            n=self.length(); node=Node('CPLX',[complex(self.f64(),self.f64()) for _ in range(n)],flags=flags,offset=off)
        elif typ in (16,19,20):
            n=self.length(); node=Node(TYPES[typ],[self.parse() for _ in range(n)],flags=flags,offset=off)
        elif typ==24:
            n=self.length(); node=Node('RAW',self.b[self.o:self.o+n],flags=flags,offset=off); self.o+=n
        elif typ==25:
            node=Node('S4',None,flags=flags,offset=off)
        else: raise RuntimeError(f'Unsupported RDS type={typ}, flags={hex(flags)}, offset={off}')
        if has_attr: node.attr=self.parse()
        return node

def pairlist_to_dict(n):
    d={}; cur=n; i=0
    while isinstance(cur,Node) and cur.t in ('LIST','LANG','DOTS'):
        key=None
        if cur.tag and cur.tag.t=='SYM' and isinstance(cur.tag.val,Node) and cur.tag.val.t=='CHAR': key=cur.tag.val.val
        car,cdr=cur.val; d[key if key is not None else i]=car; cur=cdr; i+=1
        if i>10000: raise RuntimeError('pairlist too long')
    return d

def simplify(n):
    if not isinstance(n,Node): return n
    if n.t=='CHAR': return n.val
    if n.t=='SYM': return simplify(n.val)
    if n.t in ('REAL','INT','LGL','RAW'): return n.val
    if n.t=='STR': return [simplify(x) for x in n.val]
    if n.t=='VEC':
        vals=[simplify(x) for x in n.val]
        attrs=pairlist_to_dict(n.attr) if n.attr else {}
        names=attrs.get('names')
        if names: return dict(zip(simplify(names),vals))
        return vals
    if n.t in ('LIST','LANG','DOTS'): return {k:simplify(v) for k,v in pairlist_to_dict(n).items()}
    if n.t=='NIL': return None
    return str(n.t)

def read_rds(path:Path)->Node:
    b=lzma.open(path,'rb').read(); p=RDSParser(b); p.read_header(); return p.parse()

def attrs(n): return {k:simplify(v) for k,v in pairlist_to_dict(n.attr).items()} if n.attr else {}

def xts_to_df(n:Node)->pd.DataFrame:
    a=attrs(n); nr,nc=map(int,a['dim'])
    mat=np.array(n.val,dtype=float).reshape((nc,nr)).T
    idx=pd.to_datetime(np.array(a['index'],dtype=float),unit='s',utc=True).tz_convert(None)
    dn=a.get('dimnames'); cols=dn[1] if isinstance(dn,list) and len(dn)>1 else [f'V{i+1}' for i in range(nc)]
    return pd.DataFrame(mat,index=idx,columns=cols)

def named_xts_list(n:Node)->dict[str,pd.DataFrame]:
    names=simplify(pairlist_to_dict(n.attr)['names'])
    return {name:xts_to_df(child) for name,child in zip(names,n.val)}

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def adjusted(df:pd.DataFrame)->pd.Series:
    cols=[c for c in df.columns if 'Adjusted' in c]
    if len(cols)!=1: raise RuntimeError(f'Adjusted column not unique: {list(df.columns)}')
    return df[cols[0]].astype(float)

def month_add(p:pd.Period,n:int)->pd.Period: return p+n

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default=str(Path(__file__).resolve().parents[2])); args=ap.parse_args()
    root=Path(args.project_root).resolve(); raw=root/'03_Data_and_Code'/'01_Data'/'raw_freeze_v0_8'; out=root/'03_Data_and_Code'/'04_Outputs'; out.mkdir(parents=True,exist_ok=True)

    # SHA integrity
    manifest=pd.read_csv(raw/'RAW_MANIFEST_SHA256.csv')
    sha_rows=[]
    for _,r in manifest.iterrows():
        fn=r['file']; expected=r['sha256']; actual=sha256(raw/fn); sha_rows.append([fn,expected,actual,expected==actual])
    sha_df=pd.DataFrame(sha_rows,columns=['file','expected_sha256','actual_sha256','match'])
    sha_df.to_csv(out/'G2_RAW_MANIFEST_RECHECK_v0_10.csv',index=False)
    if not sha_df['match'].all(): raise RuntimeError('raw manifest SHA mismatch')

    primary=named_xts_list(read_rds(raw/'yahoo_primary_raw.rds'))
    proxy=named_xts_list(read_rds(raw/'yahoo_proxy_raw.rds'))
    unrate=xts_to_df(read_rds(raw/'fred_UNRATE_current_vintage_raw.rds'))
    fx=xts_to_df(read_rds(raw/'yahoo_KRWUSD_raw.rds'))

    # KRW missingness detail
    miss=fx.isna()
    fx_rows=[]
    periods=fx.index.to_period('M')
    last_row_by_month=pd.Series(fx.index,index=periods).groupby(level=0).max().to_dict()
    for dt in fx.index[miss.any(axis=1)]:
        cols=[c for c in fx.columns if pd.isna(fx.loc[dt,c])]
        fx_rows.append([dt.date(),';'.join(cols),len(cols),dt==last_row_by_month[dt.to_period('M')],float(fx.loc[dt,'KRW=X.Volume']) if pd.notna(fx.loc[dt,'KRW=X.Volume']) else np.nan])
    pd.DataFrame(fx_rows,columns=['date','missing_columns','n_missing_columns','is_last_frozen_row_of_calendar_month','volume']).to_csv(out/'G2_KRWUSD_MISSINGNESS_DETAIL_v0_10.csv',index=False)

    # UNRATE missingness
    un_rows=[]
    for dt in unrate.index[unrate.isna().any(axis=1)]: un_rows.append([dt.date(),';'.join([c for c in unrate.columns if pd.isna(unrate.loc[dt,c])])])
    pd.DataFrame(un_rows,columns=['observation_month','missing_columns']).to_csv(out/'G2_UNRATE_MISSINGNESS_DETAIL_v0_10.csv',index=False)

    # Primary/proxy diagnostics
    mapping={'EEM':'VEIEX','AGG':'VBMFX','VGK':'VEURX','VNQ':'VGSIX','DBC':'PCRAX','GLD':'FKRCX','TLT':'VUSTX','HYG':'VWEHX','LQD':'VWESX','TIP':'VIPSX','BIL':'VFISX','IEF':'VFITX','SHY':'VFISX'}
    diag=[]
    extreme=[]
    for p,q in mapping.items():
        sp=adjusted(primary[p]); sq=adjusted(proxy[q])
        common=sp.to_frame('primary').join(sq.to_frame('proxy'),how='inner').dropna()
        dr=common.pct_change(fill_method=None).dropna()
        dcorr=float(dr.corr().iloc[0,1]); dte=float((dr.primary-dr.proxy).std(ddof=1)*np.sqrt(252))
        m=common.groupby(common.index.to_period('M')).last(); mr=m.pct_change(fill_method=None).dropna()
        mcorr=float(mr.corr().iloc[0,1]); mte=float((mr.primary-mr.proxy).std(ddof=1)*np.sqrt(12))
        diag.append([p,q,common.index.min().date(),common.index.max().date(),len(common),dcorr,dte,mcorr,mte])
        pr=sq.pct_change(fill_method=None)
        for dt in pr.abs().nlargest(8).index:
            prev=sq.shift(1).loc[dt]; extreme.append([q,dt.date(),float(pr.loc[dt]),float(prev),float(sq.loc[dt])])
    diag_df=pd.DataFrame(diag,columns=['primary','proxy','overlap_start','overlap_end','overlap_days','daily_return_corr','daily_tracking_error_ann','monthly_return_corr','monthly_tracking_error_ann'])
    diag_df.to_csv(out/'G2_PROXY_OVERLAP_AUDIT_v0_10.csv',index=False)
    pd.DataFrame(extreme,columns=['proxy','date','daily_adjusted_return','prior_adjusted','adjusted']).to_csv(out/'G2_PROXY_EXTREME_RETURN_AUDIT_v0_10.csv',index=False)

    # Legacy row-position splice alignment: compare the primary outer date grid with proxy complete-case grid.
    p2=pd.concat({k:adjusted(v) for k,v in proxy.items()},axis=1).dropna()
    start=p2.index[0]
    p1=pd.concat({k:adjusted(v) for k,v in primary.items()},axis=1)
    p1=p1.loc[p1.index>=start]
    date_mismatch_count=sum(a!=b for a,b in zip(p1.index,p2.index)) + abs(len(p1)-len(p2))
    p1ret=p1.pct_change(fill_method=None); p1ret.iloc[0,:]=0.0
    splice=[]
    for p,q in mapping.items():
        nna=int(p1ret[p].isna().sum()); nrows=nna+1 if nna>0 else 0
        overwrite_end=p1ret.index[nrows-1] if nrows else pd.NaT
        rawret=p1[p].pct_change(fill_method=None); first_valid=rawret.first_valid_index(); first_price=adjusted(primary[p]).index.min()
        canonical_transition=first_valid
        same_boundary=(pd.notna(overwrite_end) and pd.notna(canonical_transition) and overwrite_end < canonical_transition and (p1ret.index.get_loc(canonical_transition)==p1ret.index.get_loc(overwrite_end)+1))
        splice.append([p,q,nna,nrows,overwrite_end.date() if pd.notna(overwrite_end) else None,first_price.date(),first_valid.date() if pd.notna(first_valid) else None,bool(same_boundary),date_mismatch_count])
    pd.DataFrame(splice,columns=['primary','proxy','legacy_na_count_after_first_row_zero','legacy_proxy_overwrite_rows','legacy_proxy_overwrite_end','primary_first_price_date','primary_first_valid_return_date','legacy_boundary_equals_date_keyed_boundary','primary_proxy_panel_date_mismatch_count']).to_csv(out/'G2_LEGACY_SPLICE_ALIGNMENT_AUDIT_v0_10.csv',index=False)

    # LAA timing alignment. Reconstruct only the row/month chronology visible in the dashboard code.
    first_daily=p1.index.min().to_period('M'); last_daily=p1.index.max().to_period('M')
    market_months=pd.period_range(first_daily,last_daily,freq='M')
    # dashboard date_temp = first market date - 35 days, then first day of that month -> May 2002 in frozen panel
    date_temp=(p1.index.min()-pd.Timedelta(days=35)).to_period('M')
    un_periods=unrate.index.to_period('M'); selected=un_periods[un_periods>=date_temp]
    n=min(len(market_months),len(selected)); market_months=market_months[:n]; selected=selected[:n]
    laa=[]
    for um,wm in zip(selected,market_months):
        em=wm+1
        laa.append([str(um),str(wm),str(em),int(wm.ordinal-um.ordinal),int(em.ordinal-um.ordinal)])
    laa_df=pd.DataFrame(laa,columns=['unrate_observation_month','weight_month','effective_holding_month','weight_minus_observation_months','effective_minus_observation_months'])
    laa_df.to_csv(out/'G2_LAA_TIMING_ALIGNMENT_v0_10.csv',index=False)

    # ETF-only monthly signal readiness. Count full monthly observations for required lookbacks.
    # 13 observations is the maximum needed across the five sleeves (12m price ratio / 13m SMA).
    strategy_assets={
        'HAA':['SPY','QQQ','IWM','EFA','EEM','VNQ','DBC','IEF','TLT','EWY','GLD','BIL','TIP'],
        'BAA_Aggressive':['QQQ','EEM','EFA','AGG','TIP','DBC','IEF','TLT','LQD','BIL','SPY'],
        'ADM':['SPY','QQQ','VGK','EWY','EEM','VNQ','DBC','GLD','TLT','HYG','LQD','TIP','SHY','BIL'],
        'FAA':['SPY','QQQ','VGK','EWY','EEM','VNQ','DBC','GLD','TLT','HYG','LQD','TIP','SHY','BIL'],
        'LAA':['SPY','QQQ','EEM','EWY','IEF','GLD','SHY'],
    }
    readiness=[]
    strategy_ready={}
    for sname,assets in strategy_assets.items():
        asset_13th=[]
        for a in assets:
            ser=adjusted(primary[a]).dropna(); months=pd.Index(ser.index.to_period('M').unique()).sort_values()
            if len(months)<13: raise RuntimeError(f'{a} has <13 months')
            m13=months[12]; asset_13th.append((a,m13))
        binding=max(asset_13th,key=lambda x:x[1]); ready=binding[1]; effective=ready+1; strategy_ready[sname]=ready
        readiness.append([sname,binding[0],str(ready),str(effective)])
    all_ready=max(strategy_ready.values()); all_effective=all_ready+1
    readiness.append(['ALL_FIVE_SLEEVES',','.join([k for k,v in strategy_ready.items() if v==all_ready]),str(all_ready),str(all_effective)])
    pd.DataFrame(readiness,columns=['scope','binding_asset_or_strategy','first_signal_month_with_13_monthly_observations','first_effective_holding_month']).to_csv(out/'G2_ETF_ONLY_READINESS_v0_10.csv',index=False)

    # Last complete month based on local freeze retrieval date.
    env=pd.read_csv(raw/'environment_metadata.csv'); retrieval=pd.Timestamp(env.loc[0,'retrieval_timestamp'])
    last_complete=(retrieval.to_period('M')-1)

    summary={
        'audit_version':'v0.10',
        'performance_blind':True,
        'raw_manifest_sha_match':bool(sha_df['match'].all()),
        'primary_series_count':len(primary),
        'proxy_series_count':len(proxy),
        'krw_rows_with_any_na':int(fx.isna().any(axis=1).sum()),
        'unrate_rows_with_any_na':int(unrate.isna().any(axis=1).sum()),
        'legacy_primary_proxy_panel_date_mismatch_count':int(date_mismatch_count),
        'laa_alignment_rows':int(len(laa_df)),
        'laa_weight_minus_observation_unique':sorted(map(int,laa_df['weight_minus_observation_months'].unique())),
        'laa_effective_minus_observation_unique':sorted(map(int,laa_df['effective_minus_observation_months'].unique())),
        'all_five_etf_only_first_signal_month':str(all_ready),
        'all_five_etf_only_first_effective_holding_month':str(all_effective),
        'last_complete_calendar_month_at_freeze':str(last_complete),
        'headline_strategy_performance_computed':False,
    }
    (out/'G2_FROZEN_AUDIT_SUMMARY_v0_10.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
