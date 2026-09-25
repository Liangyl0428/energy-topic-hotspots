import argparse,json
from pathlib import Path
from .replay import replay

def main():
 p=argparse.ArgumentParser(description='750主题多年热点评分与统一潜在证据复现')
 sub=p.add_subparsers(dest='command',required=True)
 r=sub.add_parser('replay',help='重算750主题多年指标、时间窗和潜在证据')
 r.add_argument('--output',required=True);r.add_argument('--experiments',action='store_true')
 s=sub.add_parser('score',help='文献季度计数和情景机构引用汇总 → 多年数值资格；另需语义审核')
 for k in ['taxonomy','quarters','context','output']:s.add_argument('--'+k,required=True)
 s.add_argument('--end',default='2026Q2');s.add_argument('--core-years',type=int,choices=[1,3,5],default=3);s.add_argument('--baseline-years',type=int,choices=[2,3,4],default=3)
 a=p.parse_args()
 if a.command=='replay':
  result=replay(a.output,a.experiments);print(json.dumps({k:v for k,v in result.items() if k!='details'},ensure_ascii=False,indent=2))
 else:
  import pandas as pd
  from .scoring import score
  z,_,_=score(pd.read_csv(a.taxonomy).set_index('category_id'),pd.read_csv(a.quarters),pd.read_csv(a.context).set_index('category_id'),end=a.end,core_years=a.core_years,baseline_years=a.baseline_years)
  out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
  with out.open('x') as h:z.to_csv(h)
