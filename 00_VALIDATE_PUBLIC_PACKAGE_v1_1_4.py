from pathlib import Path
import csv
import hashlib
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parent
FAIL = []
WARN = []

TEXT_EXT = {'.py', '.r', '.md', '.txt', '.csv', '.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.ps1', '.sh'}
CODE_EXT = {'.py', '.r', '.ps1', '.sh'}
FORBIDDEN_EXT = {'.rds', '.rda', '.rdata', '.rhistory', '.pdf', '.docx', '.xlsx', '.xls', '.xlsm', '.parquet', '.feather'}


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def read_text(path):
    for enc in ('utf-8', 'utf-8-sig'):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            pass
    WARN.append('undecodable text file: ' + rel(path))
    return None


files = sorted(
    p for p in ROOT.rglob('*')
    if p.is_file() and '.git' not in p.relative_to(ROOT).parts
)

# Distribution-boundary checks.
for p in files:
    r = rel(p)
    low = r.lower()
    if p.suffix.lower() in FORBIDDEN_EXT:
        FAIL.append('forbidden redistributed extension: ' + r)
    if '__pycache__' in p.parts or p.suffix.lower() == '.pyc' or '.rproj.user' in low:
        FAIL.append('local environment artifact: ' + r)
    if any(part.lower().startswith('raw_freeze') for part in p.relative_to(ROOT).parts):
        FAIL.append('raw/runtime input path: ' + r)
    if re.search(r'(^|/)(yahoo|fred).*raw', low) or ('adjusted_daily' in low and '/01_data/' in '/' + low):
        FAIL.append('raw-like market-data artifact: ' + r)

# Required current release files.
required = [
    'README.md',
    'RELEASE_CONTROL_v1.1.4.md',
    'RELEASE_NOTES_v1.1.4.md',
    'STATIC_VALIDATION_RECORD_v1.1.4.txt',
    'MANIFEST_SHA256_v1.1.4.csv',
    'RUN_ORDER_v1.0.1.md',
    'RIGHTS_AND_PRIVACY_GUARDRAILS.md',
    '06_Public_Metadata/PUBLICATION_TARGET_v1.1.4.csv',
    '05_Practical_Paper/EXHIBIT_DATA_POINTERS_v1.1.6.csv',
    '05_Practical_Paper/03_Figures/EXACT_FIGURE_RENDER_MANIFEST_v1.1.6.csv',
    '03_Data_and_Code/02_Code/18_RENDER_PUBLICATION_EXHIBITS_v1_1_6.py',
    '03_Data_and_Code/03_Validation/Release_Clean_Run/SSRN_v1.34_FINAL_PUBLIC_RELEASE_BINDING_v1.1.4.md',
]
for r in required:
    if not (ROOT / r).exists():
        FAIL.append('missing required release file: ' + r)

# Exact paper binding metadata.
pt = ROOT / '06_Public_Metadata/PUBLICATION_TARGET_v1.1.4.csv'
if pt.exists():
    with pt.open(encoding='utf-8-sig', newline='') as f:
        md = {row['field']: row['value'] for row in csv.DictReader(f)}
    expected = {
        'paper_filename': 'ADAA_SSRN_Working_Paper_v1.34_FINAL_PUBLIC.pdf',
        'paper_pdf_sha256': 'eb50bd50eb6e159c76e77444d716ef477f9daec05a881606e154b3e3317ce90a',
        'paper_pages': '26',
        'paper_status': 'SSRN_v1.34_FINAL_PUBLIC_LIVE_VERIFIED',
        'ssrn_abstract_id': '7251518',
        'public_replication_predecessor': 'v1.1.2_IMMUTABLE',
        'science_change_from_v1.1.2': 'NO',
        'exact_renderer': '18_RENDER_PUBLICATION_EXHIBITS_v1_1_6.py',
        'exact_figure_manifest': 'EXACT_FIGURE_RENDER_MANIFEST_v1.1.6.csv',
        'exhibit_pointer_map': 'EXHIBIT_DATA_POINTERS_v1.1.6.csv',
    }
    for k, v in expected.items():
        if md.get(k) != v:
            FAIL.append('publication target mismatch {}={!r}'.format(k, md.get(k)))

# Exact exhibit checks.
figdir = ROOT / '05_Practical_Paper/03_Figures'
fig_manifest = figdir / 'EXACT_FIGURE_RENDER_MANIFEST_v1.1.6.csv'
expected_labels = [
    'Figure 1', 'Figure 2', 'Figure 3', 'Figure 4', 'Figure 5', 'Figure 6',
    'Figure 7', 'Figure 8', 'Appendix Figure Z1', 'Appendix Figure Z2',
    'Appendix FX Figure 1', 'Appendix FX Figure 2'
]
if fig_manifest.exists():
    with fig_manifest.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 12:
        FAIL.append('exact figure manifest row count: {}'.format(len(rows)))
    labels = [row.get('exhibit') for row in rows]
    if labels != expected_labels:
        FAIL.append('unexpected current exhibit labels/order')
    for row in rows:
        for field, hfield in (('publication_png', 'png_sha256'), ('publication_svg', 'svg_sha256'), ('source_data', 'source_sha256')):
            name = row.get(field, '')
            p = figdir / name
            if not p.exists():
                FAIL.append('exact exhibit missing: ' + name)
                continue
            if sha256(p) != row.get(hfield):
                FAIL.append('exact exhibit hash mismatch: ' + name)
    active_png = {row['publication_png'] for row in rows}
    active_svg = {row['publication_svg'] for row in rows}
    current_png = {p.name for p in figdir.glob('*PAPER_v1.34_EXACT.png')}
    current_svg = {p.name for p in figdir.glob('*PAPER_v1.34_EXACT.svg')}
    if current_png != active_png:
        FAIL.append('active v1.34 PNG set mismatch')
    if current_svg != active_svg:
        FAIL.append('active v1.34 SVG set mismatch')

