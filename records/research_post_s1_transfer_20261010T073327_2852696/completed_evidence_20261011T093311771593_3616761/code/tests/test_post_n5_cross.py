"""CPU tests for actual N1/N2 intervention graphs and dispatch lifecycle."""
import copy,json,os,sys,tempfile,types,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
SCRATCH=ROOT/'test_scratch';SCRATCH.mkdir(exist_ok=True)
torch.set_num_threads(1)
import post_n5_cross_common as c
from prepare_post_n5_cross import standardize,strata
from summarize_post_n5_cross import screens
from model.rebuild_v1_post_ab_n1 import N1Segmenter
from model.rebuild_v1_post_ab_n2 import N2Segmenter
from model.post_n5_cross_paths import CrossPaths
from post_d30_evaluation import metric,counts,joint_counts,encode_joint,joint_report,save_prediction
from control_post_n5_cross import run_stage
class Expert(torch.nn.Module):
    def __init__(self,rgb):
        super().__init__();self.rgb=rgb;self.p=torch.nn.Parameter(torch.tensor(1.))
        self.net=torch.nn.Module();self.net.encoder=torch.nn.Module();self.net.encoder.blocks=torch.nn.ModuleList([torch.nn.Identity() for _ in range(12)])
        self.net.transformer=torch.nn.Module();self.net.transformer.encoder=torch.nn.Module();self.net.transformer.encoder.layer=torch.nn.ModuleList([torch.nn.Identity() for _ in range(12)])
    def configure(self,joint):pass
    def forward(self,rgb,dsm):
        x=rgb.mean(1,keepdim=True) if self.rgb else dsm[:,None]
        x=torch.nn.functional.avg_pool2d(x,9,1,4)*self.p
        logits=torch.cat([x+i*.01 for i in range(6)],1)
        feature=torch.nn.functional.avg_pool2d(x,4).repeat(1,32,1,1)
        return logits,feature
def make_model(n2=False,tmp=None):
    torch.manual_seed(5)
    base=N1Segmenter(Expert(True),Expert(False),dict(id='N1-2',information_entry='late',adaptation='last4_and_heads')).eval()
    if not n2:return base
    path=Path(tmp)/'base.pth';torch.save(dict(global_step=8000,model=base.state_dict()),path)
    return N2Segmenter(Expert(True),Expert(False),dict(id='N2-0',relation_mode='spatial',
        initial_checkpoint_path=str(path),initial_checkpoint_sha256=c.sha(path))).eval()
def fixture(root):
    parent=dict(data=dict(fit12=[f'f{i}' for i in range(12)],validation=['3_11','5_10'],test6_loaded=False,independent_final_loaded=False),experts={},expected_configs={},input_manifest_sha256='x')
    return c.make_plan(root,root/'records/research_post_n5_cross_test','commit',parent)
