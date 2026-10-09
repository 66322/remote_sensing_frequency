"""Synthetic CPU validation of registered model/data/queue and gate paths."""
import copy,os,sys,tempfile,types,unittest,subprocess
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
torch.set_num_threads(1);SCRATCH=ROOT/'test_scratch';SCRATCH.mkdir(exist_ok=True)
import post_n3_s1_common as c
from model.post_n3_s1_model import RegionBlock,assign_regions,grouped,Continuation
from model.rebuild_v1_post_ab_n1 import N1Segmenter
from model.post_n5_cross_paths import CrossPaths
from control_post_n3_s1 import run_stage
from post_ab_n1_data import objective
from post_d30_evaluation import metric
from summarize_post_n3_s1 import gates
from unittest.mock import patch
class Expert(torch.nn.Module):
    def __init__(self,rgb):
        super().__init__();self.is_rgb=rgb;self.p=torch.nn.Parameter(torch.tensor(1.))
        self.net=torch.nn.Module();self.net.encoder=torch.nn.Module();self.net.encoder.blocks=torch.nn.ModuleList([torch.nn.Identity() for _ in range(12)])
        self.net.transformer=torch.nn.Module();self.net.transformer.encoder=torch.nn.Module();self.net.transformer.encoder.layer=torch.nn.ModuleList([torch.nn.Identity() for _ in range(12)])
    def configure(self,joint):pass
    def forward(self,rgb,ds):
        x=rgb.mean(1,keepdim=True) if self.is_rgb else ds[:,None]
        x=torch.nn.functional.avg_pool2d(x,9,1,4)*self.p
        return torch.cat([x+i*.01 for i in range(6)],1),torch.nn.functional.avg_pool2d(x,4).repeat(1,32,1,1)
def fixture(root):
    parent=dict(data=dict(fit12=[f'f{i}' for i in range(12)],validation=['3_11','5_10'],test6_loaded=False,independent_final_loaded=False),
        physical_gpus=[0,1],experts={},expected_configs={},input_manifest_sha256='x',
        training=dict(steps=8000,seed=42,physical_batch=16,gradient_accumulation=False,validation_steps=[4000,8000],selection_states=['clean','dsm_missing','rgb_missing']),
        design=dict(geometry_conditions=['geom_dx8'],missing_conditions=['rgb_missing']),
        evaluation=dict(primary=['clean','qr','qd','qj'],families={'C':['clean'],'QR':['qr'],'QD':['qd'],'QJ':['qj']}))
    return c.make_plan(root,root/'records/research_post_n3_s1_test','commit',parent)
def base_state(tmp):
    torch.manual_seed(42);m=N1Segmenter(Expert(True),Expert(False),dict(id='N1-2',information_entry='late',adaptation='last4_and_heads')).eval()
    path=Path(tmp)/'base.pth';torch.save(dict(global_step=8000,model=m.state_dict()),path);return m,path,c.sha(path)
