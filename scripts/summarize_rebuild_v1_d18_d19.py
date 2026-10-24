"""Frozen single-seed screening and conditional allocation, without image access."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'configs/rebuild_v1/d18_d19_night_20260927.json'
OUT = ROOT/'records/rebuild_v1_d18_d19_20260927'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def scores(summary, cfg):
    values = {k:v['pooled']['noboundary']['metrics']['mIoU_fg5']*100 for k,v in summary['conditions'].items()}
    families = {k:sum(values[c] for c in cs)/len(cs) for k,cs in cfg['families'].items()}
    return values, families, sum(families.values())/len(families)


def assess(candidate, controls, baseline, data, cfg):
    required = [candidate, baseline]+controls
    if any(a not in data for a in required):
        return dict(arm=candidate, status='INCOMPLETE')
    sc = {a:scores(data[a],cfg) for a in required}
    guard = cfg['screen']
    gain = sc[candidate][2]-max(sc[a][2] for a in controls)
    families = {k:sc[candidate][1][k]-sc[baseline][1][k] for k in cfg['families']}
    tile_families = {}
    for tile in ('3_11', '5_10'):
        values = {c:100*(data[candidate]['conditions'][c]['tiles'][tile]['metrics']['noboundary']['metrics']['mIoU_fg5']-
                         data[baseline]['conditions'][c]['tiles'][tile]['metrics']['noboundary']['metrics']['mIoU_fg5'])
                  for c in cfg['evaluation_conditions']}
        tile_families[tile] = {k:sum(values[c] for c in cs)/len(cs) for k,cs in cfg['families'].items()}
    checks = dict(gain=gain>=guard['gain_pp'], clean=families['clean']>=-guard['clean_loss_pp'],
        families=min(families.values())>=-guard['family_loss_pp'],
        tile_clean=all(v['clean']>=-guard['tile_clean_loss_pp'] for v in tile_families.values()),
        tile_families=all(min(v.values())>=-guard['tile_family_loss_pp'] for v in tile_families.values()))
    def hr(arm):
        rows = [data[arm]['conditions'][c]['joint_noboundary'] for c in cfg['families']['aux_quality']]
        valid = sum(x['valid'] for x in rows)
        return sum(x['only_r01_correct'] for x in rows)/valid, sum(x['only_candidate_correct'] for x in rows)/valid
    h,r = hr(candidate)
    hb,rb = hr(baseline)
    return dict(arm=candidate,status='COMPLETE',passed=all(checks.values()),checks=checks,
        macro_gain_pp=gain,baseline=baseline,controls=controls,family_delta_pp=families,
        tile_family_delta_pp=tile_families,harm_percent=100*h,rescue_percent=100*r,
        negative_transfer_claim_supported=h<hb and rb>0 and r>=guard['rescue_retention']*rb)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--gate',action='store_true')
    args=ap.parse_args()
    cfg=read(CONFIG)
    checksum=hashlib.sha256(CONFIG.read_bytes()).hexdigest()
    data={}
    for arm in cfg['arms']:
        path=OUT/f'{arm}_seed42/summary.json'
        if not path.exists():
            continue
        s=read(path)
        if s['smoke'] or s['seed']!=42 or s['config_sha256']!=checksum or s['test6_loaded']:
            raise RuntimeError(f'invalid completed summary: {arm}')
        if set(s['conditions']) != set(cfg['evaluation_conditions']+cfg['diagnostics']):
            raise RuntimeError(f'incomplete conditions: {arm}')
        data[arm]=s
    rows=[assess(a,c,b,data,cfg) for a,c,b in (
        ('P2',['P0','P1'],'P0'),('C2',['C0','CP'],'C0'),('C3',['C1','CP'],'C0'),
        ('C4',['C3','C5'],'C0'))]
    trigger=any(x['arm'] in ('C2','C3') and x.get('passed') for x in rows)
    missing_conditional=[a for a in cfg['conditional_arms'] if a not in data] if trigger else []
    result=dict(status='COMPLETE' if all(a in data for a in cfg['base_arms']) and not missing_conditional else 'INCOMPLETE',
        seed=42,test6_loaded=False,val2_exploratory=True,config_sha256=checksum,
        missing_base=[a for a in cfg['base_arms'] if a not in data],
        missing_conditional=missing_conditional,
        conditional_trigger=trigger,conditional_completed=[a for a in cfg['conditional_arms'] if a in data],
        decisions=rows,candidates=[x['arm'] for x in rows if x.get('passed')],
        score_rows=[dict(arm=a,macro_percent=scores(d,cfg)[2],families=scores(d,cfg)[1]) for a,d in data.items()],
        seed17_policy='not scheduled; inspect candidate and matched controls after review')
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/('conditional_gate.json' if args.gate else 'decision.json')
    tmp=target.with_suffix('.tmp')
    tmp.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    tmp.replace(target)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    main()
