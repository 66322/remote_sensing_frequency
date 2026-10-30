"""Inventory, evidence export and authorized file-only cleanup of the bound M2 run.

Python 3.9+, standard library. No model import, GPU work, credentials or training.
Default is audit; --apply exports and verifies evidence before deleting candidates.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tarfile

ROOT = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
LATCH = 'phase3_engineering_restart_20261024_once.json'
RECEIPT = 'phase3_m2_storage_cleanup_20261029.json'
LOCK = 'phase3_m2_storage_cleanup_20261029.lock'
JOB = re.compile(r'^F[012]_s(?:42|17|2026)_(?:R|T[0-3]|D0|DSelf|DClean|DF|DShuffle|DEntropy|DMix)$')
PUB = ('summary.json', 'gates.json', 'REPORT.md', 'metrics.csv',
       'F0_counts.jsonl.gz', 'F1_counts.jsonl.gz', 'F2_counts.jsonl.gz',
       'server_evidence_index.json', 'manifest.json')


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp.' + str(os.getpid()))
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))


def safe(path, root):
    root = Path(root).absolute()
    path = Path(path).absolute()
    path.relative_to(root)
    for node in (root, *root.parents):
        if node.is_symlink():
            raise RuntimeError('Symlink in root: ' + str(node))
    for node in (path, *path.parents):
        if node.is_symlink():
            raise RuntimeError('Symlink refused: ' + str(node))
        if node == root:
            break
    resolved = path.resolve()
    resolved.relative_to(root.resolve())
    if resolved == root.resolve():
        raise RuntimeError('Refuse root itself')
    return resolved


def bound_runs(records):
    receipt = read(records / LATCH)
    runs = {}
    for key, prefix in [('m2_directory', 'research_phase3_m2_revision_'),
                        ('combined_directory', 'research_phase3_combined_revision_'),
                        ('old_m2', 'research_phase3_m2_'),
                        ('old_combined', 'research_phase3_combined_')]:
        if key not in receipt:
            continue
        base = safe(Path(receipt[key]), records)
        if base.parent != records.resolve() or not base.name.startswith(prefix):
            raise RuntimeError('Unexpected registered run: ' + str(base))
        if base.is_dir():
            runs[key] = base
        elif key in ('m2_directory', 'combined_directory'):
            raise RuntimeError('Current run missing: ' + str(base))
    return receipt, runs


def assert_stopped(runs, proc=Path('/proc')):
    m2 = runs['m2_directory']
    q = runs['combined_directory']
    if read(m2 / 'queue_status.json').get('status') != 'COMPLETE_SERVER_CHECKED':
        raise RuntimeError('M2 not complete')
    if read(q / 'queue_status.json').get('status') not in (
            'STOPPED_NO_AUTOMATIC_RETRY', 'COMPLETE_SERVER_CHECKED', 'COMPLETE'):
        raise RuntimeError('Combined queue not stopped/complete')
    if not proc.is_dir():
        raise RuntimeError('Linux /proc required for cleanup process check')
    hits = []
    for folder in proc.iterdir():
        if not folder.name.isdigit() or int(folder.name) == os.getpid():
            continue
        try:
            cmd = (folder / 'cmdline').read_bytes().replace(b'\x00', b' ').decode('utf-8', 'replace')
        except (FileNotFoundError, ProcessLookupError):
            continue
        if any(str(base) in cmd for base in runs.values()):
            hits.append(dict(pid=int(folder.name), command=cmd[:1000]))
    if hits:
        raise RuntimeError('Run still referenced by live processes: ' + json.dumps(hits))


def inventory(runs):
    rows = []
    excluded = []
    for label, base in runs.items():
        for folder, dirs, files in os.walk(str(base), followlinks=False):
            parent = Path(folder)
            kept = []
            for name in dirs:
                p = parent / name
                if p.is_symlink():
                    excluded.append(str(p))
                else:
                    kept.append(name)
            dirs[:] = kept
            for name in files:
                p = parent / name
                if p.is_symlink():
                    excluded.append(str(p))
                    continue
                p = safe(p, base)
                st = p.stat()
                if not stat.S_ISREG(st.st_mode):
                    excluded.append(str(p))
                    continue
                rows.append(dict(run=label, relative=str(p.relative_to(base)), path=str(p),
                                 bytes=st.st_size, allocated_bytes=getattr(st, 'st_blocks', 0) * 512,
                                 dev=st.st_dev, ino=st.st_ino, mtime_ns=st.st_mtime_ns,
                                 links=st.st_nlink))
    unique = {}
    for row in rows:
        unique.setdefault((row['dev'], row['ino']), row)
    return dict(observed_at=now(), files=rows, excluded_symlinks_or_special=excluded,
                logical_bytes=sum(r['bytes'] for r in rows),
                unique_allocated_bytes=sum(r['allocated_bytes'] for r in unique.values()),
                by_run={label: dict(files=sum(r['run'] == label for r in rows),
                                    logical_bytes=sum(r['bytes'] for r in rows if r['run'] == label),
                                    allocated_bytes=sum(r['allocated_bytes'] for r in rows if r['run'] == label))
                        for label in runs},
                largest_files=sorted(rows, key=lambda r: r['bytes'], reverse=True)[:30])


def verify_evidence(m2):
    pub = m2 / 'publication'
    summary = read(pub / 'summary.json')
    if (summary.get('status') != 'COMPLETE_SERVER_CHECKED' or
            summary.get('jobs_complete') != 108 or summary.get('evaluated_cases') != 77868 or
            summary.get('errors') or summary.get('failures') or not summary.get('gates', {}).get('G0')):
        raise RuntimeError('Incomplete M2 evidence')
    binding = summary['binding']
    if read(m2 / 'registration.json')['binding'] != binding:
        raise RuntimeError('Run binding mismatch')
    for name in ('plan.json', 'code_manifest.json', 'folds.json'):
        if not safe(m2 / name, m2).is_file():
            raise RuntimeError('Missing accepted run metadata: ' + name)
    gates = read(pub / 'gates.json')
    if gates['status'] != summary['gates']:
        raise RuntimeError('Summary/gates mismatch')
    listed = {row['file']: row for row in read(pub / 'manifest.json')['files']}
    checked = []
    for name in PUB:
        p = safe(pub / name, m2)
        if not p.is_file():
            raise RuntimeError('Missing publication evidence: ' + name)
        row = dict(file=name, size=p.stat().st_size)
        if name != 'manifest.json':
            expected = listed.get(name)
            if expected is None or expected['size'] != row['size']:
                raise RuntimeError('Publication manifest mismatch: ' + name)
            row['sha256_from_existing_manifest'] = expected.get('sha256')
        checked.append(row)
    # Preserve the original case-level and full auxiliary aggregates, not only their summaries.
    evidence_index = read(pub / 'server_evidence_index.json')
    if evidence_index.get('binding') != binding:
        raise RuntimeError('Evidence index binding mismatch')
    original = {row['path']: row for row in evidence_index['files']}
    for name in ('case_counts.jsonl.gz', 'all_aggregates.jsonl.gz'):
        p = safe(m2 / name, m2)
        row = original.get(name)
        if not p.is_file() or row is None or p.stat().st_size != row['size']:
            raise RuntimeError('Original sufficient counts missing/changed: ' + name)
    return summary, checked


def choose_candidates(runs, inv, binding):
    m2 = runs['m2_directory']
    weights = {}
    retained = []
    for parameters in sorted((m2 / 'jobs').glob('*/parameters.json')):
        params = read(safe(parameters, m2))
        job = params['job']
        jobid = parameters.parent.name
        if not JOB.fullmatch(jobid) or job['id'] != jobid or params['binding'] != binding:
            raise RuntimeError('Unexpected job identity/binding: ' + jobid)
        complete = read(safe(parameters.parent / 'complete.json', m2))
        if (complete['job'] != jobid or complete['binding'] != binding or
                complete['optimizer_updates'] != 32000):
            raise RuntimeError('Endpoint receipt mismatch: ' + jobid)
        is_reference = jobid.endswith('_R') and job['role'] == 'rgb_reference'
        is_d0 = jobid.endswith('_D0') and job['role'] == 'dsm_student' and job['arm'] == 'D0'
        teacher = re.search(r'_T[0-3]$', jobid) and job['role'] == 'rgb_oof_teacher'
        other_dsm = job['role'] == 'dsm_student' and job['arm'] in ('DSelf', 'DClean', 'DF', 'DShuffle', 'DEntropy', 'DMix')
        endpoint = safe(parameters.parent / 'endpoint.pth', m2)
        if not endpoint.is_file():
            raise RuntimeError('Unexpected missing endpoint before cleanup: ' + str(endpoint))
        if is_reference or is_d0:
            retained.append(str(endpoint))
        elif teacher or other_dsm:
            weights[str(endpoint)] = dict(reason='retired_oof_teacher' if teacher else 'closed_dsm_recipe',
                                          expected_sha256=complete['checkpoint_sha256'], job=jobid)
        else:
            raise RuntimeError('Unclassified M2 endpoint: ' + jobid)
    if len(retained) != 18 or len(weights) != 90:
        raise RuntimeError('Expected 18 retained and 90 retired endpoints')
    candidates = []
    for row in inv['files']:
        p = Path(row['path'])
        parts = Path(row['relative']).parts
        reason = None
        info = weights.get(row['path'])
        if info:
            reason = info['reason']
        elif row['run'] == 'm2_directory' and len(parts) == 3 and parts[0] == 'jobs' and parts[2] == 'last_resume.pth':
            if not JOB.fullmatch(parts[1]):
                raise RuntimeError('Unknown rolling checkpoint owner')
            reason = 'completed_m2_optimizer_resume'
        elif parts and (parts[0] == 'temporary' or (len(parts) >= 3 and parts[0] == 'cache' and parts[1] in ('cuda', 'triton', 'kernels'))):
            reason = 'inactive_run_temporary_or_compiler_cache'
        if reason:
            if row['links'] != 1:
                continue
            value = dict(row, reason=reason, sha256_from_receipt=info['expected_sha256'] if info else None)
            candidates.append(value)
    return candidates, retained


def export_evidence(records, runs, output, checked):
    sources = [(runs['m2_directory'] / 'publication' / row['file'], 'M2/publication/' + row['file']) for row in checked]
    for label, base in runs.items():
        for name in ('plan.json', 'registration.json', 'code_manifest.json', 'folds.json',
                     'input_index.json', 'pretrained.json', 'queue_status.json',
                     'runtime_revision_failure.json', 'runtime_revision_entry_failure.json', 'controller_failure.json'):
            if (base / name).is_file():
                sources.append((safe(base / name, base), label + '/' + name))
        for p in sorted((base / 'jobs').glob('*/*.json')):
            if p.name in ('parameters.json', 'complete.json', 'progress.json', 'training_complete.json'):
                sources.append((safe(p, base), label + '/' + p.relative_to(base).as_posix()))
        for p in sorted((base / 'failures').glob('*.json')):
            sources.append((safe(p, base), label + '/' + p.relative_to(base).as_posix()))
    sources.append((safe(records / LATCH, records), LATCH))
    manifest = []
    for source, relative in sources:
        manifest.append(dict(file=relative, bytes=source.stat().st_size))
    write(output / 'export_manifest.json', dict(observed_at=now(), files=manifest,
          check_policy='existing accepted bindings, names and sizes; no repeated file hashing'))
    archive = output / 'M2_light_evidence.tar.gz'
    with tarfile.open(str(archive), 'w:gz', compresslevel=3) as tar:
        for source, relative in sources:
            tar.add(str(source), arcname=relative, recursive=False)
        tar.add(str(output / 'export_manifest.json'), arcname='export_manifest.json', recursive=False)
    expected = {row['file']: row['bytes'] for row in manifest}
    expected['export_manifest.json'] = (output / 'export_manifest.json').stat().st_size
    with tarfile.open(str(archive), 'r:gz') as tar:
        actual = set()
        for member in tar:
            if not member.isfile() or member.name not in expected or member.name in actual:
                raise RuntimeError('Unexpected archive entry')
            if member.size != expected[member.name]:
                raise RuntimeError('Archive size mismatch: ' + member.name)
            actual.add(member.name)
        if actual != set(expected):
            raise RuntimeError('Archive entries missing')
    return dict(path=str(archive), bytes=archive.stat().st_size,
                listed_members=len(expected), status='LOCAL_EXPORT_LISTED_NOT_YET_UPLOADED',
                check_policy='names and sizes; no repeated hashing')


def delete_checked(row, root):
    p = safe(Path(row['path']), root)
    st = p.lstat()
    expected = (row['dev'], row['ino'], row['bytes'], row['mtime_ns'], 1)
    actual = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_nlink)
    if not stat.S_ISREG(st.st_mode) or actual != expected:
        raise RuntimeError('Candidate changed: ' + str(p))
    # Bound the unlink to an open parent directory and reject final-component symlinks.
    parentfd = os.open(str(p.parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parentfd)
        try:
            current = os.fstat(fd)
            if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns, current.st_nlink) != expected:
                raise RuntimeError('Candidate descriptor changed')
            current = os.stat(p.name, dir_fd=parentfd, follow_symlinks=False)
            if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns, current.st_nlink) != expected:
                raise RuntimeError('Candidate pathname changed')
            os.unlink(p.name, dir_fd=parentfd)
        finally:
            os.close(fd)
    finally:
        os.close(parentfd)


def linux_delete_selfcheck(output):
    base = output / 'filesystem_selfcheck'
    base.mkdir()
    p = base / 'owned_sentinel'
    p.write_bytes(b'new cleanup implementation check\n')
    st = p.stat()
    row = dict(path=str(p), dev=st.st_dev, ino=st.st_ino, bytes=st.st_size,
               mtime_ns=st.st_mtime_ns)
    changed = dict(row, bytes=st.st_size + 1)
    try:
        delete_checked(changed, base)
    except RuntimeError:
        pass
    else:
        raise RuntimeError('Changed-file refusal selfcheck failed')
    if not p.is_file():
        raise RuntimeError('Refusal deleted sentinel')
    delete_checked(row, base)
    if p.exists():
        raise RuntimeError('File-only deletion selfcheck failed')
    outside = output / 'external_sentinel'
    outside.write_bytes(b'keep')
    link = base / 'link'
    link.symlink_to(outside)
    try:
        safe(link, base)
    except RuntimeError:
        pass
    else:
        raise RuntimeError('Symlink refusal selfcheck failed')
    if outside.read_bytes() != b'keep':
        raise RuntimeError('Outside sentinel changed')
    link.unlink()
    outside.unlink()
    return dict(status='PASSED', scope='owned newly created sentinels only', observed_at=now())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Authorized cleanup after inventory and verified export')
    args = parser.parse_args()
    records = ROOT / 'records'
    if sys.platform != 'linux':
        raise RuntimeError('This entry point runs only on the bound Linux server')
    receipt, runs = bound_runs(records)
    assert_stopped(runs)
    previous = records / RECEIPT
    if previous.is_file():
        old = read(previous)
        if old.get('status') == 'COMPLETE' and old.get('m2_directory') == str(runs['m2_directory']):
            print('ALREADY_CLEANED', json.dumps(old, ensure_ascii=False), flush=True)
            return
        raise RuntimeError('Prior incomplete cleanup receipt exists; inspect its saved plan/journal, do not blindly restart')
    lock = records / LOCK
    lockfd = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    output = records / ('m2_closeout_storage_' + datetime.now().strftime('%Y%m%dT%H%M%S') + '_' + str(os.getpid()))
    try:
        os.write(lockfd, str(os.getpid()).encode('ascii'))
        output.mkdir()
        print('PHASE inventory_of_registered_runs', flush=True)
        before = inventory(runs)
        write(output / 'inventory_before.json', before)
        free_before = shutil.disk_usage(str(records)).free
        print('PHASE verify_existing_evidence_and_prepare_candidates', flush=True)
        summary, checked = verify_evidence(runs['m2_directory'])
        candidates, retained = choose_candidates(runs, before, summary['binding'])
        plan = dict(observed_at=now(), m2_directory=str(runs['m2_directory']), binding=summary['binding'],
                    policy='retain 9 RGB references + 9 DSM-D0 endpoints; retire 36 OOF teachers + 54 closed DSM endpoints; '
                           'retain all sufficient counts/config/log/receipts/pretrained and J endpoints; remove only listed inactive temporary/compiler caches',
                    candidates=candidates, retained_endpoints=retained,
                    candidate_logical_bytes=sum(r['bytes'] for r in candidates),
                    candidate_allocated_bytes=sum(r['allocated_bytes'] for r in candidates))
        write(output / 'cleanup_plan.json', plan)
        print('INVENTORY', json.dumps(dict(output=str(output), by_run=before['by_run'],
              unique_allocated_bytes=before['unique_allocated_bytes'], candidates=len(candidates),
              candidate_reasons=dict(Counter(r['reason'] for r in candidates)),
              candidate_logical_bytes=plan['candidate_logical_bytes'],
              candidate_allocated_bytes=plan['candidate_allocated_bytes'], retained_endpoints=len(retained)), ensure_ascii=False), flush=True)
        archive = export_evidence(records, runs, output, checked)
        write(output / 'export_receipt.json', archive)
        print('EVIDENCE_EXPORT', json.dumps(archive, ensure_ascii=False), flush=True)
        if not args.apply:
            print('AUDIT_ONLY_NO_FILES_DELETED', flush=True)
            return
        assert_stopped(runs)
        write(output / 'filesystem_selfcheck.json', linux_delete_selfcheck(output))
        state = dict(status='APPLYING', observed_at=now(), m2_directory=str(runs['m2_directory']),
                     binding=summary['binding'], output=str(output), archive=archive,
                     cleanup_plan=str(output / 'cleanup_plan.json'), deleted_files=0,
                     deleted_logical_bytes=0, deleted_allocated_bytes=0)
        write(previous, state)
        with (output / 'deletions.jsonl').open('x', encoding='utf-8') as log:
            for row in candidates:
                delete_checked(row, runs[row['run']])
                log.write(json.dumps(dict(path=row['path'], reason=row['reason'], sha256_from_receipt=row['sha256_from_receipt'],
                                          bytes=row['bytes'], observed_at=now()), ensure_ascii=False) + '\n')
                log.flush()
                os.fsync(log.fileno())
                state['deleted_files'] += 1
                state['deleted_logical_bytes'] += row['bytes']
                state['deleted_allocated_bytes'] += row['allocated_bytes']
                write(previous, state)
        after = inventory(runs)
        write(output / 'inventory_after.json', after)
        for name in retained:
            if not Path(name).is_file():
                raise RuntimeError('Retained endpoint missing: ' + name)
        verify_evidence(runs['m2_directory'])
        state.update(status='COMPLETE', observed_at=now(), remaining_retained_endpoints=len(retained),
                     run_allocated_bytes_before=before['unique_allocated_bytes'],
                     run_allocated_bytes_after=after['unique_allocated_bytes'],
                     run_allocated_reduction_bytes=before['unique_allocated_bytes'] - after['unique_allocated_bytes'],
                     export_storage_bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),
                     disk_free_bytes_before=free_before, disk_free_bytes_after=shutil.disk_usage(str(records)).free,
                     archive_bytes=Path(archive['path']).stat().st_size)
        state['export_allocated_bytes'] = sum(getattr(p.stat(), 'st_blocks', 0) * 512 for p in output.rglob('*') if p.is_file())
        state['estimated_net_reclaimed_bytes'] = state['run_allocated_reduction_bytes'] - state['export_allocated_bytes']
        write(previous, state)
        write(output / 'cleanup_result.json', state)
        print('CLEANUP_COMPLETE', json.dumps(state, ensure_ascii=False), flush=True)
        print('SEND_BACK', str(output / 'cleanup_result.json'), str(output / 'M2_light_evidence.tar.gz'), flush=True)
    except BaseException as exc:
        if output.is_dir():
            write(output / 'failure.json', dict(error=str(exc), observed_at=now()))
        raise
    finally:
        os.close(lockfd)
        if lock.exists():
            lock.unlink()


if __name__ == '__main__':
    main()
