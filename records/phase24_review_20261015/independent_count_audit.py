import collections
import functools
import hashlib
import itertools
import json
import math
import argparse
from pathlib import Path
import numpy as np

parser=argparse.ArgumentParser(description='Independent arithmetic audit of SHA-verified Phase2.4 archive payloads; no model inference or training.')
parser.add_argument('--evidence-directory',type=Path,default=Path.cwd()/'验收记录'/'phase24_76ae973b')
ROOT=parser.parse_args().evidence_directory.resolve()
RAW = ROOT / 'originals'
OUT = ROOT / 'analysis'
OUT.mkdir(exist_ok=True)
TILES = ('3_11', '5_10')
FAMILIES = ('pixel', 'random', 'gradient', 'matched')
REGIONS = ('all', 'missing', 'healthy', 'observed')
PANELS = ('clean', 'P-U', 'P-M', 'dose', 'ordinary')
CASE_FIELDS = ('tile', 'panel', 'direction', 'family', 'realization', 'ratio', 'damage')

def read(p):
    return json.loads(p.read_bytes())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def check(condition, message):
    if not condition:
        raise AssertionError(message)

def close(a, b, path=''):
    if isinstance(a, dict):
        check(set(a) == set(b), 'Keys differ: ' + path)
        for k in a:
            close(a[k], b[k], path + '/' + k)
    elif isinstance(a, (list, tuple)):
        check(len(a) == len(b), 'Lengths differ: ' + path)
        for i, (x, y) in enumerate(zip(a, b)):
            close(x, y, path + '/' + str(i))
    elif isinstance(a, (float, np.floating)):
        check(b is not None and abs(a-b) < 1e-10, 'Float differs: ' + path)
    else:
        check(a == b, 'Value differs: ' + path)

def cid(c):
    return tuple(c[n] for n in CASE_FIELDS)

def sparse_counts(raw, size):
    out=np.zeros(size,np.int64)
    if not raw:
        return out
    pairs=np.asarray(raw)
    check(pairs.ndim==2 and pairs.shape[1]==2 and pairs.dtype.kind in 'iu', 'Invalid sparse count pairs')
    idx=pairs[:,0];values=pairs[:,1]
    check(np.all(idx>=0) and np.all(idx<size) and np.all(values>0) and
          len(np.unique(idx))==len(idx), 'Invalid sparse indices/values')
    out[idx]=values
    return out

def condition(c):
    return tuple(c[n] for n in CASE_FIELDS if n != 'tile')

def metric(a):
    den = a.sum(0) + a.sum(1) - a.diagonal()
    ok = den[:5] > 0
    return float(np.mean(a.diagonal()[:5][ok] / den[:5][ok]) * 100) if ok.any() else None

transport = read(ROOT / 'transport_verification.json')
check(transport['all_payload_sha256'], 'Transport audit incomplete')
payloads = {r['path']:r for r in read(ROOT / 'payload_index.json')}
summary = read(RAW / 'summary.json')
plan = read(RAW / 'plan.json')
index = read(RAW / 'evidence_index.json')
binding = {n:sha(RAW / n) for n in ('plan.json', 'code_manifest.json')}
check(binding == summary['binding'] == index['binding'], 'Primary binding differs')
check(sha(RAW/'summary.json') == index['summary_sha256'], 'Index summary SHA differs')
check(plan['val2'] == list(TILES) and plan['seed'] == 42 and plan['gpus'] == [0,1], 'Protocol changed')
check(plan['test6_loaded'] is False and plan['held4_loaded'] is False and
      plan['new_seeds'] is False and plan['automatic_retry'] is False, 'Boundary declarations differ')

fits = {}
for p in (RAW/'fits').glob('*.json'):
    v = read(p)
    check(v['binding'] == binding and not v['target_used_for_fitting'], 'Fit binding/target use')
    check(v['source'] in TILES and v['target'] in TILES and v['source'] != v['target'], 'Fit split')
    fits[p.relative_to(RAW).as_posix()] = v

