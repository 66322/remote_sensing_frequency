"""One fixed analysis after all mask pairs; conditional mask bootstrap, no p fishing."""
import argparse
from pathlib import Path
import numpy as np
from structured_v0_common import *
from structured_v0_metrics import difference, metric


def interval(values):
    if any(v is None for v in values):
        return dict(mean=None, ci95=None, valid_pairs=sum(v is not None for v in values))
    a = np.asarray(values, float)
    rng = np.random.Generator(np.random.PCG64(61011))
    samples = a[rng.integers(0,len(a),(5000,len(a)))].mean(1)
    return dict(mean=float(a.mean()), median=float(np.median(a)), ci95=np.percentile(samples,[2.5,97.5]).tolist(),valid_pairs=len(a))


def subtract(a,b):
    return None if a is None or b is None else a-b


def classify(pe, tiles, no_car, classes):
    if pe is None or any(x is None for x in tiles):
        return 'INCONCLUSIVE'
    class_support = no_car is not None and no_car >= .15 or sum(x is not None and x > 0 for x in classes) >= 4
    if pe >= .3 and min(tiles) > 0 and class_support:
        return 'STRUCTURED_SIGNAL'
    if pe < .15:
        return 'NO_SUPPORT_THIS_PROTOCOL'
    return 'INCONCLUSIVE_OR_MIXED'


def main(base):
    p=validate(base)
    verify_code(base)
    rows={}
    for job in JOBS:
        receipt=accept(base,job)
        if job.startswith('pair_'):
            for name in receipt['records']:
                row=read(base/'jobs'/job/name)
                rows[row['realization'],row['tile'],row['family'],row['system']]=row
    def matrices(i, family, model, tiles=TILES, scope='noboundary', region='missing'):
        selected=[rows[i,t,family,model]['scopes'][scope][region] for t in tiles]
        return tuple(sum(np.asarray(r[k],np.int64) for r in selected) for k in ('clean_cm','missing_cm'))
    def damage(i,f,m,tiles=TILES,classes=(0,1,2,3,4)):
        return difference(*matrices(i,f,m,tiles),classes=classes)
    per_pair=[]
    for i in range(1,21):
        report=dict(realization=i,models={})
        for model in MODELS:
            d={f:damage(i,f,model) for f in FAMILIES}
            pe=subtract(d['gradient'],d['matched'])
            no_car=subtract(damage(i,'gradient',model,classes=(0,1,2,3)),damage(i,'matched',model,classes=(0,1,2,3)))
            classes=[subtract(damage(i,'gradient',model,classes=(c,)),damage(i,'matched',model,classes=(c,))) for c in range(5)]
            report['models'][model]=dict(damage=d,CE=subtract(d['random'],d['pixel']),PE=pe,
                PE_total=subtract(d['gradient'],d['random']),PE_no_car=no_car,PE_classes=classes,
                tile_PE={t:subtract(damage(i,'gradient',model,(t,)),damage(i,'matched',model,(t,))) for t in TILES})
        cb, corrected={},{}
        for family in FAMILIES:
            masked=matrices(i,family,'MASKED')
            context=matrices(i,family,'CONTEXT')
            a,b=metric(context[1]),metric(masked[1])
            cb[family]=None if a is None or b is None else 100*(a-b)
            corrected[family]=subtract(damage(i,family,'MASKED'),damage(i,family,'CONTEXT'))
        report.update(CB=cb,damage_reduction=corrected,
            I_placement=subtract(cb['gradient'],cb['matched']),I_geometry=subtract(cb['random'],cb['pixel']))
        per_pair.append(report)
    results={m:{key:interval([r['models'][m][key] for r in per_pair]) for key in ('CE','PE','PE_total','PE_no_car')} for m in MODELS}
    primary=results['S1']['PE']['mean']
    tiles=[interval([r['models']['S1']['tile_PE'][t] for r in per_pair])['mean'] for t in TILES]
    classes=[interval([r['models']['S1']['PE_classes'][c] for r in per_pair])['mean'] for c in range(5)]
    gate=classify(primary,tiles,results['S1']['PE_no_car']['mean'],classes)
    write(base/'summary.json',dict(protocol=p['protocol'],plan_sha256=sha(base/'plan.json'),
        mask_manifest_sha256=sha(base/'mask_manifest.json'),models=results,per_pair=per_pair,
        primary_model='S1',primary_PE=primary,primary_tile_PE=dict(zip(TILES,tiles)),primary_class_PE=classes,
        development_gate=gate,CB={f:interval([r['CB'][f] for r in per_pair]) for f in FAMILIES},
        I_placement=interval([r['I_placement'] for r in per_pair]),I_geometry=interval([r['I_geometry'] for r in per_pair]),
        inference_cases=640,clean_cases=8,old_endpoint_checks=6,optimizer_updates=0,
        statistical_scope='5000 paired-mask bootstrap resamples, conditional on two repeatedly used Val2 tiles and fixed models; not independent sites or training seeds',
        test6_loaded=False,independent_final_loaded=False,next_training_launched=False,automatic_expansion=False,completed_at=now()))
    print('STRUCTURED_ANALYSIS_COMPLETE',gate,'NO_FURTHER_DISPATCH',flush=True)


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True)
    main(a.parse_args().directory.resolve())