# Preserve the frozen 40-check table reconciliation.
table_check = ROOT / '03_Data_and_Code/03_Validation/Release_Clean_Run/SSRN_v1.24_TABLE_RECONCILIATION_v1.1.csv'
if table_check.exists():
    with table_check.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 40:
        FAIL.append('table reconciliation row count: {}'.format(len(rows)))
    for row in rows:
        if row.get('status') != 'PASS':
            FAIL.append('table reconciliation failure')

# Public code-hygiene and privacy-surface checks on the exact distributed tree.
ai_terms = [
    'chat' + 'gpt', 'open' + 'ai', 'clau' + 'de', 'gem' + 'ini', 'co' + 'pilot',
    'generated' + ' by ' + 'ai', 'as an ' + 'ai', 'assis' + 'tant-generated', 'ai' + '-generated'
]
unfinished_terms = ['TO' + 'DO', 'FIX' + 'ME']
local_patterns = [
    re.compile(r'[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s]+', re.I),
    re.compile(r'/(?:Users|home)/[^/\s]+/', re.I),
    re.compile(re.escape('/' + 'mnt' + '/' + 'data') + r'(?:/|\b)', re.I),
]
zero_width = {chr(0x200B), chr(0x200C), chr(0x200D), chr(0x2060), chr(0xFEFF)}
emoji_ranges = [(0x1F000, 0x1FAFF), (0x2600, 0x26FF), (0x2700, 0x27BF)]

for p in files:
    if p.suffix.lower() not in TEXT_EXT:
        continue
    txt = read_text(p)
    if txt is None:
        continue
    r = rel(p)
    low = txt.lower()
    if any(term in low for term in ai_terms):
        FAIL.append('assistant/provenance phrase: ' + r)
    if any(re.search(r'\b' + re.escape(term) + r'\b', txt, flags=re.I) for term in unfinished_terms):
        FAIL.append('unfinished marker: ' + r)
    if any(pattern.search(txt) for pattern in local_patterns):
        FAIL.append('concrete local absolute path: ' + r)
    if any(ch in txt for ch in zero_width):
        FAIL.append('zero-width/invisible unicode: ' + r)
    for ch in txt:
        cat = unicodedata.category(ch)
        if cat in {'Cc', 'Cf'} and ch not in {'\n', '\r', '\t'}:
            FAIL.append('suspicious control character U+{:04X}: {}'.format(ord(ch), r))
            break
    if p.suffix.lower() in CODE_EXT:
        for ch in txt:
            cp = ord(ch)
            if any(lo <= cp <= hi for lo, hi in emoji_ranges):
                FAIL.append('decorative emoji/dingbat in code: ' + r)
                break

# Root release-manifest coverage and integrity. Manifest excludes itself to avoid a hash cycle.
manifest = ROOT / 'MANIFEST_SHA256_v1.1.4.csv'
if manifest.exists():
    with manifest.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    listed = [row['path'] for row in rows]
    if len(listed) != len(set(listed)):
        FAIL.append('duplicate path in release manifest')
    expected_paths = sorted(rel(p) for p in files if p != manifest)
    if sorted(listed) != expected_paths:
        missing = sorted(set(expected_paths) - set(listed))
        extra = sorted(set(listed) - set(expected_paths))
        if missing:
            FAIL.append('manifest coverage missing: ' + ', '.join(missing[:20]))
        if extra:
            FAIL.append('manifest coverage extra: ' + ', '.join(extra[:20]))
    for row in rows:
        p = ROOT / row['path']
        if not p.exists():
            FAIL.append('manifest payload missing: ' + row['path'])
            continue
        if sha256(p) != row['sha256']:
            FAIL.append('manifest hash mismatch: ' + row['path'])
        if str(p.stat().st_size) != row['bytes']:
            FAIL.append('manifest byte-size mismatch: ' + row['path'])

print('PUBLIC_PACKAGE_V1_1_4_VALIDATION:', 'PASS' if not FAIL else 'FAIL')
print('files={}'.format(len(files)))
print('failures={}'.format(len(FAIL)))
print('warnings={}'.format(len(WARN)))
for item in WARN:
    print('WARN:', item)
for item in FAIL:
    print('FAIL:', item)
sys.exit(1 if FAIL else 0)
