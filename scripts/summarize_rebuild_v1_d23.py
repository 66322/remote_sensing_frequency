"""Frozen D23 eight-arm development screen; no selection or automatic new runs."""
import argparse
import json
from pathlib import Path
import d23_engine as e
import d23_lifecycle as life
import numpy as np

ARMS=('T0','TS','TF','TSF','TCAP','TSF_CE','TSF_shuffleS','TSF_shuffleF')
FAMILIES={'clean':['clean'],'rgb_quality':['rgb_down2','rgb_down4','rgb_blur5','rgb_local_down4_q1'],
          'aux_quality':['aux_down4','aux_noise_std010']}


def screen(summaries):
    if set(summaries)!=set(ARMS):raise RuntimeError('all eight completed development arms required')
    rows={}
    for arm,summary in summaries.items():
        if summary.get('test6_loaded') is not False or summary.get('independent_final_loaded') is not False:
            raise RuntimeError('test/final scope mismatch')
        if set(summary['pooled'])!=set(e.CONDITIONS):raise RuntimeError('fourteen conditions required')
        for cond in e.CONDITIONS:
            if set(summary['tiles'][cond])!={'3_11','5_10'}:raise RuntimeError('Val2 incomplete')
            for name,scopes in summary['pooled'][cond].items():
                for scope in ('full','noboundary'):
                    originals=[summary['tiles'][cond][tile][name]['scopes'][scope] for tile in ('3_11','5_10')]
                    for row in originals:
                        cm=np.asarray(row['cm'])
                        if cm.shape!=(6,6) or cm.dtype.kind not in 'iu' or (cm<0).any() or int(cm.sum())!=row['all']['valid']:
                            raise RuntimeError('invalid raw confusion counts')
                    rebuilt=life.pool(originals)
                    if rebuilt!=scopes[scope]:raise RuntimeError('pooled raw-count recomputation mismatch')
            rows.setdefault(arm,{})[cond]=summary['pooled'][cond][arm]['noboundary']
    anchor=summaries['TSF']
    # Shared baselines are evaluated in every arm; they must actually agree.
    for arm,summary in summaries.items():
        a=summary['signature']['training'];b=anchor['signature']['training']
        for field in ('experts','sources','base_sha256','split_sha256','input_manifest_sha256','torch_version',
                      'matmul_allow_tf32','cudnn_allow_tf32','expert_micro_batch','gate_batch','backward_calls_per_step'):
            if a[field]!=b[field]:raise RuntimeError('cross-arm binding mismatch '+field)
        for cond in e.CONDITIONS:
            for tile in ('3_11','5_10'):
                for name in e.FIXED:
                    if summary['tiles'][cond][tile][name]['prediction_sha256']!=anchor['tiles'][cond][tile][name]['prediction_sha256']:
                        raise RuntimeError('fixed baseline differs across arms/devices')
    for name in e.FIXED:rows[name]={cond:anchor['pooled'][cond][name]['noboundary'] for cond in e.CONDITIONS}
    def metric(name,cond,tile=None):
        value=(rows[name][cond] if tile is None else
               (summaries[name] if name in ARMS else anchor)['tiles'][cond][tile][name]['scopes']['noboundary'])['mIoU_fg5']
        if value is None:raise RuntimeError('undefined primary metric')
        return value*100
    def family(name,conds,tile=None):return sum(metric(name,c,tile) for c in conds)/len(conds)
    composites={name:sum(family(name,conds) for conds in FAMILIES.values())/3 for name in rows}
    comparator=max((*e.FIXED,'T0','TCAP'),key=lambda n:composites[n])
    checks={'primary_gain':composites['TSF']-composites[comparator]>=.2}
    mechanism={n:composites['TSF']-composites[n] for n in ('TS','TF','TSF_CE','TSF_shuffleS','TSF_shuffleF')}
    checks.update({n+'_increment':v>=.1 for n,v in mechanism.items()})
    checks['clean_protection']=metric('TSF','clean')>=metric('R0','clean')-.1
    for tile in ('3_11','5_10'):
        checks['tile_'+tile+'_clean']=metric('TSF','clean',tile)>=metric('R0','clean',tile)-.1
        for name,conds in FAMILIES.items():
            checks['tile_'+tile+'_'+name]=family('TSF',conds,tile)>=family('R0',conds,tile)-(.1 if name=='clean' else .3)
    for name,conds in FAMILIES.items():checks['family_'+name]=family('TSF',conds)>=family('R0',conds)-(.1 if name=='clean' else .3)
    for cond in e.CONDITIONS[-3:]:checks['stress_'+cond]=metric('TSF',cond)>=metric('R0',cond)-.3
    available=[c for c in e.CONDITIONS[:11] if c not in ('aux_zero','aux_local_zero_q1')]
    def macro(name,field):
        return sum(rows[name][c]['all'][field]/max(1,rows[name][c]['all']['valid']) for c in available)/len(available)
    h,h0=macro('TSF','harm'),macro('M0_safe','harm');r,r0=macro('TSF','rescue'),macro('M0_safe','rescue')
    checks['harm_reduction']=h==0 if h0==0 else h<=.9*h0
    checks['rescue_retention']=None if r0==0 else r>=.9*r0
    worst=max(anchor['tiles'][c][t]['TSF']['scopes']['noboundary']['all']['harm']/max(1,anchor['tiles'][c][t]['TSF']['scopes']['noboundary']['all']['valid'])
              for c in e.CONDITIONS[:11] for t in ('3_11','5_10'))
    checks['worst_harm']=worst<=.005
    checks['missing_fallback']=all(anchor['tiles'][c][t][n]['missing_logits_equal'] for c in e.CONDITIONS for t in ('3_11','5_10') for n in anchor['tiles'][c][t])
    return dict(composite_pp=composites,strongest_comparator=comparator,primary_gain_pp=composites['TSF']-composites[comparator],
      mechanism_gain_pp=mechanism,macro_harm=h,reference_harm=h0,macro_rescue=r,reference_rescue=r0,
      rescue_retention_ratio=None if r0==0 else r/r0,worst_tile_condition_harm=worst,checks=checks,
      eligible_to_plan_confirmation=all(v is True for v in checks.values()),
      meaning='development engineering screen; no independent confirmation; NA rescue does not prove retention')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();scope=Path('/home/jovyan/zzx').resolve();args.output.resolve().relative_to(scope)
    paths=json.loads(args.manifest.read_text())
    summaries={}
    for arm,path in paths.items():
        path=Path(path).resolve();path.relative_to(scope);summaries[arm]=json.loads(path.read_text())
        complete=path.parents[1]/'formal_complete.json'
        if not complete.exists() or json.loads(complete.read_text()).get('global_step')!=4000:raise RuntimeError('formal completion evidence absent')
    result=screen(summaries)
    with args.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
