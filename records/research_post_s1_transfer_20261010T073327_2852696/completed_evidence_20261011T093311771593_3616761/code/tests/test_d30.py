"""Target decomposition, exact legacy regression, interventions and handover checks."""
import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'scripts'))
import torch
from torch import nn
from model.rebuild_v1_d27 import D27Segmenter
from model.rebuild_v1_d30 import ForcedMixture
from d27_data import objective as original,training_batch
from d30_data import objective,recovery,gradient_components
from d30_common import runtime_plan,validate_plan,predecessor_verdict,next_job,D28_IDS,D27_COMMIT
torch.set_num_threads(1)
class FakeExpert(nn.Module):
    def __init__(self,kind):
        super().__init__();self.kind=kind;self.channels=4
        self.conv=nn.Conv2d(3,4,1);self.classifier=nn.Conv2d(4,6,1)
    def configure(self,joint):self.requires_grad_(False);self.eval()
    def forward(self,rgb,dsm):
        x=rgb if self.kind=='rgb' else dsm[:,None].repeat(1,3,1,1)
        f=self.conv(x);return self.classifier(f),f
def make(arm='S1',forced=None):
    torch.manual_seed(42);r,d=FakeExpert('rgb'),FakeExpert('dsm')
    return D27Segmenter(r,d,arm) if forced is None else ForcedMixture(r,d,arm,forced)
def batch():
    torch.manual_seed(3);x=torch.rand(2,3,17,19);d=torch.rand(2,17,19);mask=torch.ones_like(d,dtype=torch.bool)
    return dict(rgb=x,aux=d,gt=torch.randint(0,6,d.shape),rgb2=x*.5,aux2=d+.1,rm2=mask,dm2=mask,
                treatment=['rgb_down4+aux_noise_std010+clean']*2)
def warmed():
    net=make();b=batch()
    for _ in range(3):
        net.zero_grad();loss,_=original(net,b);loss.backward()
        with torch.no_grad():
            for p in net.parameters():
                if p.requires_grad:p.add_(p.grad,alpha=-.01)
    return net
