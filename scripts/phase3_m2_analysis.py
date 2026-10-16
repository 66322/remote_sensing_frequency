"""Server-side aggregation, explicit gates, compact publication products."""
import csv
import gzip
import json
from pathlib import Path
import numpy as np
import phase3_m2_common as c
from phase3_m2_counts import validate_counts,lists

def arrays(x):
    if isinstance(x,dict):return {k:arrays(v) for k,v in x.items()}
    return np.asarray(x) if isinstance(x,list) else x

class Sink:
    def __init__(self,base):
        self.base=Path(base);self.groups={};self.cases=set();self.trajectories=0;self.trajectory_by_job={}
        self.stream=gzip.open(self.base/'case_counts.jsonl.gz','xt',encoding='utf-8',compresslevel=1)
    def accept(self,result):
        meta=result['metadata'];counts=result['counts']
        if result['kind']=='trajectory':
            path=self.base/'trajectory_counts'/meta['job']/f"{meta['step']}_{meta['tile']}.json"
            c.write(path,dict(metadata=meta,counts=counts));self.trajectories+=1
            self.trajectory_by_job.setdefault(meta['job'],set()).add((meta['step'],meta['tile']));return
        identity=tuple(meta[k] for k in ['tile','rseed','dseed','arm','condition','family','realization'])
        if identity in self.cases:raise RuntimeError('duplicate evaluation case')
        self.cases.add(identity);validate_counts(counts)
        self.stream.write(json.dumps(dict(metadata=meta,counts=counts),separators=(',',':'))+'\n')
        group=identity[:5]
        if group not in self.groups:self.groups[group]=dict(metadata={k:meta[k] for k in ['tile','fold','rseed','dseed','arm','condition']},cases=0,counts=arrays(counts))
        else:
            from phase3_m2_counts import add
            self.groups[group]['counts']=add(self.groups[group]['counts'],arrays(counts))
        self.groups[group]['cases']+=1
    def close(self):self.stream.close()

def flow(joint):
    j=np.asarray(joint,np.int64);right=wrong=rescued=harmed=0
    # Independent explicit enumeration of the conditional numerators/denominators.
    for gt in range(5):
        for r in range(6):
            for d in range(6):
                n=int(j[gt,r,d])
                if r==gt:right+=n;harmed+=n*(d!=gt)
                else:wrong+=n;rescued+=n*(d==gt)
    return dict(rgb_correct=right,rgb_wrong=wrong,rescued=rescued,harmed=harmed,
        rescue_pp=None if not wrong else 100*rescued/wrong,harm_pp=None if not right else 100*harmed/right)

def pool(groups,arm,condition,seed=None,rseed=None,dseed=None,tile=None,fold=None,region='all'):
    selected=[]
    for z in groups.values():
        m=z['metadata']
        if m['arm']!=arm or m['condition']!=condition:continue
        if seed is not None and (m['rseed']!=seed or m['dseed']!=seed):continue
        if any(value is not None and m[k]!=value for k,value in [('rseed',rseed),('dseed',dseed),('tile',tile),('fold',fold)]):continue
        selected.append(z['counts']['nb'][region])
    if not selected:return None
    return {k:sum((np.asarray(z[k],np.int64) for z in selected)) for k in ['joint','fusion_joint','cms','logit_cm']}

def gain(groups,other,condition='down4',region='all',measure='miou',**filters):
    rows=[pool(groups,a,condition,region=region,**filters) for a in ['DF',other]]
    if any(r is None for r in rows):return None
    values=[c.cm_metric(r['cms'][2]) if measure=='miou' else flow(r['joint'])['rescue_pp'] for r in rows]
    return None if any(v is None for v in values) else values[0]-values[1]

