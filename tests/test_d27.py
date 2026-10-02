"""Behavioral checks of safety, specialist supervision, fallback and queue boundary."""
import copy,importlib.util,json,sys,unittest
from pathlib import Path
import torch
from torch import nn
BASE=Path(__file__).resolve().parents[1]
PARENT=BASE.parent/'d26-bidirectional-20261002'
if PARENT.exists():
    sys.path.insert(0,str(PARENT));sys.path.insert(0,str(PARENT/'scripts'))
sys.path.insert(0,str(BASE/'scripts'))
# Local namespace contains only the new model; the server snapshot is self-contained.
import model
if PARENT.exists():model.__path__.append(str(PARENT/'model'))
spec=importlib.util.spec_from_file_location('d27model',BASE/'model/rebuild_v1_d27.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from d27_data import safety,strata,objective,treatment
from d27_common import validate_plan,parent_terminal
torch.set_num_threads(1)
class FakeExpert(nn.Module):
    def __init__(self,kind):
        super().__init__();self.kind=kind;self.channels=4
        self.conv=nn.Conv2d(3,4,1);self.classifier=nn.Conv2d(4,6,1)
    def configure(self,joint):self.requires_grad_(False);self.eval()
    def forward(self,rgb,dsm):
        x=rgb if self.kind=='rgb' else dsm[:,None].repeat(1,3,1,1)
        f=self.conv(x);return self.classifier(f),f
def make(arm):
    torch.manual_seed(42);return m.D27Segmenter(FakeExpert('rgb'),FakeExpert('dsm'),arm)
def inputs():
    torch.manual_seed(3);rgb=torch.rand(2,3,17,19);dsm=torch.rand(2,17,19);mask=torch.ones_like(dsm,dtype=torch.bool)
    return rgb,dsm,mask
class Checks(unittest.TestCase):
    def test_fixed_contract(self):
        p=json.loads((BASE/'records/research_d27_plan_20261002/plan.json').read_text(encoding='utf-8'));self.assertEqual(len(validate_plan(p)),10)
        p['training']['gradient_accumulation']=True
        with self.assertRaises(ValueError):validate_plan(p)
    def test_waits_for_entire_parent_and_preserves_failure(self):
        rows={str(i):{'status':'COMPLETE'} for i in range(9)}
        self.assertFalse(parent_terminal({'status':'RUNNING','jobs':rows}))
        rows['8']['status']='RUNNING';self.assertFalse(parent_terminal({'status':'COMPLETE','jobs':rows}))
        rows['8']['status']='TECHNICAL_FAILURE';self.assertTrue(parent_terminal({'status':'COMPLETE_WITH_TECHNICAL_FAILURES','jobs':rows}))
    def test_equal_capacity_initial_state_and_first_fit_token(self):
        x,d,mask=inputs();states=[];counts=[]
        for arm in m.ARMS:
            net=make(arm);states.append(net.state_dict());counts.append(sum(p.numel() for p in net.parameters() if p.requires_grad));net(x,d,mask,mask)
        self.assertEqual(len(set(counts)),1)
        for state in states[1:]:self.assertTrue(all(torch.equal(states[0][n],state[n]) for n in state))
    def test_zero_residual_initialization_and_exact_bilateral_fallback(self):
        x,d,mask=inputs()
        for arm in m.ARMS:
            net=make(arm);initial=net(x,d,mask,mask,True)
            self.assertTrue(torch.equal(initial['logits'],initial['rgb']))
            with torch.no_grad():
                for head in net.expert_pool:head[-1].bias.fill_(2)
            rm,dm=mask.clone(),mask.clone();dm[:,2:9,2:9]=False;rm[:,10:,10:]=False;rm[:,0,0]=False;dm[:,0,0]=False
            parts=net(x,d,rm,dm,True)
            self.assertTrue(torch.equal(parts['logits'].masked_select((rm&~dm)[:,None]),parts['rgb'].masked_select((rm&~dm)[:,None])))
            self.assertTrue(torch.equal(parts['logits'].masked_select((dm&~rm)[:,None]),parts['dsm'].masked_select((dm&~rm)[:,None])))
            self.assertTrue((parts['logits'][:,:,0,0]==0).all())
    def test_known_missing_does_not_initialize_fit_token(self):
        x,d,mask=inputs();net=make('S0')
        with self.assertRaises(RuntimeError):net(x,d,mask,~mask)
    def test_route_granularity_and_semantic_shuffle(self):
        x,d,mask=inputs()
        for arm in m.ARMS:
            net=make(arm);net(x,d,mask,mask)
            with torch.no_grad():net.router[-1].weight.normal_();net.router[-1].bias.normal_()
            w=net(x,d,mask,mask,True)['route_weights']
            self.assertTrue(torch.allclose(w.sum(2),torch.ones_like(w.sum(2)),atol=1e-6))
            if not arm.startswith('C'):self.assertTrue(torch.equal(w[:,0],w[:,5]))
            if arm.startswith(('S','G')):self.assertTrue(torch.allclose(w[...,0,0],w[...,-1,-1],atol=1e-7))
        net=make('C1');net(x,d,mask,mask);cond=torch.rand(2,20,5,5)
        shuffled=m.permuted_condition(cond,x,d)
        self.assertTrue(torch.equal(shuffled,m.permuted_condition(cond,x,d)))
        self.assertTrue(torch.equal(shuffled[:,18:],cond[:,18:]))
        self.assertFalse(torch.equal(shuffled[:,:12],cond[:,:12]))
        self.assertTrue(torch.equal(shuffled[:1],m.permuted_condition(cond[:1],x[:1],d[:1])))
    def test_static_route_independent_of_current_sample(self):
        x,d,mask=inputs();net=make('S1');net(x,d,mask,mask)
        with torch.no_grad():net.router[-1].weight.normal_()
        a=net(x,d,mask,mask,True)['route_weights'];b=net(x.flip(0),d.flip(0),mask,mask,True)['route_weights']
        self.assertTrue(torch.equal(a,b))
    def test_safety_target_signs_and_empty_regions(self):
        gt=torch.tensor([[[0,1]]]);r=torch.tensor([[[[4.,4.]],[[0.,0.]],[[0.,0.]],[[0.,0.]],[[0.,0.]],[[0.,0.]]]])
        d=r.flip(1);d[:,1,0,1]=10.;mask=torch.ones_like(gt,dtype=torch.bool)
        bad=r.clone();bad[:,1,0,0]=10.
        protect,recover,count=safety(bad,r,d,gt,mask,mask)
        self.assertGreater(float(protect),0);self.assertEqual(count['protect_pixels'],1);self.assertEqual(count['recover_pixels'],1)
        p,q,_=safety(r,r,d,gt,~mask,~mask);self.assertEqual(float(p+q),0)
    def test_expert_strata(self):
        s=strata(['clean+clean+clean','rgb_down4+aux_noise_std010+clean','clean+clean+dsm_missing'],'aug','cpu')
        self.assertEqual(s.tolist(),[[True,False,False],[False,True,True],[True,False,False]])
    def test_objective_frozen_anchors_and_learned_gradients(self):
        x,d,mask=inputs();gt=torch.randint(0,6,d.shape)
        batch=dict(rgb=x,aux=d,gt=gt,rgb2=x*.5,aux2=d+.1,rm2=mask,dm2=mask,treatment=['rgb_down4+aux_noise_std010+clean']*2)
        for arm in ('G0','G1','S1','C1-sh'):
            net=make(arm);opt=torch.optim.AdamW([p for p in net.parameters() if p.requires_grad],lr=.01)
            for _ in range(3):
                opt.zero_grad();loss,counts=objective(net,batch);loss.backward();opt.step()
            self.assertTrue(torch.isfinite(loss));self.assertTrue(all(p.grad is None for p in net.parameters() if not p.requires_grad))
            for prefix in ('project_rgb.','project_dsm.','expert_pool.','router.'):
                self.assertTrue(any(p.grad is not None and p.grad.abs().sum()>0 for n,p in net.named_parameters() if n.startswith(prefix)))
            self.assertEqual(('clean_protect_pixels' in counts),arm!='G0')
    def test_missing_vs_present_neutralization(self):
        x,d,mask=inputs()
        _,zero,rm,dm=treatment(x,d,'dsm_present_zero',42);self.assertTrue((zero==0).all());self.assertTrue(dm.all())
        _,_,rm,dm=treatment(x,d,'dsm_missing',42);self.assertFalse(dm.any())
    def test_snapshot_reload_and_eval_diagnostics(self):
        x,d,mask=inputs();net=make('C1');net(x,d,mask,mask);clone=make('C1');clone.load_state_dict(net.state_dict());clone.eval()
        clone.reset_route_stats();a=clone(x,d,mask,mask);diag=clone.route_stats()
        self.assertTrue(torch.equal(a,net(x,d,mask,mask)))
        self.assertEqual(diag['observed_cells'],2*5*5);self.assertEqual(diag['expert_disagreement_rate'],0)
    def test_raw_joint_harm_denominator_and_zero_baseline(self):
        from summarize_rebuild_v1_d27 import harm_rate,reduced
        rep={'both_correct':{'valid':80,'fused_wrong':4},'only_rgb_correct':{'valid':20,'fused_wrong':6}}
        summary={'tiles':{'noise':{'tile':{'scopes':{'noboundary':{'joint_reports':{'both':rep}}}}}}}
        row=harm_rate(summary,['noise']);self.assertEqual(row,{'correct':100,'harm':10,'rate':.1})
        self.assertTrue(reduced({'rate':.08},row));self.assertFalse(reduced({'rate':0},{'rate':0}))
    def test_launcher_snapshot_sources_and_wait_before_gpu(self):
        import ast
        source=(BASE/'scripts/launch_rebuild_v1_d27.py').read_text(encoding='utf-8');tree=ast.parse(source)
        constants={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('FILES','PARENT_FILES','PARENT_COMMIT')}
        self.assertFalse(set(constants['FILES'])&set(constants['PARENT_FILES']))
        self.assertTrue('model/rebuild_v1_d26.py' in constants['PARENT_FILES'])
        self.assertEqual(constants['PARENT_COMMIT'],'52f94388b1a9c7557e9ef533075661139cd55eda')
        self.assertLess(source.index("state.update(status='WAITING_D26'"),source.index("['nvidia-smi','--query-gpu=index,uuid'"))
        self.assertIn('fcntl.LOCK_EX|fcntl.LOCK_NB',source)
if __name__=='__main__':unittest.main()
