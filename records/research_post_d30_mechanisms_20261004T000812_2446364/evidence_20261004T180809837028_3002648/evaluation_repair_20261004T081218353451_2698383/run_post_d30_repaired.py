"""Original training runner with explicit evaluation compatibility provenance."""
import json,os,sys
from pathlib import Path
def main():
    repair=Path(os.environ['POST_D30_REPAIR_DIRECTORY']).resolve()
    def argument(name):return sys.argv[sys.argv.index(name)+1]
    base=Path(argument('--directory')).resolve();base.relative_to(Path('/home/jovyan/zzx'))
    repair.relative_to(base);job=argument('--job');root=Path(argument('--root')).resolve()
    sys.path[:0]=[str(repair),str(base/'code/scripts'),str(base/'code'),str(root)]
    from post_d30_eval_compat import read,sha,ORIGINAL,compatible,reuse_equal_age
    manifest=read(repair/'repair_manifest.json')
    for p,digest in manifest['files'].items():
        if sha(repair/p)!=digest:raise RuntimeError('repair snapshot changed')
    plan=read(base/'plan.json')
    if plan['execution_commit']!=ORIGINAL or sha(base/'plan.json')!=manifest['original_plan_sha256']:raise RuntimeError('original plan changed')
    import run_post_d30 as runner
    import post_d30_evaluation as evaluation
    import post_d30_data as data
    overlay=dict(repair_manifest_path=str(repair/'repair_manifest.json'),repair_manifest_sha256=sha(repair/'repair_manifest.json'),repair_commit=manifest['repair_commit'],
                 scope='evaluation diagnostic compatibility only; training code/config/checkpoint signatures remain original',conditions=['dsm_present_zero','dsm_present_shift_half'])
    original=data.treatment;evaluation.treatment=compatible(original)
    old_evaluation_write=evaluation.write
    def evaluation_write(path,value):
        if Path(path).name=='summary.json' or value.get('condition') in overlay['conditions']:
            value=dict(value,evaluation_patch=overlay)
        return old_evaluation_write(path,value)
    evaluation.write=evaluation_write
    old_worker_write=runner.write
    def worker_write(path,value):
        if Path(path).name=='complete.json':value=dict(value,evaluation_patch=overlay)
        return old_worker_write(path,value)
    runner.write=worker_write
    folder=base/'jobs'/job
    if job.startswith('A') and not (folder/'complete.json').exists():
        import torch
        state=torch.load(folder/'last_train_state.pth',map_location='cpu',weights_only=False)
        if state['global_step']!=8000 or state['signature']['plan_sha256']!=sha(base/'plan.json') or state['signature']['execution_commit']!=ORIGINAL:raise RuntimeError('A recovery must be evaluation-only at exact step8000')
        hashes={str(p.relative_to(folder)):sha(p) for p in (folder/'selected.pth',folder/'checkpoints/step_8000.pth')}
        resumed=reuse_equal_age(base,folder,state,old_worker_write);del state
        old_worker_write(folder/'evaluation_repair_binding.json',dict(**overlay,optimizer_updates=0,immutable_checkpoint_hashes=hashes,reused_selected_rows=resumed))
        print('PORTFOLIO_REPAIR_EVAL_ONLY',job,'optimizer_updates=0','reused_rows='+str(len(resumed)),flush=True)
    rc=runner.main()
    if rc==0 and job.startswith('A') and (folder/'evaluation_repair_binding.json').exists():
        record=read(folder/'evaluation_repair_binding.json')
        if any(sha(folder/p)!=digest for p,digest in record['immutable_checkpoint_hashes'].items()):raise RuntimeError('trained A checkpoint changed during recovery')
    return rc
if __name__=='__main__':
    try:sys.exit(main())
    except Exception:
        import traceback;traceback.print_exc();sys.exit(2)
