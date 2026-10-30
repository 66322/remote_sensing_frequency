import copy,sys,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'scripts')]
import torch
from torch import nn
from torch.nn import functional as F
torch.set_num_threads(1)
from model.rebuild_v1_d26 import Expert
from model.rebuild_v1_post_ab_n1 import N1Segmenter
from post_ab_queue_common import runtime_plan,validate_plan,predecessor_verdict,next_job,initial_state,IDS
from summarize_post_ab_n1 import screen,audit_summary
from post_d30_evaluation import encode_joint,metric
import numpy as np

def fixture():
    return dict(training=dict(steps=8000,seed=42,physical_batch=16,gradient_accumulation=False,validation_steps=[4000,8000],selection_states=['clean','dsm_missing','rgb_missing']),physical_gpus=[0,1],data=dict(validation=['3_11','5_10'],test6_loaded=False,independent_final_loaded=False),runtime={},design={})

class Block(nn.Module):
    def __init__(self,tuple_output=False):super().__init__();self.fc=nn.Linear(32,32);self.tuple_output=tuple_output
    def forward(self,x):
        x=x+.1*torch.tanh(self.fc(x))
        return (x,None) if self.tuple_output else x

class RGB(nn.Module):
    def __init__(self):
        super().__init__();self.encoder=nn.Module();self.encoder.blocks=nn.ModuleList([Block() for _ in range(12)])
        self.rgb=nn.Conv2d(3,32,1);self.decoder=nn.Sequential(nn.Conv2d(32,32,1),nn.GELU(),nn.Conv2d(32,6,1))
    def forward(self,rgb,dsm):
        h,w=rgb.shape[-2:];hh,ww=(h+13)//14,(w+13)//14
        x=F.adaptive_avg_pool2d(self.rgb(rgb),(hh,ww)).flatten(2).transpose(1,2)
        x=torch.cat((x[:,:1]*0,x),1)
        for block in self.encoder.blocks:x=block(x)
        x=x[:,1:].transpose(1,2).reshape(len(rgb),32,hh,ww)
        return F.interpolate(self.decoder(F.interpolate(x,((h+3)//4,(w+3)//4),mode='nearest')),(h,w),mode='nearest')

class DSM(nn.Module):
    def __init__(self):
        super().__init__();self.transformer=nn.Module();self.transformer.encoder=nn.Module()
        self.transformer.encoder.layer=nn.ModuleList([Block(True) for _ in range(12)])
        self.embed=nn.Conv2d(3,32,1);self.decoder=nn.Conv2d(32,32,1);self.segmentation_head=nn.Sequential(nn.Conv2d(32,6,1))
    def forward(self,x):
        h,w=x.shape[-2:];z=F.adaptive_avg_pool2d(self.embed(x),(4,4)).flatten(2).transpose(1,2)
        for block in self.transformer.encoder.layer:z,_=block(z)
        z=z.transpose(1,2).reshape(len(x),32,4,4)
        return F.interpolate(self.segmentation_head(self.decoder(z)),(h,w),mode='nearest')

def experts():
    r=RGB();d=DSM();return Expert(r,r.decoder[-1],'rgb'),Expert(d,d.segmentation_head[0],'dsm')

class QueueTests(unittest.TestCase):
    def test_complete_does_not_mean_released(self):
        jobs={j:dict(status='COMPLETE') for j in [f'A{i}' for i in range(6)]+[f'B{i}' for i in range(1,7)]+[f'C{i}' for i in range(6)]}
        jobs.update({f'F{i}':dict(status='SKIPPED_GATE') for i in range(4)})
        state=dict(status='COMPLETE',jobs=jobs)
        self.assertEqual(predecessor_verdict(state,False,False,False),'WAITING_PREDECESSOR_RELEASE')
        self.assertEqual(predecessor_verdict(state,True,True,False),'WAITING_PREDECESSOR_RELEASE')
        self.assertEqual(predecessor_verdict(state,True,False,True),'WAITING_PREDECESSOR_RELEASE')
        self.assertEqual(predecessor_verdict(state,True,False,False),'READY')
        jobs['C0']['status']='RUNNING'
        self.assertEqual(predecessor_verdict(state,True,False,False),'HOLD_INVALID_PREDECESSOR_COMPLETE')

    def test_failure_and_unexpected_frequency_hold(self):
        self.assertEqual(predecessor_verdict(dict(status='RUNNING',jobs={}),True,False,False),'HOLD_PREDECESSOR_STOPPED')
        self.assertEqual(predecessor_verdict(dict(status='RUNNING',jobs={'B1':dict(status='TECHNICAL_FAILURE')}),True,False,True),'HOLD_PREDECESSOR_FAILURE')

    def test_reservations_never_dispatched(self):
        p=runtime_plan(fixture(),'abc',Path('/home/jovyan/zzx/root/records/research_post_ab_followup_test'))
        validate_plan(p);self.assertEqual(len(p['jobs']),26)
        state=initial_state(p)
        self.assertEqual(sum(r['status']=='RESERVED_PROTOCOL_PENDING' for r in state['jobs'].values()),22)
        self.assertEqual(next_job(state,0),'N1-0');self.assertEqual(next_job(state,1),'N1-1')
        for j in IDS[:4]:state['jobs'][j]['status']='COMPLETE'
        # Even accidental PENDING on a reservation cannot reach the worker dispatch path.
        state['jobs']['N2-0']['status']='PENDING'
        self.assertIsNone(next_job(state,0));self.assertIsNone(next_job(state,1))
        p['physical_gpus']=[0,2]
        with self.assertRaises(ValueError):validate_plan(p)

class ModelTests(unittest.TestCase):
    def test_capacity_and_gradient_flow(self):
        plan=runtime_plan(fixture(),'abc',Path('/home/jovyan/zzx/root/records/research_post_ab_followup_test'))
        totals=[];trainable=[]
        for job in plan['jobs'][:4]:
            torch.manual_seed(42);model=N1Segmenter(*experts(),job)
            model.train();rgb=torch.rand(2,3,32,32);ds=torch.rand(2,32,32);mask=torch.ones_like(ds,dtype=torch.bool)
            parts=model(rgb,ds,mask,mask,return_parts=True)
            loss=parts['logits'].square().mean()+.25*(parts['rgb'].square().mean()+parts['dsm'].square().mean());loss.backward()
            for name,p in model.named_parameters():
                if p.requires_grad:self.assertIsNotNone(p.grad,name);self.assertTrue(torch.isfinite(p.grad).all(),name)
                else:self.assertIsNone(p.grad,name)
            self.assertEqual(model.taps,{'rgb':{},'dsm':{}})
            totals.append(sum(p.numel() for p in model.parameters()));trainable.append(sum(p.numel() for p in model.parameters() if p.requires_grad))
        self.assertEqual(len(set(totals)),1)
        self.assertEqual(trainable[0],trainable[1]);self.assertEqual(trainable[2],trainable[3]);self.assertGreater(trainable[2],trainable[0])

    def test_missing_input_is_inaccessible_and_fallback_exact(self):
        p=runtime_plan(fixture(),'abc',Path('/home/jovyan/zzx/root/records/research_post_ab_followup_test'))
        for job in p['jobs'][:4]:
            model=N1Segmenter(*experts(),job).eval();rgb=torch.rand(1,3,32,32);ds=torch.rand(1,32,32)
            rm=torch.ones_like(ds,dtype=torch.bool);dm=torch.zeros_like(rm)
            with torch.no_grad():
                a=model(rgb,ds,rm,dm,return_parts=True);b=model(rgb,ds+100,rm,dm,return_parts=True)
            self.assertTrue(torch.equal(a['logits'],a['rgb']));self.assertTrue(torch.equal(a['logits'],b['logits']))
            with torch.no_grad():
                a=model(rgb,ds,dm,rm,return_parts=True);b=model(rgb+100,ds,dm,rm,return_parts=True)
            self.assertTrue(torch.equal(a['logits'],a['dsm']));self.assertTrue(torch.equal(a['logits'],b['logits']))
            with torch.no_grad():z=model(rgb,ds,dm,dm)
            self.assertEqual(int(torch.count_nonzero(z)),0)

    def test_reserved_models_cannot_run(self):
        with self.assertRaises(ValueError):N1Segmenter(*experts(),dict(id='N2-0'))

class ScreenTests(unittest.TestCase):
    def summary(self,accuracy):
        cm=np.zeros((6,6),np.int64)
        for c in range(6):cm[c,c]=accuracy;cm[c,(c+1)%6]=10000-accuracy
        joint=np.zeros((6,)*4,np.int64);joint[0,0,0,0]=1
        block=dict(metrics={'candidate':{'valid':metric(cm)}},joint={'both':encode_joint(joint)})
        tiles={c:{tile:dict(scopes={'noboundary':copy.deepcopy(block),'full':copy.deepcopy(block)}) for tile in ('3_11','5_10')} for c in ('clean','dsm_missing','rgb_missing')}
        pooled={c:{scope:dict(metrics={'candidate':{'valid':metric(cm*2)}}) for scope in ('noboundary','full')} for c in tiles}
        return dict(tiles=tiles,pooled=pooled,test6_loaded=False,independent_final_loaded=False)

    def test_gate_uses_fixed_candidate_and_both_controls(self):
        p=fixture();p['evaluation']=dict(primary=['clean','dsm_missing','rgb_missing'],families={n:['clean'] for n in ('C','QR','QD','QJ')})
        data={j:{tag:self.summary(8000 if j!='N1-3' else 8200) for tag in ('evaluation','fixed8000')} for j in IDS[:4]}
        result=screen(data,p);self.assertTrue(result['passed']);self.assertEqual(result['baseline_for_reserved_N2'],'N1-3')
        data['N1-0']={tag:self.summary(9000) for tag in ('evaluation','fixed8000')}
        data['N1-3']['fixed8000']=self.summary(7900)
        result=screen(data,p);self.assertFalse(result['passed']);self.assertEqual(result['baseline_for_reserved_N2'],'N1-2')

    def test_count_audit_rejects_pooled_and_float_corruption(self):
        p=fixture();s=self.summary(8000);audit_summary(s,p)
        s['pooled']['clean']['noboundary']['metrics']['candidate']['valid']['cm'][0][0]+=1
        with self.assertRaises(RuntimeError):audit_summary(s,p)
        s=self.summary(8000);s['tiles']['clean']['3_11']['scopes']['full']['metrics']['candidate']['valid']['cm'][0][0]=8000.0
        with self.assertRaises(RuntimeError):audit_summary(s,p)

if __name__=='__main__':unittest.main()