groups = collections.defaultdict(dict)
integer_matrices = 0
joint_marginals = 0
flow_checks = 0
source_locks = 0
all_checks = []
flowdest = np.zeros((6,6,6,6), np.int64)
for y, r, d, f in itertools.product(range(6), repeat=4):
    flowdest[y,r,d,f] = 8*y + int(r==y) + 2*int(d==y) + 4*int(f==y)
oracle_dest = np.zeros((6,6,6),np.int64)
for y,r,d in itertools.product(range(6),repeat=3):
    oracle_dest[y,r,d]=6*y+(y if r==y or d==y else r)

for i, entry in enumerate(index['records']):
    name = entry['path']
    check(name in payloads and entry['sha256'] == payloads[name]['sha256'], 'Index payload differs: '+name)
    check(entry['bytes'] == payloads[name]['bytes'], 'Index size differs')
    row = read(RAW/name)
    check(row['binding'] == binding, 'Row binding differs')
    check(row['checkpoint_age'] == 16000 and row['segmentation_optimizer_updates'] == 0, 'Evaluation budget')
    check(row['physical_gpu'] in (0,1), 'Unregistered GPU')
    check(row['case']['tile'] in TILES, 'Unregistered evaluation tile')
    check(row['fallback_errors'] == 0, 'Availability fallback error')
    key = cid(row['case'])
    stage = row['stage']
    check(key not in groups[stage], 'Duplicate case within stage')
    lock = row.get('lock')
    if stage in ('D2', 'D3', 'E', 'E_T3'):
        check(lock is not None, 'Missing deployment source lock')
    if lock:
        check(lock['path'] in fits and sha(RAW/lock['path']) == lock['sha256'], 'Fit SHA differs')
        fit = fits[lock['path']]
        check(lock['target'] == row['case']['tile'] == fit['target'] and
              lock['source'] == fit['source'] and lock['source'] != lock['target'], 'Fit directions differ')
        source_locks += 1
    compact = dict(case=row['case'], stage=stage, fallback_errors=0, lock=lock,
                   matrices={}, flows={}, oracle={}, calibration=row['calibration'])
    for scope, systems in row['matrices'].items():
        check(scope in ('full','noboundary'), 'Unexpected scope')
        matrices = {}
        for system, regions in systems.items():
            matrices[system] = {}
            for region, raw in regions.items():
                a = np.asarray(raw)
                check(a.shape == (6,6) and a.dtype.kind in 'iu' and np.all(a>=0), 'Invalid integer CM')
                matrices[system][region] = a.astype(np.int64)
                integer_matrices += 1
            check(np.array_equal(matrices[system]['all'], matrices[system]['missing']+
                                 matrices[system]['observed']), 'ROI CM partition differs')
            check(np.all(matrices[system]['healthy'] <= matrices[system]['observed']), 'Healthy outside observed')
        compact['matrices'][scope] = matrices
        compact['flows'][scope] = {}
        compact['oracle'][scope] = {}
        for system, regions in row['joint'][scope].items():
            compact['flows'][scope][system] = {}
            for region, raw in regions.items():
                j = sparse_counts(raw,1296).reshape(6,6,6,6)
                check(j.shape == (6,6,6,6) and j.dtype.kind in 'iu' and np.all(j>=0), 'Invalid joint counts')
                check(np.array_equal(j.sum((1,2)), matrices[system][region]), 'Candidate joint marginal differs')
                check(np.array_equal(j.sum((2,3)), matrices['rgb'][region]), 'RGB joint marginal differs')
                check(np.array_equal(j.sum((1,3)), matrices['dsm'][region]), 'DSM joint marginal differs')
                joint_marginals += 3
                if region not in compact['oracle'][scope]:
                    oracle=np.zeros(36,np.int64)
                    np.add.at(oracle,oracle_dest.ravel(),j.sum(3).ravel())
                    compact['oracle'][scope][region]=oracle.reshape(6,6)
                f = np.zeros(48, np.int64)
                np.add.at(f, flowdest.ravel(), j.ravel())
                f = f.reshape(6,8)
                check(np.array_equal(f, row['flows'][scope][system][region]), 'Correctness flow differs')
                compact['flows'][scope][system][region] = f
                flow_checks += 1
    # The block diagnostic uses GT classes 0..4; flow rows retain all six classes.
    for system, blocks in row['blocks'].items():
        b = sparse_counts(blocks,24*24*8).reshape(-1,8)
        check(np.array_equal(b.sum(0), compact['flows']['noboundary'][system]['all'][:5].sum(0)),
              'Block/flow total differs')
    groups[stage][key] = compact
    if (i+1) % 256 == 0:
        print('AUDIT_ROWS', i+1, '/', len(index['records']), flush=True)

