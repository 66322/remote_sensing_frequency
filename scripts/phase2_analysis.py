"""Integer CPU evidence, preregistered C/L/static gates and no post-hoc bin search."""
import argparse
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.ndimage import maximum_filter
from phase2_common import *
from structured_v0_metrics import cm,metric,transitions

def analyze_case(base,out):
    base=Path(base);out=Path(out);row=read(out/'arrays.json');c=row['case']
    arrays={n:compact_load(r) for n,r in row['arrays'].items()}
    inputs=read(base/'input_manifest.json')['arrays'][c['tile']]
    mask=arrays['mask'];valid=arrays['rm']|arrays['dm']
    healthy=~maximum_filter(mask,size=17,mode='constant',cval=0).astype(bool)
    regions=dict(all=valid,missing=mask&valid,healthy=healthy&valid,observed=(~mask)&valid)
    r,d=arrays['rgb'],arrays['dsm'];pred=arrays['pred'];results={};preference={}
    for scope in ('full','noboundary'):
        gt=np.load(inputs[scope+'_gt']['path'],mmap_mode='r');oracle=np.where(r==gt,r,np.where(d==gt,d,r)).astype(np.uint8)
        reverse=np.where(d==gt,d,np.where(r==gt,r,d)).astype(np.uint8)
        # Report availability-constrained oracle separately; never call illegal experts deployable.
        constrained=np.where(arrays['rm']&arrays['dm'],oracle,np.where(arrays['rm'],r,d)).astype(np.uint8)
        systems=dict(rgb=r,dsm=d,candidate=pred,oracle=oracle,oracle_dsm_priority=reverse,availability_oracle=constrained)
        results[scope]={name:{region:cm(gt,z,keep).tolist() for region,keep in regions.items()} for name,z in systems.items()}
        results[scope]['per_class_counts']={name:{region:dict(true=np.asarray(m,np.int64).sum(1).tolist(),
            predicted=np.asarray(m,np.int64).sum(0).tolist(),correct=np.asarray(m,np.int64).diagonal().tolist())
            for region,m in regs.items()} for name,regs in results[scope].items()}
        results[scope]['transitions']={region:transitions(gt,r,pred,keep) for region,keep in regions.items()}
        if scope=='noboundary' and c['panel']=='P-U':
            disagreement=(r!=d)&(gt<5)&valid
            for tail,keep in (('rgb',arrays['entropy_bin']==0),('dsm',arrays['entropy_bin']==2)):
                keep=keep&disagreement
                packed=np.packbits(keep,bitorder='little');ar=array_save(out/('tail_'+tail+'.npy'),packed)
                preference[tail]=dict(valid=int(keep.sum()),rgb_correct=int((keep&(r==gt)).sum()),
                    dsm_correct=int((keep&(d==gt)).sum()),both_wrong=int((keep&(r!=gt)&(d!=gt)).sum()),coordinates=ar)
    result=dict(case=c,system=row['system'],age=row['age'],binding=binding(base),fallback_exact=row['fallback_exact'],
                matrices=results,preference=preference,observed_at=now())
    write(out/'counts.json',result);complete(base,out,dict(case=c,system=row['system'],age=row['age']))
    return str(out/'counts.json')

def rows(base,system='average',age=16000):
    folder=Path(base)/'evaluation'/('%s_%d'%(system,age));values=[]
    for f in sorted(folder.glob('*/counts.json')):
        r=read(f)
        if r['binding']!=binding(base):raise RuntimeError('counts source differs')
        done=read(f.parent/'complete.json')
        if done['files'].get('counts.json')!=sha(f):raise RuntimeError('counts receipt differs')
        values.append(r)
    if not values:raise RuntimeError('empty evaluation')
    return values

def scores(values,system,region='all',panel='P-U',direction=None,tile=None,scope='noboundary'):
    pooled=defaultdict(lambda:np.zeros((6,6),np.int64))
    for row in values:
        c=row['case']
        if c['panel']!=panel or (direction and c['direction']!=direction) or (tile and c['tile']!=tile):continue
        ident=(c['direction'],c['family'],c['realization'],c['ratio'],c['damage'])
        pooled[ident]+=np.asarray(row['matrices'][scope][system][region],np.int64)
    metrics=[metric(v) for v in pooled.values()];defined=[100*x for x in metrics if x is not None]
    if not defined:return None
    return float(np.mean(defined))

def delta(a,b):return None if a is None or b is None else a-b

