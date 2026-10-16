import json
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent;S=json.loads((P/'summary.json').read_bytes())
def read(n):return json.loads((P/'decoded'/n).read_bytes())
def score(a):
    a=np.asarray(a,np.int64);u=a.sum(0)+a.sum(1)-a.diagonal()
    return 100*float((a.diagonal()[:5]/u[:5]).mean())
def check(x,y):assert np.allclose(x,y,rtol=1e-10,atol=1e-9),(x,y)
families=('pixel','random','gradient','matched');tiles=('3_11','5_10')
H=[];Hb=[];disagreement_bins={t:{} for t in tiles};fallback_core=[]
for i in range(1,21):
    gains=[];best=[]
    for f in families:
        records=[read(f'analysis/D/{t}_{i:02d}_{f}.json')['result'] for t in tiles]
        v={n:score(sum((np.array(r['systems'][n]['valid']['missing_cm'],np.int64) for r in records))) for n in records[0]['systems']}
        gains.append(v['oracle_pixel']-v['S1']);best.append(v['oracle_pixel']-v['R16'])
        for tile,r in zip(tiles,records):
            for field,regions in r['conditional_counts'].items():
                dst=disagreement_bins[tile].setdefault(field,{})
                for region,bins in regions.items():
                    d=dst.setdefault(region,{})
                    for b,z in bins.items():
                        q=d.setdefault(b,{'valid':0,'correct':[0]*5});q['valid']+=z['valid']
                        q['correct']=[a+c for a,c in zip(q['correct'],z['correct'])]
    H.append(sum(gains)/4);Hb.append(sum(best)/4)
    for t in tiles:
        rs=[read(f'cases/S1_{t}_intact_{i:02d}_pixel_{ratio}.json')['scopes']['noboundary']['core5'] for ratio in (5,10,25)]
        assert rs[0]==rs[1]==rs[2],('common M5 differs',t,i)
check(H,S['routing']['H_NB']['per_realization']);check(Hb,S['routing']['oracle_gain_vs_best_fixed_expert']['per_realization'])
assert disagreement_bins==S['routing']['conditional_counts'],'conditional aggregate differs'
for name,subset in [('pooled',tiles),('3_11',tiles[:1]),('5_10',tiles[1:])]:
    counts=[]
    for i in range(1,21):
        a=np.zeros((4,3),np.int64)
        for t in subset:
            for f in families[1:]:
                row=read(f'analysis/E/{t}_{i:02d}_{f}.json')['result']
                for k in range(4):a[k]+=np.array([row[str(k)][n] for n in ('valid','harmed','rescued')])
                case=read(f'cases/S1_{t}_intact_{i:02d}_{f}_25.json')['scopes']['noboundary']['missing']['transitions']
                for col,key in enumerate(('valid','harmed','rescued')):assert int(sum(a[k,col] for k in range(4)))>=case[key]
        counts.append(a)
    a=np.array(counts)
    def eci(q):
        x=q.sum(0);edge=x[0];inside=x[2:].sum(0)
        if not edge[0] or not inside[0] or inside[1]-inside[2]<=0:return None
        return ((edge[1]-edge[2])/edge[0])/((inside[1]-inside[2])/inside[0])
    check(a.sum(0).tolist(),S['E'][name]['distance_bin_totals']);check(eci(a),S['E'][name]['ECI'])
    rng=np.random.Generator(np.random.PCG64(61011));boot=[eci(a[idx]) for idx in rng.integers(0,20,size=(5000,20))]
    check(np.quantile(boot,[.025,.975]).tolist(),S['E'][name]['CI95'])
result=dict(status='PASS',H_NB=float(np.mean(H)),H_vs_R16=float(np.mean(Hb)),conditional_aggregation_exact=True,
    common_M5_all_40_groups_exact=True,ECI_counts_and_5000_CI_exact=True,
    inference='S1 common support invariance is consistent with frozen own-DSM fallback; legacy DSM-only is distinct',
    observable_review='R16 wins entropy/disagreement bins across both tiles; S13 preference in low DSM variance/gradient reverses by tile; simple routing learnability gate not established')
(P/'mechanism_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
