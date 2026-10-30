"""Publish server-checked compact results. Existing authentication only; no Git fetch."""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
import phase3_m2_common as c

REPO='66322/remote_sensing_frequency'
BRANCH='rebuild-v1-protocol-20260915'
READY_STATUS_BLOB='17ccc8ae45eeb4e82bf404532ccefc89ae97b324'

def may_refresh_shared(blob,text,run_name):
    if blob==READY_STATUS_BLOB:return True
    # A historical mention of this run in a later experiment is insufficient.
    return any(line.startswith('运行：`'+run_name+'`；状态：') for line in text.splitlines()[:6])

def shared_documents(base,summary,prefix):
    """Result pointers, not a claim of new-method success or live GPU state."""
    gate_text='；'.join(k+'='+str(v) for k,v in summary['gates'].items())
    next_action=('A已满足本轮推进规则；先冻结B反向执行合同，尚未自动启动B/C。' if summary['advance_reverse'] else
        '按各假设和失败门禁收束本轮；不自动调参、延长训练或扩骨干。' if summary['status']=='COMPLETE_SERVER_CHECKED' else
        '记录不完整；先核对具体失败回执，不自动重训或覆盖旧run。')
    documents={}
    for path,title in [('docs/START_HERE.md','共享入口'),('docs/current/PROJECT_STATUS.md','当前状态'),
            ('docs/current/HANDOFF.md','当前交接'),('docs/current/NEXT_EXPERIMENT.md','下一步'),('docs/current/RESEARCH_DECISION.md','当前研究决定')]:
        relative='../' if path=='docs/START_HERE.md' else '../../'
        target=relative+prefix
        documents[path]=(f'# {title}：M2-A服务器结果已归档\n\n'
            f'运行：`{base.name}`；状态：`{summary["status"]}`。\n\n'
            f'先读[结果报告]({target}/REPORT.md)、[汇总表]({target}/metrics.csv)、[完整门禁]({target}/gates.json)和[原件索引]({target}/server_evidence_index.json)。\n\n'
            f'完成训练{summary["jobs_complete"]}/108，更新{summary["optimizer_updates"]}；评价{summary["evaluated_cases"]}/{summary["expected_cases"]}。\n\n'
            f'门禁：{gate_text}。\n\n{next_action}\n\n'
            '结果是Fit12同城开发CV，不构成独立城市泛化、统计显著性或新颖性的证明。M1幅度路线关闭；Val2/Test6/held4/final与另一篇点云不进入本轮。\n\n'
            f'服务器目录：`{base}`。逐mask原件、完整辅助统计、端点和轨迹留服务器；通常只读上述小结果，不重复下载整包。GPU当前是否空闲仍需现场检查。\n')
    return documents

def existing_credential():
    for name in ['GH_TOKEN','GITHUB_TOKEN']:
        if os.environ.get(name):return os.environ[name]
    try:
        value=subprocess.check_output(['gh','auth','token','--hostname','github.com'],stderr=subprocess.DEVNULL,text=True,timeout=15).strip()
        if value:return value
    except (OSError,subprocess.SubprocessError):pass
    try:
        env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never')
        row=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,text=True,env=env,timeout=15)
        if row.returncode==0:
            fields=dict(x.split('=',1) for x in row.stdout.splitlines() if '=' in x)
            return fields.get('password')
    except (OSError,subprocess.SubprocessError):pass
    return None

class Api:
    def __init__(self,credential):self.credential=credential
    def call(self,method,path,value=None):
        if not path.startswith('/repos/'+REPO+'/'):raise ValueError('unexpected API destination')
        for attempt in range(3):
            request=urllib.request.Request('https://api.github.com'+path,method=method,
                data=None if value is None else json.dumps(value,separators=(',',':')).encode(),
                headers={'Authorization':'Bearer '+self.credential,'Accept':'application/vnd.github+json',
                    'Content-Type':'application/json','User-Agent':'M2-compact-results','X-GitHub-Api-Version':'2022-11-28'})
            try:
                with urllib.request.urlopen(request,timeout=120) as r:return json.load(r)
            except urllib.error.HTTPError as exc:
                if exc.code not in [429,500,502,503,504] or attempt==2:raise RuntimeError('GitHub request failed, HTTP '+str(exc.code)) from None
            except (urllib.error.URLError,TimeoutError):
                if attempt==2:raise RuntimeError('GitHub network unavailable; computation and publication files retained') from None
            time.sleep(2**(attempt+1))
    def head(self):return self.call('GET','/repos/'+REPO+'/git/ref/heads/'+BRANCH)['object']['sha']