def job(j,path,digest):return dict(id=j,initial_checkpoint_path=str(path),initial_checkpoint_sha256=digest,geometry_aug=False)
class NSTests(unittest.TestCase):
    def test_contract_invalid_timeout_scope_budget(self):
        p=fixture(Path('root'));c.validate_plan(p)
        for v in (None,0,-1,True,float('nan'),float('inf')):
            q=copy.deepcopy(p);q['runtime']['per_job_timeout_hours']=v
            with self.assertRaises(ValueError):c.validate_plan(q)
        for key,v in [('physical_gpus',[0,2]),('total_optimizer_steps',80000),('automatic_training_after_stage',True)]:
            q=copy.deepcopy(p);q[key]=v
            with self.assertRaises(ValueError):c.validate_plan(q)
    def test_regions_constant_descriptors_equal_grid_no_label_oracle(self):
        f=torch.ones(2,128,32,32);h=torch.zeros(2,1,32,32);v=torch.ones(2,32,32,dtype=torch.bool)
        grid=assign_regions(f,h,v,'grid')
        self.assertEqual(grid.unique().numel(),64)
        for kind in ('rgb','dsm'):self.assertTrue(torch.equal(grid,assign_regions(f,h,v,kind)))
    def test_region_donors_invalid_and_empty_rows(self):
        x=torch.randn(1,128,32,32);h=torch.zeros(1,1,32,32);v=torch.ones(1,32,32,dtype=torch.bool);v[:,:4,:4]=False
        ids=assign_regions(x,h,v,'rgb');a=grouped(x,ids,v);y=x.clone();y[:,:,:4,:4]=1e8
        self.assertTrue(torch.equal(a,grouped(y,ids,v)));self.assertEqual(float(a[:,:,:4,:4].abs().sum()),0)
        v[:]=False;ids=assign_regions(x,h,v,'dsm');self.assertEqual(float(grouped(x,ids,v).abs().sum()),0)
    def test_region_capacity_all_modes_and_gradient(self):
        counts=[]
        for mode in ('pixel','grid','rgb_region','dsm_region','bilateral'):
            torch.manual_seed(9);m=RegionBlock(mode);counts.append(sum(p.numel() for p in m.parameters()))
            r=torch.randn(1,128,128,128,requires_grad=True);d=torch.randn_like(r,requires_grad=True);h=torch.rand(1,512,512);v=torch.ones(1,128,128,dtype=torch.bool)
            a,b=m(r,d,h,v);(a.square().mean()+b.square().mean()).backward()
            self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in m.parameters()))
            self.assertTrue(torch.isfinite(r.grad).all() and torch.isfinite(d.grad).all())
        self.assertEqual(counts,[32768]*5)
    def test_region_condition_direction_and_graph_detach(self):
        torch.manual_seed(12);r=torch.randn(1,128,32,32,requires_grad=True);v=torch.ones(1,32,32,dtype=torch.bool)
        h=torch.rand(1,1,32,32);a=assign_regions(r,h,v,'dsm');b=assign_regions(r,h.flip(-1),v,'dsm')
        self.assertFalse(torch.equal(a,b));self.assertFalse(a.requires_grad)
    def test_all_nine_full_base_binding_and_exact_shared_state(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            original,path,digest=base_state(tmp);capacities={}
            for j in c.IDS:
                torch.manual_seed(42);m=Continuation(Expert(True),Expert(False),job(j,path,digest))
                for name,value in original.state_dict().items():self.assertTrue(torch.equal(m.state_dict()[name],value),j)
                capacities[j]=sum(p.numel() for p in m.parameters())
            self.assertEqual(len(set(capacities[j] for j in c.IDS[:5])),1);self.assertEqual(len(set(capacities[j] for j in c.IDS[5:])),1)
            self.assertEqual(capacities['N3-0']-capacities['S1-0'],32768)
            with self.assertRaises(RuntimeError):Continuation(Expert(True),Expert(False),job('S1-0',path,'bad'))
    def test_S1_four_forward_paths_equal_bound_diagnostic_graph(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            original,path,digest=base_state(tmp);r=torch.rand(2,3,64,64);d=torch.rand(2,64,64);rm=torch.ones_like(d,dtype=torch.bool);dm=rm.clone();rm[:,16:48,16:48]=False
            for j,path_id in zip(c.IDS[5:],['A1B1C1','A1B0C1','A1B1C0','A1B0C0']):
                m=Continuation(Expert(True),Expert(False),job(j,path,digest)).eval()
                with torch.no_grad():a=m(r,d,rm,dm,True);b=CrossPaths(original,path_id)(r,d,rm,dm,True)
                for name in a:self.assertTrue(torch.equal(a[name],b[name]),(j,name))
    def test_S1_full_missing_other_side_partial_and_neither(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            original,path,digest=base_state(tmp);r=torch.rand(1,3,64,64);d=torch.rand(1,64,64)
            for direction in ('rgb','dsm','neither'):
                rm=torch.ones_like(d,dtype=torch.bool);dm=rm.clone();rm[:,16:48,16:48]=False
                if direction in ('rgb','neither'):rm[:]=False
                if direction in ('dsm','neither'):dm[:]=False
                with torch.no_grad():
                    expect=original(r,d,rm,dm)
                    for j in c.IDS[5:]:self.assertTrue(torch.equal(expect,Continuation(Expert(True),Expert(False),job(j,path,digest))(r,d,rm,dm)))
    def test_S1_objective_loss_denominators_and_gradients(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            _,path,digest=base_state(tmp);gt=torch.zeros(2,64,64,dtype=torch.long);full=torch.ones_like(gt,dtype=torch.bool);rm=full.clone();rm[:,:,:16]=False
            batch=dict(gt=gt,rgb=torch.rand(2,3,64,64),aux=torch.rand(2,64,64),rgb2=torch.rand(2,3,64,64),aux2=torch.rand(2,64,64),rm2=rm,dm2=full)
            exposure=[]
            for j in c.IDS[5:]:
                m=Continuation(Expert(True),Expert(False),job(j,path,digest));loss,n=objective(m,batch);loss.backward();exposure.append(n)
                self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in m.parameters() if p.requires_grad))
            self.assertTrue(all(n==exposure[0] for n in exposure))
    def test_actual_optimizer_encoder_lr_preserved(self):
        from run_post_n3_s1 import optimizer_for
        class M(torch.nn.Module):
            def __init__(self):
                super().__init__();self.rgb_expert=torch.nn.Module();self.rgb_expert.net=torch.nn.Module();self.rgb_expert.net.encoder=torch.nn.Linear(2,2);self.head=torch.nn.Linear(2,2)
        m=M();opt=optimizer_for(m,dict(encoder_last4_lr=1e-5,head_lr=1e-4,betas=[.9,.999],weight_decay=.01))
        self.assertEqual([g['lr'] for g in opt.param_groups],[1e-5,1e-4])
    def monitor(self,fail=False,timeout=False,artifact=False):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            base=Path(tmp);(base/'logs').mkdir();p=fixture(base);state=c.initial_state(p);ticks=[0.];calls=[];procs=[]
            if artifact:(base/'jobs/N3-0').mkdir(parents=True)
            def spawn(cmd,**kwargs):
                j=cmd[cmd.index('--job')+1];calls.append((j,kwargs['env']['CUDA_VISIBLE_DEVICES']))
                class P:
                    pid=100+len(calls);killed=False;terminated=False
                    def poll(self):return (2 if fail else 0) if not timeout else (0 if self.killed else None)
                    def terminate(self):self.terminated=True
                    def kill(self):self.killed=True
                obj=P();procs.append(obj);return obj
            def sleep(t):ticks[0]+=50000
            return run_stage(base,base,p,state,{}, {0:'u0',1:'u1'},lambda *a:None,popen=spawn,sleep=sleep,clock=lambda:ticks[0],accept=lambda *a:None),calls,state,procs
    def test_real_dispatch_all_nine_and_final_exit(self):
        ok,calls,state,_=self.monitor();self.assertTrue(ok)
        self.assertEqual(calls,[(j,str(i%2)) for i,j in enumerate(c.IDS)])
        self.assertTrue(all(x['status']=='COMPLETE' for x in state['jobs'].values()))
    def test_failure_stops_dispatch_no_retry(self):
        ok,calls,_,_=self.monitor(fail=True);self.assertFalse(ok);self.assertEqual(len(calls),1)
    def test_timeout_rc_zero_not_complete(self):
        ok,calls,state,procs=self.monitor(timeout=True);self.assertFalse(ok);self.assertEqual(len(calls),2)
        self.assertTrue(all(p.terminated and p.killed for p in procs));self.assertEqual(state['jobs']['N3-0']['status'],'TIMEOUT')
    def test_existing_artifact_requires_explicit_recovery(self):
        with self.assertRaises(RuntimeError):self.monitor(artifact=True)
    def test_entry_import_help(self):
        env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(ROOT),str(ROOT/'scripts')]),CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
        for n in ('run_post_n3_s1','prepare_post_n3_s1','control_post_n3_s1','status_post_n3_s1','summarize_post_n3_s1','upload_post_n3_s1_records'):
            r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts'/(n+'.py')),'--help'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(r.returncode,0,(n,r.stderr))
    def test_standalone_completed_nine_summary_exit(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            base=Path(tmp);p=fixture(base);c.write(base/'plan.json',p);c.write(base/'mask_manifest.json',{})
            cm=np.eye(6,dtype=np.int64)*100
            joint=dict(shape=[6,6,6,6],dtype='int64',nonzero=[[i*259,100] for i in range(6)])
            def scope(n=1):return dict(metrics={'candidate':{'valid':metric(cm*n)}},joint={'both':joint})
            for j in c.IDS:
                folder=base/'jobs'/j;folder.mkdir(parents=True);(folder/'selected.pth').write_bytes(b'fixture state')
                sig=dict(execution_commit=p['execution_commit'],plan_sha256=c.sha(base/'plan.json'),initial_checkpoint_sha256=c.BASE_SHA,mask_manifest_sha256=c.sha(base/'mask_manifest.json'))
                done=dict(global_step=8000,signature=sig,selected_checkpoint_sha256=c.sha(folder/'selected.pth'))
                for tag in ('evaluation','fixed8000','support_evaluation','support_fixed8000'):
                    keys=['rgb_U','dsm_U'] if tag.startswith('support') else p['evaluation']['primary']+['dsm_missing','rgb_missing']
                    row=dict(binding={'training':sig},test6_loaded=False,independent_final_loaded=False,
                        tiles={k:{t:dict(scopes={s:scope() for s in ('full','noboundary')}) for t in p['data']['validation']} for k in keys},
                        pooled={k:{s:scope(2) for s in ('full','noboundary')} for k in keys})
                    c.write(folder/tag/'summary.json',row);done[tag+'_summary_sha256']=c.sha(folder/tag/'summary.json')
                c.write(folder/'complete.json',done)
            env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(ROOT),str(ROOT/'scripts')]),CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
            r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/summarize_post_n3_s1.py'),'--directory',str(base)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(r.returncode,0,r.stderr)
            out=c.read(base/'n3_s1_screen.json');self.assertFalse(out['N3']['passed']);self.assertFalse(out['S1']['passed'])
    def test_fixed_gate_uniform_no_gain_rejects(self):
        p=fixture(Path('root'));data={}
        cm=np.eye(6,dtype=np.int64)*100
        conditions=p['evaluation']['primary']+['dsm_missing','rgb_missing']
        def summary(keys):
            m=dict(metrics={'candidate':{'valid':metric(cm)}})
            return dict(tiles={k:{t:dict(scopes={'noboundary':copy.deepcopy(m)}) for t in p['data']['validation']} for k in keys},
                pooled={k:{'noboundary':copy.deepcopy(m)} for k in keys})
        # retention expects original joint partitions. Patch only that output;
        # the numerical score/gate functions run their actual implementation.
        for j in c.IDS:data[j]=dict(evaluation=summary(conditions),fixed8000=summary(conditions),support_evaluation=summary(['rgb_U','dsm_U']),support_fixed8000=summary(['rgb_U','dsm_U']))
        with patch('summarize_post_n3_s1.retention',return_value={}):out=gates(data,p)
        self.assertFalse(out['N3']['passed']);self.assertFalse(out['S1']['passed']);self.assertFalse(out['S1']['bilateral_candidate'])
if __name__=='__main__':unittest.main()
