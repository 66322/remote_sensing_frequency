"""Fixed paired-mask summaries; no scientific gate dispatches new training."""
import argparse
from pathlib import Path
import numpy as np
from phase15_common import *
from phase15_numeric import bootstrap, exact_signflip
from structured_v0_metrics import metric


def score(cm,classes=(0,1,2,3,4)):
    x=metric(cm,classes)
    return None if x is None else 100*x


def diff(a,b,classes=(0,1,2,3,4)):
    x,y=score(a,classes),score(b,classes)
    return None if x is None or y is None else x-y


def numbers(values):
    return [np.nan if x is None else x for x in values]


def summary(values,permutation=False):
    result=bootstrap(numbers(values))
    result['per_realization']=values
    if permutation:
        result['secondary_exact_signflip_p']=exact_signflip(numbers(values))
        result['signflip_assumption']='paired differences sign-exchangeable/symmetric; not independent pixels'
    return result


def pool(rows,field):
    return sum((np.asarray(x[field],np.int64) for x in rows),np.zeros((6,6),np.int64))


def class_stats(matrix):
    a=np.asarray(matrix,np.int64)
    tp=a.diagonal();support=a.sum(1);union=a.sum(0)+support-tp
    return dict(support=support.tolist(),TP=tp.tolist(),FP=(a.sum(0)-tp).tolist(),FN=(support-tp).tolist(),
        IoU=[float(tp[i]/union[i]) if union[i] else None for i in range(6)],
        recall=[float(tp[i]/support[i]) if support[i] else None for i in range(6)])