def main(base):
    import fcntl
    base=Path(base).resolve();base.relative_to(Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records'))
    with (base/'upload.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (base/'github_upload_receipt.json').exists():print((base/'github_upload_receipt.json').read_text());return
        publication=base/'publication';manifest=c.read(publication/'manifest.json');summary=c.read(publication/'summary.json')
        if summary['status'] not in ['COMPLETE_SERVER_CHECKED','INCOMPLETE_NO_RETRY']:raise RuntimeError('server finalization is not complete')
        for row in manifest['files']:
            if c.sha(publication/row['file'])!=row['sha256']:raise RuntimeError('publication changed after server checks')
        credential=existing_credential()
        if not credential:
            c.write(base/'upload_pending.json',dict(status='EXISTING_AUTH_UNAVAILABLE',publication=str(publication),
                no_token_requested=True,no_recompute=True,observed_at=c.now()))
            print('M2_RESULTS_READY_UPLOAD_PENDING_EXISTING_AUTH_UNAVAILABLE',publication,flush=True);return
        api=Api(credential);prefix='records/'+base.name
        checkpoint=base/'upload_checkpoint.json'
        state=c.read(checkpoint) if checkpoint.exists() else dict(files={},commit=None)
        entries=[]
        for f in sorted(publication.iterdir()):
            if not f.is_file():continue
            data=f.read_bytes();oid=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if state['files'].get(f.name)!=oid:
                result=api.call('POST','/repos/'+REPO+'/git/blobs',dict(encoding='base64',content=base64.b64encode(data).decode('ascii')))
                if result['sha']!=oid:raise RuntimeError('Git object acknowledgment differs')
                state['files'][f.name]=oid;c.write(checkpoint,state)
            entries.append(dict(path=prefix+'/'+f.name,mode='100644',type='blob',sha=oid))
        if state['commit'] is None:
            for attempt in range(4):
                head=api.head();parent=api.call('GET','/repos/'+REPO+'/git/commits/'+head)
                current=api.call('GET','/repos/'+REPO+'/contents/docs/current/PROJECT_STATUS.md?ref='+head)
                current_text=base64.b64decode(current['content']).decode('utf-8')
                update_shared=may_refresh_shared(current['sha'],current_text,base.name)
                attempt_entries=list(entries)
                if update_shared:
                    for path,content in shared_documents(base,summary,prefix).items():
                        data=content.encode('utf-8');oid=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
                        if state['files'].get('shared:'+path)!=oid:
                            result=api.call('POST','/repos/'+REPO+'/git/blobs',dict(encoding='base64',content=base64.b64encode(data).decode('ascii')))
                            if result['sha']!=oid:raise RuntimeError('shared entry acknowledgment differs')
                            state['files']['shared:'+path]=oid;c.write(checkpoint,state)
                        attempt_entries.append(dict(path=path,mode='100644',type='blob',sha=oid))
                tree=api.call('POST','/repos/'+REPO+'/git/trees',dict(base_tree=parent['tree']['sha'],tree=attempt_entries))['sha']
                commit=api.call('POST','/repos/'+REPO+'/git/commits',dict(message='Publish Phase3-M2 server-checked compact results',tree=tree,parents=[head]))['sha']
                if api.head()!=head:continue
                try:api.call('PATCH','/repos/'+REPO+'/git/refs/heads/'+BRANCH,dict(sha=commit,force=False))
                except RuntimeError:
                    observed=api.head()
                    if observed!=commit:
                        if observed!=head:continue
                        raise
                state['commit']=commit;state['shared_entries_updated']=update_shared;c.write(checkpoint,state);break
            if state['commit'] is None:raise RuntimeError('branch advanced repeatedly; uploaded objects retained, no force push')
        # Only the small, user-readable results are downloaded once. The three
        # sufficient-count files are acknowledged by their Git object IDs.
        for name in ['manifest.json','summary.json','gates.json']:
            path=prefix+'/'+name
            row=api.call('GET','/repos/'+REPO+'/contents/'+path+'?ref='+state['commit'])
            if base64.b64decode(row['content'])!=(publication/name).read_bytes():raise RuntimeError('small result readback differs')
        c.write(base/'github_upload_receipt.json',dict(commit=state['commit'],prefix=prefix,
            small_results_readback=True,count_objects_acknowledged=True,full_archive_downloaded=False,
            shared_entries_updated=state.get('shared_entries_updated',False),files=state['files'],observed_at=c.now()))
        print('M2_GITHUB_RESULTS',state['commit'],'https://github.com/'+REPO+'/tree/'+state['commit']+'/'+prefix,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True)
    args=p.parse_args()
    try:main(args.directory)
    except Exception as exc:
        c.write(Path(args.directory)/'upload_pending.json',dict(status='PUBLICATION_FAILED_NO_RECOMPUTE',error=str(exc),observed_at=c.now()))
        print('M2_UPLOAD_PENDING',str(exc),flush=True);raise SystemExit(1)
