from pathlib import Path
import csv, hashlib, re, sys

root = Path(__file__).resolve().parent
fail, warn = [], []
files = [p for p in root.rglob('*') if p.is_file()]
forbidden_ext = {'.rds','.rda','.rdata','.rhistory','.pdf','.docx','.xlsx','.xls','.xlsm','.parquet','.feather'}
text_ext = {'.py','.r','.md','.txt','.csv','.json','.yml','.yaml'}

for p in files:
    rel = p.relative_to(root).as_posix(); low = rel.lower()
    if p.suffix.lower() in forbidden_ext: fail.append(f'forbidden redistributed extension: {rel}')
    if any(part.lower().startswith('raw_freeze') for part in p.relative_to(root).parts): fail.append(f'raw/runtime input path not redistributable: {rel}')
    if '__pycache__' in p.parts or p.suffix.lower()=='.pyc' or '.rproj.user' in low: fail.append(f'local environment artifact: {rel}')
    if re.search(r'(^|/)(yahoo|fred).*raw', low) or ('adjusted_daily' in low and '/01_data/' in '/' + low): fail.append(f'raw-like market-data artifact: {rel}')
    if rel != '00_VALIDATE_PUBLIC_PACKAGE_v1_1_2.py' and p.suffix.lower() in text_ext and p.stat().st_size < 5_000_000:
        txt = p.read_text(encoding='utf-8', errors='ignore')
        if (re.search(r'[A-Za-z]:\\Users\\[^\\\s]+', txt) or re.search(r'[A-Za-z]:/Users/[^/\s]+', txt)
            or re.search(r'/(?:Users|home)/[^/\s]+/', txt) or '/mnt/data' in txt):
            fail.append(f'concrete local absolute path string: {rel}')
        if re.search(r'(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*["\'][A-Za-z0-9_\-]{16,}["\']', txt):
            fail.append(f'credential-like literal: {rel}')

figdir = root/'05_Practical_Paper/03_Figures'
active = [
'Figure_1_Return_Correlation_vs_Decision_Timing_PAPER_v1.25_EXACT.png',
'Figure_2_What_When_HowMuch_Decision_Fingerprints_PAPER_v1.25_EXACT.png',
'Figure_3_Different_Decision_Clocks_PAPER_v1.25_EXACT.png',
'Figure_4_Rolling_60M_Hindsight_Winner_PAPER_v1.25_EXACT.png',
'Figure_5_Broad_Plateau_Unstable_Optimum_PAPER_v1.25_EXACT.png',
'Figure_6_Cumulative_Wealth_PAPER_v1.25_EXACT.png',
'Figure_7_Drawdown_Depth_and_Duration_PAPER_v1.25_EXACT.png',
'Figure_8_Stress_Protection_and_Rapid_Reversal_PAPER_v1.25_EXACT.png',
'Figure_A1_Full_2023_Pairwise_Decision_Distance_PAPER_v1.25_EXACT.png',
'Figure_A2_Full_2023_Five_Rule_Score_Distribution_PAPER_v1.25_EXACT.png',
'Figure_B1_Currency_Exposure_Growth_PAPER_v1.25_EXACT.png',
'Figure_B2_Threshold_Sensitivity_PAPER_v1.25_EXACT.png']
missing=[x for x in active if not (figdir/x).exists()]
if missing: fail.append('missing active figures: '+', '.join(missing))
pngs=[p.name for p in figdir.glob('*.png')]
extra=sorted(set(pngs)-set(active))
if extra: fail.append('nonactive PNGs present in active figure directory: '+', '.join(extra))

required=[
'README.md','RELEASE_NOTES_v1.1.2.md','RUN_ORDER_v1.0.1.md','RIGHTS_AND_PRIVACY_GUARDRAILS.md',
'05_Practical_Paper/EXHIBIT_DATA_POINTERS_v1.1.6.csv',
'05_Practical_Paper/04_Tables/TABLE_1_PUBLICATION_SOURCE_v1.1.csv',
'05_Practical_Paper/04_Tables/TABLE_1B_PUBLICATION_SOURCE_v1.1.csv',
'05_Practical_Paper/03_Figures/EXACT_FIGURE_RENDER_MANIFEST_v1.1.6.csv',
'03_Data_and_Code/02_Code/18_RENDER_PUBLICATION_EXHIBITS_v1_1_6.py',
'05_Practical_Paper/PUBLICATION_LABEL_MAP_v1.0.1.csv',
'06_Public_Metadata/PUBLICATION_TARGET_v1.1.2.csv',
'03_Data_and_Code/03_Validation/Release_Clean_Run/SSRN_v1.25_FINAL_HOUSE_REVIEW_AND_RELEASE_BINDING_v1.1.2.md',
'03_Data_and_Code/03_Validation/Release_Clean_Run/SSRN_v1.24_TABLE_RECONCILIATION_v1.1.csv',
'STATIC_VALIDATION_RECORD_v1.1.2.txt','MANIFEST_SHA256_v1.1.2.csv']
for x in required:
    if not (root/x).exists(): fail.append(f'missing required release file: {x}')