class CrossTests(unittest.TestCase):
    def test_contract_timeout_scope_and_new_training_rejected(self):
        p=fixture(Path('root'));c.validate(p)
        for v in (None,0,-1,True,float('nan'),float('inf')):
            q=copy.deepcopy(p);q['runtime']['per_job_timeout_hours']=v
            with self.assertRaises(ValueError):c.validate(q)
        for k,v in [('new_optimizer_updates',1),('automatic_training',True),('physical_gpus',[0,2]),('paths',c.PATHS[:-1])]:
            q=copy.deepcopy(p);q[k]=v
            with self.assertRaises(ValueError):c.validate(q)
    def inputs(self):
        torch.manual_seed(4);r=torch.rand(2,3,64,64);d=torch.rand(2,64,64);rm=torch.ones_like(d,dtype=torch.bool);dm=rm.clone();rm[:,16:48,16:48]=False
        return r,d,rm,dm
    def test_baseline_exact_N1_N2_same_capacity(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            for n2 in (False,True):
                base=make_model(n2,tmp);wrap=CrossPaths(base,'A1B1C1');xs=self.inputs()
                with torch.no_grad():
                    a=base(*xs,return_parts=True);b=wrap(*xs,return_parts=True)
                for k in a:self.assertTrue(torch.equal(a[k],b[k]),(n2,k))
                self.assertEqual(sum(x.numel() for x in base.parameters()),sum(x.numel() for x in wrap.parameters()))
    def test_A_zero_input_negative_control_all_B_C_N1_N2(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            for n2 in (False,True):
                base=make_model(n2,tmp);r,d,rm,dm=self.inputs();r=r.masked_fill(~rm[:,None],0)
                with torch.no_grad():
                    for b in (0,1):
                        for cc in (0,1):
                            a=CrossPaths(base,f'A0B{b}C{cc}')(r,d,rm,dm,True)
                            z=CrossPaths(base,f'A1B{b}C{cc}')(r,d,rm,dm,True)
                            for k in a:self.assertTrue(torch.equal(a[k],z[k]))
    def test_B_covers_pyramid_and_relation_masks(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            for n2 in (False,True):
                base=make_model(n2,tmp);xs=self.inputs();a=CrossPaths(base,'A1B1C0');b=CrossPaths(base,'A1B0C0')
                with torch.no_grad():a(*xs);b(*xs)
                self.assertNotEqual(a.trace['pyramid_rgb_support'],b.trace['pyramid_rgb_support'])
                self.assertNotEqual(a.trace['rgb_feature'],b.trace['rgb_feature'])
                if n2:self.assertNotEqual(a.trace['relation_support'],b.trace['relation_support'])
    def test_full_missing_and_neither_safe_in_all_paths(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            for n2 in (False,True):
                base=make_model(n2,tmp)
                for direction in ('rgb','dsm','neither'):
                    r,d,rm,dm=self.inputs()
                    if direction in ('rgb','neither'):rm[:]=False
                    if direction in ('dsm','neither'):dm[:]=False
                    with torch.no_grad():
                        expected=base(r,d,rm,dm)
                        for path in c.PATHS:
                            got=CrossPaths(base,path)(r,d,rm,dm)
                            self.assertTrue(torch.equal(expected,got),(n2,direction,path))
    def test_A_false_positive_changes_actual_expert_input(self):
        base=make_model();xs=self.inputs();a=CrossPaths(base,'A0B1C1');b=CrossPaths(base,'A1B1C1')
        with torch.no_grad():a(*xs);b(*xs)
        self.assertEqual(a.trace['received_rgb'],b.trace['received_rgb'])
        self.assertNotEqual(a.trace['expert_rgb'],b.trace['expert_rgb'])
    def test_standardization_shared_support_and_uncovered_mass(self):
        rows={'U':{'x':dict(support=100,correct=60),'y':dict(support=99,correct=99)},
              'H':{'x':dict(support=100,correct=50),'y':dict(support=200,correct=0)}}
        s=standardize(rows,{'x':800,'y':200},100)
        self.assertEqual(s['common_strata'],['x']);self.assertEqual(s['covered_weight_fraction'],.8)
        self.assertEqual(s['standardized_accuracy'],{'U':.6,'H':.5})
    def test_class_boundary_counts_exclude_invalid_and_clutter(self):
        gt=np.array([[0,1,255],[4,5,0]],np.uint8);pred=np.zeros_like(gt);band=np.array([[True,False,True],[False,True,False]])
        rows=strata(gt,pred,band,np.ones_like(band))
        self.assertEqual(sum(x['support'] for x in rows.values()),4)
        self.assertEqual(rows['0_boundary']['correct'],1)
    def test_source_completion_changed_summary_rejected(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            base=Path(tmp);p=fixture(base);c.write(base/'plan.json',p);c.write(base/'code_manifest.json',{})
            j=p['jobs'][0]['id'];folder=base/'jobs'/j;c.write(folder/'summary.json',{})
            sig=dict(job=p['jobs'][0],plan_sha256=c.sha(base/'plan.json'),code_manifest_sha256=c.sha(base/'code_manifest.json'),execution_commit='commit')
            c.write(folder/'complete.json',dict(signature=sig,optimizer_updates=0,inference_tile_units=64,test6_loaded=False,independent_final_loaded=False,summary_sha256='bad'))
            with self.assertRaises(RuntimeError):c.complete_job(base,j,p)
    def monitor(self,fail=False,timeout=False,artifact=False):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            base=Path(tmp);(base/'logs').mkdir();p=fixture(base);state=c.initial_state(p);calls=[];ticks=[0.];procs=[]
            if artifact:(base/'jobs'/p['jobs'][0]['id']).mkdir(parents=True)
            def spawn(cmd,**kwargs):
                j=cmd[cmd.index('--job')+1];calls.append((j,kwargs['env']['CUDA_VISIBLE_DEVICES']))
                class Process:
                    pid=100+len(calls)
                    killed=False;terminated=False
                    def poll(self):return (2 if fail else 0) if not timeout else (0 if self.killed else None)
                    def terminate(self):self.terminated=True
                    def kill(self):self.killed=True
                obj=Process();procs.append(obj);return obj
            def sleep(seconds):ticks[0]+=40000
            return run_stage(base,base,p,state,{}, {0:'u0',1:'u1'},lambda *a:None,popen=spawn,sleep=sleep,clock=lambda:ticks[0],accept=lambda *a:None),calls,state,procs
    def test_dispatch_two_lanes_and_final_exit(self):
        ok,calls,state,_=self.monitor()
        self.assertTrue(ok);self.assertEqual(calls,[('E4_N1-2','0'),('E4_N2-0','1'),('E4_N2-3','0')])
        self.assertTrue(all(x['status']=='COMPLETE' for x in state['jobs'].values()))
    def test_failure_stops_new_dispatch_and_no_retry(self):
        ok,calls,state,_=self.monitor(fail=True)
        self.assertFalse(ok);self.assertEqual(len(calls),1);self.assertEqual(state['jobs']['E4_N1-2']['status'],'TECHNICAL_FAILURE')
    def test_timeout_terminate_kill_not_accept_rc_zero(self):
        ok,calls,state,procs=self.monitor(timeout=True)
        self.assertFalse(ok);self.assertEqual(len(calls),2)
        self.assertTrue(all(x.terminated and x.killed for x in procs))
        self.assertTrue(all(x['status']=='TIMEOUT' for x in list(state['jobs'].values())[:2]))
    def test_partial_artifacts_prevent_dispatch(self):
        with self.assertRaises(RuntimeError):self.monitor(artifact=True)
    def test_fixed_gate_rejects_one_negative_tile_or_side_model_rescue(self):
        p=fixture(Path('root'));data={}
        for model in ('N1-2','N2-0','N2-3'):
            cm=np.eye(6,dtype=np.int64)*1000
            s=dict(tiles={},pooled={})
            for d in ('rgb','dsm'):
                for path in c.PATHS:
                    key=d+'_known_missing_'+path;s['tiles'][key]={t:cm.tolist() for t in p['data']['validation']};s['pooled'][key]=metric(cm*2)
            data[model]=s
        gates=screens(data,p);self.assertFalse(gates['output']['trigger']);self.assertFalse(gates['feature']['trigger'])
    def test_standalone_entry_imports_and_help(self):
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONPATH=os.pathsep.join([str(ROOT),str(ROOT/'scripts')]),PYTHONDONTWRITEBYTECODE='1')
        for name in ('prepare_post_n5_cross.py','run_post_n5_cross.py','summarize_post_n5_cross.py','control_post_n5_cross.py','status_post_n5_cross.py','upload_post_n5_cross_records.py'):
            r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts'/name),'--help'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(r.returncode,0,(name,r.stderr))
    def test_gate_positive_pool_does_not_override_negative_tile(self):
        p=fixture(Path('root'));data={}
        def cm(v):
            a=np.eye(6,dtype=np.int64)*v
            for i in range(6):a[i,(i+1)%6]=1000-v
            return a
        for model in ('N1-2','N2-0','N2-3'):
            s=dict(tiles={},pooled={})
            for d in ('rgb','dsm'):
                for path in c.PATHS:
                    values=[900,900] if path=='A1B1C1' else [930,930]
                    if model=='N1-2' and path=='A1B1C0':values=[880,970]
                    key=d+'_known_missing_'+path
                    s['tiles'][key]={t:cm(v).tolist() for t,v in zip(p['data']['validation'],values)}
                    s['pooled'][key]=metric(sum(cm(v) for v in values))
            data[model]=s
        gates=screens(data,p)
        self.assertGreater(gates['output']['directions']['rgb']['N1-2']['pooled_gain_pp'],.5)
        self.assertFalse(gates['output']['trigger'])
        self.assertTrue(gates['output']['directions']['rgb']['N2-3']['passed'])
    def test_standalone_complete_summary_counts_binding_and_exit(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            base=Path(tmp);p=fixture(base);c.write(base/'plan.json',p);c.write(base/'code_manifest.json',{})
            c.write(base/'cpu_preparation_complete.json',{});c.write(base/'boundary_screen.json',dict(N3_problem_trigger=False))
            gt=np.arange(6,dtype=np.uint8).reshape(2,3);mask=np.zeros_like(gt,dtype=bool);mask[0]=True
            regs=dict(all=np.ones_like(mask),mask_location=mask,other_locations=~mask)
            scopes={scope:dict(metrics={n:{r:counts(gt,gt,m) for r,m in regs.items()} for n in ('candidate','rgb','dsm')},
                joint={r:encode_joint(joint_counts(gt,gt,gt,gt,m)) for r,m in regs.items()},
                joint_report={r:joint_report(joint_counts(gt,gt,gt,gt,m)) for r,m in regs.items()}) for scope in ('full','noboundary')}
            for job in p['jobs']:
                folder=base/'jobs'/job['id'];sig=dict(job=job,plan_sha256=c.sha(base/'plan.json'),code_manifest_sha256=c.sha(base/'code_manifest.json'),execution_commit='commit')
                records={};cms={}
                for d in p['E4']['directions']:
                    for case in p['E4']['cases']:
                        for path in p['paths']:
                            key=d+'_'+case+'_'+path
                            for tile in p['data']['validation']:
                                target=folder/'evaluation'/key;hashes={n:save_prediction(target/n/(tile+'.npy'),gt) for n in ('candidate','rgb','dsm')}
                                row=dict(binding=sig,condition=key,tile=tile,path=path,scopes=scopes,predictions=hashes,
                                    original_E2_parity={n:dict(array_equal=True) for n in hashes} if path=='A1B1C1' else None,
                                    fallback_logits_equal_own=dict(rgb_only=True,dsm_only=True),
                                    physical_input_sha256=dict(rgb='r',dsm='d'),reported_mask_sha256=dict(rgb='r',dsm='d'),
                                    first_batch_trace={n:'same' for n in ('expert_rgb','expert_dsm','rgb_feature','dsm_feature','raw_logits','output_logits')})
                                record=target/(tile+'.json');c.write(record,row)
                                records.setdefault(key,{})[tile]=dict(path=str(record),sha256=c.sha(record))
                                cms.setdefault(key,{})[tile]=metric(np.eye(6,dtype=np.int64))['cm']
                pooled={k:metric(sum(np.asarray(cm,np.int64) for cm in ts.values())) for k,ts in cms.items()}
                c.write(folder/'summary.json',dict(binding=sig,records=records,tiles=cms,pooled=pooled))
                c.write(folder/'complete.json',dict(signature=sig,summary_sha256=c.sha(folder/'summary.json'),optimizer_updates=0,inference_tile_units=64,test6_loaded=False,independent_final_loaded=False))
            env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONPATH=os.pathsep.join([str(ROOT),str(ROOT/'scripts')]))
            cmd=[sys.executable,'-B',str(ROOT/'scripts/summarize_post_n5_cross.py'),'--directory',str(base)]
            r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(r.returncode,0,r.stderr)
            result=c.read(base/'cross_screen.json');self.assertEqual(result['records_checked'],192);self.assertEqual(result['recommended_next_families'],[])
if __name__=='__main__':unittest.main()
