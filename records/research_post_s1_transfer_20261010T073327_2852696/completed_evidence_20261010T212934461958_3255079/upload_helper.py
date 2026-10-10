"""Read-only completed-job evidence snapshot while GPU0 queue continues."""
import argparse,hashlib,json,os,subprocess,sys
from datetime import datetime
from pathlib import Path
def digest(raw):return hashlib.sha256(raw).hexdigest()
def json_bytes(obj):return (json.dumps(obj,indent=2,allow_nan=False)+'\n').encode()
def safe(path,parent):
    p=Path(path).resolve();p.relative_to(Path(parent).resolve());return p
def read(path):return json.loads(Path(path).read_bytes())
def collect(root,base,accept,source_binding=None):
    plan=read(base/'plan.json');queue_raw=(base/'queue_status.json').read_bytes();queue=json.loads(queue_raw)
    if queue.get('CPU')!='COMPLETE':raise RuntimeError('preparation not complete; retry upload after CPU preparation finishes')
    order=[j['id'] for j in plan['jobs']]
    if set(order)!=set(queue['jobs']):raise RuntimeError('registered membership differs')
    included=[j for j in order if queue['jobs'][j]['status']=='COMPLETE']
    if not included:raise RuntimeError('no fully completed transfer cells yet; no partial worker evidence uploaded')
    data={'queue_status.json':queue_raw};artifacts=[];completed={}
    def add(path,key=None):
        path=safe(path,base);raw=path.read_bytes();raw.decode('utf-8')
        if path.suffix=='.json':json.loads(raw)
        name=key or path.relative_to(base).as_posix()
        if name in data and data[name]!=raw:raise RuntimeError('conflicting evidence '+name)
        data[name]=raw
    def predictions(path,row):
        if 'predictions' not in row or 'tile' not in row:return
        for name,h in row['predictions'].items():
            arr=safe(path.parent/name/(row['tile']+'.npy'),base)
            if not arr.is_file():raise RuntimeError('completed prediction missing '+str(arr))
            artifacts.append(dict(path=str(arr),bytes=arr.stat().st_size,sha256=h,storage='server_only',sha_source='accepted completed JSON; body not rehashed in light upload'))
    for name in ('plan.json','execution_commit.txt','code_manifest.json','cpu_checks.log','preparation_complete.json','mask_manifest.json','reference_index.json','predecessor_acceptance.json'):
        add(base/name)
    for name in ('registration_observation.json','launch.json','controller.pid'):
        if (base/name).is_file():add(base/name)
    for name,h in read(base/'code_manifest.json')['files'].items():
        path=safe(base/'code'/name,base/'code')
        if digest(path.read_bytes())!=h:raise RuntimeError('source snapshot changed '+name)
        add(path)
    prep=read(base/'preparation_complete.json')
    if digest((base/'reference_index.json').read_bytes())!=prep['reference_index_sha256']:raise RuntimeError('reference index changed')
    for row in read(base/'reference_index.json').values():
        path=safe(row['path'],base)
        if digest(path.read_bytes())!=row['sha256']:raise RuntimeError('embedded reference changed')
        add(path)
    for rows in read(base/'mask_manifest.json')['tiles'].values():
        for row in rows.values():
            path=safe(row['path'],base)
            if digest(path.read_bytes())!=row['sha256']:raise RuntimeError('mask changed')
            artifacts.append(dict(path=str(path),bytes=path.stat().st_size,sha256=row['sha256'],storage='server_only'))
    # Membership is frozen before scanning. RUNNING/PENDING paths are never opened.
    for j in included:
        folder=base/'jobs'/j;c=accept(base,j,plan)
        completed[j]=dict(complete_sha256=digest((folder/'complete.json').read_bytes()),artifacts=c['artifacts'])
        for path in sorted(folder.rglob('*.json')):
            row=read(path);add(path);predictions(path,row)
        logfile=queue['jobs'][j].get('log_path')
        if logfile and Path(logfile).is_file():add(safe(logfile,base))
        for name,h in c['artifacts'].items():
            path=safe(folder/name,folder)
            if path.suffix=='.pth':artifacts.append(dict(path=str(path),bytes=path.stat().st_size,sha256=h,storage='server_only'))
    final=queue['status']=='TRANSFER_COMPLETE_AWAITING_REVIEW' and len(included)==len(order)
    if final:
        path=base/'transfer_screen.json'
        if digest(path.read_bytes())!=queue['screen_sha256']:raise RuntimeError('final screen changed')
        add(path)
    state=dict(captured_at=datetime.now().astimezone().isoformat(),queue_last_observed=queue['observed_at'],
        execution_commit=plan['execution_commit'],server_directory=str(base),included_jobs=included,
        excluded_jobs={j:queue['jobs'][j]['status'] for j in order if j not in included},completed_bindings=completed,
        CPU_complete=True,core_training_complete=len(included),core_training_total=len(order),
        fixed_candidate='T7',fixed_candidate_complete='T7' in included,scientific_final_gate_available=final,
        membership_frozen_at_queue_snapshot=True,snapshot_mutates_science_files=False,training_launched=False,
        GPU_tasks_launched=False,unfinished_job_records_read=False)
    data['completed_snapshot.json']=json_bytes(state)
    data['server_artifact_index.json']=json_bytes(dict(server_directory=str(base),artifacts=artifacts,prediction_bodies_uploaded=False))
    return data,state

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--commit',required=True,help='published upload helper commit, not scientific execution commit')
    ap.add_argument('--prepare-only',action='store_true');args=ap.parse_args()
    root=safe(args.root,'/home/jovyan/zzx');base=safe(args.directory,root/'records')
    if not base.name.startswith('research_post_s1_transfer_'):raise ValueError('unexpected source directory')
    sys.path[:0]=[str(base/'code'),str(base/'code/scripts')]
    from post_s1_transfer_common import validate,verify_snapshot,accept_worker
    from upload_post_s1_transfer_records import encode_record,decode_record,git,RECORD_ENCODING
    validate(read(base/'plan.json'));verify_snapshot(base)
    # A separate upload lock never locks/stops the training controller/workers.
    import fcntl
    with (base/'completed_upload.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        helper_commit=git(root,'rev-parse',args.commit+'^{commit}',capture=True).strip()
        helper_bytes=subprocess.check_output(['git','-C',str(root),'show',helper_commit+':scripts/upload_post_s1_transfer_completed_records.py'])
        if Path(__file__).read_bytes()!=helper_bytes:raise RuntimeError('upload helper code differs from bound commit')
        original,state=collect(root,base,accept_worker)
        original['upload_helper.py']=helper_bytes
        original['upload_helper_binding.json']=json_bytes(dict(commit=helper_commit,sha256=digest(helper_bytes),
            scientific_execution_commit=read(base/'plan.json')['execution_commit']))
        data={};source_files=[]
        for name,raw in original.items():
            packed=encode_record(raw) if name.endswith('.json') else raw
            if packed!=raw and decode_record(packed)!=raw:raise RuntimeError('record roundtrip failed')
            if len(packed)>80*1024**2:raise RuntimeError('oversized encoded light record '+name)
            data[name]=packed;source_files.append(dict(path=name,original_bytes=len(raw),original_sha256=digest(raw),encoded=packed!=raw))
        size=sum(map(len,data.values()))
        report=dict(**state,source_bytes=sum(map(len,original.values())),upload_bytes=size,files=len(data),limit_bytes=512*1024**2)
        stamp=datetime.now().strftime('%Y%m%dT%H%M%S%f')+'_'+str(os.getpid())
        report_path=base/('completed_upload_preparation_'+stamp+'.json');report_path.write_bytes(json_bytes(report))
        print('COMPLETED_UPLOAD_PREPARED',report_path,'JOBS='+','.join(state['included_jobs']),'FILES='+str(len(data)),'UPLOAD_BYTES='+str(size),flush=True)
        if size>512*1024**2:raise RuntimeError('oversized light snapshot; preparation report preserved')
        if args.prepare_only:return
        origin=git(root,'remote','get-url','origin',capture=True).strip()
        if origin not in ('https://github.com/66322/remote_sensing_frequency.git','https://github.com/66322/remote_sensing_frequency','git@github.com:66322/remote_sensing_frequency.git'):raise RuntimeError('unexpected Git origin')
        branch='rebuild-v1-protocol-20260915';git(root,'fetch','origin',branch);parent=git(root,'rev-parse','FETCH_HEAD',capture=True).strip()
        worktree=base/('github_completed_upload_'+stamp);git(root,'worktree','add','--detach',str(worktree),parent)
        relative=Path('records')/base.name/('completed_evidence_'+stamp);target=worktree/relative;target.mkdir(parents=True)
        for name,raw in data.items():
            path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as f:f.write(raw)
        upload_manifest=dict(created_at=state['captured_at'],server_directory=str(base),base_commit=parent,
            snapshot_kind='completed_jobs_while_queue_continues',completed_snapshot=state,
            files=[dict(path=n,bytes=len(v),sha256=digest(v)) for n,v in data.items()],source_files=source_files,
            source_total_bytes=sum(map(len,original.values())),upload_total_bytes=size,
            record_encoding=RECORD_ENCODING,predictions_and_checkpoints_uploaded=False,training_launched=False,
            originals_preserved_on_server=True,upload_helper_commit=helper_commit,
            decoder_script='scripts/decode_rebuild_light_record.py')
        (target/'upload_manifest.json').write_bytes(json_bytes(upload_manifest))
        paths=[(relative/name).as_posix() for name in data]+[(relative/'upload_manifest.json').as_posix()]
        git(worktree,'add','-f','--',*paths)
        git(worktree,'-c','user.name=66322','-c','user.email=57258129+66322@users.noreply.github.com','commit','-m','records: snapshot completed Post-S1 transfer jobs while GPU0 queue continues')
        commit=git(worktree,'rev-parse','HEAD',capture=True).strip();git(worktree,'push','origin','HEAD:refs/heads/'+branch)
        print('COMPLETED_GITHUB_COMMIT='+commit)
        print('COMPLETED_GITHUB_RECORDS=https://github.com/66322/remote_sensing_frequency/tree/'+commit+'/'+relative.as_posix())
        print('COMPLETED_INCLUDED_JOBS='+','.join(state['included_jobs']))
        print('COMPLETED_EXCLUDED_JOBS='+json.dumps(state['excluded_jobs'],sort_keys=True))
if __name__=='__main__':main()

