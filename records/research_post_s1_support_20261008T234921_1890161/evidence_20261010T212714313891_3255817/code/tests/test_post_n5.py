"""CPU scientific contracts and real controller paths; no data/GPU access."""
import copy,importlib.util,json,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
torch.set_num_threads(1)
import post_n5_common as c
import post_n5_data as data
from post_d30_evaluation import metric
from summarize_post_n5 import screen
def fixture(root):
    parent=dict(training=dict(steps=8000,seed=42,physical_batch=16,gradient_accumulation=False,validation_steps=[4000,8000],selection_states=['clean','dsm_missing','rgb_missing']),
        physical_gpus=[0,1],data=dict(fit12=['f'+str(i) for i in range(12)],validation=['3_11','5_10'],test6_loaded=False,independent_final_loaded=False),
        runtime={},evaluation=dict(primary=['clean','dsm_missing','rgb_missing'],missing=['dsm_missing','rgb_missing'],local={'r':['rgb_local_q1'],'d':['dsm_local_q1']},families={'C':['clean'],'QR':['clean'],'QD':['clean'],'QJ':['clean']}),
        augmentation=dict(rgb=['clean'],dsm=['clean'],rgb_probability=0.,dsm_probability=0.,availability={'full':1.},local_shapes=['q1']),experts={},expected_configs={},input_manifest_sha256='x')
    return c.make_plan(root,root/'records/new','commit',parent)
def load_controller():
    spec=importlib.util.spec_from_file_location('n5_controller_test',ROOT/'scripts/control_post_n5.py');m=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{'fcntl':types.SimpleNamespace(flock=lambda *a:None,LOCK_EX=2,LOCK_NB=4)} if os.name!='posix' else {}):spec.loader.exec_module(m)
    return m
def summary(value,conditions):
    cm=np.zeros((6,6),np.int64)
    for i in range(6):cm[i,i]=value;cm[i,(i+1)%6]=10000-value
    block=dict(metrics={'candidate':{'valid':metric(cm)}})
    return dict(tiles={key:{t:dict(scopes={s:copy.deepcopy(block) for s in ('full','noboundary')}) for t in ('3_11','5_10')} for key in conditions},
        pooled={key:{s:dict(metrics={'candidate':{'valid':metric(cm*2)}}) for s in ('full','noboundary')} for key in conditions},test6_loaded=False,independent_final_loaded=False)
