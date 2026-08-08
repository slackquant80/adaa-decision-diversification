from pathlib import Path
import hashlib, csv, re, sys
root=Path(__file__).resolve().parent
fail=[]; warn=[]
files=[p for p in root.rglob('*') if p.is_file()]
forbidden_ext={'.rds','.rda','.rdata','.rhistory','.pdf','.docx','.xlsx','.xls','.xlsm','.parquet','.feather'}
for p in files:
    rel=p.relative_to(root).as_posix(); low=rel.lower()
    if p.suffix.lower() in forbidden_ext: fail.append(f'forbidden redistributed extension: {rel}')
    if any(part.lower().startswith('raw_freeze') for part in p.relative_to(root).parts): fail.append(f'raw/runtime input path not redistributable: {rel}')
    if '__pycache__' in p.parts or p.suffix.lower()=='.pyc' or '.rproj.user' in low: fail.append(f'local environment artifact: {rel}')
    if re.search(r'(^|/)(yahoo|fred).*raw', low) or ('adjusted_daily' in low and '/01_data/' in '/'+low): fail.append(f'raw-like market-data artifact: {rel}')
    if rel not in {'00_VALIDATE_PUBLIC_PACKAGE_v1_0.py','00_VALIDATE_PUBLIC_PACKAGE_v1_0_1.py'} and p.suffix.lower() in {'.py','.r','.md','.txt','.csv','.json','.yml','.yaml'} and p.stat().st_size < 5_000_000:
        txt=p.read_text(encoding='utf-8',errors='ignore')
        if re.search(r'[A-Za-z]:\\Users\\[^\\\s]+', txt) or re.search(r'[A-Za-z]:/Users/[^/\s]+',txt) or '/Users/' in txt or '/home/oai/' in txt:
            fail.append(f'concrete local absolute path string: {rel}')
        if re.search(r'(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*["\'][A-Za-z0-9_\-]{16,}["\']',txt): fail.append(f'credential-like literal: {rel}')
figdir=root/'05_Practical_Paper/03_Figures'
active=[
'Figure_1_Return_Correlation_vs_Decision_Timing_PAPER_v1.15.png',
'Figure_2_What_When_HowMuch_Decision_Fingerprints_PAPER_v1.15.png',
'Figure_3_Different_Decision_Clocks_PAPER_v1.15.png',
'Figure_4_Rolling_60M_Hindsight_Winner_PAPER_v1.15.png',
'Figure_5_Broad_Plateau_Unstable_Optimum_PAPER_v1.15.png',
'Figure_6_Cumulative_Wealth_PAPER_v1.15.png',
'Figure_7_Drawdown_Depth_and_Duration_PAPER_v1.15.png',
'Figure_8_Stress_Protection_and_Rapid_Reversal_PAPER_v1.15.png',
'Figure_FX1_Currency_Exposure_Growth_PAPER_v1.15.png',
'Figure_FX2_Threshold_Sensitivity_PAPER_v1.15.png',
'Figure_Z1_Full_2023_Strategy_Zoo_Decision_Distance_PAPER_v1.15.png',
'Figure_Z2_Full_2023_Five_Rule_Score_Distribution_PAPER_v1.15.png']
missing=[x for x in active if not (figdir/x).exists()]
if missing: fail.append('missing active figures: '+', '.join(missing))
pngs=[p.name for p in figdir.glob('*.png')]
extra=sorted(set(pngs)-set(active))
if extra: fail.append('nonactive PNGs present in active figure directory: '+', '.join(extra))
arch=list((figdir/'Archive_v1.0').glob('*.png'))
if len(arch)!=11: fail.append(f'expected 11 archived v1.0 figure renders, found {len(arch)}')
required=['RUN_ORDER_v1.0.1.md','RIGHTS_AND_PRIVACY_GUARDRAILS.md','05_Practical_Paper/EXHIBIT_DATA_POINTERS_v1.0.1.csv','05_Practical_Paper/PUBLICATION_LABEL_MAP_v1.0.1.csv','06_Public_Metadata/PUBLICATION_TARGET_v1.0.1.csv','03_Data_and_Code/03_Validation/Release_Clean_Run/CLEAN_RUN_RELEASE_VALIDATION_v1.0.md','03_Data_and_Code/03_Validation/Release_Clean_Run/PUBLICATION_RECONCILIATION_v1.0.1.md','03_Data_and_Code/03_Validation/Release_Clean_Run/PUBLICATION_RECONCILIATION_CHECKS_v1.0.1.csv','MANIFEST_SHA256_v1.0.1.csv']
for x in required:
    if not (root/x).exists(): fail.append(f'missing required release file: {x}')
# reconciliation rows must all PASS
rc=root/'03_Data_and_Code/03_Validation/Release_Clean_Run/PUBLICATION_RECONCILIATION_CHECKS_v1.0.1.csv'
if rc.exists():
    with rc.open(encoding='utf-8-sig',newline='') as f: rr=list(csv.DictReader(f))
    if len(rr)<17: fail.append(f'publication reconciliation unexpectedly short: {len(rr)} rows')
    for r in rr:
        if r.get('status')!='PASS': fail.append(f'publication reconciliation failure: {r}')
# manifest coverage: every file except manifest itself must be listed exactly once
manifest=root/'MANIFEST_SHA256_v1.0.1.csv'
if manifest.exists():
    with manifest.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    listed=[r['path'] for r in rows]
    if len(listed)!=len(set(listed)): fail.append('duplicate path in manifest')
    expected=sorted(p.relative_to(root).as_posix() for p in files if p!=manifest)
    if sorted(listed)!=expected:
        missing_m=sorted(set(expected)-set(listed)); extra_m=sorted(set(listed)-set(expected))
        if missing_m: fail.append('manifest coverage missing: '+', '.join(missing_m[:20]))
        if extra_m: fail.append('manifest coverage extra: '+', '.join(extra_m[:20]))
    for r in rows:
        p=root/r['path']
        if not p.exists(): fail.append(f'manifest missing payload: {r["path"]}'); continue
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        if h!=r['sha256']: fail.append(f'manifest hash mismatch: {r["path"]}')
print('PUBLIC_PACKAGE_V1_0_1_VALIDATION:', 'PASS' if not fail else 'FAIL')
print(f'files={len(files)} active_png={len(pngs)} archived_v1_0_png={len(arch)} warnings={len(warn)} failures={len(fail)}')
for x in warn: print('WARN:',x)
for x in fail: print('FAIL:',x)
sys.exit(1 if fail else 0)