pt=root/'06_Public_Metadata/PUBLICATION_TARGET_v1.1.2.csv'
if pt.exists():
    with pt.open(encoding='utf-8-sig',newline='') as f: md={r['field']:r['value'] for r in csv.DictReader(f)}
    checks={
      'paper_filename':'ADAA_SSRN_Working_Paper_v1.25_FINAL_FREEZE.pdf',
      'paper_pdf_sha256':'833459a65cc76dc17f2624367b4ffeaf9ff75a63ac19493b2f31a51e93c531a5',
      'paper_pages':'25','science_change_from_v1.1.1':'NO','science_change_from_v1.0.2':'NO',
      'exact_renderer':'18_RENDER_PUBLICATION_EXHIBITS_v1_1_6.py',
      'exact_figure_manifest':'EXACT_FIGURE_RENDER_MANIFEST_v1.1.6.csv'}
    for k,v in checks.items():
        if md.get(k)!=v: fail.append(f'unexpected publication target {k}: {md.get(k)!r}')

exact_manifest=figdir/'EXACT_FIGURE_RENDER_MANIFEST_v1.1.6.csv'
if exact_manifest.exists():
    with exact_manifest.open(encoding='utf-8-sig',newline='') as f: erows=list(csv.DictReader(f))
    if len(erows)!=12: fail.append(f'exact figure manifest row count: {len(erows)}')
    labels=[r['exhibit'] for r in erows]
    expected_labels=['Figure 1','Figure 2','Figure 3','Figure 4','Figure 5','Figure 6','Figure 7','Figure 8','Figure A1','Figure A2','Figure B1','Figure B2']
    if labels!=expected_labels: fail.append('unexpected current exhibit labels/order')
    for r in erows:
        for field,hfield in [('publication_png','png_sha256'),('publication_svg','svg_sha256'),('source_data','source_sha256')]:
            p=figdir/r[field]
            if not p.exists(): fail.append(f'exact exhibit missing: {r[field]}'); continue
            h=hashlib.sha256(p.read_bytes()).hexdigest()
            if h!=r[hfield]: fail.append(f'exact exhibit hash mismatch: {r[field]}')

# Preserve the previously frozen 40-check table reconciliation without recomputation.
table_check=root/'03_Data_and_Code/03_Validation/Release_Clean_Run/SSRN_v1.24_TABLE_RECONCILIATION_v1.1.csv'
if table_check.exists():
    with table_check.open(encoding='utf-8-sig',newline='') as f: trows=list(csv.DictReader(f))
    if len(trows)!=40: fail.append(f'table reconciliation row count: {len(trows)}')
    for r in trows:
        if r.get('status')!='PASS': fail.append(f'table reconciliation failure: {r}')

manifest=root/'MANIFEST_SHA256_v1.1.2.csv'
if manifest.exists():
    with manifest.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    listed=[r['path'] for r in rows]
    if len(listed)!=len(set(listed)): fail.append('duplicate path in manifest')
    current=[p for p in root.rglob('*') if p.is_file()]
    expected=sorted(p.relative_to(root).as_posix() for p in current if p!=manifest)
    if sorted(listed)!=expected:
        mm=sorted(set(expected)-set(listed)); ee=sorted(set(listed)-set(expected))
        if mm: fail.append('manifest coverage missing: '+', '.join(mm[:20]))
        if ee: fail.append('manifest coverage extra: '+', '.join(ee[:20]))
    for r in rows:
        p=root/r['path']
        if not p.exists(): fail.append(f'manifest missing payload: {r["path"]}'); continue
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        if h!=r['sha256']: fail.append(f'manifest hash mismatch: {r["path"]}')
        if str(p.stat().st_size)!=r['bytes']: fail.append(f'manifest byte-size mismatch: {r["path"]}')

print('PUBLIC_PACKAGE_V1_1_2_VALIDATION:', 'PASS' if not fail else 'FAIL')
print(f'files={len(files)} active_png={len(pngs)} warnings={len(warn)} failures={len(fail)}')
for x in warn: print('WARN:',x)
for x in fail: print('FAIL:',x)
sys.exit(1 if fail else 0)
