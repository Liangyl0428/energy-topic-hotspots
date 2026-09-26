"""Export aggregate replay inputs/reports, never raw bodies, models or embeddings."""
import hashlib
import json
import shutil
from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parents[2]


def export():
    source, dest = REPO/'outputs/nmf500_v021', REPO/'assets/nmf500'
    dest.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.iterdir()):
        if path.is_file() and path.suffix in {'.csv','.json','.md','.xlsx'}:
            shutil.copy2(path,dest/path.name)
    cols = ['doc_id','source','date','topic_1_id','topic_1_cosine','top1_top2_margin','needs_review','similarity_filter_passed']
    t = pd.read_parquet(source/'patent_policy_assignments.parquet',columns=cols)
    t['category_id'] = t.topic_1_id.map(lambda i: f'N{i+1:04d}')
    t.to_csv(dest/'transfer_scores.csv',index=False,encoding='utf-8-sig')
    if (source/'experiments').exists():
        shutil.copytree(source/'experiments',dest/'experiments',dirs_exist_ok=True)
    manifest = {str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
    (dest/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Exported',len(manifest),'files to',dest)


if __name__ == '__main__':
    export()
