"""Create a compact, decision-complete cross-computer D18 evidence package."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT/'records/rebuild_v1_d18_replication_20260928'
QUEUE = ROOT/'records/rebuild_v1_d18_replication_queue_20260928'
ARCHIVE = ROOT/'records/rebuild_v1_d18_replication_compact_20260928'
REPORT = ROOT/'docs/experiments/D18_REPLICATION_RESULTS_20260928.md'
ARMS = ('P0','P1','P2')


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda:file.read(8*1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def entry(path):
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=sha(path))


def main():
    ARCHIVE.mkdir(parents=True,exist_ok=True)
    copied={}
    missing=[]
    sources={'status.tsv':QUEUE/'status.tsv','planned_jobs.json':QUEUE/'planned_jobs.json',
             'decision.json':RESULTS/'decision.json'}
    for seed in (42,17):
        for arm in ARMS:
            base=(ROOT/'records/rebuild_v1_d18_d19_20260927' if seed==42 else RESULTS)/f'{arm}_seed{seed}'
            sources[f'server_{arm}_seed{seed}_summary.json']=base/'summary.json'
    for name,path in sources.items():
        if path.is_file():
            shutil.copy2(path,ARCHIVE/name)
            copied[name]=dict(server=entry(path),archive_sha256=sha(ARCHIVE/name))
        else:
            missing.append(dict(archive_name=name,server_path=str(path.resolve())))
    weights={}
    for arm in ARMS:
        path=ROOT/'runs/rebuild_v1'/f'D18_REPL_{arm}_seed17_8000_20260928/last_train_state.pth'
        if path.is_file():
            summary=ROOT/'runs/rebuild_v1'/f'D18_REPL_{arm}_seed17_8000_20260928/summary.json'
            weights[arm]=dict(path=str(path.resolve()),bytes=path.stat().st_size,
                              sha256=json.loads(summary.read_text())['checkpoint_sha256'] if summary.is_file() else sha(path))
    plan=json.loads((ARCHIVE/'planned_jobs.json').read_text()) if 'planned_jobs.json' in copied else {}
    decision=json.loads((ARCHIVE/'decision.json').read_text()) if 'decision.json' in copied else None
    lines=(ARCHIVE/'status.tsv').read_text(encoding='utf-8').splitlines() if 'status.tsv' in copied else []
    starts=[i for i,line in enumerate(lines) if '\tQUEUE\tSTART\t' in line]
    final=lines[starts[-1]:] if starts else []
    queue_ok=bool(final and any('\tQUEUE\tFINISHED\t' in line and 'analysis_ok=True' in line for line in final))
    manifest=dict(status='COMPLETE' if decision and not missing and queue_ok else 'INCOMPLETE',
        executed_git_commit=plan.get('git_commit'),server_root=str(ROOT.resolve()),
        data_root=plan.get('data_root'),source_sha256=plan.get('source_sha256'),
        files=copied,missing=missing,new_seed17_checkpoints=weights,queue_final_line=next((line for line in reversed(final) if '\tQUEUE\tFINISHED\t' in line),None),
        note='prediction NPZ, source imagery, checkpoints and full logs remain within /home/jovyan/zzx')
    (ARCHIVE/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    readme=[
        '# D18 seed17 matched replication: compact cross-computer evidence', '',
        f"Status: **{manifest['status']}**. Executed commit: `{manifest['executed_git_commit']}`.",
        'Training seed17 uses the original frozen DINO P0/P1/P2 protocol. Seed42 summaries are preserved unchanged.',
        'The evaluator uses seed42 corruption keys for both training seeds. Historical R01 fallback stays separate from same-seed P0 fallback.',
        '', '## Archived files', '',
        *[f'- `{name}`: {info["archive_sha256"]}' for name,info in copied.items()],
        '', '## Missing files', '',
        *([f'- `{row["archive_name"]}` ← `{row["server_path"]}`' for row in missing] or ['- None']),
        '', 'Large predictions, data, checkpoints and full logs remain on the server. Their locations and hashes are in `manifest.json`.',
        'Use `decision.json` plus all six arm summaries to inspect gates, paired errors, class/tile counts and absence cost.',
    ]
    (ARCHIVE/'README.md').write_text('\n'.join(readme)+'\n',encoding='utf-8')
    report=['# D18 matched seed17 replication results (2026-09-28)', '',
            f"Status: **{manifest['status']}**. Executed commit: `{manifest['executed_git_commit']}`.",
            'This is exploratory Val2 evidence; Test6 remains sealed. Train16 has 16 tiles and Val2 has two.',
            'P0 is RGB, P1 is RGB plus RGB-derived gray, P2 is RGB plus DSM. All use the same frozen DINO backbone and 8000 steps.',
            '', '## Score and prespecified decision', '']
    if decision and manifest['status']=='COMPLETE':
        report += ['| Training seed | Arm | Macro mIoU_fg5 (%) | Clean (%) | RGB quality (%) | Auxiliary quality (%) |',
                   '|---:|---|---:|---:|---:|---:|']
        for seed in (42,17):
            outcome=decision['outcomes'][str(seed)]
            for arm in ARMS:
                row=outcome['score_rows'][arm]
                family=row['families']
                report.append(f'| {seed} | {arm} | {row["macro_percent"]:.4f} | {family["clean"]:.4f} | {family["rgb_quality"]:.4f} | {family["aux_quality"]:.4f} |')
        report += ['', '| Training seed | P2 passed | Gain vs stronger P0/P1 (pp) | Clean guard | Family guard | Tile clean | Tile family |',
                   '|---:|---|---:|---|---|---|---|']
        for seed in (42,17):
            row=decision['outcomes'][str(seed)]['decision']
            c=row['checks']
            report.append(f'| {seed} | {row["passed"]} | {row["macro_gain_pp"]:.4f} | {c["clean"]} | {c["families"]} | {c["tile_clean"]} | {c["tile_families"]} |')
        report += ['', f"Both seeds pass: **{decision['both_seeds_pass']}**.",
                   'Main score weights clean, RGB quality and auxiliary quality equally; each family averages its prespecified conditions.',
                   'Contrast0.6 and shift8 remain diagnostics outside the gate.',
                   '', '## DSM absence and paired error', '',
                   '| Training seed | Original P2 aux_zero (%) | Same-seed P0 fallback (%) | P0-only correct pixels (clean) | P2-only correct pixels (clean) |',
                   '|---:|---:|---:|---:|---:|']
        for seed in (42,17):
            paired=decision['paired'][str(seed)]
            absence=paired['aux_zero']
            clean=paired['clean']['pooled_paired']['P2']['all']
            report.append(f'| {seed} | {absence["pooled_raw_p2_mIoU_fg5_percent"]:.4f} | {absence["pooled_matched_p0_fallback_mIoU_fg5_percent"]:.4f} | {clean["only_p0_correct"]} | {clean["only_candidate_correct"]} |')
        report += ['', 'The same-seed P0 fallback uses an explicit availability mask. Full absence equality with P0 verifies the switch implementation; it does not show learned missing-input detection.',
                   'Detailed per-class, per-tile and affected-region integer counts and both confusion matrices are in `decision.json`.',
                   'The historical R01 fallback and harm/rescue values remain in each arm summary and are not the same-seed P0 comparison.',
                   '', '## Next decision', '']
        if decision['both_seeds_pass']:
            report.append('Keep the DSM utility candidate. Inspect where P2 introduces errors and DSM absence cost, then design a reliability intervention with matched P0/P1/P2 controls. Plan independent-scene validation after freezing the method and checking prior data exposure.')
        else:
            report.append('Record cross-seed instability and pause promotion of the current 8000-step candidate. Inspect the failed seed, class, tile and condition before any new matched design.')
    else:
        report += ['Analysis is incomplete. Inspect `status.tsv`, the missing list in `manifest.json`, and server logs; preserve completed arms.']
    report += ['', '## Evidence locations and limits', '',
               'Compact evidence: `records/rebuild_v1_d18_replication_compact_20260928/`.',
               'Full server evaluations: `records/rebuild_v1_d18_replication_20260928/`; training checkpoints: `runs/rebuild_v1/D18_REPL_*_seed17_8000_20260928/`.',
               'Val2 contains only two scenes and was used repeatedly. Seed17 replication does not constitute independent Test6 validation.',
               'The old C0 score is from a different backbone and training start, so absolute performance differences are not attributable to DSM alone.',
               'Check manifest hashes and all six summaries before making another research decision.',
               '']
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text('\n'.join(report),encoding='utf-8')
    print('ARCHIVE',manifest['status'],ARCHIVE,flush=True)
    print('REPORT',REPORT,flush=True)
    print('To share: git add records/rebuild_v1_d18_replication_compact_20260928 docs/experiments/D18_REPLICATION_RESULTS_20260928.md',flush=True)


if __name__=='__main__':
    main()
