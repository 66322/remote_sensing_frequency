"""Offline audit of the six compact D18 summaries and paired decision counts."""
import hashlib
import json
import math
from pathlib import Path
import subprocess

from audit_rebuild_v1_d18_d19_archived import check_condition, equal, scores, assess, add_matrices

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'records/rebuild_v1_d18_replication_compact_20260928'
CFG=ROOT/'configs/rebuild_v1/d18_d19_night_20260927.json'
REPL=ROOT/'configs/rebuild_v1/d18_replication_seed17_20260928.json'
ARMS=('P0','P1','P2')
TILES=('3_11','5_10')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def blob_sha(commit, path):
    raw=subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=ROOT)
    return hashlib.sha256(raw).hexdigest()


def check_pair(row):
    keys=('both_correct','only_p0_correct','only_candidate_correct','both_wrong')
    assert row['valid']==sum(row[key] for key in keys)
    assert all(isinstance(row[key],int) and row[key]>=0 for key in ('valid',*keys))


def miou_percent(cm):
    values=[]
    for i in range(5):
        tp=cm[i][i]
        union=sum(cm[i])+sum(row[i] for row in cm)-tp
        if union:
            values.append(tp/union)
    return 100*sum(values)/len(values)


def main():
    cfg=read(CFG)
    manifest=read(BASE/'manifest.json')
    assert manifest['status']=='COMPLETE' and not manifest['missing']
    plan=read(BASE/'planned_jobs.json')
    assert plan['git_commit']==manifest['executed_git_commit']
    assert plan['training_seed']==17 and plan['evaluation_corruption_seed']==42
    commit=plan['git_commit']
    config_sha=blob_sha(commit,str(CFG.relative_to(ROOT)).replace('\\','/'))
    replication_sha=blob_sha(commit,str(REPL.relative_to(ROOT)).replace('\\','/'))
    for name,digest in plan['source_sha256'].items():
        assert blob_sha(commit,name)==digest,name
    for name, info in manifest['files'].items():
        archived=str((BASE/name).relative_to(ROOT)).replace('\\','/')
        assert blob_sha('HEAD',archived)==info['archive_sha256'],name
    data={}
    for seed in (42,17):
        data[seed]={}
        for arm in ARMS:
            name=f'server_{arm}_seed{seed}_summary.json'
            summary=read(BASE/name)
            assert (summary['arm'],summary['seed'],summary['smoke'],summary['test6_loaded'])==(arm,seed,False,False)
            assert summary['val2_loaded'] and summary['clean_reproduction_pass']
            assert summary['config_sha256']==config_sha
            assert set(summary['conditions'])==set(cfg['evaluation_conditions']+cfg['diagnostics'])
            if seed==17:
                assert summary['replication_config_sha256']==replication_sha
                assert summary['evaluation_corruption_seed']==42
                assert summary['historical_r01_reference_seed']==42
                assert summary['signature']['training']['seed']==17
            for condition in summary['conditions'].values():
                check_condition(condition)
            data[seed][arm]=summary
        assert data[seed]['P1']['trainable_parameters']==data[seed]['P2']['trainable_parameters']
        assert len({data[seed][arm]['signature']['training']['anchor_sha256'] for arm in ARMS})==1
    decision=read(BASE/'decision.json')
    assert decision['status']=='COMPLETE' and decision['seeds']==[42,17]
    assert decision['test6_loaded'] is False and decision['val2_exploratory'] is True
    assert decision['original_config_sha256']==config_sha
    assert decision['replication_config_sha256']==replication_sha
    for seed in (42,17):
        reported=decision['outcomes'][str(seed)]
        equal(reported['decision'],assess('P2',['P0','P1'],'P0',data[seed],cfg))
        for arm in ARMS:
            _,families,macro=scores(data[seed][arm],cfg)
            equal(reported['score_rows'][arm],dict(macro_percent=macro,families=families))
        for condition,entry in decision['paired'][str(seed)].items():
            assert set(entry['tiles'])==set(TILES)
            pooled=entry['pooled_paired']
            for arm in ('P1','P2'):
                for part in ('all','damaged_region'):
                    check_pair(pooled[arm][part])
                    equal(pooled[arm][part],{key:sum(entry['tiles'][tile]['paired'][arm][part][key] for tile in TILES)
                                                  for key in pooled[arm][part]})
                assert sum(row['valid'] for row in pooled[arm]['by_class'].values())==pooled[arm]['all']['valid']
                for row in pooled[arm]['by_class'].values():
                    check_pair(row)
                for key in pooled[arm]['all']:
                    assert pooled[arm]['all'][key]==sum(row[key] for row in pooled[arm]['by_class'].values())
            for field in ('pooled_raw_p2_cm','pooled_matched_p0_fallback_cm'):
                tile_field='raw_p2_cm' if field=='pooled_raw_p2_cm' else 'matched_p0_fallback_cm'
                equal(entry[field],add_matrices([entry['tiles'][tile][tile_field] for tile in TILES]))
            equal(entry['pooled_raw_p2_cm'],data[seed]['P2']['conditions'][condition]['pooled']['noboundary']['cm'])
            for prefix in ('pooled_raw_p2','pooled_matched_p0_fallback'):
                assert math.isclose(entry[f'{prefix}_mIoU_fg5_percent'],miou_percent(entry[f'{prefix}_cm']),abs_tol=1e-9)
            for tile in TILES:
                row=entry['tiles'][tile]
                equal(row['raw_p2_cm'],data[seed]['P2']['conditions'][condition]['tiles'][tile]['metrics']['noboundary']['cm'])
                for prefix in ('raw_p2','matched_p0_fallback'):
                    assert math.isclose(row[f'{prefix}_mIoU_fg5_percent'],miou_percent(row[f'{prefix}_cm']),abs_tol=1e-9)
            if condition=='aux_zero':
                equal(entry['pooled_matched_p0_fallback_cm'],data[seed]['P0']['conditions'][condition]['pooled']['noboundary']['cm'])
                assert all(entry['tiles'][tile]['absent_valid_pixels']>0 for tile in TILES)
                for tile in TILES:
                    equal(entry['tiles'][tile]['matched_p0_fallback_cm'],
                          data[seed]['P0']['conditions'][condition]['tiles'][tile]['metrics']['noboundary']['cm'])
    assert decision['both_seeds_pass']==all(decision['outcomes'][str(s)]['decision']['passed'] for s in (42,17))
    lines=(BASE/'status.tsv').read_text(encoding='utf-8').splitlines()
    starts=[i for i,line in enumerate(lines) if '\tQUEUE\tSTART\t' in line]
    assert starts
    final=lines[starts[-1]:]
    assert final[0].endswith(commit)
    assert any('\tQUEUE\tFINISHED\t' in line and 'analysis_ok=True' in line for line in final)
    status='\n'.join(final)
    assert '\tANALYSIS\tCOMPLETE\t0' in status
    for arm in ARMS:
        assert f'\tFORMAL_{arm}_17\tCOMPLETE\ttrain=0' in status
        assert f'\tEVAL_FORMAL_{arm}_17\tCOMPLETE\t0' in status
    audit=dict(status='PASS',executed_git_commit=plan['git_commit'],summaries=6,
               both_seeds_pass=decision['both_seeds_pass'],
               checks=['six original evaluation summaries and all condition integer CMs',
                       'matched model and evaluation provenance','both prespecified seed decisions',
                       'paired error totals, class totals, pooled CMs and full-absence P0 fallback'],
               limitation='Prediction arrays, dataset and checkpoints remain on the server; this offline audit verifies archived counts and decisions, not independent re-inference. Val2 is exploratory.')
    (BASE/'offline_audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    print('D18 SEED17 ARCHIVE AUDIT PASS: six summaries; both-seed decision reproduced')


if __name__=='__main__':
    main()