class N5Tests(unittest.TestCase):
    def test_contract_rejects_timeout_none_scope_seed_candidate(self):
        p=fixture(Path('root'));c.validate(p)
        for v in (None,True,0,-1,float('nan'),float('inf')):
            q=copy.deepcopy(p);q['runtime']['per_job_timeout_hours']=v
            with self.assertRaises(ValueError):c.validate(q)
        for key,val in (('physical_gpus',[0,2]),('initial_checkpoint',{'sha256':'wrong'})):
            q=copy.deepcopy(p);q[key]=val
            with self.assertRaises(ValueError):c.validate(q)
    def test_schedule_exact_rule_direction_counts(self):
        counts={}
        for j in c.IDS[1:]:
            rules=[data.rule_at(j,s) for s in range(8000)];counts[j]={r:rules.count(r) for r in set(rules)}
        self.assertEqual(counts['N5-1'],{'U':8000});self.assertEqual(counts['N5-2'],{'H':4000,'L':4000})
        self.assertEqual(counts['N5-3'],{'U':4000,'H':2000,'L':2000})
        self.assertEqual(sum(i%2==0 for i in range(8,16)),4)
    def test_all_four_masks_geometry_area_T_maximum(self):
        rng=np.random.default_rng(7);item=dict(optical=rng.random((768,752,3),dtype=np.float32),dsm=rng.random((768,752),dtype=np.float32))
        shape=[];masks={}
        for r in ('U','H','L','T'):
            m,b=data.make_mask(item,r,'tile');shape.append([(x[2],x[3]) for x in b]);masks[r]=m
            self.assertEqual(int(m.sum())*4,m.size)
        self.assertTrue(all(x==shape[0] for x in shape))
        score=__import__('post_n2_masks').scores(item['optical'],item['dsm'])['L']
        self.assertGreaterEqual(float(score[masks['T']].mean()),float(score[masks['L']].mean()))
    def test_crop_flip_whole_tile_masks_exact_quarter_and_clean_identical(self):
        rng=np.random.default_rng(4);item=dict(optical=rng.random((768,768,3),dtype=np.float32),dsm=rng.random((768,768),dtype=np.float32),full_gt=np.zeros((768,768),np.uint8))
        spec=dict(fy=.83,fx=.91,vflip=True,hflip=True)
        clean=data.native_sample(item,spec)
        for r in ('U','H','L'):
            m,_=data.make_mask(item,r,'tile');op,ds,gt,missing=data.native_sample(item,spec,m)
            self.assertTrue(torch.equal(op,clean[0]));self.assertTrue(torch.equal(ds,clean[1]));self.assertEqual(int(missing.sum()),65536)
    def test_actual_dataset_masks_and_supervision_matched(self):
        rng=np.random.default_rng(8);item=dict(optical=rng.random((768,768,3),dtype=np.float32),dsm=rng.random((768,768),dtype=np.float32),full_gt=np.zeros((768,768),np.uint8))
        masks={r:data.make_mask(item,r,'f0')[0] for r in ('U','H','L')}
        aug={'random_scale_min':.5,'random_scale_max':2.,'vertical_flip_p':.5,'horizontal_flip_p':.5}
        p=fixture(Path('root'));samples=[]
        with patch.object(data,'load_mask',side_effect=lambda b,t,r:(masks[r],{})):
            for j in p['jobs']:
                ds=data.Crops({'f0':item},['f0'],aug,p,job=j,base=Path('b'))
                samples.append(ds[2*16+8])
        for s in samples[1:]:
            self.assertTrue(torch.equal(s['rgb'],samples[0]['rgb']));self.assertTrue(torch.equal(s['gt'],samples[0]['gt']))
            self.assertEqual(int((~s['rm2']).sum()),65536);self.assertTrue(s['dm2'].all());self.assertEqual(int(s['rgb2'][:,~s['rm2']].abs().sum()),0)
        self.assertTrue(all(torch.equal(s['rm2']|s['dm2'],torch.ones_like(s['gt'],dtype=torch.bool)) for s in samples))
    def test_objective_valid_supervision_and_gradients(self):
        class Dummy(torch.nn.Module):
            def __init__(self):super().__init__();self.p=torch.nn.Parameter(torch.arange(6,dtype=torch.float32))
            def forward(self,rgb,ds,rm,dm,return_parts=True):
                z=self.p[None,:,None,None].expand(len(rgb),6,*ds.shape[-2:]);return dict(logits=z,rgb=z,dsm=z)
        m=Dummy();gt=torch.zeros((2,16,16),dtype=torch.long);rm=torch.ones_like(gt,dtype=torch.bool);rm[:,:,:4]=False;dm=torch.ones_like(rm)
        b=dict(gt=gt,rgb=torch.ones(2,3,16,16),aux=torch.ones(2,16,16),rgb2=torch.ones(2,3,16,16),aux2=torch.ones(2,16,16),rm2=rm,dm2=dm)
        loss,n=data.objective(m,b);loss.backward();self.assertTrue(torch.isfinite(m.p.grad).all());self.assertEqual(n['aug_fusion_pixels'],512);self.assertEqual(n['aug_rgb_pixels'],384);self.assertEqual(n['aug_dsm_pixels'],512)
    def monitor(self,fail=False,artifact=False):
        ctl=load_controller()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);base=root/'n5';(base/'logs').mkdir(parents=True);p=fixture(root);c.write(base/'plan.json',p);state=c.initial_state(p);calls=[]
            if artifact:(base/'jobs/N5-0').mkdir(parents=True)
            def spawn(cmd,**kwargs):
                j=cmd[cmd.index('--job')+1];calls.append(j)
                if not fail:c.write(base/'jobs'/j/'complete.json',{})
                return types.SimpleNamespace(pid=55,poll=Mock(return_value=2 if fail else 0),terminate=Mock(),kill=Mock())
            if artifact:
                with self.assertRaisesRegex(RuntimeError,'existing job'):ctl.run_stage(root,base,p,state,{}, {},lambda *a:None,popen=spawn,sleep=lambda x:None)
                self.assertEqual(calls,[]);return
            # Actual run_stage still checks completion presence before the binding validator.
            with patch.object(ctl,'job_complete'):
                ok=ctl.run_stage(root,base,p,state,{}, {},lambda *a:None,popen=spawn,sleep=lambda x:None)
            return ok,calls,state
    def test_actual_dispatch_all_four_then_exit(self):
        ok,js,st=self.monitor();self.assertTrue(ok);self.assertEqual(js,['N5-0','N5-1','N5-2','N5-3']);self.assertTrue(all(x['status']=='COMPLETE' for x in st['jobs'].values()))
    def test_actual_failure_stops_other_lane(self):
        ok,js,st=self.monitor(fail=True);self.assertFalse(ok);self.assertEqual(js,['N5-0'])
    def test_existing_partial_directory_never_retried(self):self.monitor(artifact=True)
    def test_actual_null_timeout_before_dispatch(self):
        ctl=load_controller();p=fixture(Path('root'));p['runtime']['per_job_timeout_hours']=None
        with patch.object(ctl.subprocess,'Popen') as spawn:
            with self.assertRaises(ValueError):ctl.run_stage(Path('r'),Path('b'),p,c.initial_state(p),{}, {},lambda *a:None)
            spawn.assert_not_called()
    def test_main_predecessor_failure_never_prepares_or_dispatches(self):
        ctl=load_controller()
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'records').mkdir();b=r/'n5';b.mkdir();p=fixture(r);c.write(b/'plan.json',p);c.write(b/'queue_status.json',c.initial_state(p))
            with patch.object(ctl,'directories',return_value=(r,b)),patch.object(ctl,'verify_snapshot'),patch.object(ctl,'released',side_effect=RuntimeError('not released')),patch.object(sys,'argv',['ctl','--root',str(r),'--directory',str(b)]),patch.object(ctl.subprocess,'run') as run,patch.object(ctl.subprocess,'Popen') as pop:
                with self.assertRaisesRegex(RuntimeError,'not released'):ctl.main()
                run.assert_not_called();pop.assert_not_called()
                self.assertEqual(c.read(b/'queue_status.json')['status'],'CONTROLLER_INTERRUPTED')
    def test_fixed_gate_rejects_unsafe_and_fixed_reverse(self):
        p=fixture(Path('r'));p['N5_old_random_conditions']=['dsm_missing','rgb_missing']
        old=['clean','dsm_missing','rgb_missing'];new=[d+'_'+r for d in ('rgb','dsm') for r in ('U','H','L','T')]
        ds={j:{tag:summary(8000,old) for tag in ('evaluation','fixed8000')} for j in c.IDS}
        ns={j:{tag:summary(8200 if j=='N5-3' else 8000,new) for tag in ('content_evaluation','content_fixed8000')} for j in c.IDS}
        with patch('summarize_post_n5.retention',return_value={}):
            self.assertTrue(screen(ds,ns,p)['passed'])
            ns['N5-3']['content_fixed8000']=summary(7900,new);self.assertFalse(screen(ds,ns,p)['passed'])
            ns['N5-3']['content_fixed8000']=summary(8200,new);ds['N5-3']['evaluation']=summary(7900,old);self.assertFalse(screen(ds,ns,p)['passed'])
    def test_bound_initial_full_state_loads_before_fresh_optimizer(self):
        import run_post_n5 as worker
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);path=r/'selected.pth';model=torch.nn.Linear(2,2);source=torch.nn.Linear(2,2)
            state=dict(model=source.state_dict(),signature={'x':1},global_step=8000)
            torch.save(state,path);p={'initial_checkpoint':{'path':str(path)}}
            with patch.object(worker,'sha',return_value=c.BASE_SHA),patch.object(worker,'bind_model',return_value=({},None,dict(signature={'x':1},selected={'step':8000}))):
                worker.load_initial(model,r,p)
                self.assertTrue(all(torch.equal(v,source.state_dict()[n]) for n,v in model.state_dict().items()))
                optimizer=torch.optim.AdamW(model.parameters());self.assertEqual(len(optimizer.state),0)
                state['global_step']=4000;torch.save(state,path)
                with self.assertRaisesRegex(RuntimeError,'state binding'):worker.load_initial(model,r,p)
    def test_main_calls_summary_and_records_final_exit(self):
        ctl=load_controller()
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/'records').mkdir();b=r/'n5';b.mkdir();p=fixture(r);c.write(b/'plan.json',p);c.write(b/'queue_status.json',c.initial_state(p))
            commands=[]
            def run(cmd,**kw):
                commands.append(cmd)
                if any(str(x).endswith('summarize_post_n5.py') for x in cmd):c.write(b/'n5_screen.json',{'passed':False})
            with patch.object(ctl,'directories',return_value=(r,b)),patch.object(ctl,'verify_snapshot'),patch.object(ctl,'released',return_value={}),patch.object(sys,'argv',['ctl','--root',str(r),'--directory',str(b)]),patch.object(ctl.subprocess,'run',side_effect=run),patch.object(ctl.subprocess,'check_output',return_value='0, GPU-A\n1, GPU-B\n'),patch.object(ctl,'run_stage',return_value=True):
                self.assertEqual(ctl.main(),0)
                self.assertTrue(str(commands[-1][2]).endswith('summarize_post_n5.py'))
                self.assertEqual(c.read(b/'queue_status.json')['status'],'N5_COMPLETE_AWAITING_REVIEW')
    def test_upload_roundtrip_tamper(self):
        import upload_post_n5_records as u
        raw=json.dumps({'data':[3]*20000}).encode();packed=u.encode_record(raw);self.assertEqual(u.decode_record(packed),raw)
        x=json.loads(packed);x['original_sha256']='bad'
        with self.assertRaises(ValueError):u.decode_record(json.dumps(x).encode())
if __name__=='__main__':unittest.main()
