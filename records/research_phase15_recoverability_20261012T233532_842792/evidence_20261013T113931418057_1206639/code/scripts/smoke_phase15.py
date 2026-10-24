"""Actual Val2/model smoke; never use this realization for scientific selection."""
import argparse
from pathlib import Path
import numpy as np
from phase15_common import *
from phase15_numeric import *
from prepare_phase15 import old_prediction, load_mask, checked_array


def value(row, name='prediction'):
    with np.load(checked_array(row['arrays'][name]), allow_pickle=False) as z:
        return z['value']


def main(base, gpu):
    from phase15_inference import Runner, infer_one, make_model
    p = validate(base)
    tile, realization = TILES[0], 1
    folder = base/'smoke'/('gpu'+str(gpu))
    folder.mkdir(parents=True,exist_ok=False)
    def progress(**kw):
        write(folder/'progress.json',dict(observed_at=now(),optimizer_updates=0,**kw))
    runner = Runner(base,gpu,progress)
    checks = []
    cross = [case('S1',tile,'intact',1,'pixel'),case('R16',tile,'intact',1,'random')]
    if gpu == 1:
        for c in cross:
            row = runner.run(c,folder/(case_id(c)+'.json'))
            reference = read(base/'cases'/(case_id(c)+'.json'))
            if not np.array_equal(value(row),value(reference)) or row['scopes'] != reference['scopes']:
                raise RuntimeError('cross-device native label/count mismatch')
            if 'entropy' in row['arrays'] and not np.array_equal(value(row,'entropy'),value(reference,'entropy')):
                raise RuntimeError('cross-device entropy bin mismatch')
            checks.append(dict(check='cross_gpu_exact',case=c,passed=True))
    else:
        for model in ('S1','R16'):
            for ds in DSM:
                runner.run(case(model,tile,ds))
        for model in ('S13','DSM'):
            runner.run(case(model,tile))
        # Replay all four original masks for the single frozen realization.
        for family in FAMILIES:
            c = case('S1',tile,'intact',realization,family)
            row = runner.run(c)
            old = old_prediction(base,'S1',tile,realization,family)
            if not np.array_equal(value(row),old):
                raise RuntimeError('archived native prediction replay mismatch')
            oldrow = read(Path(p['structured'])/'jobs'/f'pair_01_{tile}'/(family+'_S1.json'))
            for scope in ('full','noboundary'):
                for region in oldrow['scopes'][scope]:
                    for field in ('clean_cm','missing_cm'):
                        if row['scopes'][scope][region][field] != oldrow['scopes'][scope][region][field]:
                            raise RuntimeError('archived integer matrix replay mismatch')
            checks.append(dict(check='archived_replay_exact',family=family,passed=True))
        for model in ('S1','R16'):
            for ds in DSM:
                runner.run(case(model,tile,ds,realization,'gradient'))
        for c in cross + [case('S13',tile,'intact',realization,'gradient')]:
            runner.run(c)
        for ratio in (5,10):
            runner.run(case('S1',tile,'intact',realization,'pixel',ratio))
        from post_s1_support_evaluation import source_case
        expected,_,_ = source_case(Path(p['root']),'S1-3','evaluation','clean',tile)
        if not np.array_equal(value(read(base/'cases'/(case_id(case('S13',tile))+'.json'))),expected['candidate']):
            raise RuntimeError('S1-3 original clean graph not reproduced')
        fixed,_,_ = source_case(Path(p['root']),'S1-0','evaluation','clean',tile)
        ds = value(read(base/'cases'/(case_id(case('DSM',tile))+'.json')))
        if not np.array_equal(ds,fixed['fixed_dsm']):
            raise RuntimeError('D15 DSM-only clean reference differs')
        oldpath = Path(p['paired'])/'jobs/R16/endpoint_ordinary/clean/candidate'/(tile+'.npy')
        oldrecord = read(oldpath.parent.parent/(tile+'.json'))
        if sha(oldpath) != oldrecord['predictions']['candidate']:
            raise RuntimeError('R16 archived endpoint changed')
        if not np.array_equal(value(read(base/'cases'/(case_id(case('R16',tile))+'.json'))),np.load(oldpath,allow_pickle=False)):
            raise RuntimeError('R16 clean endpoint graph differs')
        # DSM-only exact RGB independence; no new expert training.
        model,_ = make_model(base,'DSM')
        full = np.ones(runner.item['dsm'].shape,bool)
        check,_,_ = infer_one(model,'DSM',np.zeros_like(runner.item['optical']),runner.item['dsm'],full,full,progress)
        if not np.array_equal(check,ds):
            raise RuntimeError('DSM-only RGB invariance failed')
        checks.extend([dict(check=n,passed=True) for n in ('S13_clean_graph','R16_clean_endpoint','DSM_legacy_clean','DSM_RGB_invariance')])
        for family in FAMILIES:
            m25,_ = load_mask(base,tile,realization,family)
            if family == 'pixel':
                m5,_ = load_mask(base,tile,realization,family,5)
                m10,_ = load_mask(base,tile,realization,family,10)
                if not ((m5<=m10).all() and (m10<=m25).all()):
                    raise RuntimeError('nested identity')
        checks.append(dict(check='actual_M25_SHA_nested_counts',passed=True))
        for mode,row in read(base/'map_manifest.json')['tiles'][tile].items():
            with np.load(checked_array(row),allow_pickle=False) as z:
                checked = map_check(z['index'],runner.item['dsm'].shape)
                if checked['canonical_index_sha256'] != row['canonical_index_sha256']:
                    raise RuntimeError('DSM map identity')
        checks.append(dict(check='actual_DSM_bijections',passed=True))
        # Exercise whole D postprocessor with all five real frozen experts.
        c = case('S1',tile,'intact',realization,'gradient')
        preds = [value(read(base/'cases'/(case_id(case(n,tile,'intact',realization,'gradient'))+'.json'))) if n not in ('DSM','RGB') else
                 ds if n=='DSM' else old_prediction(base,'RGB',tile,realization,'gradient') for n in EXPERTS]
        mask,_ = load_mask(base,tile,realization,'gradient')
        primary = read(base/'cases'/(case_id(c)+'.json'))
        stats = oracle_evidence(runner.item['noboundary_gt'],old_prediction(base,'S1',tile),preds,mask,value(primary,'entropy'),{})
        for systems in stats['systems'].values():
            for region,row in systems.items():
                if sum(map(sum,row['missing_cm'])) != row['transitions']['valid']:
                    raise RuntimeError('real D confusion conservation')
        write(folder/'oracle_smoke.json',stats)
        checks.append(dict(check='real_composition_oracle_conservation',passed=True))
    runner.finish()
    write(folder/'complete.json',dict(binding=binding(base),checks=checks,all_passed=True,
        optimizer_updates=0,test6_loaded=False,held4_loaded=False,independent_final_loaded=False,
        role='engineering only; not scientific selection',completed_at=now()))


if __name__ == '__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--directory',type=Path,required=True)
    a.add_argument('--gpu',type=int,choices=(0,1),required=True)
    x=a.parse_args()
    main(x.directory.resolve(),x.gpu)