def gates(groups,g0):
    checks={}
    def check(name,values,mean=None,floor=None,strict=False,strict_mean=False):
        valid=all(v is not None and np.isfinite(v) for v in values)
        passed=valid and (mean is None or (float(np.mean(values))>mean if strict_mean else float(np.mean(values))>=mean)) and (floor is None or all(v>floor if strict else v>=floor for v in values))
        checks[name]=dict(pass_=bool(passed),values_pp=values,mean_threshold_pp=mean,floor_pp=floor,strict_floor=strict,strict_mean=strict_mean)
        return bool(passed)
    g1=[]
    for other in ['D0','DSelf','DShuffle','DEntropy']:
        g1.append(check('G1_rescue_DF-'+other,[gain(groups,other,seed=s,measure='rescue') for s in c.SEEDS],.5,0,True))
    specificity=check('H2_DF-DClean_all',[gain(groups,'DClean',seed=s,measure='rescue') for s in c.SEEDS],.3,0,True)
    specificity &= check('H2_DF-DClean_damaged',[gain(groups,'DClean',seed=s,measure='rescue',region='damaged') for s in c.SEEDS],.3,0,True)
    g2=[check('G2_fusion_DF-D0',[gain(groups,'D0',seed=s) for s in c.SEEDS],.3,0,True)]
    for other in ['DSelf','DShuffle','DEntropy','DMix','DClean']:
        g2.append(check('G2_fusion_DF-'+other,[gain(groups,other,seed=s) for s in c.SEEDS],.2,0,True))
    values=[gain(groups,'D0',seed=s,fold=f) for s in c.SEEDS for f in ['F0','F1','F2']]
    checks['G2_fold_consistency']=dict(pass_=all(v is not None for v in values) and sum(v>0 for v in values if v is not None)>=7,values_pp=values,positive_required=7)
    g2.append(checks['G2_fold_consistency']['pass_'])
    g3=[]
    # The per-tile floor applies to EVERY protection panel/ROI listed here.
    for condition,region in [('clean','all'),('down4','healthy'),('dsm_down4','all'),('dsm_shift8','all')]:
        g3.append(check('G3_'+condition+'_'+region,[gain(groups,'D0',condition,region,seed=s) for s in c.SEEDS],floor=-.2))
        means=[]
        for tile in c.FIT:
            vs=[gain(groups,'D0',condition,region,seed=s,tile=tile) for s in c.SEEDS]
            means.append(None if any(v is None for v in vs) else float(np.mean(vs)))
        g3.append(check('G3_tile_'+condition+'_'+region,means,floor=-.5))
    cross=[gain(groups,'D0',rseed=r,dseed=d) for r in c.SEEDS for d in c.SEEDS if r!=d]
    checks['G4_cross_pairing']=dict(pass_=all(v is not None for v in cross) and sum(v>0 for v in cross if v is not None)>=5,values_pp=cross,positive_required=5)
    g4=[checks['G4_cross_pairing']['pass_']]
    for cond in ['down8','blur2','noise005']:g4.append(check('G4_'+cond,[gain(groups,'D0',cond,seed=s) for s in c.SEEDS],mean=0.,floor=-.2,strict_mean=True))
    status=dict(G0=bool(g0),G1=all(g1),H2_degradation_specificity=bool(specificity),G2=all(g2),G3=all(g3),G4=all(g4))
    return dict(status=status,checks=checks,advance_reverse=all(status.values()),
        interpretation='practical development gates, not significance/equivalence or independent-city confirmation')