def make_case(tile, panel, direction, family, realization, ratio, damage):
    return (tile, panel, direction, family, realization, ratio, damage)

expected = set()
for t in TILES:
    expected.add(make_case(t,'clean','none','clean',0,0,'clean'))
    for dr in ('rgb','dsm'):
        for family in FAMILIES:
            for realization in range(1,21):
                for damage in ('zero','down4'):
                    expected.add(make_case(t,'P-U',dr,family,realization,25,damage))
                expected.add(make_case(t,'P-M',dr,family,realization,25,'zero'))
        for ratio in (5,10):
            for realization in range(1,21):
                expected.add(make_case(t,'dose',dr,'pixel',realization,ratio,'zero'))
    for damage in plan['fixed_conditions']:
        if damage != 'clean':
            expected.add(make_case(t,'ordinary','none',damage,0,0,damage))
core = {k for k in expected if k[1] in ('clean','P-U')}
check(len(expected)==1164 and len(core)==642, 'Independent panel construction')
check(set(groups['E']) == expected, 'Endpoint panel incomplete')
check(set(groups['D2']) | set(groups['D3']) == expected and
      not (set(groups['D2']) & set(groups['D3'])), 'D2/D3 panel differs')
smoke_core = {k for k in groups['SMOKE'] if k[1] in ('clean','P-U')}
check(set(groups['D1']) | smoke_core == core, 'D1/smoke reuse differs')
check(not(set(groups['D1']) & smoke_core), 'Smoke repeated in D1')
end = list(groups['E'].values())
deployment = list(groups['D2'].values()) + list(groups['D3'].values())

bridge_fields = 0
for other in deployment:
    current = groups['E'][cid(other['case'])]
    for scope in ('full','noboundary'):
        for system in ('rgb','dsm','average','B0','B2'):
            for region in REGIONS:
                check(np.array_equal(current['matrices'][scope][system][region],
                                     other['matrices'][scope][system][region]), 'Cross-stage original CM drift')
                bridge_fields += 1

def score(rows, system, panel='P-U', direction=None, tile=None, region='all', damage=None, family=None):
    pooled = {}
    for row in rows:
        c = row['case']
        if c['panel'] != panel or (direction and c['direction'] != direction) or (tile and c['tile'] != tile):
            continue
        if damage and c['damage'] != damage:
            continue
        if family and c['family'] != family:
            continue
        key = condition(c)
        a = (row['oracle']['noboundary'][region] if system=='oracle' else
             row['matrices']['noboundary'][system][region])
        if key not in pooled:
            pooled[key] = a.copy()
        else:
            pooled[key] += a
    values = [metric(a) for a in pooled.values()]
    values = [v for v in values if v is not None]
    return float(np.mean(values)) if values else None

def gate(rows, name, reference='reference'):
    def delta(panel='P-U', dr=None, tile=None, region='all', ref=reference, damage=None, family=None):
        a = score(rows,name,panel,dr,tile,region,damage,family)
        b = score(rows,ref,panel,dr,tile,region,damage,family)
        return None if a is None or b is None else a-b
    checks = dict(P_U_gain=delta(), rgb_fault_gain=delta(dr='rgb'),
                  positive_RGB_fault_tiles={t:delta(dr='rgb',tile=t) for t in TILES})
    protection = {}
    for panel, dr, region in (('clean',None,'all'),('P-U','dsm','all'),('P-U',None,'healthy')):
        for t in TILES:
            for ref in (reference,'rgb'):
                protection['/'.join((panel,dr or 'both',region,t,ref))] = delta(panel,dr,t,region,ref)
    checks['protections'] = protection
    worst = []
    for dr, family, damage, ref in itertools.product(('rgb','dsm'),FAMILIES,('zero','down4'),(reference,'rgb')):
        v = delta(dr=dr,family=family,damage=damage,ref=ref)
        if v is not None:
            worst.append(v)
    checks['worst_family_damage'] = min(worst)
    checks['fallback_exact'] = all(r['fallback_errors']==0 for r in rows)
    accepted = (checks['P_U_gain'] >= .3 and checks['rgb_fault_gain'] >= .5 and
                all(x>0 for x in checks['positive_RGB_fault_tiles'].values()) and
                all(x>=-.2 for x in protection.values()) and min(worst)>=-.5 and checks['fallback_exact'])
    return dict(accepted=bool(accepted),candidate=name,reference=reference,checks=checks,
                interpretation='development gate on two reused Val2 tiles, seed42; no independent test claim')

