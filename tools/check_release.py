"""Validate the portable 750-topic release and checksummed allowlisted files."""
from pathlib import Path
import ast
import csv
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','.venv','work','outputs','data','models','dist','build','__pycache__','.pytest_cache','.ruff_cache'}
BINARY={
 'assets/snapshot_20260925/hotspots/evidence/potential_unified_candidates.parquet',
 'assets/snapshot_20260925/hotspots/data/patent_metadata.parquet',
 'assets/snapshot_20260925/hotspots/data/potential_unified_global_dedup.parquet',
 'assets/snapshot_20260925/hotspots/750类核心新兴潜在热点分析.xlsx',
 'assets/snapshot_20260925/hotspots/750类热点消融实验与灵敏度分析.xlsx',
 'assets/nmf500/500主题核心新兴潜在热点.xlsx',
 'assets/nmf500/500主题热点审阅结果.xlsx',
}

def publishable_files():
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if rel.parts[0] in EXCLUDED or set(rel.parts)&{'__pycache__','.pytest_cache','.ruff_cache'} or any(x.endswith('.egg-info') for x in rel.parts):continue
        if p.is_file() or p.is_symlink():yield p

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def validate(check_manifest=True):
    files=list(publishable_files())
    for p in files:
        rel=p.relative_to(ROOT).as_posix()
        assert not p.is_symlink(),rel
        assert p.stat().st_size<10*1024**2,rel
        if rel in BINARY or (rel.startswith('assets/snapshot_20260925/hotspots/figures/') and p.suffix in {'.png','.pdf'}):continue
        assert p.suffix in {'.py','.csv','.json','.md','.toml','.txt','.in','.yml'} or p.name in {'.gitignore','.gitattributes'},rel
        s=p.read_text()
        assert not re.search(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}',s),rel
        assert '/pyg'+'-vepfs/' not in s,rel
        if p.suffix=='.py':ast.parse(s)
    snap=ROOT/'assets/snapshot_20260925/hotspots/results'
    with (snap/'category_catalog.csv').open(encoding='utf-8-sig') as h:topics=list(csv.DictReader(h))
    with (snap/'potential_unified_metrics.csv').open(encoding='utf-8-sig') as h:units=list(csv.DictReader(h))
    assert len(topics)==750 and len({x['category_id'] for x in topics})==750
    assert len(units)==4
    manifest_file=ROOT/'provenance/FILE_MANIFEST.json'
    if check_manifest:
        expected={x['file']:x['sha256'] for x in json.loads(manifest_file.read_text())['files']}
        actual={p.relative_to(ROOT).as_posix():digest(p) for p in files if p!=manifest_file}
        assert actual==expected,'Release manifest mismatch; rebuild after edits'
    return dict(files=len(files),bytes=sum(p.stat().st_size for p in files),topics=750,potential_units=4,checks_passed=True)

if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False,indent=2))
