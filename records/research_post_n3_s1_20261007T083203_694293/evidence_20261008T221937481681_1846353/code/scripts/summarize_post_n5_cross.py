"""Hash/count checks and fixed problem screens, never dispatch training."""
import argparse
from pathlib import Path
import numpy as np
from post_n5_cross_common import *
from post_d30_evaluation import metric,decode_joint
def screens(data,p):
    result={}
    for factor,better,control in [('output','A1B1C0','A1B1C1'),('feature','A1B0C0','A1B1C0')]:
        directions={}
        for direction in ('rgb','dsm'):
            rows={}
            for name in ('N1-2','N2-0','N2-3'):
                s=data[name];key=lambda path:direction+'_known_missing_'+path
                gains={tile:100*(metric(s['tiles'][key(better)][tile])['mIoU_fg5']-metric(s['tiles'][key(control)][tile])['mIoU_fg5']) for tile in p['data']['validation']}
                gain=100*(s['pooled'][key(better)]['mIoU_fg5']-s['pooled'][key(control)]['mIoU_fg5'])
                rows[name]=dict(pooled_gain_pp=gain,tile_gains_pp=gains,passed=gain>=p['E4']['gap_pp']-1e-9 and all(v>0 for v in gains.values()))
            directions[direction]=rows
        passed=all(directions['rgb'][m]['passed'] for m in p['E4']['gate_models'])
        result[factor]=dict(trigger=bool(passed),direction='rgb',directions=directions,better=better,control=control)
    return result
def validate_metrics(row):
    for scope in ('full','noboundary'):
        s=row['scopes'][scope]
        for n,rgs in s['metrics'].items():
            for region,m in rgs.items():
                arr=np.asarray(m['cm'])
                if arr.shape!=(6,6) or not np.issubdtype(arr.dtype,np.integer) or (arr<0).any():raise RuntimeError('invalid integer CM')
                if metric(arr)!=m:raise RuntimeError('derived raw metrics differ')
        for region,j in s['joint'].items():
            a=decode_joint(j)
            if (a<0).any() or not np.array_equal(a.sum((1,2)),s['metrics']['candidate'][region]['cm']) or not np.array_equal(a.sum((2,3)),s['metrics']['rgb'][region]['cm']) or not np.array_equal(a.sum((1,3)),s['metrics']['dsm'][region]['cm']):raise RuntimeError('joint marginal differs')
def summarize(base):
    p=validate(read(base/'plan.json'));data={};bindings={};records_checked=0
    for job in p['jobs']:
        j=job['id'];c=complete_job(base,j,p);folder=base/'jobs'/j;s=read(folder/'summary.json')
        if s['binding']!=c['signature']:raise RuntimeError('summary signature differs')
        expected={d+'_'+case+'_'+path for d in p['E4']['directions'] for case in p['E4']['cases'] for path in p['paths']}
        if set(s['records'])!=expected or set(s['tiles'])!=expected or set(s['pooled'])!=expected:raise RuntimeError('case set differs')
        for key,ts in s['records'].items():
            if set(ts)!=set(p['data']['validation']):raise RuntimeError('tile set differs')
            for tile,ref in ts.items():
                path=within(ref['path'],folder);row=read(path)
                if sha(path)!=ref['sha256'] or row['binding']!=s['binding'] or row['condition']!=key or row['tile']!=tile:raise RuntimeError('case binding differs')
                validate_metrics(row)
                if row['path']=='A1B1C1' and (not row.get('original_E2_parity') or not all(x['array_equal'] for x in row['original_E2_parity'].values())):raise RuntimeError('original E2 parity absent')
                if row['path'][-1]=='1' and not all(row['fallback_logits_equal_own'].values()):raise RuntimeError('hard fallback parity absent')
                if row['scopes']['noboundary']['metrics']['candidate']['all']['cm']!=s['tiles'][key][tile]:raise RuntimeError('summary CM differs')
                for name,digest in row['predictions'].items():
                    if sha(path.parent/name/(tile+'.npy'))!=digest:raise RuntimeError('prediction changed')
                records_checked+=1
            if metric(sum((np.asarray(cm,np.int64) for cm in s['tiles'][key].values()),np.zeros((6,6),np.int64)))!=s['pooled'][key]:raise RuntimeError('pooled CM differs')
        for direction in p['E4']['directions']:
            for case in p['E4']['cases']:
                for tile in p['data']['validation']:
                    rr=[read(s['records'][direction+'_'+case+'_'+path][tile]['path']) for path in p['paths']]
                    if any(r['physical_input_sha256']!=rr[0]['physical_input_sha256'] or r['reported_mask_sha256']!=rr[0]['reported_mask_sha256'] for r in rr):raise RuntimeError('physical/report binding differs across switches')
                    for a in (0,1):
                        for b in (0,1):
                            pair=[read(s['records'][f'{direction}_{case}_A{a}B{b}C{cc}'][tile]['path']) for cc in (0,1)]
                            if any(pair[0]['first_batch_trace'][k]!=pair[1]['first_batch_trace'][k] for k in ('expert_rgb','expert_dsm','rgb_feature','dsm_feature','raw_logits')):raise RuntimeError('C changed upstream graph')
        # Physical zero blocks: A alone must change nothing, for every B/C.
        for direction in p['E4']['directions']:
            for b in (0,1):
                for cc in (0,1):
                    ks=[f'{direction}_known_missing_A{a}B{b}C{cc}' for a in (0,1)]
                    for tile in p['data']['validation']:
                        rs=[read(s['records'][k][tile]['path']) for k in ks]
                        if rs[0]['physical_input_sha256']!=rs[1]['physical_input_sha256'] or rs[0]['reported_mask_sha256']!=rs[1]['reported_mask_sha256'] or rs[0]['predictions']!=rs[1]['predictions']:raise RuntimeError('A zero-input negative control differs')
                        for n in ('expert_rgb','expert_dsm','rgb_feature','dsm_feature','raw_logits','output_logits'):
                            if rs[0]['first_batch_trace'][n]!=rs[1]['first_batch_trace'][n]:raise RuntimeError('A zero-input intermediate negative control differs')
        data[job['model']]=s;bindings[j]=sha(folder/'complete.json')
    gates=screens(data,p);boundary=read(base/'boundary_screen.json')
    eligible=[f for f,yes in [('R1',gates['output']['trigger']),('N3',boundary['N3_problem_trigger']),('S1',gates['feature']['trigger'])] if yes]
    # At most two families. Selection is prospective priority, not highest metric.
    selected=eligible[:2]
    result=dict(E4=gates,N3_problem_trigger=boundary['N3_problem_trigger'],eligible_families=eligible,
        recommended_next_families=selected,max_new_training_jobs=sum({'R1':4,'N3':5,'S1':4}[f] for f in selected),
        automatic_training=False,training_protocol_status='not implemented; review bound diagnostics before freezing training package',
        records_checked=records_checked,complete_bindings=bindings,plan_sha256=sha(base/'plan.json'),
        preparation_sha256=sha(base/'cpu_preparation_complete.json'),optimizer_updates=0,test6_loaded=False,independent_final_loaded=False,observed_at=now())
    write(base/'cross_screen.json',result);print('CROSS_SCREEN',gates['output']['trigger'],gates['feature']['trigger'],boundary['N3_problem_trigger'],'NEXT',selected,flush=True)
    return result
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();summarize(a.directory)
if __name__=='__main__':main()
