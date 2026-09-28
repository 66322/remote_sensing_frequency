"""Reconcile a running 48-job D21 queue stopped after the 32 matched jobs.

Run only after the old queue has exited. Preserve the original plan and its
INCOMPLETE status; create a separate, audited two-seed scope record.
"""
from datetime import datetime
import shutil
import subprocess
import d21_common as p
from analyze_rebuild_v1_d21 import main as analyze


def main():
    cfg = p.config()
    if cfg['seeds'] != [42, 17] or len(p.jobs()) != 32:
        raise RuntimeError('effective two-seed configuration mismatch')
    old_plan = p.read(p.OUT/'plan.json')
    old_status = p.read(p.OUT/'queue_summary.json')
    preflight = p.read(p.OUT/'preflight.json')
    events = (p.OUT/'status.tsv').read_text(encoding='utf-8')
    if len(old_plan['jobs']) != 48 or old_status['planned'] != 48:
        raise RuntimeError('not the original 48-job queue')
    if preflight['git_commit'][:7] != '10f63ea':
        raise RuntimeError('unexpected original launch commit')
    if old_status['completed'] != 32 or old_status['failures'] or not old_status['stop_requested']:
        raise RuntimeError('old queue did not stop cleanly after 32 jobs')
    if '\tQUEUE\tINCOMPLETE\t32/48' not in events:
        raise RuntimeError('old queue has not fully exited')
    if '_seed2026\tSTART\t' in events or any((p.eval_dir(dict(dataset=d,arm=a,seed=2026))/'summary.json').exists()
                                             for d in cfg['datasets'] for a in cfg['arms']):
        raise RuntimeError('third seed was already started; manual review required')
    if not (p.OUT/'STOP').is_file():
        raise RuntimeError('user stop marker missing')
    for job in p.jobs():
        train = p.read(p.run_dir(job)/'summary.json')
        ck = p.run_dir(job)/'last_train_state.pth'
        if train['global_step'] != cfg['steps'] or train['checkpoint_sha256'] != p.sha(ck):
            raise RuntimeError('training checkpoint changed: '+p.key(job))
    analyze()
    decision = p.read(p.COMPACT/'decision.json')
    if decision['completed'] != 32 or len(decision['decisions']) != 4 or decision['integer_count_audit'] != 'PASS':
        raise RuntimeError('two-seed integer-count audit incomplete')
    shutil.copy2(p.OUT/'queue_summary.json',p.COMPACT/'original_queue_summary.json')
    shutil.copy2(p.OUT/'status.tsv',p.COMPACT/'original_status.tsv')
    scope = dict(
        observed_at=datetime.now().astimezone().isoformat(),
        original_launch_commit=preflight['git_commit'],
        effective_protocol_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=p.ROOT,text=True).strip(),
        original_plan_jobs=48, original_queue_status=old_status['status'],
        scope_change='User removed automatic third seed after the old queue started; STOP was set once all 32 matched jobs began.',
        effective_datasets=cfg['datasets'], effective_seeds=cfg['seeds'], effective_arms=cfg['arms'],
        completed=32, planned=32, effective_scope_status='COMPLETE',
        integer_count_audit='PASS', test6_loaded=False, independent_final_loaded=False)
    p.write(p.COMPACT/'effective_scope.json',scope)
    print('D21 EFFECTIVE TWO-SEED SCOPE COMPLETE 32/32; original 48-job plan and status retained',flush=True)


if __name__ == '__main__':
    main()
