"""CPU behavior, module identity, routing, count summaries and FIFO safety."""
import copy,sys,tempfile,unittest
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
torch.set_num_threads(1)
from test_post_s1_support import state,inputs,Expert,SCRATCH
from test_post_s1_transfer import fixture as parent_fixture
import post_t_mechanism_common as c
from model.post_t_mechanism import compose,group
from model.post_n5_cross_paths import CrossPaths
from post_s1_support_evaluation import simple_route
from control_post_t_mechanism import run_fifo,wait_predecessor
from summarize_post_t_mechanism import signal,score,scores,compare
from post_d30_evaluation import metric
def fixture(root):
    p=parent_fixture(root);p['execution_commit']=c.PREDECESSOR_COMMIT
    return c.make_plan(root,root/'records'/c.PREFIX,'newcommit',p)
class MechanismTests(unittest.TestCase):
    def test_contract_26_zero_training_and_gpu0(self):
        p=fixture(Path('root'));c.validate(p)
        self.assertEqual(len(p['jobs']),26);self.assertEqual(len({x['id'] for x in p['jobs']}),26)
        self.assertEqual(sum(len(x['keys'])*2 for x in p['jobs']),296)
        for key,val in [('physical_gpus',[0,1]),('total_optimizer_steps',8000),('primary_candidate','M333_context'),('automatic_retry',True)]:
            q=copy.deepcopy(p);q[key]=val
            with self.assertRaises(ValueError):c.validate(q)
        for timeout in (None,True,0,-1,float('nan')):
            q=copy.deepcopy(p);q['runtime']['per_job_timeout_hours']=timeout
            with self.assertRaises(ValueError):c.validate(q)
    def test_all_package_compositions_and_exact_endpoints(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            model,_,_=state(tmp);a=model.state_dict();b={k:v+.2 if v.dtype.is_floating_point else v.clone() for k,v in a.items()}
            for card in c.cards()[:16]:
                z=compose(a,b,card)
                for k,v in z.items():self.assertTrue(torch.equal(v,a[k] if card[group(k)]==0 else b[k]))
            z=compose(a,b,dict(rgb=3,dsm=3,head=3));self.assertTrue(all(torch.equal(z[k],b[k]) for k in b))
            with self.assertRaises(ValueError):compose(dict(a,unknown=torch.ones(1)),dict(b,unknown=torch.ones(1)),dict(rgb=0,dsm=0,head=0))
    def test_same_source_forward_identity_and_zero_training(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            model,_,_=state(tmp);other=copy.deepcopy(model)
            card=dict(rgb=3,dsm=3,head=3)
            other.load_state_dict(compose(model.state_dict(),model.state_dict(),card))
            r,d,rm,dm=inputs();a=CrossPaths(model,'A1B0C0').eval().requires_grad_(False);b=CrossPaths(other,'A1B0C0').eval().requires_grad_(False)
            with torch.inference_mode():x=a(r,d,rm,dm);y=b(r,d,rm,dm)
            self.assertTrue(torch.equal(x,y));self.assertFalse(any(p.requires_grad for p in b.parameters()))
    def test_route_uses_availability_only_and_all_missing_guard(self):
        a=np.zeros((64,64),np.uint8);b=np.ones_like(a);rm=np.ones_like(a,dtype=bool);dm=rm.copy();rm[16:32,16:32]=False
        z,use=simple_route(a,b,rm,dm,32,16)
        self.assertTrue(np.array_equal(z[~use],a[~use]));self.assertTrue((z[use]==1).all())
        z,use=simple_route(a,b,np.zeros_like(rm),dm,32,16)
        self.assertFalse(use.any());self.assertTrue(np.array_equal(z,a))
        z,use=simple_route(a,b,rm,np.zeros_like(dm),32,16);self.assertFalse(use.any())
    def test_complete_requires_all_t_and_release(self):
        s=dict(status='TRANSFER_COMPLETE_AWAITING_REVIEW',CPU='COMPLETE',jobs={j:dict(status='COMPLETE') for j in c.previous.ORDER})
        self.assertEqual(c.predecessor_verdict(s,False,False,True),'READY')
        for a,b,r in [(True,False,True),(False,True,True),(False,False,False)]:self.assertEqual(c.predecessor_verdict(s,a,b,r),'WAITING_PREDECESSOR_RELEASE')
        s['jobs']['T9']['status']='PENDING';self.assertEqual(c.predecessor_verdict(s,False,False,True),'HOLD_INVALID_COMPLETE')
        self.assertEqual(c.predecessor_verdict(dict(status='CONTROLLER_INTERRUPTED'),False,True,False),'HOLD_PREDECESSOR_FAILURE')
        self.assertEqual(c.predecessor_verdict(dict(status='RUNNING_T5'),False,True,False),'HOLD_PREDECESSOR_STOPPED')
    def test_wait_does_not_start_gpu(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            base=Path(tmp);p=fixture(base);s=c.initial_state(p);seen=[]
            rows=iter([dict(verdict='WAITING_PREDECESSOR',status='RUNNING_T5'),dict(verdict='READY',status='TRANSFER_COMPLETE_AWAITING_REVIEW')])
            self.assertTrue(wait_predecessor(base,base,p,s,sleep=lambda n:seen.append(n),inspect=lambda *x:next(rows)))
            self.assertEqual(seen,[30]);self.assertTrue(all(x['status']=='PENDING' for x in s['jobs'].values()))
    def fifo(self,fail=False,timeout=False,accept_fail=False):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            b=Path(tmp);(b/'logs').mkdir();p=fixture(b);s=c.initial_state(p);calls=[];clock=[0.]
            class Process:
                pid=77;killed=False
                def poll(self):return None if timeout and not self.killed else 2 if fail else 0
                def terminate(self):pass
                def kill(self):self.killed=True
            def spawn(cmd,**kw):calls.append((cmd,kw));return Process()
            def sleep(n):clock[0]+=50000
            def accept(*args):
                if accept_fail:raise ValueError('bad digest')
            ok=run_fifo(b,b,p,s,{},popen=spawn,sleep=sleep,clock=lambda:clock[0],check=lambda u:'GPU0',accept=accept)
            return ok,calls,s
    def test_fifo_26_only_one_gpu(self):
        ok,calls,s=self.fifo();self.assertTrue(ok);self.assertEqual(len(calls),26)
        self.assertEqual([cmd[cmd.index('--job')+1] for cmd,_ in calls],c.ORDER)
        for cmd,kw in calls:self.assertTrue(cmd[3].endswith('run_post_t_mechanism.py'));self.assertEqual(kw['env']['CUDA_VISIBLE_DEVICES'],'0')
    def test_worker_failure_no_retry(self):
        for options in [dict(fail=True),dict(timeout=True),dict(accept_fail=True)]:
            ok,calls,s=self.fifo(**options);self.assertFalse(ok);self.assertEqual(len(calls),1)
    def test_counts_recompute_and_signal_not_single_tile(self):
        cm=np.eye(6,dtype=np.int64)*100;row=metric(cm)
        self.assertAlmostEqual(score(row),100.)
        row['mIoU_fg5']=.2
        with self.assertRaises(ValueError):score(row)
        self.assertFalse(signal(dict(pooled_gain_pp=.4,tile_gains_pp={'3_11':.9,'5_10':-.1})))
        self.assertFalse(signal(dict(pooled_gain_pp=.29,tile_gains_pp={'3_11':.2,'5_10':.4})))
        self.assertTrue(signal(dict(pooled_gain_pp=.3,tile_gains_pp={'3_11':.1,'5_10':.5})))
    def test_plan_fixed_learning_curves_all_t(self):
        jobs=c.cards()[16:];self.assertEqual([j['source_job'] for j in jobs],c.previous.ORDER)
        self.assertTrue(all(j['step']==4000 and j['keys']==['rgb_U','dsm_U'] for j in jobs))
    def test_worker_end_to_end_with_synthetic_native_predictions(self):
        from unittest.mock import patch, MagicMock
        import run_post_t_mechanism as worker
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            b=Path(tmp);root=b/'root';base=root/'records'/c.PREFIX;base.mkdir(parents=True)
            p=fixture(root);c.write(base/'plan.json',p);c.write(base/'code_manifest.json',{});c.write(base/'mask_manifest.json',{});c.write(base/'reference_index.json',{})
            c.write(base/'preparation_complete.json',dict(plan_sha256=c.sha(base/'plan.json'),mask_manifest_sha256=c.sha(base/'mask_manifest.json'),reference_index_sha256=c.sha(base/'reference_index.json')))
            shape=(512,512);full=np.ones(shape,bool);rm=full.copy();rm[128:384,128:384]=False;gt=np.zeros(shape,np.uint8)
            item=dict(full_gt=gt,noboundary_gt=gt,optical=np.zeros(shape+(3,),np.float32),dsm=np.zeros(shape,np.float32))
            def view(*args):return item,rm,full,None
            def ref(_b,_p,key,tile,which,cache):
                candidate=np.where(~rm,1,0).astype(np.uint8) if which=='R0' else gt.copy()
                return dict(candidate=candidate,fixed_rgb=gt.copy(),fixed_dsm=gt.copy()),{}
            argv=['worker','--root',str(root),'--directory',str(base),'--job','M333_context','--gpu','0']
            with patch.object(sys,'argv',argv),patch.dict('os.environ',{'CUDA_VISIBLE_DEVICES':'0'}),patch.object(torch,'__version__','2.2.2+cu121'),patch.object(worker,'dirs',return_value=(root,base)),patch.object(worker,'verify_snapshot'),patch('post_n2_diag_runtime.input_contract'),patch.object(worker,'load_model',return_value=(object(),{})),patch.object(worker,'Loader',return_value=lambda *a:item),patch.object(worker,'view_for',side_effect=view),patch.object(worker,'reference',side_effect=ref),patch.object(worker,'infer',return_value=(dict(candidate=np.ones(shape,np.uint8)),{})),patch.object(torch.cuda,'max_memory_allocated',return_value=0):
                with patch.dict(sys.modules, {'fcntl': MagicMock(LOCK_EX=2, LOCK_NB=4)}):
                    worker.main()
            c.accept_worker(base,'M333_context',p)
            s=c.read(base/'jobs/M333_context/summary.json');self.assertEqual(len(scores(s)),8)
            self.assertEqual(len(c.read(base/'jobs/M333_context/endpoint_checks.json')),16)
if __name__=='__main__':unittest.main()
