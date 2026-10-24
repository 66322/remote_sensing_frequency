"""Upload completed D30 compact analysis records, without weights/predictions/raw matrices."""
import argparse,hashlib,json,os,subprocess
from datetime import datetime
from pathlib import Path

def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(root,*args,capture=False):
    return subprocess.run(['git','-C',str(root),*args],check=True,text=True,stdout=subprocess.PIPE if capture else None).stdout
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx'));base=a.directory.resolve();base.relative_to(root/'records')
    if base.name!='research_d30_loss_decomposition_20261003T205144_2349167':raise ValueError('bound D30 directory differs')
    state=json.loads((base/'queue_status.json').read_text());screen=json.loads((base/'screen_result.json').read_text())
    if state['status']!='COMPLETE' or screen['status']!='COMPLETE' or screen['test6_loaded'] or screen['independent_final_loaded']:raise RuntimeError('not completed permitted development result')
    if set(state['jobs'])!={'replay_G0','replay_G1','P','R','PR_area','PR_pixel'} or any(r['status']!='COMPLETE' for r in state['jobs'].values()):raise RuntimeError('six job completion required')
    plan=json.loads((base/'plan.json').read_text())
    if plan['execution_commit']!='9db12dfb7ee85dff91dd6c246c7f161b60aca603':raise RuntimeError('execution differs')
    required=['plan.json','execution_commit.txt','code_manifest.json','queue_status.json','screen_result.json','results.csv','reuse_binding.json']
    required+=['jobs/'+j+'/complete.json' for j in state['jobs']]
    optional=['cpu_checks.log','nohup.log']+['reused/'+j+'/complete.json' for j in ('S0','S1')]
    # Native loss/gradient JSON is small; retain actual denominators, no new computation.
    for job in ('P','R','PR_area','PR_pixel'):
        for category in ('loss_components','gradient_diagnostics'):
            optional += [p.relative_to(base).as_posix() for p in (base/'jobs'/job/category).glob('*.json')]
    data={}
    for name in required+optional:
        p=(base/name).resolve();p.relative_to(base)
        if name in required and not p.is_file():raise FileNotFoundError(p)
        if not p.is_file():continue
        raw=p.read_bytes();raw.decode('utf-8')
        if p.suffix=='.json':json.loads(raw)
        data[name]=raw
    if sum(map(len,data.values()))>64*1024**2:raise RuntimeError('unexpected compact summary size')
    origin=git(root,'remote','get-url','origin',capture=True).strip()
    if origin not in ('https://github.com/66322/remote_sensing_frequency.git','https://github.com/66322/remote_sensing_frequency','git@github.com:66322/remote_sensing_frequency.git'):raise ValueError('unexpected origin')
    branch='rebuild-v1-protocol-20260915';git(root,'fetch','origin',branch)
    parent=git(root,'rev-parse','FETCH_HEAD',capture=True).strip();stamp=datetime.now().strftime('%Y%m%dT%H%M%S%f')+'_'+str(os.getpid())
    worktree=base/('github_summary_upload_'+stamp);git(root,'worktree','add','--detach',str(worktree),parent)
    relative=Path('records')/base.name/('summary_evidence_'+stamp);target=worktree/relative;target.mkdir(parents=True)
    for name,raw in data.items():
        dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    manifest=dict(server_directory=str(base),observed_at=datetime.now().astimezone().isoformat(),base_commit=parent,
        files=[dict(path=n,bytes=len(v),sha256=sha(v)) for n,v in data.items()],
        evidence_scope='native compact summary, paired tile deltas, retention, checkpoint interventions, loss and gradient records, source/completion bindings',
        raw_tile_matrices_uploaded=False,predictions_and_checkpoints_uploaded=False,new_training=False,new_inference=False,originals_preserved=True)
    (target/'upload_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    paths=[(relative/n).as_posix() for n in data]+[(relative/'upload_manifest.json').as_posix()]
    git(worktree,'add','-f','--',*paths)
    git(worktree,'-c','user.name=66322','-c','user.email=57258129+66322@users.noreply.github.com','commit','-m','records: upload completed D30 compact analysis evidence')
    commit=git(worktree,'rev-parse','HEAD',capture=True).strip();git(worktree,'push','origin','HEAD:refs/heads/'+branch)
    print('D30_SUMMARY_COMMIT='+commit)
    print('D30_SUMMARY_RECORDS=https://github.com/66322/remote_sensing_frequency/tree/'+commit+'/'+relative.as_posix())
    print('D30_SUMMARY_FILES='+str(len(data)+1)+' BYTES='+str(sum(map(len,data.values()))))
if __name__=='__main__':main()
