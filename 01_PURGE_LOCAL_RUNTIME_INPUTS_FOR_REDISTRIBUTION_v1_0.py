from pathlib import Path
import argparse, shutil

parser=argparse.ArgumentParser(description='Remove locally generated raw/runtime inputs before redistributing a completed ADAA clean-run tree.')
parser.add_argument('--confirm', action='store_true', help='required to perform deletion')
args=parser.parse_args()
root=Path(__file__).resolve().parent
if not args.confirm:
    raise SystemExit('DRY STOP: no files deleted. Re-run with --confirm only AFTER the full reproduction is complete.')

targets=[
    root/'03_Data_and_Code/01_Data/raw_freeze_v0_8',
    root/'03_Data_and_Code/01_Data/raw_freeze_parent_v0_14',
    root/'03_Data_and_Code/01_Data/raw_freeze_strategy_zoo_v0_29',
]
for p in targets:
    if p.exists():
        shutil.rmtree(p)
        print(f'PURGED: {p.relative_to(root)}')
for p in sorted(root.rglob('__pycache__'), reverse=True):
    if p.is_dir(): shutil.rmtree(p); print(f'PURGED: {p.relative_to(root)}')
for p in root.rglob('*.pyc'):
    try: p.unlink(); print(f'PURGED: {p.relative_to(root)}')
    except FileNotFoundError: pass
print('PURGE_COMPLETE. Re-run 00_VALIDATE_PUBLIC_PACKAGE_v1_0.py before redistributing.')