rebuilt = {name:{p:{region:score(end,name,p,region=region) for region in REGIONS} for p in PANELS}
           for name in sorted(end[0]['matrices']['noboundary'])}
close(rebuilt,summary['results'],'summary/results')
d0=read(RAW/'analysis/D0.json')['decomposition']
d0_rebuilt={}
for dr in ('rgb','dsm'):
    best=max(score(end,'rgb',direction=dr),score(end,'dsm',direction=dr))
    oracle=score(end,'oracle',direction=dr)
    b2=score(end,'B2',direction=dr)
    d0_rebuilt[dr]=dict(oracle_minus_best_fixed=oracle-best,oracle_minus_B2=oracle-b2,B2_minus_best_fixed=b2-best)
close(d0_rebuilt,d0,'D0/current-expert-joint-rebuild')
for name in ('calibrated','probe'):
    close(gate(deployment,name),summary['deployment_gate'][name],'gate/'+name)
check(summary['trained_heads']==['T0'] and summary['total_optimizer_updates']==8000 and
      summary['old_expert_optimizer_updates']==0 and summary['signal_gate'] is None,
      'Training dispatch/budget differs')
check(not summary['deployment_gate']['allow_paired_heads'], 'Unexpected head gate')

parameters = read(RAW/'jobs/T0/parameters.json')
completion = read(RAW/'jobs/T0/complete.json')
check(parameters['trainable']==8 and parameters['experts_frozen'] and parameters['endpoint']==8000, 'T0 settings')
check(parameters['initial_state_sha256'] == completion['initial_state_sha256'] ==
      '4a3c4bafb567b46b71c30c4577b4b6b96906250d74ea14d2cf477048456d0a69', 'T0 initial state')
check(completion['binding']==binding and completion['stream_verified'], 'T0 completion binding')
for file,key in (('batch_hashes.jsonl','stream_sha256'),('endpoint_weights.json','weights_sha256'),
                 ('trajectory_04000_weights.json','trajectory_weights_sha256')):
    check(sha(RAW/'jobs/T0'/file)==completion[key], 'T0 file SHA differs: '+file)
batch = [json.loads(line) for line in (RAW/'jobs/T0/batch_hashes.jsonl').read_text().splitlines()]
check([r['step'] for r in batch]==list(range(1,8001)), 'T0 batch sequence incomplete')
trajectory = [json.loads(line) for line in (RAW/'jobs/T0/trajectory.jsonl').read_text().splitlines()]
check([r['step'] for r in trajectory] == [1]+list(range(20,8001,20)), 'T0 trajectory cadence')
check(all(math.isfinite(r['loss']) and r['optimizer_updates']==r['step'] for r in trajectory), 'T0 trajectory invalid')

paired = np.array([score([r for r in end if r['case']['realization']==i],'T0')-
                   score([r for r in end if r['case']['realization']==i],'reference') for i in range(1,21)])
rng=np.random.default_rng(20261014)
interval=np.quantile(paired[rng.integers(0,20,(5000,20))].mean(1),[.025,.975]).tolist()
close(float(paired.mean()),summary['paired_mask_intervals']['T0']['mean'],'paired/mean')
close(interval,summary['paired_mask_intervals']['T0']['interval95'],'paired/interval')