class Checks(unittest.TestCase):
    def test_legacy_loss_and_gradient_exact_at_00_and_11(self):
        for arm in ('S0','S1'):
            a=warmed();a.arm=arm;b=copy.deepcopy(a);b.loss_variant=arm
            a.zero_grad();b.zero_grad();data=batch()
            la,_=original(a,data);lb,_=objective(b,data)
            self.assertTrue(torch.equal(la,lb),(arm,float(la),float(lb)))
            la.backward();lb.backward()
            for (na,pa),(nb,pb) in zip(a.named_parameters(),b.named_parameters()):
                self.assertEqual(na,nb)
                if pa.grad is not None:self.assertTrue(torch.equal(pa.grad,pb.grad),na)
    def test_four_variants_are_only_weight_or_normalization_changes(self):
        data=batch();base=warmed()
        for variant,expected in [('P',(.1,0)),('R',(0,.1)),('PR_area',(.1,.1)),('PR_pixel',(.1,.1))]:
            net=copy.deepcopy(base);net.loss_variant=variant
            total,_,log,graph=objective(net,data,True)
            self.assertEqual(log['clean']['weights']['protect'],expected[0]);self.assertEqual(log['clean']['weights']['recover'],expected[1])
            reconstructed=sum(.5*sum(row['weighted'].values()) for row in log.values())
            self.assertAlmostEqual(float(total),reconstructed,places=6)
            self.assertTrue(torch.allclose(sum(graph.values()),total,atol=1e-6))
    def test_recovery_area_scaling_and_class_pixel_difference(self):
        target=torch.tensor([[[0,0,0,1]]]);mask=torch.ones_like(target,dtype=torch.bool)
        rgb=torch.zeros(1,6,1,4);rgb[:,2]=10
        dsm=torch.zeros_like(rgb);dsm.scatter_(1,target[:,None],10)
        logits=torch.zeros_like(rgb,requires_grad=True)
        with torch.no_grad():logits[:,0,0,:3]=4
        cb,info=recovery(logits,target,rgb,dsm,mask,mask,'R')
        pixel,_=recovery(logits,target,rgb,dsm,mask,mask,'PR_pixel')
        self.assertNotAlmostEqual(float(cb),float(pixel),places=4)
        dsm2=dsm.clone();dsm2[:,2,0,2:]=20
        cb2,i=recovery(logits,target,rgb,dsm2,mask,mask,'R')
        area,j=recovery(logits,target,rgb,dsm2,mask,mask,'PR_area')
        self.assertEqual(i['recover_pixels'],2);self.assertEqual(i['both_valid_pixels'],4)
        self.assertTrue(torch.equal(area,cb2*.5));self.assertEqual(j['recover_class_counts'],[2,0,0,0,0,0])
    def test_empty_recovery_has_finite_zero_gradient(self):
        b=batch();z=torch.zeros(2,6,17,19,requires_grad=True)
        for variant in ('R','PR_area','PR_pixel'):
            value,info=recovery(z,b['gt'],z,z,~b['rm2'],~b['dm2'],variant)
            self.assertEqual(float(value),0);self.assertEqual(info['recover_pixels'],0)
            grad=torch.autograd.grad(value,z,retain_graph=True)[0];self.assertTrue((grad==0).all())
    def test_missing_pixels_excluded_from_protect_recover(self):
        data=batch();data['rm2'].zero_();net=warmed();net.loss_variant='PR_area'
        _,_,logs,_=objective(net,data,True)
        self.assertEqual(logs['aug']['denominators']['both_valid_pixels'],0)
        self.assertEqual(logs['aug']['weighted']['protect'],0);self.assertEqual(logs['aug']['weighted']['recover'],0)
    def test_component_gradients_do_not_change_optimizer_or_rng(self):
        net=warmed();net.loss_variant='PR_pixel';net.zero_grad();data=batch()
        total,_,_,components=objective(net,data,True);rng=torch.get_rng_state().clone()
        diag=gradient_components(net,components)
        self.assertTrue(torch.equal(rng,torch.get_rng_state()))
        self.assertTrue(all(p.grad is None for p in net.parameters()))
        self.assertEqual(set(diag['weighted_gradient_norms']),{'ce','aux','protect','recover'})
        self.assertTrue(all(v>=0 for v in diag['weighted_gradient_norms'].values()))
        total.backward();expected=[None if p.grad is None else p.grad.clone() for p in net.parameters()]
        net.zero_grad();again,_,_,_=objective(net,data,True);again.backward()
        for grad,p in zip(expected,net.parameters()):
            if grad is not None:self.assertTrue(torch.equal(grad,p.grad))
    def test_training_metadata_survives_and_frozen_anchors_stay_frozen(self):
        net=warmed();net.loss_variant='P';b=training_batch(batch(),'cpu')
        self.assertEqual(b['treatment'],batch()['treatment'])
        loss,_=objective(net,b);loss.backward()
        self.assertTrue(all(p.grad is None for p in net.parameters() if not p.requires_grad))
    def test_forced_model_same_state_and_strict_reload(self):
        old=make('G1');new=make('G1','uniform')
        self.assertEqual(set(old.state_dict()),set(new.state_dict()))
        self.assertTrue(all(torch.equal(v,new.state_dict()[n]) for n,v in old.state_dict().items()))
        new.load_state_dict(warmed().state_dict(),strict=True)
    def test_forced_mix_exact_residual_combination_and_fallback(self):
        data=batch();old=warmed()
        for mode in ('uniform','expert0','expert1','expert2'):
            net=make('G1',mode);net.load_state_dict(old.state_dict());net.eval()
            rm=data['rm2'].clone();dm=data['dm2'].clone();dm[:,2:9,2:9]=False;rm[:,10:,10:]=False
            rm[:,0,0]=False;dm[:,0,0]=False
            net.reset_route_stats();parts=net(data['rgb'],data['aux'],rm,dm,True)
            w=parts['route_weights'];self.assertTrue(torch.allclose(w.sum(2),torch.ones_like(w.sum(2))))
            if mode=='uniform':self.assertTrue(torch.all(w==torch.tensor(1/3)))
            else:self.assertTrue(torch.all(w[:,:,int(mode[-1])]==1))
            for mask,ref in ((rm&~dm,'rgb'),(dm&~rm,'dsm')):
                self.assertTrue(torch.equal(parts['logits'].masked_select(mask[:,None]),parts[ref].masked_select(mask[:,None])))
            self.assertTrue((parts['logits'][:,:,0,0]==0).all())
            stats=net.route_stats()
            if mode.startswith('expert'):self.assertAlmostEqual(stats['mean_weights'][int(mode[-1])],1)
    def test_original_mode_unchanged_logits(self):
        data=batch();old=warmed();new=make('S1','original');new.load_state_dict(old.state_dict())
        args=(data['rgb'],data['aux'],data['rm2'],data['dm2'])
        self.assertTrue(torch.equal(old(*args),new(*args)))
    def test_predecessor_requires_complete_all_jobs_released_and_no_workers(self):
        state=dict(status='COMPLETE',jobs={n:dict(status='COMPLETE') for n in D28_IDS})
        self.assertEqual(predecessor_verdict(state,True,False,False),'READY')
        self.assertEqual(predecessor_verdict(state,False,False,True),'WAITING_D28_RELEASE')
        self.assertEqual(predecessor_verdict(state,True,True,False),'WAITING_D28_RELEASE')
        state['jobs'].pop('D27_L1');self.assertEqual(predecessor_verdict(state,True,False,False),'HOLD_INVALID_COMPLETE')
    def test_failure_or_dead_controller_holds_no_retry(self):
        self.assertEqual(predecessor_verdict({'status':'COMPLETE_WITH_TECHNICAL_FAILURES'},True,False,False),'HOLD_PREDECESSOR_FAILURE')
        self.assertEqual(predecessor_verdict({'status':'RUNNING'},True,False,False),'HOLD_PREDECESSOR_STOPPED')
        self.assertEqual(predecessor_verdict({'status':'RUNNING'},False,False,True),'WAITING_D28')
    def test_two_gpu_lanes_and_phase_barrier(self):
        state={'jobs':{j:dict(status='PENDING',gpu=g) for j,g in [('replay_G0',0),('replay_G1',1),('P',0),('R',1),('PR_area',0),('PR_pixel',1)]}}
        self.assertEqual(next_job(state,0,'replay'),'replay_G0');self.assertEqual(next_job(state,1,'training'),'R')
        state['jobs']['P']['status']='RUNNING'
        self.assertEqual(next_job(state,0,'training'),'PR_area')
        state['jobs']['PR_area']['status']='TECHNICAL_FAILURE';self.assertIsNone(next_job(state,0,'training'))
    def test_runtime_plan_reuses_scientific_contract(self):
        parent=json.loads((BASE/'records/research_d27_plan_20261002/plan.json').read_text(encoding='utf-8'))
        parent['execution_commit']=D27_COMMIT
        design=json.loads((BASE/'records/research_d30_plan_20261003/plan.json').read_text(encoding='utf-8'))
        runtime=runtime_plan(parent,design,'new','d28','d27')
        self.assertEqual(len(validate_plan(runtime)),4)
        for key in ('training','augmentation','data','experts','evaluation','expected_configs','input_manifest_sha256'):self.assertEqual(runtime[key],parent[key])
        runtime['physical_gpus']=[0,2]
        with self.assertRaises(ValueError):validate_plan(runtime)
    def test_raw_paired_summary_checks_reference_identity(self):
        from summarize_rebuild_v1_d30 import paired,describe
        plan={'evaluation':{'primary':['clean'],'families':{'C':['clean'],'QR':['clean'],'QD':['clean'],'QJ':['clean']}},'data':{'validation':['3_11','5_10']}}
        from d27_evaluation import encode_joint,metric
        import numpy as np
        joint=np.zeros((6,)*4,np.int64);joint[0,0,1,0]=10;joint[1,2,1,1]=5
        cm=np.diag([10,5,1,1,1,1]);record={'predictions':{n:'same' for n in ('fixed_rgb','fixed_dsm','fixed_probability_average','fixed_availability_switch')},'scopes':{'noboundary':{'metrics':{'candidate':{'valid':metric(cm)}},'joint':{'both':encode_joint(joint)},'joint_reports':{'both':{'both_correct':{'valid':0,'fused_wrong':0},'only_rgb_correct':{'valid':10,'fused_wrong':0}}}}}}
        data={'tiles':{'clean':{t:copy.deepcopy(record) for t in plan['data']['validation']}},'pooled':{'clean':{'noboundary':{'metrics':{'candidate':{'valid':metric(cm*2)}}}}}}
        row=describe(data,plan);self.assertEqual(row['only_rgb_correct']['valid'],20);self.assertEqual(row['only_dsm_correct']['valid'],10)
        self.assertEqual(paired(data,copy.deepcopy(data),plan)['worst_delta_pp'],0)
        bad=copy.deepcopy(data);bad['tiles']['clean']['3_11']['predictions']['fixed_rgb']='changed'
        with self.assertRaises(RuntimeError):paired(data,bad,plan)
    def test_native_controller_lock_released_only_after_close(self):
        import os,tempfile
        if os.name!='posix':self.skipTest('Linux fcntl checked by server CPU suite')
        import fcntl
        from d30_common import lock_free
        directory=BASE/'test_artifacts';directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temp:
            path=Path(temp);handle=(path/'controller.lock').open('a')
            try:
                fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);self.assertFalse(lock_free(path))
            finally:handle.close()
            self.assertTrue(lock_free(path))
    def test_lossless_upload_round_trip(self):
        from upload_rebuild_v1_d30_records import encode_record,decode_record
        raw=(json.dumps({'matrix':[[123]*6 for _ in range(6)],'copies':['x'*100]*12000})+'\n').encode()
        encoded=encode_record(raw)
        self.assertLess(len(encoded),len(raw));self.assertEqual(decode_record(encoded),raw)
    def test_sources_parse_as_python310_and_no_training_before_release(self):
        import ast
        for path in list((BASE/'scripts').glob('*d30*.py'))+list((BASE/'model').glob('*d30*.py')):
            ast.parse(path.read_text(encoding='utf-8'),feature_version=(3,10))
        source=(BASE/'scripts/launch_rebuild_v1_d30.py').read_text(encoding='utf-8')
        self.assertLess(source.index("if verdict=='READY'"),source.index("['nvidia-smi','--query-gpu=index,uuid'"))
        self.assertIn('start_new_session=True',source);self.assertIn('stdin=subprocess.DEVNULL',source)
        self.assertIn("for phase in ('replay','training')",source)
if __name__=='__main__':unittest.main()