def summarize(base):
    p=validate(base)
    for j in p['jobs']:
        accept_job(base,j)
    for phase,expected in (('E',120),('D',160)):
        done=read(base/'analysis'/phase/'complete.json')
        if done['binding']!=binding(base) or len(done['records'])!=expected:
            raise RuntimeError('CPU analysis incomplete')
        for n,h in done['records'].items():
            if sha(base/'analysis'/phase/(n+'.json'))!=h:
                raise RuntimeError('CPU evidence changed')
    cases={}
    for j in p['jobs']:
        for c in j['cases']:
            cases[case_id(c)]=read(base/'cases'/(case_id(c)+'.json'))
    def cells(model,ds,i,family,ratio=25,region='missing',tiles=TILES):
        return [cases[case_id(case(model,t,ds,i,family,ratio))]['scopes']['noboundary'][region] for t in tiles]
    def damage(model,ds,i,family,ratio=25,region='missing',tiles=TILES,classes=(0,1,2,3,4)):
        rows=cells(model,ds,i,family,ratio,region,tiles)
        return diff(pool(rows,'clean_cm'),pool(rows,'missing_cm'),classes)
    A,C={},{}
    for model in ('S1','R16'):
        A[model]={};C[model]={}
        for ds in DSM:
            effects={}
            for tiles in (TILES,(TILES[0],),(TILES[1],)):
                scope='pooled' if len(tiles)==2 else tiles[0]
                D={f:[damage(model,ds,i,f,tiles=tiles) for i in range(1,21)] for f in FAMILIES}
                pe=[None if x is None or y is None else x-y for x,y in zip(D['gradient'],D['matched'])]
                total=[None if x is None or y is None else x-y for x,y in zip(D['gradient'],D['random'])]
                effects[scope]=dict(damage={f:summary(v) for f,v in D.items()},PE=summary(pe,permutation=(len(tiles)==2)),PE_total=summary(total))
            A[model][ds]=effects
            C[model][ds]={}
            for f in FAMILIES:
                per_class={str(k):summary([damage(model,ds,i,f,classes=(k,)) for i in range(1,21)]) for k in range(5)}
                contrast=[]
                total_intact=[]
                for i in range(1,21):
                    a=damage(model,ds,i,f,classes=(4,));b=damage(model,ds,i,f,classes=(1,))
                    contrast.append(None if a is None or b is None else a-b)
                    rows=cells(model,ds,i,f)
                    total_intact.append(diff(pool(rows,'intact_clean_cm'),pool(rows,'missing_cm')))
                C[model][ds][f]=dict(damage_by_class=per_class,primary_Car_minus_Building=summary(contrast),total_vs_intact_clean=summary(total_intact))
        for ds in DSM[1:]:
            a=A[model][ds]['pooled']['PE']['per_realization']
            b=A[model]['intact']['pooled']['PE']['per_realization']
            A[model][ds]['delta_PE_vs_intact']=summary([None if x is None or y is None else x-y for x,y in zip(a,b)],permutation=True)
    B={}
    for ratio in (5,10,25):
        result={}
        for region in ('all','missing','core5'):
            ds=[damage('S1','intact',i,'pixel',ratio,region) for i in range(1,21)]
            density=[]
            for i in range(1,21):
                rows=cells('S1','intact',i,'pixel',ratio,region)
                n=sum(x['transitions']['valid'] for x in rows)
                net=sum(x['transitions']['harmed']-x['transitions']['rescued'] for x in rows)
                density.append(100*net/n if n else None)
            result[region]=dict(damage=summary(ds),net_error_density_pp=summary(density))
        result.update(PE=None,PE_status='NOT_DEFINED_PIXEL_ONLY',dose_normalized_mIoU_effect_not_per_pixel=summary([
            None if x is None else x/(ratio/100) for x in result['all']['damage']['per_realization']]))
        B[str(ratio)]=result
    E={}
    all_profiles={(t,i,f):read(base/'analysis/E'/f'{t}_{i:02d}_{f}.json')['result'] for t in TILES for i in range(1,21) for f in FAMILIES[1:]}
    def eci_counts(tile_set):
        result=[]
        for i in range(1,21):
            counts=np.zeros((4,3),np.int64)
            for t in tile_set:
                for f in FAMILIES[1:]:
                    for b in range(4):
                        r=all_profiles[t,i,f][str(b)]
                        counts[b]+=np.array([r['valid'],r['harmed'],r['rescued']])
            result.append(counts)
        return np.array(result)
    def ratio_stat(counts,flip=False):
        sums=counts.sum(0)
        edge,inside=sums[0],sums[2:].sum(0)
        num=edge[1] if flip else edge[1]-edge[2]
        den=inside[1] if flip else inside[1]-inside[2]
        if not edge[0] or not inside[0] or den<=0:
            return None
        return float((num/edge[0])/(den/inside[0]))
    for tiles in (TILES,(TILES[0],),(TILES[1],)):
        name='pooled' if len(tiles)==2 else tiles[0]
        a=eci_counts(tiles)
        eci=ratio_stat(a)
        rng=np.random.Generator(np.random.PCG64(61011))
        boot=[ratio_stat(a[idx]) for idx in rng.integers(0,20,size=(5000,20))]
        ci=None if any(x is None for x in boot) else np.quantile(boot,[.025,.975]).tolist()
        sums=a.sum(0)
        densities=[float(100*(b[1]-b[2])/b[0]) if b[0] else None for b in sums]
        E[name]=dict(ECI=eci,CI95=ci,new_error_ECI=ratio_stat(a,True),distance_bin_totals=sums.tolist(),
            net_damage_density_pp=densities,status='INCONCLUSIVE_DENOMINATOR' if eci is None or ci is None else 'VALID')
    r=E['pooled'];tile_positive=all(E[t]['ECI'] is not None and E[t]['ECI']>1 for t in TILES)
    if r['ECI'] is not None and r['CI95'] is not None and r['ECI']>=1.5 and r['CI95'][0]>1 and tile_positive:
        E['profile_verdict']='EDGE_DOMINANT'
    elif r['ECI'] is not None and r['CI95'] is not None and .8<=r['ECI']<=1.25 and r['CI95'][1]<1.5:
        # Conservative uniform classification: stable positive edge trend cannot coexist.
        stable=any(E[t]['CI95'] is not None and E[t]['CI95'][0]>1 for t in TILES)
        E['profile_verdict']='MIXED_OR_INCONCLUSIVE' if stable else 'APPROXIMATELY_UNIFORM'
    else:
        E['profile_verdict']='MIXED_OR_INCONCLUSIVE'
    D={}
    drows={(t,i,f):read(base/'analysis/D'/f'{t}_{i:02d}_{f}.json')['result'] for t in TILES for i in range(1,21) for f in FAMILIES}
    system_names=list(drows[TILES[0],1,'pixel']['systems'])
    for family in FAMILIES:
        D[family]={}
        for tiles in (TILES,(TILES[0],),(TILES[1],)):
            name='pooled' if len(tiles)==2 else tiles[0]
            data={}
            for region in ('valid','mask','healthy'):
                values={n:[] for n in system_names}
                per_class={n:[] for n in system_names}
                for i in range(1,21):
                    for n in system_names:
                        cm=pool([drows[t,i,family]['systems'][n][region] for t in tiles],'missing_cm')
                        values[n].append(score(cm));per_class[n].append(class_stats(cm))
                gains={n:summary([None if x is None or y is None else x-y for x,y in zip(values[n],values['S1'])]) for n in system_names}
                best=[max(v) if all(x is not None for x in v) else None for v in zip(*(values[n] for n in EXPERTS))]
                head=[None if x is None or y is None else x-y for x,y in zip(values['oracle_pixel'],best)]
                data[region]=dict(scores={n:summary(v) for n,v in values.items()},gain_vs_S1=gains,
                    gain_vs_best_expert_per_case=summary(head),per_realization_class_metrics=per_class)
            D[family][name]=data
    H=[]
    for i in range(20):
        xs=[D[f]['pooled']['valid']['gain_vs_S1']['oracle_pixel']['per_realization'][i] for f in FAMILIES]
        H.append(sum(xs)/4 if all(x is not None for x in xs) else None)
    head=summary(H)
    expert_family_means={n:np.mean([D[f]['pooled']['valid']['scores'][n]['mean'] for f in FAMILIES])
                         if all(D[f]['pooled']['valid']['scores'][n]['mean'] is not None for f in FAMILIES) else None for n in EXPERTS}
    best_fixed=max((n for n in EXPERTS if expert_family_means[n] is not None),key=lambda n:expert_family_means[n],default=None)
    h_fixed=[]
    for i in range(20):
        a=[D[f]['pooled']['valid']['scores']['oracle_pixel']['per_realization'][i] for f in FAMILIES]
        b=[D[f]['pooled']['valid']['scores'][best_fixed]['per_realization'][i] for f in FAMILIES] if best_fixed else [None]*4
        h_fixed.append(sum(x-y for x,y in zip(a,b))/4 if all(x is not None for x in a+b) else None)
    mean=head['mean']
    verdict='INCONCLUSIVE' if mean is None else 'CONDITIONAL_ENTRY_REQUIRES_OBSERVABLE_REVIEW' if mean>=6 else 'GRAY_ZONE' if mean>=2 else 'PROVISIONAL_CLOSE_LEGACY_DSM_LIMITED'
    aggregate={}
    for (tile,i,family),row in drows.items():
        for feature,regions in row['conditional_counts'].items():
            for region,bins in regions.items():
                target=aggregate.setdefault(tile,{}).setdefault(feature,{}).setdefault(region,{})
                for bin_id,v in bins.items():
                    out=target.setdefault(bin_id,dict(valid=0,correct=[0]*5))
                    out['valid']+=v['valid']
                    out['correct']=[x+y for x,y in zip(out['correct'],v['correct'])]
    # Descriptive conditional counts; they do not automatically pass a learnability gate.
    result=dict(protocol=p['protocol'],binding=binding(base),A=A,B=B,C=C,D=D,E=E,
        routing=dict(primary_support='complete NB fg5; 4-family mean of paired-realization gains',H_NB=head,
            best_fixed_expert_descriptive=best_fixed,best_fixed_expert_scores={n:float(v) if v is not None else None for n,v in expert_family_means.items()},
            oracle_gain_vs_best_fixed_expert=summary(h_fixed),
            verdict=verdict,learnability='REQUIRES_INDEPENDENT_HUMAN_REVIEW_NOT_AUTOMATIC',conditional_counts=aggregate,
            DSM_compatibility='LEGACY_TRAIN16_SEED42',new_training_dispatched=False),
        optimizer_updates=0,test6_loaded=False,held4_loaded=False,independent_final_loaded=False,
        evidence_grade='repeatedly used Potsdam Val2; 20 mask realizations, not 20 sites or training seeds',
        next='NO_AUTOMATIC_TRAINING; upload light originals and review all five diagnostics',observed_at=now())
    write(base/'summary.json',result)
    return result


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True)
    summarize(a.parse_args().directory.resolve())
