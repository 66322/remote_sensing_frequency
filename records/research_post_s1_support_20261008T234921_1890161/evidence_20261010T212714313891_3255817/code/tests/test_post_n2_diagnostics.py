"""CPU contracts plus actual controller dispatch/wait integration; no native GPU."""
import importlib.util,json,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
from scipy.ndimage import label
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import post_n2_diag_common as c
import post_n2_masks as m
def load_control():
    spec=importlib.util.spec_from_file_location('diagnostic_controller_test',ROOT/'scripts/control_post_n2_diagnostics.py');module=importlib.util.module_from_spec(spec)
    substitutes={'d30_common':types.SimpleNamespace(live_owned=lambda *a:False,lock_free=lambda *a:True)}
    if os.name!='posix':substitutes['fcntl']=types.SimpleNamespace(flock=lambda *a:None,LOCK_EX=2,LOCK_NB=4)
    with patch.dict(sys.modules,substitutes):spec.loader.exec_module(module)
    return module
def plan_fixture(root):
    parent={'data':{'fit12':['f'+str(i) for i in range(12)],'validation':['3_11','5_10'],'test6_loaded':False,'independent_final_loaded':False},'experts':{},'input_manifest_sha256':'x','expected_configs':{},'evaluation':{'primary':['clean']}}
    return c.make_plan(root,root/'records/new','testcommit',parent)
