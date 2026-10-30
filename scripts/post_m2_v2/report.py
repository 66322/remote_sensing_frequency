import csv
import json
from pathlib import Path
import numpy as np
from . import common as c

def _score(panel,condition,metric='full'):
    return panel['pooled'][condition]['boundary_f1'] if metric=='boundary_f1' else panel['pooled'][condition][metric]['fg5']

def route_gate(name,panels):
    if name=='G':candidate,control='G2','G1';conditions=['dsm_shift'];metric='full';mismatch='G3'
    elif name=='Q':candidate,control='Q2','Q1';conditions=['rgb_blur','dsm_shift'];metric='full';mismatch='Q3'
    elif name=='S':candidate,control='S2','S1';conditions=['clean'];metric='boundary_f1';mismatch='S3'
    else:raise ValueError(name)
    if not all(x in panels for x in (candidate,control,mismatch)):return dict(status='INCOMPLETE_NO_SCIENTIFIC_CONCLUSION')
    a,b,broken=panels[candidate],panels[control],panels[mismatch]
    primary=float(np.mean([_score(a,k,metric)-_score(b,k,metric) for k in conditions]))
    mechanism=float(np.mean([_score(a,k,metric)-_score(broken,k,metric) for k in conditions]))
    clean=_score(a,'clean')-_score(b,'clean')
    diffs=[]
    for tile in a['tiles']:
        diffs.append(float(np.mean([a['tiles'][tile][k]['full']['fg5']-b['tiles'][tile][k]['full']['fg5'] for k in conditions])))
    healthy=min(_score(a,k,'healthy')-_score(b,k,'healthy') for k in conditions)
    protected=clean>=-.2 and min(diffs)>=-.5
    if name=='Q':protected &= healthy>=-.2
    if name=='S':protected &= _score(a,'clean','nonboundary')-_score(b,'clean','nonboundary')>=-.2
    return dict(status='SCREEN_PASSED_NEEDS_INDEPENDENT_CONFIRMATION' if primary>=.5 and mechanism>0 and protected else 'SPECIFIC_IMPLEMENTATION_NOT_PASSED',
        candidate=candidate,control=control,primary_gain_pp=primary,correspondence_or_time_control_gain_pp=mechanism,
        clean_delta_pp=clean,worst_tile_delta_pp=min(diffs),healthy_delta_pp=healthy,protection_passed=bool(protected),
        thresholds=dict(primary_gain_pp=.5,clean_floor_pp=-.2,worst_tile_floor_pp=-.5,mechanism_gap='strictly_positive'),
        caveat='development utility screening; no significance or general impossibility claim')

def summarize(base):
    base=Path(base);rows=[];panels={};costs={};partial={}
    for arm in c.JOBS:
        folder=base/'jobs'/arm
        if (folder/'result.json').exists():
            r=c.read(folder/'result.json');costs[arm]=r
            if r['status']=='COMPLETE' and (folder/'outer_selected.json').exists():
                panels[arm]=c.read(folder/'outer_selected.json')
                for condition,p in panels[arm]['pooled'].items():
                    rows.append(dict(arm=arm,condition=condition,selected_step=r['selected_step'],full_fg5=p['full']['fg5'],
                        nb_fg5=p['nb']['fg5'],boundary_f1=p['boundary_f1'],car_iou=p['full']['iou'][4],
                        car_recall=(100*p['full']['cm'][4][4]/p['full']['support'][4] if p['full']['support'][4] else None)))
        elif (folder/'started.json').exists():
            trajectory=folder/'trajectory.jsonl';last=0
            if trajectory.exists():
                for line in trajectory.read_text(encoding='utf-8').splitlines():
                    if line.strip():last=max(last,json.loads(line)['step'])
            partial[arm]=dict(last_logged_successful_step=last,unlogged_tail_updates_possible=99,
                interpretation='lower bound only; started/failed does not prove zero optimization')
    publication=base/'publication';publication.mkdir(parents=True,exist_ok=True)
    if rows:
        with (publication/'metrics.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    gates={name:route_gate(name,panels) for name in ('G','Q','S')}
    result=dict(observed_at=c.now(),jobs_complete=sum(x.get('status')=='COMPLETE' for x in costs.values()),
        expected_jobs=11,completed_receipt_updates=sum(x.get('updates',0) for x in costs.values()),
        observed_updates_lower_bound=sum(x.get('updates',0) for x in costs.values())+sum(x['last_logged_successful_step'] for x in partial.values()),
        partial_jobs=partial,exact_total_updates_known=not partial,
        gates=gates,evidence_scope='Potsdam F0 reused development; sealed datasets closed',
        status='FULL_GROUPS_AVAILABLE' if len(panels)==11 else 'INCOMPLETE_NO_RETRY')
    c.write(publication/'summary.json',result);c.write(publication/'gates.json',gates)
    (publication/'REPORT.md').write_text('# 多路线 v2 执行结果\n\n'+json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2));return result

def export(base):
    import gzip
    base=Path(base);summarize(base);selected=[];seen=set()
    # One bounded stream, avoiding hundreds of network requests and ordinary Git logits.
    with gzip.open(base/'publication/evidence.jsonl.gz','wt',encoding='utf-8',compresslevel=6) as archive:
        for pattern in ['contract.json','budget.json','measured_budget.json','execution_tuning.json','*_complete.json','*_first_failure.json','*_progress.json',
            '*resources.jsonl','*gpu*.log','a_spatial_*.log','worker_gpu*.json','profiles/*.json','jobs/*/*.json','jobs/*/*.jsonl','a_spatial/*/*.json']:
            for p in base.glob(pattern):
                if not p.is_file() or p in seen:continue
                seen.add(p)
                if p.stat().st_size>25*1024**2:raise RuntimeError('unexpected oversized evidence: '+str(p))
                rel=p.relative_to(base).as_posix()
                archive.write(json.dumps(dict(path=rel,content=p.read_text(encoding='utf-8')),ensure_ascii=False)+'\n')
                selected.append(dict(path=rel,bytes=p.stat().st_size))
    c.write(base/'publication/manifest.json',dict(files=selected,large_files_uploaded=False,observed_at=c.now()))
    print('PUBLICATION_READY',base/'publication')
