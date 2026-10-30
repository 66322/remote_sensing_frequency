"""Synthetic CPU contract tests; no real server image, backbone or GPU run."""
import copy,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
torch.set_num_threads(1);SCRATCH=ROOT/'test_scratch';SCRATCH.mkdir(exist_ok=True)
import post_s1_support_common as c
from model.rebuild_v1_post_ab_n1 import N1Segmenter
from model.post_n5_cross_paths import CrossPaths
from model.post_s1_support_model import SupportResidual,shuffle_context,state_digest
from post_ab_n1_data import objective as inherited_objective
from post_s1_support_evaluation import support_objective as objective
from run_post_s1_support import optimizer_for,verify_gradients
from control_post_s1_support import run_fifo,TASKS
from post_s1_support_evaluation import simple_route,transition
from prepare_post_s1_support import stress_masks
from summarize_post_s1_support import screens,verify_summary
from post_d30_evaluation import infer,metric,encode_joint
class Expert(torch.nn.Module):
    def __init__(self,is_rgb):
        super().__init__();self.is_rgb=is_rgb;self.p=torch.nn.Parameter(torch.tensor(1.))
        self.net=torch.nn.Module();self.net.encoder=torch.nn.Module();self.net.encoder.blocks=torch.nn.ModuleList([torch.nn.Identity() for _ in range(12)])
        self.net.transformer=torch.nn.Module();self.net.transformer.encoder=torch.nn.Module();self.net.transformer.encoder.layer=torch.nn.ModuleList([torch.nn.Identity() for _ in range(12)])
    def configure(self,joint):self.requires_grad_(joint)
    def forward(self,rgb,ds):
        x=rgb.mean(1,keepdim=True) if self.is_rgb else ds[:,None]
        x=torch.nn.functional.avg_pool2d(x,9,1,4)*self.p
        return torch.cat([x+i*.01 for i in range(6)],1),torch.nn.functional.avg_pool2d(x,4).repeat(1,32,1,1)
def fixture(root):
    parent=dict(data=dict(fit12=[f'f{i}' for i in range(12)],validation=['3_11','5_10'],test6_loaded=False,independent_final_loaded=False),
        experts={},input_manifest_sha256='x',expected_configs={},augmentation={},evaluation=dict(primary=['clean','bad'],missing=['rgb_missing','dsm_missing'],
        local={'LR':['rgb_local_q1'],'LD':['dsm_local_q1']},diagnostic=[]),fixed_conditions=['clean','bad','rgb_missing','dsm_missing'],
        training=dict(steps=8000,seed=42,physical_batch=16,gradient_accumulation=False,views_per_crop=2,head_lr=.0002,encoder_last4_lr=.00002,weight_decay=.01,
        betas=[.9,.999],warmup_steps=100,checkpoint_every=500,validation_steps=[4000,8000],selection_states=['clean','dsm_missing','rgb_missing'],validation_batch=8))
    return c.make_plan(root,root/'records/research_post_s1_support_test','commit',parent)
def state(tmp):
    torch.manual_seed(42);m=N1Segmenter(Expert(True),Expert(False),dict(id='N1-2',information_entry='late',adaptation='last4_and_heads')).eval()
    path=Path(tmp)/'base.pth';torch.save(dict(global_step=8000,model=m.state_dict()),path);return m,path,c.sha(path)
def inputs():
    r=torch.rand(2,3,64,64);d=torch.rand(2,64,64);rm=torch.ones_like(d,dtype=torch.bool);dm=rm.clone();rm[:,16:48,16:48]=False
    return r,d,rm,dm
