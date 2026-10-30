"""Read-only completed-job evidence snapshot while GPU0 queue continues."""
import argparse,hashlib,json,os,subprocess,sys
from datetime import datetime
from pathlib import Path
def digest(raw):return hashlib.sha256(raw).hexdigest()
def json_bytes(obj):return (json.dumps(obj,indent=2,allow_nan=False)+'\n').encode()
def safe(path,parent):
    p=Path(path).resolve();p.relative_to(Path(parent).resolve());return p
def read(path):return json.loads(Path(path).read_bytes())
def collect(root,base,accept,source_binding):
    # Capture membership ONCE. Never enumerate a RUNNING job, even if it
    # changes to COMPLETE while the immutable completed evidence is collected.
    plan=read(base/'plan.json');queue_raw=(base/'queue_status.json').read_bytes();queue=json.loads(queue_raw)
    if queue.get('CPU')!='COMPLETE':raise RuntimeError('D0 not complete')
    order=['D1']+[j['id'] for j in plan['jobs']]+['E']
    included=[j for j in order if queue['jobs'][j]['status']=='COMPLETE']
    if 'D1' not in included:raise RuntimeError('D1 must be complete for partial analysis')
    data={'queue_status.json':queue_raw};artifacts=[];completed={}
    def add(path,key=None):
        path=Path(path);safe(path,root)
        raw=path.read_bytes();raw.decode('utf-8')
        name=key or path.relative_to(base).as_posix()
        if path.suffix=='.json':json.loads(raw)
        if name in data and data[name]!=raw:raise RuntimeError('conflicting evidence key '+name)
        data[name]=raw
    def index_predictions(record_path,row):
        if 'predictions' not in row or 'tile' not in row:return
        for name,sha256 in row['predictions'].items():
            path=safe(record_path.parent/name/(row['tile']+'.npy'),root)
            if not path.is_file():raise RuntimeError('completed prediction missing '+str(path))
            artifacts.append(dict(path=str(path),bytes=path.stat().st_size,sha256=sha256,
                sha_source='immutable completed JSON; array body not rehashed by this light snapshot',storage='server_only'))
    required=['plan.json','execution_commit.txt','code_manifest.json','cpu_checks.log','preparation_complete.json',
        'mask_manifest.json','d0_index.json','source_acceptance.json']
    optional=['registration_acceptance.json','predecessor_acceptance.json','preparation_progress.json','launch.json','controller.pid']
    for name in required:add(base/name)
    for name in optional:
        if (base/name).is_file():add(base/name)
    manifest=read(base/'code_manifest.json')
    for name,sha256 in manifest['files'].items():
        path=safe(base/'code'/name,base/'code')
        raw=path.read_bytes()
        if digest(raw)!=sha256:raise RuntimeError('science snapshot changed '+name)
        add(path)
    for stage in ('D0','R0_U','R0_ordinary'):
        folder=base/stage
        if not folder.is_dir():raise RuntimeError('completed CPU stage missing '+stage)
        for path in sorted(folder.rglob('*.json')):
            row=read(path);add(path);index_predictions(path,row)
    for j in included:
        c=accept(base,j,plan);folder=base/'jobs'/j
        completed[j]=dict(complete_sha256=digest((folder/'complete.json').read_bytes()),artifacts=c['artifacts'])
        for path in sorted(folder.rglob('*.json')):
            row=read(path);add(path);index_predictions(path,row)
        # Finished worker logs are closed by the controller before COMPLETE.
        logfile=queue['jobs'][j].get('log_path')
        if logfile and Path(logfile).is_file():add(safe(logfile,base))
        for name,sha256 in c['artifacts'].items():
            path=safe(folder/name,folder)
            if path.suffix=='.pth':artifacts.append(dict(path=str(path),bytes=path.stat().st_size,sha256=sha256,storage='server_only'))
    # Existing baseline is required now, so later analysis does not depend
    # on downloading an unrelated large historical bundle.
    binding,_,_=source_binding(root,'S1-0',checkpoint=False)
    source=root/'records/research_post_n3_s1_20261007T083203_694293';folder=source/'jobs/S1-0'
    add(folder/'complete.json','references/S1-0/complete.json')
    if (folder/'model_capacity.json').exists():add(folder/'model_capacity.json','references/S1-0/model_capacity.json')
    for tag in ('evaluation','fixed8000','support_evaluation','support_fixed8000'):
        if not (folder/tag/'summary.json').exists():raise RuntimeError('baseline summary missing '+tag)
        for path in sorted((folder/tag).rglob('*.json')):
            row=read(path);add(path,'references/S1-0/'+path.relative_to(folder).as_posix());index_predictions(path,row)
    masks=read(base/'mask_manifest.json')
    for rows in masks['tiles'].values():
        for row in rows.values():
            path=safe(row['path'],base)
            if digest(path.read_bytes())!=row['sha256']:raise RuntimeError('fixed mask changed')
            artifacts.append(dict(path=str(path),bytes=path.stat().st_size,sha256=row['sha256'],storage='server_only'))
    state=dict(captured_at=datetime.now().astimezone().isoformat(),queue_last_observed=queue['observed_at'],
        execution_commit=plan['execution_commit'],server_directory=str(base),included_jobs=included,
        excluded_jobs={j:queue['jobs'][j]['status'] for j in order if j not in included},
        completed_bindings=completed,source_baseline_binding=binding,CPU_complete=True,
        core_training_complete=len([j for j in included if j.startswith('P')]),core_training_total=10,
        E_complete='E' in included,scientific_final_gate_available='E' in included and all(j['id'] in included for j in plan['jobs']),
        membership_frozen_at_queue_snapshot=True,snapshot_mutates_science_files=False,
        training_launched=False,GPU_tasks_launched=False,unfinished_job_records_read=False)
    data['completed_snapshot.json']=json_bytes(state)
    data['server_artifact_index.json']=json_bytes(dict(server_directory=str(base),artifacts=artifacts,
        checkpoint_digests_checked_by_complete_acceptance=True,prediction_bodies_uploaded=False,
        prediction_bodies_rehashed_by_this_snapshot=False))
    return data,state
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--commit',required=True,help='published upload helper commit, not scientific execution commit')
    ap.add_argument('--prepare-only',action='store_true');args=ap.parse_args()
    root=safe(args.root,'/home/jovyan/zzx');base=safe(args.directory,root/'records')
    if not base.name.startswith('research_post_s1_support_'):raise ValueError('unexpected source directory')
    sys.path[:0]=[str(base/'code'),str(base/'code/scripts')]
    from post_s1_support_common import validate,verify_snapshot,accept_worker,source_binding
    from upload_post_s1_support_records import encode_record,decode_record,git,RECORD_ENCODING
    validate(read(base/'plan.json'));verify_snapshot(base)
    # A separate upload lock never locks/stops the training controller/workers.
    import fcntl
    with (base/'completed_upload.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        helper_commit=git(root,'rev-parse',args.commit+'^{commit}',capture=True).strip()
        helper_bytes=subprocess.check_output(['git','-C',str(root),'show',helper_commit+':scripts/upload_post_s1_completed_records.py'])
        if Path(__file__).read_bytes()!=helper_bytes:raise RuntimeError('upload helper code differs from bound commit')
        original,state=collect(root,base,accept_worker,source_binding)
        original['upload_helper.py']=helper_bytes
        original['upload_helper_binding.json']=json_bytes(dict(commit=helper_commit,sha256=digest(helper_bytes),
            scientific_execution_commit=read(base/'plan.json')['execution_commit']))
        data={};source_files=[]
        for name,raw in original.items():
            packed=encode_record(raw) if name.endswith(('.json','.log')) else raw
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
        git(worktree,'-c','user.name=66322','-c','user.email=57258129+66322@users.noreply.github.com','commit','-m','records: snapshot completed Post-S1 jobs while GPU0 queue continues')
        commit=git(worktree,'rev-parse','HEAD',capture=True).strip();git(worktree,'push','origin','HEAD:refs/heads/'+branch)
        print('COMPLETED_GITHUB_COMMIT='+commit)
        print('COMPLETED_GITHUB_RECORDS=https://github.com/66322/remote_sensing_frequency/tree/'+commit+'/'+relative.as_posix())
        print('COMPLETED_INCLUDED_JOBS='+','.join(state['included_jobs']))
        print('COMPLETED_EXCLUDED_JOBS='+json.dumps(state['excluded_jobs'],sort_keys=True))
if __name__=='__main__':main()