details=[]
for system,panel,dr,tile,damage,region in itertools.product(
        ('rgb','dsm','reference','calibrated','probe','stump','B0','B2','T0_4000','T0'),
        ('clean','P-U'),(None,'rgb','dsm'),(None,)+TILES,(None,'zero','down4'),('all','missing','healthy')):
    if panel=='clean' and (dr is not None or damage is not None or region=='missing'):
        continue
    value=score(end,system,panel,dr,tile,region,damage)
    if value is not None:
        details.append(dict(system=system,panel=panel,direction=dr,tile=tile,damage=damage,region=region,value=value))

flows=[]
for system,dr,tile,damage,region in itertools.product(('probe','stump','T0','B0'),('rgb','dsm'),TILES,('zero','down4'),('all','missing','healthy')):
    chosen=[r for r in end if r['case']['panel']=='P-U' and r['case']['direction']==dr and
            r['case']['tile']==tile and r['case']['damage']==damage]
    f=sum((r['flows']['noboundary'][system][region][:5] for r in chosen),np.zeros((5,8),np.int64))
    harmed=int(f[:,[1,3]].sum());rescued=int(f[:,[4,6]].sum())
    rc=int(f[:,[1,3,5,7]].sum());opportunity=int(f[:,[2,6]].sum())
    flows.append(dict(system=system,direction=dr,tile=tile,damage=damage,region=region,
                      valid=int(f.sum()),harmed=harmed,rescued=rescued,net=rescued-harmed,
                      RGB_correct_harmed_fraction=harmed/rc if rc else None,
                      DSM_unique_correct=opportunity))

calibration=[]
for row in end:
    if row['case']['panel']!='clean':
        continue
    for name,v in row['calibration'].items():
        if not isinstance(v,dict) or 'nll_sum' not in v:
            continue
        count=np.asarray(v['count'])[:5].sum()
        hist=np.asarray(v['histogram'])[:5].sum(0)
        ece=float(np.abs(hist[:,1]-hist[:,2]).sum()/count)
        calibration.append(dict(tile=row['case']['tile'],expert=name,count=int(count),
                                NLL=float(np.asarray(v['nll_sum'])[:5].sum()/count),
                                Brier=float(np.asarray(v['brier_sum'])[:5].sum()/count),ECE15=ece))

result=dict(status='COUNTS_AND_BINDINGS_VERIFIED_NOT_A_TRAINING_RERUN',binding=binding,
            stage_records={k:len(v) for k,v in groups.items()},validated_records=len(index['records']),
            integer_matrices_checked=integer_matrices,joint_marginals_checked=joint_marginals,
            correctness_flows_checked=flow_checks,source_locks_checked=source_locks,
            cross_stage_original_CM_fields=bridge_fields,summary_rebuilt=True,deployment_gates_rebuilt=True,
            paired_mask_interval_rebuilt=True,T0_batch_rows=len(batch),T0_trajectory_rows=len(trajectory),
            D0_empirical_decomposition_rebuilt=True,
            actual_server_pth_weights_rehashed_locally=False,training_rerun=False,
            old_B0_raw_batch_stream_independently_compared=False)
(OUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
(OUT/'recomputed_summary.json').write_text(json.dumps(rebuilt,indent=2),encoding='utf-8')
(OUT/'diagnostic_gates.json').write_text(json.dumps({n:gate(end,n) for n in ('rgb','reference','T0','T0_4000','stump')},indent=2),encoding='utf-8')
(OUT/'detailed_scores.json').write_text(json.dumps(details,indent=2),encoding='utf-8')
(OUT/'correctness_flows.json').write_text(json.dumps(flows,indent=2),encoding='utf-8')
(OUT/'clean_calibration.json').write_text(json.dumps(calibration,indent=2),encoding='utf-8')
(OUT/'D0_recomputed.json').write_text(json.dumps(d0_rebuilt,indent=2),encoding='utf-8')
(OUT/'T0_trajectory_summary.json').write_text(json.dumps({'first':trajectory[0],'last':trajectory[-1],
                 'loss_min':min(x['loss'] for x in trajectory),'loss_max':max(x['loss'] for x in trajectory)},indent=2),encoding='utf-8')
print('INDEPENDENT_AUDIT_OK',json.dumps(result),flush=True)
for n in ('T0','stump'):
    g=gate(end,n)
    print('DIAGNOSTIC_GATE',n,json.dumps(g),flush=True)