def gates(base):
    values=rows(base);C={};h={}
    for direction in ('rgb','dsm'):
        keyd={}
        for tile in (None,*VAL):
            best=max(scores(values,'rgb',direction=direction,tile=tile),scores(values,'dsm',direction=direction,tile=tile))
            head=scores(values,'oracle',direction=direction,tile=tile)-best
            keyd[tile or 'pooled']=head
        h[direction]=keyd;C[direction]=keyd['pooled']>=2 and all(keyd[t]>0 for t in VAL)
    # Union of distinct coordinates; mask pixels are not independent observations.
    sums=defaultdict(lambda:dict(valid=0,rgb_correct=0,dsm_correct=0,both_wrong=0))
    unions={};id_support=defaultdict(int)
    for row in values:
        c=row['case']
        if c['panel']!='P-U':continue
        for tail,z in row['preference'].items():
            ident=(c['tile'],tail);where=np.load(z['coordinates']['path'],mmap_mode='r')
            if ident not in unions:unions[ident]=np.zeros_like(where)
            np.bitwise_or(unions[ident],where,out=unions[ident])
            id_support[(c['tile'],c['direction'],tail,c['realization'])]+=z['valid']
            for ident2 in (ident,(c['tile'],c['direction'],tail)):
                for n in sums[ident2]:sums[ident2][n]+=z[n]
    tails={};support_ok=True;win_ok=True
    for tile in VAL:
        for tail in ('rgb','dsm'):
            z=sums[(tile,tail)];unique=int(np.unpackbits(unions[(tile,tail)]).sum())
            win=z[tail+'_correct']/z['valid'] if z['valid'] else None
            coverage={dr:sum(id_support[(tile,dr,tail,i)]>=256 for i in range(1,21)) for dr in ('rgb','dsm')}
            support_ok &= unique>=10000 and all(n>=10 for n in coverage.values())
            win_ok &= win is not None and win>=.7
            tails[tile+'_'+tail]=dict(**z,distinct_coordinates=unique,selected_expert_win=win,mask_id_support=coverage)
    rule={};rule_ok=True
    for dr in ('rgb','dsm'):
        for tile in (None,*VAL):
            names=VAL if tile is None else [tile]
            z=[sums[(t,dr,tail)] for t in names for tail in ('rgb','dsm')]
            n=sum(x['valid'] for x in z)
            correct=sum(sums[(t,dr,'rgb')]['rgb_correct']+sums[(t,dr,'dsm')]['dsm_correct'] for t in names)
            best=max(sum(x['rgb_correct'] for x in z),sum(x['dsm_correct'] for x in z))
            gain=100*(correct-best)/n if n else None
            rule[dr+'_'+(tile or 'pooled')]=gain
            rule_ok &= gain is not None and gain>=(2 if tile is None else np.nextafter(0.,1.))
    L=support_ok and win_ok and rule_ok
    result=dict(C=all(C.values()),C_by_direction=C,H_initial=h,L=bool(L),L_support_passed=bool(support_ok),
                L_tail_wins=tails,L_rule_gain=rule,status='SUPPORTED' if all(C.values()) and L else 'STOP_OR_INCONCLUSIVE',
                scope='fixed Val2 masks, not independent sites/seeds',observed_at=now())
    write(Path(base)/'analysis/gates_C_L.json',result);return result

def static_gate(base):
    gate=read(Path(base)/'analysis/gates_C_L.json');v=rows(base);a=rows(base,'B0');b=rows(base,'B2')
    names={'B0':a,'B2':b};chosen=max(names,key=lambda n:scores(names[n],'candidate'))
    static=names[chosen];residual={};clean_base=scores(v,'candidate',panel='clean')
    retention=scores(static,'candidate',panel='clean')-clean_base
    for dr in ('rgb','dsm'):residual[dr]=scores(v,'oracle',direction=dr)-scores(static,'candidate',direction=dr)
    identities=all(r['fallback_exact'] for r in static)
    allowed=gate['C'] and gate['L'] and all(h>=1 for h in residual.values()) and retention>=-.3 and identities
    result=dict(allow_dynamic=bool(allowed),static_reference=chosen,residual_diagnostic_gap=residual,
        clean_retention_pp=retention,exact_fallback=identities,C=gate['C'],L=gate['L'],observed_at=now())
    write(Path(base)/'analysis/static_gate.json',result);return result