class SupportTests(unittest.TestCase):
    def test_gpu0_budget_timeout_contract(self):
        p=fixture(Path('root'));c.validate(p)
        for value in (None,0,-1,True,float('inf'),float('nan')):
            q=copy.deepcopy(p);q['runtime']['per_job_timeout_hours']=value
            with self.assertRaises(ValueError):c.validate(q)
        for key,value in [('physical_gpus',[0,1]),('max_gpu_workers',2),('total_optimizer_steps',72000),('primary_candidate','P5'),('test_release',True)]:
            q=copy.deepcopy(p);q[key]=value
            with self.assertRaises(ValueError):c.validate(q)
    def test_exact_same_base_and_zero_head_all_ten(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            original,path,digest=state(tmp);r,d,rm,dm=inputs()
            with torch.no_grad():expected=original(r,d,rm,dm)
            capacities=[]
            for j in ['P'+str(i) for i in range(10)]:
                torch.manual_seed(42);m=SupportResidual(Expert(True),Expert(False),c.job_card(j),path,digest).eval()
                self.assertEqual(state_digest(m),state_digest(original))
                with torch.no_grad():self.assertTrue(torch.equal(m(r,d,rm,dm),expected),j)
                capacities.append(sum(p.numel() for p in m.residual.parameters()))
            self.assertEqual(capacities,[20422]*10)
            with self.assertRaises(RuntimeError):SupportResidual(Expert(True),Expert(False),c.job_card('P7'),path,'bad')
    def test_frozen_local_native_support_and_full_missing(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            original,path,digest=state(tmp);m=SupportResidual(Expert(True),Expert(False),c.job_card('P7'),path,digest).eval()
            torch.nn.init.normal_(m.residual[-1].weight,std=.1);r,d,rm,dm=inputs()
            for direction in ('partial','clean','rgb_missing','dsm_missing','neither'):
                a,b=rm.clone(),dm.clone()
                if direction=='clean':a[:]=True
                if direction in ('rgb_missing','neither'):a[:]=False
                if direction in ('dsm_missing','neither'):b[:]=False
                with torch.no_grad():got=m(r,d,a,b,True);base=original(r,d,a,b)
                changed=got['residual_support']
                self.assertTrue(torch.equal(got['logits'].masked_select((~changed)[:,None]),base.masked_select((~changed)[:,None])))
                if direction!='partial':self.assertTrue(torch.equal(got['logits'],base),direction)
    def test_frozen_stats_parameters_optimizer_and_zero_exposure(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            _,path,digest=state(tmp);m=SupportResidual(Expert(True),Expert(False),c.job_card('P7'),path,digest);before=state_digest(m)
            opt=optimizer_for(m,fixture(Path('x'))['training']);self.assertEqual(len(opt.param_groups),1)
            r,d,rm,dm=inputs();gt=torch.zeros_like(d,dtype=torch.long)
            batch=dict(gt=gt,rgb=r,aux=d,rgb2=r,aux2=d,rm2=rm,dm2=dm)
            m.train();loss,_=objective(m,batch);loss.backward();diag=verify_gradients(m);opt.step()
            self.assertEqual(state_digest(m),before);self.assertTrue(any(diag['groups_nonzero'].values()))
            self.assertTrue(all(not e.training for e in (m.rgb_expert,m.dsm_expert)))
            opt.zero_grad(set_to_none=True);batch['rm2']=dm
            loss,_=objective(m,batch);loss.backward();diag=verify_gradients(m)
            self.assertFalse(any(diag['groups_nonzero'].values()));self.assertEqual(m.exposure['residual_support_pixels'],0)
    def test_actual_objective_matches_inherited_and_views_logged(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            _,path,digest=state(tmp);m=SupportResidual(Expert(True),Expert(False),c.job_card('P5'),path,digest).eval()
            r,d,rm,dm=inputs();batch=dict(gt=torch.zeros_like(d,dtype=torch.long),rgb=r,aux=d,rgb2=r,aux2=d,rm2=rm,dm2=dm)
            expected,n=inherited_objective(m,batch);got,denom=objective(m,batch)
            self.assertTrue(torch.equal(expected,got));self.assertTrue(all(denom[k]==v for k,v in n.items()))
            self.assertEqual(set(m.exposure['views']),{'clean','aug'});self.assertGreater(m.exposure['views']['clean']['residual_support_pixels'],0)
    def test_shared_parameters_can_receive_gradient(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            _,path,digest=state(tmp);m=SupportResidual(Expert(True),Expert(False),c.job_card('P3'),path,digest)
            r,d,rm,dm=inputs();m(r,d,rm,dm).square().mean().backward()
            self.assertTrue(m.rgb_expert.p.requires_grad);self.assertIsNotNone(m.rgb_expert.p.grad)
            self.assertTrue(all(p.grad is not None for p in m.residual.parameters()))
    def test_shuffle_changes_missing_context_preserves_strata(self):
        x=torch.arange(64.).reshape(1,1,8,8);mask=torch.ones(1,32,32,dtype=torch.bool);mask[:,:,:16]=False
        y,report=shuffle_context(x,mask);z,_=shuffle_context(x,mask)
        self.assertTrue(torch.equal(y,z));self.assertGreater(report['moved_tokens'],0)
        self.assertFalse(torch.equal(x[:,:,:,:4],y[:,:,:,:4]))
        self.assertEqual(sorted(x[:,:,:,:4].flatten().tolist()),sorted(y[:,:,:,:4].flatten().tolist()))
        self.assertEqual(sorted(x[:,:,:,4:].flatten().tolist()),sorted(y[:,:,:,4:].flatten().tolist()))
    def test_same_weight_policy_invariants(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            m,_,_=state(tmp);r,d,rm,dm=inputs();full=torch.ones_like(rm)
            for a,b in ((full,full),(~full,full),(full,~full),(~full,~full)):
                with torch.no_grad():outputs=[CrossPaths(m,p)(r,d,a,b) for p in c.POLICIES]
                self.assertTrue(all(torch.equal(outputs[0],v) for v in outputs))
    def test_stress_geometry_frozen_and_label_free(self):
        m=stress_masks((128,128));self.assertEqual(int(m['lines64w8'].sum()),128*128//8);self.assertEqual(int(m['blocks64q25'].sum()),128*128//4)
        for n in m:self.assertTrue(np.array_equal(m[n],stress_masks((128,128))[n]))
    def test_route_guards_and_transition_denominators(self):
        a=np.zeros((512,512),np.uint8);b=np.ones_like(a);rm=np.ones_like(a,bool);dm=rm.copy();rm[10:30]=False
        got,use=simple_route(a,b,rm,dm)
        self.assertTrue(np.array_equal(got[use],b[use]));self.assertTrue(np.array_equal(got[~use],a[~use]))
        rm[:]=False;got,_=simple_route(a,b,rm,dm);self.assertTrue(np.array_equal(got,a))
        gt=np.zeros((2,2),np.uint8);ct=np.array([[0,1],[1,0]],np.uint8);ca=np.array([[1,0],[1,0]],np.uint8)
        t=transition(gt,ct,ca,np.ones_like(gt,bool));self.assertEqual((t['valid'],t['rescued'],t['harmed'],t['both_correct'],t['both_wrong']),(4,1,1,1,1))
    def test_native_stitch_outside_support_equal(self):
        class Tiny(torch.nn.Module):
            learned_missing=True
            def __init__(self,correct):
                super().__init__();self.p=torch.nn.Parameter(torch.tensor(0.));self.correct=correct
            def forward(self,r,ds,rm,dm,return_parts=False):
                z=torch.zeros(len(r),6,*ds.shape[-2:]);z[:,0]=2
                f=z.clone();f[:,1]+=3*((~rm)&dm)*int(self.correct)
                return dict(logits=f,rgb=z,dsm=z)
        item=dict(optical=np.zeros((512,768,3),np.float32),dsm=np.zeros((512,768),np.float32))
        rm=np.ones((512,768),bool);dm=rm.copy();rm[127:309,199:489]=False
        a,_=infer(Tiny(False),item,rm,dm,batch=2);b,_=infer(Tiny(True),item,rm,dm,batch=2)
        self.assertTrue(np.array_equal(a['candidate'][rm],b['candidate'][rm]));self.assertTrue((b['candidate'][~rm]==1).all())
    def fifo(self,fail=False,timeout=False,artifact=False):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            base=Path(tmp);(base/'logs').mkdir();p=fixture(base);s=c.initial_state(p);calls=[];ticks=[0.];procs=[]
            if artifact:(base/'jobs/D1').mkdir(parents=True)
            def spawn(cmd,**kw):
                task=cmd[cmd.index('--job')+1];calls.append((task,kw['env']['CUDA_VISIBLE_DEVICES']))
                class Process:
                    pid=101;killed=False;terminated=False
                    def poll(self):return None if timeout and not self.killed else 2 if fail else 0
                    def terminate(self):self.terminated=True
                    def kill(self):self.killed=True
                proc=Process();procs.append(proc);return proc
            def sleep(seconds):ticks[0]+=90000
            result=run_fifo(base,base,p,s,{},popen=spawn,sleep=sleep,clock=lambda:ticks[0],check=lambda u:'GPU0',accept=lambda *a:None)
            return result,calls,s,procs
    def test_fifo_all_twelve_only_gpu0_and_finish(self):
        ok,calls,s,_=self.fifo();self.assertTrue(ok);self.assertEqual(calls,[(j,'0') for j in TASKS])
        self.assertTrue(all(r['status']=='COMPLETE' for r in s['jobs'].values()))
    def test_failure_stops_before_next_no_retry(self):
        ok,calls,s,_=self.fifo(fail=True);self.assertFalse(ok);self.assertEqual(calls,[('D1','0')])
    def test_timeout_rc_zero_still_failure_and_stops(self):
        ok,calls,s,procs=self.fifo(timeout=True);self.assertFalse(ok);self.assertEqual(calls,[('D1','0')]);self.assertEqual(s['jobs']['D1']['status'],'TIMEOUT')
        self.assertTrue(procs[0].terminated and procs[0].killed)
    def test_existing_artifacts_require_recovery(self):
        with self.assertRaises(RuntimeError):self.fifo(artifact=True)
    def test_acceptance_failure_holds_queue(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            base=Path(tmp);(base/'logs').mkdir();p=fixture(base);s=c.initial_state(p)
            class P:
                pid=12
                def poll(self):return 0
            def reject(*a):raise RuntimeError('bad summary')
            ok=run_fifo(base,base,p,s,{},popen=lambda *a,**k:P(),check=lambda u:'GPU0',accept=reject)
            self.assertFalse(ok);self.assertEqual(s['jobs']['D1']['status'],'TECHNICAL_FAILURE')
    def test_calibration_feature_slots_inactive(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            _,path,digest=state(tmp);m=SupportResidual(Expert(True),Expert(False),c.job_card('P9'),path,digest)
            with torch.no_grad():m.residual[-1].weight.fill_(.1)
            r,d,rm,dm=inputs();m(r,d,rm,dm).sum().backward()
            self.assertEqual(float(m.residual[0].weight.grad[:,:256].abs().sum()),0)
    def test_entries_help_no_gpu_or_server_needed(self):
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join([str(ROOT),str(ROOT/'scripts')]))
        for entry in ('enqueue','prepare','run','control','status','summarize','upload'):
            suffix='_records' if entry=='upload' else ''
            path=ROOT/'scripts'/(entry+'_post_s1_support'+suffix+'.py')
            r=subprocess.run([sys.executable,'-B',str(path),'--help'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(r.returncode,0,(entry,r.stderr))
        r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/run_post_s1_support_diagnostics.py'),'--help'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
        self.assertEqual(r.returncode,0,r.stderr)
    def test_gate_uniform_no_gain_rejected_and_no_Q(self):
        p=fixture(Path('root'));cm=np.eye(6,dtype=np.int64)*100
        def s(keys):
            r=dict(metrics={'candidate':{'valid':metric(cm)}})
            return dict(tiles={k:{t:dict(scopes={'noboundary':copy.deepcopy(r)}) for t in p['data']['validation']} for k in keys},
                pooled={k:{'noboundary':copy.deepcopy(r)} for k in keys})
        ordinary={j:s(['clean','bad','rgb_missing','dsm_missing']) for j in c.ORDER};U={j:s(['rgb_U','dsm_U']) for j in c.ORDER}
        E={j:s(c.E_KEYS) for j in ['S1-0','S1-3','R0']+c.ORDER};D1={f'S1-0/{q}':s(['rgb_U','dsm_U']) for q in c.POLICIES}
        result=screens(p,ordinary,U,E,D1,ordinary['P0'],U['P0'],U['P0'])
        self.assertFalse(result['P7_passed']);self.assertFalse(result['E_passed']);self.assertEqual(result['Q_status'],'SKIPPED_GATE')
    def test_standalone_summary_complete_twelve_tasks_exit(self):
        import summarize_post_s1_support as module
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);base=root/'records/research_post_s1_support_fixture';base.mkdir(parents=True)
            p=fixture(root);c.write(base/'plan.json',p);c.write(base/'mask_manifest.json',{})
            cm=np.eye(6,dtype=np.int64)*100;arr=np.zeros((6,)*4,np.int64)
            for i in range(6):arr[i,i,i,i]=100
            def scope(n):return dict(metrics={k:{'valid':metric(cm*n)} for k in ('candidate','fixed_rgb','fixed_dsm')},joint={'valid':encode_joint(arr*n)})
            def summary(keys):return dict(test6_loaded=False,independent_final_loaded=False,tiles={k:{t:dict(scopes={s:scope(1) for s in ('full','noboundary')}) for t in p['data']['validation']} for k in keys},pooled={k:{s:scope(2) for s in ('full','noboundary')} for k in keys})
            ordinary=['clean','bad','rgb_missing','dsm_missing']
            for j in c.ORDER:
                c.write(base/'jobs'/j/'evaluation/summary.json',summary(ordinary));c.write(base/'jobs'/j/'support_evaluation/summary.json',summary(['rgb_U','dsm_U']))
                c.write(base/'jobs'/j/'model_capacity.json',{});c.write(base/'jobs'/j/'progress.json',{})
            d={}
            for name in c.SHAS:
                for policy in c.POLICIES:
                    f=base/'jobs/D1'/name/policy/'summary.json';c.write(f,summary(['rgb_U','dsm_U']));d[name+'/'+policy]=dict(path=str(f),sha256=c.sha(f))
            c.write(base/'jobs/D1/summary.json',dict(records=d))
            es={}
            for name in ['S1-0','S1-3','R0']+c.ORDER:
                f=base/'jobs/E'/name/'evaluation/summary.json';c.write(f,summary(c.E_KEYS));es[name]=dict(path=str(f),sha256=c.sha(f))
            c.write(base/'jobs/E/summary.json',dict(records=es))
            ref=root/'records'/c.SOURCE_NAME/'jobs/S1-0'
            c.write(ref/'evaluation/summary.json',summary(ordinary));c.write(ref/'support_evaluation/summary.json',summary(['rgb_U','dsm_U']))
            c.write(base/'R0_U/summary.json',summary(['rgb_U','dsm_U']))
            with patch.object(module,'verify_snapshot'),patch.object(module,'accept_worker'),patch.object(module,'source_binding'),patch.object(sys,'argv',['summary','--directory',str(base)]):module.main()
            r=c.read(base/'support_screen.json');self.assertFalse(r['P7_passed']);self.assertFalse(r['E_passed']);self.assertEqual(r['new_optimizer_updates'],80000)
    def test_worker_completion_binding_and_tamper(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            base=Path(tmp);p=fixture(base);c.write(base/'plan.json',p);c.write(base/'mask_manifest.json',{});c.write(base/'code_manifest.json',{})
            job=next(j for j in p['jobs'] if j['id']=='P7');f=base/'jobs/P7';f.mkdir(parents=True);(f/'selected.pth').write_bytes(b'fixed8000')
            row=dict(execution_commit=p['execution_commit'],plan_sha256=c.sha(base/'plan.json'),code_manifest_sha256=c.sha(base/'code_manifest.json'),
                signature=c.signature(base,p,job),global_step=8000,selected={'step':8000},artifacts={'selected.pth':c.sha(f/'selected.pth')},test6_loaded=False,independent_final_loaded=False)
            c.write(f/'complete.json',row);c.accept_worker(base,'P7',p)
            (f/'selected.pth').write_bytes(b'tampered')
            with self.assertRaises(RuntimeError):c.accept_worker(base,'P7',p)
    def test_raw_integer_summary_rejects_corruption(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            cm=np.eye(6,dtype=np.int64)*100;arr=np.zeros((6,)*4,np.int64)
            for i in range(6):arr[i,i,i,i]=100
            def scope(n):
                return dict(metrics={k:{'valid':metric(cm*n)} for k in ('candidate','fixed_rgb','fixed_dsm')},joint={'valid':encode_joint(arr*n)})
            s=dict(test6_loaded=False,independent_final_loaded=False,tiles={'clean':{t:dict(scopes={k:scope(1) for k in ('full','noboundary')}) for t in ('3_11','5_10')}},
                pooled={'clean':{k:scope(2) for k in ('full','noboundary')}})
            path=Path(tmp)/'summary.json';c.write(path,s);verify_summary(path)
            s['pooled']['clean']['noboundary']['metrics']['candidate']['valid']['cm'][0][0]+=1;c.write(path,s)
            with self.assertRaises(RuntimeError):verify_summary(path)
if __name__=='__main__':unittest.main()
