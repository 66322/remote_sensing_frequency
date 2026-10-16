"""Frozen exploratory investment screen; incomplete work is never a negative."""
import d16_d17_portfolio as p


def scores(summary,cfg):
    values = {k:v['pooled']['noboundary']['metrics']['mIoU_fg5']*100 for k,v in summary['conditions'].items()}
    families = {k:sum(values[c] for c in cs)/len(cs) for k,cs in cfg['families'].items()}
    return values,families,sum(families.values())/len(families)


def main():
    cfg = p.read(p.CONFIG)
    data,missing = {},[]
    for seed in cfg['seeds']:
        for arm in cfg['arms']:
            file = p.evaluation_output(arm,seed)/'summary.json'
            if not file.is_file():
                missing.append(f'{arm}/{seed}')
                continue
            value = p.read(file)
            if value['smoke'] or value['test6_loaded'] or value['signature']['training']['config_sha256'] != p.sha(p.CONFIG) or set(value['conditions']) != set(cfg['evaluation_conditions']):
                raise RuntimeError(f'invalid summary {file}')
            data[arm,seed] = value
    result = dict(status='INCOMPLETE' if missing else 'COMPLETE',missing=missing,
                  test6_loaded=False,val2_exploratory=True,config_sha256=p.sha(p.CONFIG))
    if not missing:
        decisions = []
        guard = cfg['screen']
        for seed in cfg['seeds']:
            sc = {a:scores(data[a,seed],cfg) for a in cfg['arms']}
            for candidate,controls in (('A2',['A0','A1','A3']),('B1',['A0','B2'])):
                gain = sc[candidate][2] - max(sc[a][2] for a in controls)
                clean_delta = sc[candidate][0]['clean']-sc['A0'][0]['clean']
                family_delta = {k:sc[candidate][1][k]-sc['A0'][1][k] for k in cfg['families']}
                checks = dict(gain=gain>=guard['gain_pp'],clean=clean_delta>=-guard['clean_loss_pp'],
                              families=min(family_delta.values())>=-guard['family_loss_pp'])
                family = cfg['families']['aux_quality']
                def hr(arm):
                    counts = [data[arm,seed]['conditions'][c]['joint_noboundary'] for c in family]
                    valid = sum(x['valid'] for x in counts)
                    return sum(x['only_r01_correct'] for x in counts)/valid,sum(x['only_candidate_correct'] for x in counts)/valid
                h,r = hr(candidate)
                hc,rc = hr('A0')
                # This is additional evidence for a harm-reduction claim, not the accuracy screen.
                negative_transfer = h<hc and r>=guard['rescue_retention']*rc and rc>0
                specific_effect = (sc['A2'][2]-sc['A0'][2])-(sc['A5'][2]-sc['A4'][2]) if candidate=='A2' else None
                tile_deltas = {tile:{c:(data[candidate,seed]['conditions'][c]['tiles'][tile]['metrics']['noboundary']['metrics']['mIoU_fg5']-
                                         data['A0',seed]['conditions'][c]['tiles'][tile]['metrics']['noboundary']['metrics']['mIoU_fg5'])*100
                                     for c in cfg['evaluation_conditions']} for tile in data[candidate,seed]['conditions']['clean']['tiles']}
                tile_families = {tile:{family:sum(values[c] for c in conditions)/len(conditions)
                                 for family,conditions in cfg['families'].items()} for tile,values in tile_deltas.items()}
                checks['tile_families'] = all(min(values.values())>=-guard['tile_family_loss_pp'] for values in tile_families.values())
                checks['tile_clean'] = all(values['clean']>=-guard['tile_clean_loss_pp'] for values in tile_families.values())
                decisions.append(dict(arm=candidate,seed=seed,passed=all(checks.values()),checks=checks,
                    macro_gain_pp=gain,clean_delta_pp=clean_delta,family_delta_pp=family_delta,
                    harm_percent=h*100,rescue_percent=r*100,negative_transfer_claim_supported=negative_transfer,
                    dsm_specific_effect_pp=specific_effect,tile_deltas_pp=tile_deltas,tile_family_delta_pp=tile_families))
                print(candidate,seed,'pass',all(checks.values()),'gain_pp',round(gain,4),'checks',checks,flush=True)
        result['decisions'] = decisions
        result['candidates'] = [a for a in ('A2','B1') if all(x['passed'] for x in decisions if x['arm']==a)]
        result['next_action'] = 'matched longer-budget confirmation; inspect tile guards' if result['candidates'] else 'close tested variants; prepare matched pretrained-adapter comparison'
        print('CANDIDATES',result['candidates'])
    p.write(p.ROOT/'records/rebuild_v1_d16_d17_20260926/decision.json',result)
    print(result['status'],'missing=',missing,flush=True)
    if missing:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