def paired_ci(reference,candidate,region='all'):
    groups=[]
    for i in range(1,21):
        a=scores([r for r in reference if r['case']['realization']==i],'candidate',region=region)
        b=scores([r for r in candidate if r['case']['realization']==i],'candidate',region=region)
        if a is not None and b is not None:groups.append(b-a)
    if len(groups)!=20:return dict(defined_pairs=len(groups),mean=None,ci95=None)
    x=np.array(groups);rng=np.random.Generator(np.random.PCG64(20261013))
    samples=x[rng.integers(0,20,(5000,20))].mean(1)
    return dict(defined_pairs=20,mean=float(x.mean()),ci95=np.quantile(samples,[.025,.975]).tolist(),
                interpretation='paired mask perturbations conditional on two reused Val2 tiles')

def summarize(base):
    systems=['average','B0','B2']
    if (Path(base)/'jobs/B1/complete.json').exists():systems+=['B1','B3']
    summary={};values={n:rows(base,n) for n in systems}
    for n,v in values.items():
        summary[n]={panel:{region:scores(v,'candidate',region=region,panel=panel) for region in ('all','missing','healthy','observed')}
                    for panel in ('clean','P-M','P-U','dose','ordinary')}
    accepted=None;comparison={}
    if 'B1' in values:
        reference=read(Path(base)/'analysis/static_gate.json')['static_reference'];r=values[reference];v=values['B1'];control=values['B3']
        pooled={n:scores(v,'candidate')-scores(values[n],'candidate') for n in ('B0','B2')}
        directions={n:{dr:scores(v,'candidate',direction=dr)-scores(values[n],'candidate',direction=dr) for dr in ('rgb','dsm')} for n in ('B0','B2')}
        tile={n:{dr:{t:scores(v,'candidate',direction=dr,tile=t)-scores(values[n],'candidate',direction=dr,tile=t) for t in VAL} for dr in ('rgb','dsm')} for n in ('B0','B2')}
        clean=scores(v,'candidate',panel='clean')-scores(r,'candidate',panel='clean')
        healthy=delta(scores(v,'candidate',region='healthy'),scores(r,'candidate',region='healthy'))
        by_condition=[]
        for dr in ('rgb','dsm'):
            for fam in FAMILIES:
                for damage in ('zero','down4'):
                    filt=lambda arr:[x for x in arr if x['case']['direction']==dr and x['case']['family']==fam and x['case']['damage']==damage]
                    by_condition.append(scores(filt(v),'candidate')-scores(filt(r),'candidate'))
        spatial=scores(v,'candidate')-scores(control,'candidate')
        spatial_tiles={t:scores(v,'candidate',tile=t)-scores(control,'candidate',tile=t) for t in VAL}
        accepted=all(z>=.5 for z in pooled.values()) and all(z>=.3 for q in directions.values() for z in q.values()) and all(z>0 for q in tile.values() for zt in q.values() for z in zt.values()) and clean>=-.3 and healthy is not None and healthy>=-.3 and min(by_condition)>=-.5 and all(x['fallback_exact'] for x in v)
        comparison=dict(main_gains=pooled,direction_gains=directions,tile_gains=tile,clean=clean,healthy=healthy,worst_condition=min(by_condition),
            DSM_statistics_mechanism=spatial>=.3 and all(z>0 for z in spatial_tiles.values()),B1_vs_B3=spatial,B1_vs_B3_tile=spatial_tiles,
            paired_CI={n:paired_ci(values[n],v) for n in ('B0','B2')})
    matched={}
    for age in (8000,16000):
        vv=rows(base,'average',age)
        matched[str(age)]={panel:{n:scores(vv,n,panel=panel) for n in ('rgb','dsm','oracle','availability_oracle','candidate')}
                          for panel in (('clean','P-M') if age==8000 else ('clean','P-M','P-U','dose','ordinary'))}
    write(Path(base)/'summary.json',dict(results=summary,matched_expert_trajectories=matched,dynamic_accepted=bool(accepted) if accepted is not None else None,comparison=comparison,
        gate_C_L=read(Path(base)/'analysis/gates_C_L.json'),static_gate=read(Path(base)/'analysis/static_gate.json'),
        no_automatic_followup=True,new_training_seeds=False,test6_loaded=False,held4_loaded=False,observed_at=now()))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--action',choices=['gates','static','summary'],required=True)
    a=p.parse_args();verify(a.directory);{'gates':gates,'static':static_gate,'summary':summarize}[a.action](a.directory)