class Contracts(unittest.TestCase):
    def test_all_rules_exact_area_shape_separated_and_deterministic(self):
        shape=(384,368);rng=np.random.default_rng(1);field=rng.random(shape);signatures=[]
        for rule in ('U','H','L'):
            mask,boxes=m.quarter_mask(shape,rule,field,'tile')
            self.assertEqual(int(mask.sum())*4,mask.size);self.assertEqual(label(mask)[1],len(boxes))
            signatures.append(sorted((b[2],b[3]) for b in boxes));self.assertTrue(np.array_equal(mask,m.quarter_mask(shape,rule,field,'tile')[0]))
        self.assertEqual(signatures[0],signatures[1]);self.assertEqual(signatures[1],signatures[2])
    def test_content_direction_selects_high_and_low(self):
        score=np.zeros((256,256));score[48:112,48:112]=10
        hi,_=m.quarter_mask(score.shape,'H',score);lo,_=m.quarter_mask(score.shape,'L',score)
        self.assertGreater(score[hi].mean(),score[lo].mean())
    def test_reserved_rule_and_odd_shapes_rejected(self):
        for shape,rule in (((256,256),'T'),((255,256),'U'),((130,256),'U')):
            with self.assertRaises(ValueError):m.quarter_mask(shape,rule)
    def test_physical_fault_independent_of_reported_mask(self):
        item={'optical':np.ones((256,256,3),np.float32),'dsm':np.ones((256,256),np.float32)};mask,_=m.quarter_mask((256,256),'U')
        for direction in ('rgb','dsm'):
            known,kr,kd=m.physical_view(item,mask,direction,'known_missing');miss,mr,md=m.physical_view(item,mask,direction,'false_negative')
            for n in known:self.assertTrue(np.array_equal(known[n],miss[n]))
            self.assertTrue(mr.all() and md.all());self.assertFalse((kr if direction=='rgb' else kd).all())
            fp,fr,fd=m.physical_view(item,mask,direction,'false_positive')
            for n in item:self.assertTrue(np.array_equal(fp[n],item[n]))
            self.assertTrue(np.array_equal(fr,kr) and np.array_equal(fd,kd));self.assertTrue(item['optical'].all() and item['dsm'].all())
    def test_boundary_ignores_unknown_label_edges(self):
        gt=np.zeros((32,32),np.uint8);gt[:,16:]=1;gt[:2]=255
        band=m.boundary_band(gt,4);self.assertFalse(band[:2].any());self.assertTrue(band[10,16]);self.assertFalse(band[10,2])
    def test_fit_object_cutoffs_and_ignore_background(self):
        gt=np.full((20,20),255,np.uint8);gt[1:3,1:3]=0;gt[6:12,6:12]=0
        self.assertEqual(sorted(m.object_areas(gt)['0']),[4,36]);small=m.small_objects(gt,{str(i):4 for i in range(5)})
        self.assertEqual(int(small.sum()),4)
    def test_gate_requires_both_models_and_both_tiles(self):
        rows={n:{d+'_'+r:{t:.8-(.006 if r in ('H','L') else 0) for t in ('3_11','5_10')} for d in ('rgb','dsm') for r in ('U','H','L')} for n in ('A0','B1')}
        pooled={n:{k:sum(ts.values())/2 for k,ts in cs.items()} for n,cs in rows.items()}
        self.assertTrue(m.e1_gate(rows,pooled)['N5_problem_trigger'])
        for k in rows['B1']:
            if not k.endswith('_U'):rows['B1'][k]['5_10']=.81
        self.assertFalse(m.e1_gate(rows,pooled)['N5_problem_trigger'])
    def test_timeout_null_nonfinite_and_scope_rejected(self):
        p=plan_fixture(Path('root'));c.validate(p)
        for value in (None,0,-1,True,float('inf')):
            with self.assertRaises(ValueError):c.limit_hours(value)
        p['data']['validation'].append('Test6')
        with self.assertRaises(ValueError):c.validate(p)
    def test_predecessor_hold_wait_complete_release(self):
        st={'status':'RUNNING_N2','jobs':{f'N2-{i}':{'status':'PENDING'} for i in range(6)}}
        self.assertEqual(c.predecessor_verdict(st,True,True,False),'WAITING_N2');self.assertTrue(c.predecessor_verdict(st,False,False,True).startswith('HOLD'))
        st['status']='N2_COMPLETE_AWAITING_STAGE_PROTOCOL'
        for row in st['jobs'].values():row['status']='COMPLETE'
        self.assertEqual(c.predecessor_verdict(st,True,False,True),'WAITING_N2_RELEASE');self.assertEqual(c.predecessor_verdict(st,False,False,True),'READY')
        st['jobs']['N2-0']['status']='RUNNING';self.assertTrue(c.predecessor_verdict(st,False,False,True).startswith('HOLD'))
    def test_actual_controller_wait_never_starts_cpu_or_gpu(self):
        ctl=load_control()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);base=root/'diag';base.mkdir();p=plan_fixture(root);parent=Path(p['predecessor_directory']);parent.mkdir(parents=True)
            c.write(parent/'queue_status.json',{'status':'RUNNING_N2','controller_pid':99,'jobs':{f'N2-{i}':{'status':'PENDING'} for i in range(6)}})
            c.write(base/'plan.json',p);c.write(base/'code_manifest.json',{'files':{}});c.write(base/'queue_status.json',c.initial_state(p))
            # A dead predecessor controller makes the actual main return HOLD;
            # no CPU/raw-input preparation and no worker Popen are permitted.
            with patch.object(ctl,'dirs',return_value=(root,base)),patch.object(sys,'argv',['controller','--root',str(root),'--directory',str(base)]),patch.object(ctl.subprocess,'run') as run,patch.object(ctl.subprocess,'Popen') as spawn:
                self.assertEqual(ctl.main(),2);run.assert_not_called();spawn.assert_not_called()
    def monitor(self,fail=False,artifact=False):
        ctl=load_control()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);base=root/'diag';(base/'logs').mkdir(parents=True);p=plan_fixture(root);c.write(base/'plan.json',p);state=c.initial_state(p);calls=[]
            if artifact:(base/'jobs/E1_A0').mkdir(parents=True)
            def spawn(cmd,**kwargs):
                j=cmd[cmd.index('--job')+1];calls.append(j)
                if not fail:
                    folder=base/'jobs'/j;c.write(folder/'summary.json',{})
                    c.write(folder/'complete.json',{'signature':{'job':{'id':j},'execution_commit':p['execution_commit'],'plan_sha256':c.sha(base/'plan.json')},'summary_sha256':c.sha(folder/'summary.json'),'optimizer_updates':0,'test6_loaded':False,'independent_final_loaded':False})
                return types.SimpleNamespace(pid=55,poll=Mock(side_effect=[None,2 if fail else 0]),terminate=Mock())
            if artifact:
                with self.assertRaisesRegex(RuntimeError,'existing job'):ctl.run_stage(root,base,p,state,'E1',{}, {},lambda *a:None,popen=spawn,sleep=lambda x:None)
                self.assertFalse(calls);return
            result=ctl.run_stage(root,base,p,state,'E1',{}, {},lambda *a:None,popen=spawn,sleep=lambda x:None)
            return result,calls,state
    def test_actual_dispatch_and_completion_no_training(self):
        ok,calls,state=self.monitor();self.assertTrue(ok);self.assertEqual(calls,['E1_A0','E1_B1']);self.assertEqual(state['jobs']['E1_A0']['status'],'COMPLETE')
    def test_actual_failure_blocks_other_gpu_dispatch(self):
        ok,calls,state=self.monitor(fail=True);self.assertFalse(ok);self.assertEqual(calls,['E1_A0']);self.assertEqual(state['jobs']['E1_A0']['status'],'TECHNICAL_FAILURE')
    def test_partial_job_not_automatically_retried(self):self.monitor(artifact=True)
    def test_real_model_dispatch_checkpoint_binding_and_freeze(self):
        import post_n2_diag_runtime as runtime
        constructor=Mock()
        fake=Mock();fake.eval.return_value=fake;fake.requires_grad_.return_value=fake;fake.to.return_value=fake;constructor.return_value=fake
        modules={'torch':types.SimpleNamespace(load=lambda *a,**k:dict(signature={'s':1},global_step=4000,model={'weights':1})),
            'run_post_ab_n2':types.SimpleNamespace(load_anchors=lambda *a:({},{})),
            'model':types.ModuleType('model'),'model.rebuild_v1_d26':types.SimpleNamespace(build_experts=lambda *a:('rgb','dsm')),
            'model.rebuild_v1_post_d30':types.SimpleNamespace(PortfolioSegmenter=constructor),
            'model.rebuild_v1_post_ab_n1':types.SimpleNamespace(N1Segmenter=constructor),
            'model.rebuild_v1_post_ab_n2':types.SimpleNamespace(N2Segmenter=constructor)}
        for name in ('A0','B1','N1-2','N2-0','N2-3'):
            job={'id':name};complete=dict(signature={'s':1},selected={'step':4000})
            with patch.dict(sys.modules,modules),patch.object(runtime,'bind_model',return_value=({},dict(jobs=[job]),complete)),patch.object(runtime,'model_folder',return_value=(Path('source'),Path('job'))),patch.object(runtime,'read',return_value={'files':{}}):
                result,_=runtime.construct_model(Path('root'),Path('diag'),name,'cuda')
            self.assertIs(result,fake);constructor.assert_called_with('rgb','dsm',job);fake.load_state_dict.assert_called_with({'weights':1},strict=True);fake.requires_grad_.assert_called_with(False)
        complete['selected']['step']=8000
        with patch.dict(sys.modules,modules),patch.object(runtime,'bind_model',return_value=({},dict(jobs=[job]),complete)),patch.object(runtime,'model_folder',return_value=(Path('source'),Path('job'))),patch.object(runtime,'read',return_value={'files':{}}):
            with self.assertRaisesRegex(RuntimeError,'selected state signature'):runtime.construct_model(Path('root'),Path('diag'),'N2-3','cuda')
    def test_summary_rejects_metric_count_and_joint_corruption(self):
        from summarize_post_n2_diagnostics import checked_matrix,checked_joint
        cm=np.eye(6,dtype=np.int64)*2
        row=dict(cm=cm.tolist(),support=[2]*6,TP=[2]*6,FP=[0]*6,FN=[0]*6,valid=12,mIoU_fg5=1.)
        self.assertTrue(np.array_equal(checked_matrix(row),cm));row['support'][0]=3
        with self.assertRaises(RuntimeError):checked_matrix(row)
        with self.assertRaises(RuntimeError):checked_joint(dict(shape=[6]*4,dtype='int64',format='sparse_flat_index_count',nonzero=[[0,1],[0,2]]))
    def test_upload_lossless_and_tamper_rejected(self):
        import upload_post_n2_diagnostics_records as u
        raw=(json.dumps({'large':[7]*30000})+'\n').encode();packed=u.encode_record(raw)
        self.assertLess(len(packed),len(raw));self.assertEqual(u.decode_record(packed),raw)
        envelope=json.loads(packed);envelope['original_sha256']='0'*64
        with self.assertRaises(ValueError):u.decode_record(json.dumps(envelope).encode())
if __name__=='__main__':unittest.main()
