from pathlib import Path
import sys, os, json, hashlib, re, datetime
REPOSITORY = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get('ENERGY_HOTSPOTS_UPSTREAM', REPOSITORY)).resolve()
BASE = Path(os.environ.get('ENERGY_HOTSPOTS_RUN', REPOSITORY/'work/run')).resolve()
LABELS = ROOT/'jjjj/bertopic750_flat_refined_20260925'
CORPUS = ROOT/'jjjj/bertopic500_all_sources_20260925'
PREVIOUS = ROOT/'kkkk/hotspots486_20260925'
REFINED = ROOT/'jjjj/bertopic486_hierarchical_refined_20260925'
os.environ.setdefault('OMP_NUM_THREADS','4')
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
for folder in ['data/assignments','results','evidence','review','logs','figures','audit','reliability']:
    (BASE/folder).mkdir(parents=True,exist_ok=True)
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(path): return json.loads(Path(path).read_text())
def dump(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n');tmp.replace(path)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()
def save(frame,name):frame.to_csv(BASE/'results'/name,index=False,encoding='utf-8-sig')
def sqlstr(value):return "'"+str(value).replace("'","''")+"'"
