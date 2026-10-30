"""CPU-only behavioral and handover regression checks; no server data or GPU."""
import copy,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
torch.set_num_threads(1)
from test_post_s1_support import Expert,state,inputs,fixture as old_fixture,SCRATCH
import post_s1_transfer_common as c
from model.post_s1_transfer_model import PrivateDecoder,state_digest,HEADS
from model.post_n5_cross_paths import CrossPaths
from post_s1_support_evaluation import support_objective
from run_post_s1_transfer import optimizer_for,verify_gradients
from control_post_s1_transfer import run_fifo,wait_predecessor
from summarize_post_s1_transfer import screens
from post_d30_evaluation import metric

def fixture(root):return c.make_plan(root,root/'records'/c.PREFIX,'commit',old_fixture(root))
def model(path,digest,j):
    torch.manual_seed(42)
    return PrivateDecoder(Expert(True),Expert(False),c.job_card(j),path,digest,dict(path=path,sha256=digest))
class TransferTests(unittest.TestCase):
    def test_contract_gpu_budget_donor_and_timeouts(self):
        p=fixture(Path('root'));c.validate(p)
        for key,value in [('physical_gpus',[0,1]),('max_gpu_workers',2),('total_optimizer_steps',72000),('primary_candidate','T5'),('test_release',True)]:
            q=copy.deepcopy(p);q[key]=value
            with self.assertRaises(ValueError):c.validate(q)
        for v in (None,0,-1,True,float('nan'),float('inf')):
            q=copy.deepcopy(p);q['runtime']['per_job_timeout_hours']=v
            with self.assertRaises(ValueError):c.validate(q)
        q=copy.deepcopy(p);q['donors']['S1-3']['sha256']='wrong'
        with self.assertRaises(ValueError):c.validate(q)
    def test_same_capacity_all_ten_and_only_branch_trainable(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            original,path,digest=state(tmp);caps=[]
            for j in c.ORDER:
                m=model(path,digest,j);caps.append(sum(p.numel() for p in m.branch.parameters()))
                self.assertEqual(state_digest(m),state_digest(original))
                self.assertTrue(all(p.requires_grad==n.startswith('branch.') for n,p in m.named_parameters()))
            self.assertEqual(len(set(caps)),1);self.assertGreater(caps[0],20422)
    def test_private_donor_only_heads_not_encoder(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            original,path,digest=state(tmp);donor=copy.deepcopy(original.state_dict())
            for name,v in donor.items():
                if v.dtype.is_floating_point:donor[name]=v+.1
            dp=Path(tmp)/'donor.pth';torch.save(dict(global_step=8000,model=donor),dp)
            m=PrivateDecoder(Expert(True),Expert(False),c.job_card('T7'),path,digest,dict(path=dp,sha256=c.sha(dp)))
            self.assertEqual(state_digest(m),state_digest(original))
            for n,v in m.branch.state_dict().items():self.assertTrue(torch.equal(v,donor[n]))
            with self.assertRaises(RuntimeError):PrivateDecoder(Expert(True),Expert(False),c.job_card('T7'),path,digest,dict(path=dp,sha256='bad'))
    def test_frozen_native_protection_all_ten(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            original,path,digest=state(tmp);r,d,rm,dm=inputs()
            for j in c.ORDER:
                m=model(path,digest,j).eval()
                for direction in ('partial','clean','rgb_missing','dsm_missing','neither'):
                    a,b=rm.clone(),dm.clone()
                    if direction=='clean':a[:]=True
                    if direction in ('rgb_missing','neither'):a[:]=False
                    if direction in ('dsm_missing','neither'):b[:]=False
                    with torch.no_grad():z=m(r,d,a,b,True);expected=original(r,d,a,b)
                    keep=(~z['residual_support'])[:,None]
                    self.assertTrue(torch.equal(z['logits'].masked_select(keep),expected.masked_select(keep)),(j,direction))
                    if direction!='partial':self.assertTrue(torch.equal(z['logits'],expected))
    def test_one_expert_pass_and_context_affects_missing_region(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            _,path,digest=state(tmp);a=model(path,digest,'T0');b=model(path,digest,'T1');r,d,rm,dm=inputs();calls=[]
            for x in (b.rgb_expert,b.dsm_expert):x.register_forward_hook(lambda *args:calls.append(1))
            with torch.no_grad():za=a(r,d,rm,dm);zb=b(r,d,rm,dm)
            self.assertEqual(len(calls),2);self.assertFalse(torch.equal(za[:,:,~rm[0]],zb[:,:,~rm[0]]))
    def test_same_donor_context_matches_full_route_raw_on_support(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            original,path,digest=state(tmp);m=model(path,digest,'T1');r,d,rm,dm=inputs()
            with torch.no_grad():got=m(r,d,rm,dm,True);expected=CrossPaths(original,'A1B0C0')(r,d,rm,dm)
            support=got['residual_support'][:,None]
            self.assertTrue(torch.equal(got['logits'].masked_select(support),expected.masked_select(support)))
    def test_real_loss_backward_frozen_digest_and_zero_exposure(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            _,path,digest=state(tmp);r,d,rm,dm=inputs()
            for j in ('T0','T7','T9'):
                m=model(path,digest,j);before=state_digest(m);opt=optimizer_for(m,fixture(Path('x'))['training'])
                batch=dict(gt=torch.zeros_like(d,dtype=torch.long),rgb=r,aux=d,rgb2=r,aux2=d,rm2=rm,dm2=dm)
                m.train();loss,den=support_objective(m,batch);loss.backward();diag=verify_gradients(m);opt.step()
                self.assertEqual(state_digest(m),before);self.assertTrue(any(diag['groups_nonzero'].values()))
                self.assertFalse(m.rgb_expert.training);self.assertTrue(m.branch.training)
                opt.zero_grad(set_to_none=True);batch['rm2']=dm
                loss,_=support_objective(m,batch);loss.backward();diag=verify_gradients(m)
                self.assertFalse(any(diag['groups_nonzero'].values()));self.assertEqual(den['clean_residual_support_pixels'],0)
    def test_random_initialization_pair_identical_reproducible(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            _,path,digest=state(tmp);a=model(path,digest,'T8');b=model(path,digest,'T9')
            self.assertTrue(all(torch.equal(v,b.branch.state_dict()[n]) for n,v in a.branch.state_dict().items()))
    def test_predecessor_completion_requires_all_jobs_and_release(self):
        import post_s1_support_common as old
        state=dict(status='SUPPORT_COMPLETE_AWAITING_REVIEW',CPU='COMPLETE',jobs={j:dict(status='COMPLETE') for j in ['D1']+old.ORDER+['E']})
        self.assertEqual(c.predecessor_verdict(state,False,False,True),'READY')
        for a,b,d in ((True,False,True),(False,True,True),(False,False,False)):
            self.assertEqual(c.predecessor_verdict(state,a,b,d),'WAITING_PREDECESSOR_RELEASE')
        state['jobs']['E']['status']='PENDING'
        self.assertEqual(c.predecessor_verdict(state,False,False,True),'HOLD_INVALID_COMPLETE')
        self.assertEqual(c.predecessor_verdict({'status':'RUNNING_P3'},True,True,False),'WAITING_PREDECESSOR')
        self.assertEqual(c.predecessor_verdict({'status':'RUNNING_P3'},False,True,False),'HOLD_PREDECESSOR_STOPPED')
        self.assertEqual(c.predecessor_verdict({'status':'CONTROLLER_INTERRUPTED'},False,True,True),'HOLD_PREDECESSOR_FAILURE')
    def test_wait_then_release_and_failure_no_dispatch(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            b=Path(tmp);p=fixture(b);s=c.initial_state(p);seen=[]
            rows=iter([dict(verdict='WAITING_PREDECESSOR',status='RUNNING_P3'),dict(verdict='READY',status='COMPLETE')])
            self.assertTrue(wait_predecessor(b,b,p,s,sleep=lambda n:seen.append(n),inspect=lambda *args:next(rows)))
            self.assertEqual(seen,[30]);self.assertTrue(all(r['status']=='PENDING' for r in s['jobs'].values()))
            self.assertFalse(wait_predecessor(b,b,p,s,sleep=lambda n:None,inspect=lambda *a:dict(verdict='HOLD_PREDECESSOR_STOPPED',status='BAD')))
    def fifo(self,fail=False,timeout=False):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            b=Path(tmp);(b/'logs').mkdir();p=fixture(b);s=c.initial_state(p);calls=[];clock=[0.]
            class P:
                pid=101;killed=False
                def poll(self):return None if timeout and not self.killed else 2 if fail else 0
                def terminate(self):pass
                def kill(self):self.killed=True
            def spawn(cmd,**kw):calls.append((cmd[cmd.index('--job')+1],kw['env']['CUDA_VISIBLE_DEVICES']));return P()
            def sleep(n):clock[0]+=90000
            ok=run_fifo(b,b,p,s,{},popen=spawn,sleep=sleep,clock=lambda:clock[0],check=lambda u:'GPU0',accept=lambda *a:None)
            return ok,calls,s
    def test_fifo_ten_single_gpu0_no_reserved_tasks(self):
        ok,calls,s=self.fifo();self.assertTrue(ok);self.assertEqual(calls,[(j,'0') for j in c.ORDER])
    def test_failed_worker_stops_no_retry(self):
        ok,calls,s=self.fifo(fail=True);self.assertFalse(ok);self.assertEqual(calls,[('T0','0')])
    def test_timeout_zero_return_still_stops(self):
        ok,calls,s=self.fifo(timeout=True);self.assertFalse(ok);self.assertEqual(s['jobs']['T0']['status'],'TIMEOUT');self.assertEqual(len(calls),1)
    def test_gate_does_not_select_best_and_uniform_fails(self):
        p=fixture(Path('x'));cm=np.eye(6,dtype=np.int64)*100
        def summary(keys):
            r=dict(metrics={'candidate':{'valid':metric(cm)}})
            return dict(tiles={k:{t:dict(scopes={'noboundary':copy.deepcopy(r)}) for t in p['data']['validation']} for k in keys},pooled={k:{'noboundary':copy.deepcopy(r)} for k in keys})
        ordinary={j:summary(['clean','bad','rgb_missing','dsm_missing']) for j in c.ORDER};U={j:summary(['rgb_U','dsm_U']) for j in c.ORDER};E={j:summary(c.E_KEYS) for j in c.ORDER}
        refs=dict(base_ordinary=ordinary['T0'],base_U=U['T0'],R0_U=U['T0'],P7_U=U['T0'],E_R0=E['T0'],**{'E_S1-0':E['T0']})
        r=screens(p,ordinary,U,E,U,refs);self.assertFalse(r['T7_passed']);self.assertFalse(r['automatic_followup']);self.assertEqual(len(r['per_arm']),10)
    def test_entries_help_cpu_only(self):
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join([str(ROOT),str(ROOT/'scripts')]))
        for entry in ('enqueue','prepare','run','control','status','summarize','upload'):
            suffix='_records' if entry=='upload' else '';path=ROOT/'scripts'/(entry+'_post_s1_transfer'+suffix+'.py')
            r=subprocess.run([sys.executable,'-B',str(path),'--help'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(r.returncode,0,(entry,r.stderr))
    def test_lossless_upload_record(self):
        from upload_post_s1_transfer_records import encode_record,decode_record
        import json
        raw=json.dumps({'many':[1]*5000}).encode();self.assertEqual(decode_record(encode_record(raw)),raw)
    def test_standalone_summary_writes_complete_gate(self):
        import summarize_post_s1_transfer as module
        from post_d30_evaluation import encode_joint
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            base=Path(tmp);p=fixture(base);c.write(base/'plan.json',p)
            cm=np.eye(6,dtype=np.int64)*100;arr=np.zeros((6,)*4,np.int64)
            for i in range(6):arr[i,i,i,i]=100
            def scope(n):return dict(metrics={k:{'valid':metric(cm*n)} for k in ('candidate','fixed_rgb','fixed_dsm')},joint={'valid':encode_joint(arr*n)})
            def summary(keys):return dict(test6_loaded=False,independent_final_loaded=False,
                tiles={k:{t:dict(scopes={s:scope(1) for s in ('full','noboundary')},cost={'candidate_native_tile_inference_seconds':1.}) for t in p['data']['validation']} for k in keys},
                pooled={k:{s:scope(2) for s in ('full','noboundary')} for k in keys})
            ordinary=summary(['clean','bad','rgb_missing','dsm_missing']);u=summary(['rgb_U','dsm_U']);e=summary(c.E_KEYS)
            for j in c.ORDER:
                for tag,s in [('evaluation',ordinary),('support_evaluation',u),('initial_evaluation',u),('stress_evaluation',e)]:c.write(base/'jobs'/j/tag/'summary.json',s)
                c.write(base/'jobs'/j/'model_capacity.json',{})
            idx={}
            for name,s in {'base_ordinary':ordinary,'base_U':u,'R0_U':u,'R0_ordinary':ordinary,'P7_U':u,'E_S1-0':e,'E_S1-3':e,'E_R0':e,'E_P7':e}.items():
                path=base/'references'/(name+'.json');c.write(path,s);idx[name]=dict(path=str(path),sha256=c.sha(path))
            c.write(base/'reference_index.json',idx);c.write(base/'preparation_complete.json',dict(reference_index_sha256=c.sha(base/'reference_index.json')))
            with patch.object(module,'verify_snapshot'),patch.object(module,'accept_worker'),patch.object(sys,'argv',['summary','--directory',str(base)]):module.main()
            result=c.read(base/'transfer_screen.json');self.assertFalse(result['T7_passed']);self.assertEqual(result['new_optimizer_updates'],80000)
if __name__=='__main__':unittest.main()