def finalize(base,sink,failures):
    base=Path(base);folds=c.read(base/'folds.json');jobs=c.jobs(folds); errors=[]
    done=[]
    for job in jobs:
        f=base/'jobs'/job['id']/'complete.json'
        if not f.exists():errors.append('missing endpoint: '+job['id']);continue
        z=c.read(f)
        if z['optimizer_updates']!=32000 or z['binding']!=c.binding(base):errors.append('endpoint contract: '+job['id'])
        done.append(z)
    for fold in ['F0','F1','F2']:
        for seed in c.SEEDS:
            rows=[z for z in done if z['job'].startswith(f'{fold}_s{seed}_D')]
            if len(rows)!=7 or len({z['initial_state_sha256'] for z in rows})!=1 or len({z['batch_stream_sha256'] for z in rows})!=1:
                errors.append('paired initialization/stream: '+fold+'/'+str(seed))
    expected=12*3*3*7*103
    if len(sink.cases)!=expected:errors.append(f'case coverage {len(sink.cases)}/{expected}')
    if sink.trajectories!=108*4*4:errors.append(f'trajectory coverage {sink.trajectories}/1728')
    for group in sink.groups.values():
        expected_cases=20 if group['metadata']['condition'] in ['down2','down4','down8','blur2','noise005'] else 1
        if group['cases']!=expected_cases:errors.append('aggregate case coverage')
        validate_counts(lists(group['counts']))
    shared_rgb={};shared_dsm={}
    for group in sink.groups.values():
        m=group['metadata'];j=group['counts']['nb']['all']['joint']
        rgbkey=(m['tile'],m['rseed'],m['condition'])
        rgb=np.asarray(j,np.int64).sum(2)
        if rgbkey in shared_rgb and not np.array_equal(shared_rgb[rgbkey],rgb):errors.append('shared RGB reference differs')
        shared_rgb[rgbkey]=rgb
        if m['condition'] not in ['dsm_down4','dsm_shift8']:
            dkey=(m['tile'],m['dseed'],m['arm']);dsm=np.asarray(j,np.int64).sum(1)
            if dkey in shared_dsm:
                prior,n=shared_dsm[dkey]
                if not np.array_equal(prior*group['cases'],dsm*n):errors.append('DSM changed under RGB fault')
            else:shared_dsm[dkey]=(dsm,group['cases'])
    report=gates(sink.groups,not errors and not failures)
    publication=base/'publication';publication.mkdir(exist_ok=True)
    c.write(publication/'gates.json',report)
    with (publication/'metrics.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['seed','arm','condition','region','rgb_miou','dsm_miou','fusion_miou','rescue_pp','harm_pp','rescued','harmed','rgb_wrong','rgb_correct']);writer.writeheader()
        for seed in c.SEEDS:
            for arm in c.ARMS:
                for cond in ['clean','down2','down4','down8','blur2','noise005','dsm_down4','dsm_shift8']:
                    for region in ['all','damaged','healthy']:
                        row=pool(sink.groups,arm,cond,seed=seed,region=region)
                        if row is None:continue
                        fl=flow(row['joint'])
                        writer.writerow(dict(seed=seed,arm=arm,condition=cond,region=region,rgb_miou=c.cm_metric(row['cms'][0]),
                            dsm_miou=c.cm_metric(row['cms'][-1]),fusion_miou=c.cm_metric(row['cms'][2]),**fl))
    # Three ordinary compressed sufficient-statistics files, no archive nesting
    # or arbitrary binary chunk concatenation. All per-mask rows stay on server.
    for fold in ['F0','F1','F2']:
        with gzip.open(publication/(fold+'_counts.jsonl.gz'),'wt',encoding='utf-8',compresslevel=6) as f:
            for group in sorted(sink.groups.values(),key=lambda z:tuple(str(z['metadata'][k]) for k in ['tile','rseed','dseed','arm','condition'])):
                if group['metadata']['fold']==fold:
                    f.write(json.dumps(dict(metadata=group['metadata'],cases=group['cases'],nb=lists(group['counts']['nb']),
                        margin_counts=lists(group['counts']['margin_counts']),calibration=lists(group['counts']['calibration'])),separators=(',',':'))+'\n')
    # Full auxiliary statistics remain server-side, alongside individual masks.
    with gzip.open(base/'all_aggregates.jsonl.gz','wt',encoding='utf-8',compresslevel=3) as f:
        for group in sink.groups.values():f.write(json.dumps(lists(group),separators=(',',':'))+'\n')
    summary=dict(status='COMPLETE_SERVER_CHECKED' if not errors and not failures else 'INCOMPLETE_NO_RETRY',
        binding=c.binding(base),jobs_complete=len(done),jobs_expected=108,optimizer_updates=sum(z['optimizer_updates'] for z in done),
        evaluated_cases=len(sink.cases),expected_cases=expected,gates=report['status'],advance_reverse=report['advance_reverse'],
        conditional_extensions_started=False,errors=errors,failures=failures,server=str(base),observed_at=c.now(),
        scope='Fit12 same-city development CV; no Val2/Test6/held4/final or point cloud',
        extension='B requires separately frozen reverse execution contract; C remains budget reservation')
    c.write(publication/'summary.json',summary)
    lines=['# Phase3-M2 实验结果','',f"状态：{summary['status']}",f"完成训练：{len(done)}/108；更新：{summary['optimizer_updates']}",
        f"评价案例：{len(sink.cases)}/{expected}",'','## 预登记判断','']+[f'- {k}: {v}' for k,v in report['status'].items()]
    lines+=['','## RGB-down4 主结果','',
        '| 整系统种子 | DSM 臂 | DSM mIoU % | 融合 mIoU % | DSM 补救率 % | DSM 损伤率 % |',
        '|---|---|---:|---:|---:|---:|']
    fmt=lambda x:'缺失' if x is None else f'{x:.6f}'
    for seed in c.SEEDS:
        for arm in c.ARMS:
            z=pool(sink.groups,arm,'down4',seed=seed)
            if z is None:continue
            flowz=flow(z['joint'])
            lines.append(f"| {seed} | {arm} | {fmt(c.cm_metric(z['cms'][-1]))} | {fmt(c.cm_metric(z['cms'][2]))} | {fmt(flowz['rescue_pp'])} | {fmt(flowz['harm_pp'])} |")
    lines+=['','这些结果属于 Fit12 同城开发交叉验证。全部负结果、逐掩码计数、模型和日志保留在服务器。',
        'metrics.csv 包含各面板和区域；三个 fold 计数文件包含每 tile、模型换配和权重曲线所需整数统计。',
        '科学阴性不触发重训；网络失败只恢复上传。B 方向须先冻结反向执行合同，第二编码器当前不进入队列。']
    (publication/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    retained=[dict(path=str(f.relative_to(base)),size=f.stat().st_size,sha256=c.sha(f)) for f in [base/'case_counts.jsonl.gz',base/'all_aggregates.jsonl.gz',base/'input_index.json']]
    c.write(publication/'server_evidence_index.json',dict(binding=c.binding(base),server_directory=str(base),files=retained,
        endpoints=[dict(job=z['job'],path=f"jobs/{z['job']}/endpoint.pth",size=(base/'jobs'/z['job']/'endpoint.pth').stat().st_size,
            sha256=z['checkpoint_sha256']) for z in done],
        mask_designs=[dict(path=str(f.relative_to(base)),size=f.stat().st_size,sha256=c.sha(f)) for f in sorted((base/'mask_design').glob('*.json'))],
        trajectory_counts=sink.trajectories))
    small=[dict(file=f.name,size=f.stat().st_size,sha256=c.sha(f)) for f in sorted(publication.iterdir()) if f.is_file()]
    c.write(publication/'manifest.json',dict(binding=c.binding(base),files=small,total_bytes=sum(z['size'] for z in small),
        core_50MiB_target_exceeded=sum(z['size'] for z in small)>50*1024**2,readback_policy='summary/gates/manifest only; Git object IDs acknowledge other uploads',observed_at=c.now()))
    return summary
