from common import *
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
font=Path('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc')
if font.exists():
 font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams.update({'axes.unicode_minus':False,'font.size':10})
g=pd.read_csv(BASE/'reliability/gate_and_data_sensitivity.csv')
fig,axs=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
for ax,fam,sc,labels in [(axs[0],'core',['core_window_1y','baseline','core_window_5y'],['1年','3年（主窗）','5年']),(axs[1],'emerging',['baseline_window_2y','baseline','baseline_window_4y'],['前2年','前3年（主基线）','前4年'])]:
 d=g[g.family.eq(fam)].set_index('scenario').loc[sc];ax.bar(labels,d.retained,color='#277f98');ax.set_title(('核心' if fam=='core' else '新兴')+'：改变时间长度后的本版主榜保留数');ax.set_ylim(0,max(d.baseline_count)*1.18)
 for i,(_,r) in enumerate(d.iterrows()):ax.text(i,r.retained+.2,f'{r.retained}/{r.baseline_count}',ha='center')
 ax.set_ylabel('保留方向数；语义判断固定')
for ext in ['png','pdf']:fig.savefig(BASE/'figures'/('multiyear_windows.'+ext),dpi=180)
plt.close(fig)
fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained');sc=['quality','geometry','dedup','exclude_needs_review','supported_only'];x=np.arange(5)
for fam,offset,label in [('core',-.18,'核心'),('emerging',.18,'新兴')]:
 d=g[g.family.eq(fam)].set_index('scenario').loc[sc];ax.bar(x+offset,d.retention,.34,label=label)
 for i,(_,r) in enumerate(d.iterrows()):ax.text(i+offset,r.retention+.02,f'{r.retained}/{r.baseline_count}',ha='center',fontsize=8)
ax.set_xticks(x,['文本/日期质量','原几何','题名年度去重','排除待复核','仅规则支持']);ax.set_ylim(0,1.15);ax.set_ylabel('本版主榜保留比例');ax.set_title('多年口径的数据压力测试（非准确率）');ax.legend()
for ext in ['png','pdf']:fig.savefig(BASE/'figures'/('multiyear_data_stress.'+ext),dpi=180)
plt.close(fig)
