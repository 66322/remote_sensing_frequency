"""Synthetic CPU known-answer/graph/scheduler tests; not remote scientific evidence."""
import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scipy import ndimage
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase15_common import *
from phase15_numeric import *
from structured_v0_metrics import cm,metric


class KnownAnswers(unittest.TestCase):
    def scratch(self):
        p=Path(os.environ.get('PHASE15_TEST_DIRECTORY',str(Path(__file__).resolve().parents[1]/'test_scratch'))).resolve()
        p.mkdir(parents=True,exist_ok=True)
        return tempfile.TemporaryDirectory(dir=p)
    def test_task_count_unique_and_all_cells(self):
        rows=jobs();cs=[c for j in rows for c in j['cases']]
        self.assertEqual(len(rows),100);self.assertEqual(len(cs),1540)
        self.assertEqual(len({case_id(c) for c in cs}),1540)
        self.assertEqual(sum(c['model'] in ('S1','R16') and c['family']!='clean' and c['ratio']==25 for c in cs),1280)
        self.assertEqual(sum(c['ratio'] in (5,10) for c in cs),80)
        self.assertEqual(sum(c['model']=='S13' and c['family']!='clean' for c in cs),160)
        self.assertTrue(all(c['tile'] in TILES for c in cs))

    def test_scheduler_dependencies_and_no_retry(self):
        rows=jobs();s={j['id']:dict(status='PENDING') for j in rows}
        self.assertTrue(all(x['kind']=='reference' for x in ready(s,rows)))
        for j in rows:
            if j['kind']=='reference':s[j['id']]['status']='COMPLETE'
        self.assertEqual(len(ready(s,rows)),80)
        fail=rows[20]['id'];s[fail]['status']='TECHNICAL_FAILURE'
        self.assertNotIn(fail,[j['id'] for j in ready(s,rows)])

    def test_nested_exact_and_deterministic(self):
        mask=np.zeros((100,100),bool);mask.ravel()[::4]=True
        result=nested(mask,'toy',1)
        self.assertEqual([int(result[r].sum()) for r in (5,10,25)],[500,1000,2500])
        self.assertEqual(canonical(result[25]),canonical(mask))
        self.assertTrue((result[5]<=result[10]).all());self.assertTrue((result[10]<=mask).all())
        self.assertTrue(np.array_equal(result[5],nested(mask,'toy',1)[5]))

    def test_crop_permutation_unequal_edges_is_bijective(self):
        shape=(11,13);mapping=permutation(shape,'toy','crop_shuffle',block=4)
        check=map_check(mapping,shape);self.assertTrue(check['bijective'])
        src=np.arange(np.prod(shape)).reshape(shape)
        shuffled=src.ravel()[mapping].reshape(shape)
        for y in range(0,11,4):
            for x in range(0,13,4):
                hh,ww=min(4,11-y),min(4,13-x)
                block=shuffled[y:y+hh,x:x+ww]
                flat=block.ravel()
                yy,xx=divmod(int(flat[0]),13)
                self.assertTrue(np.array_equal(block,src[yy:yy+hh,xx:xx+ww]))

    def test_tile_permutation_exact_multiset(self):
        a=np.arange(77,dtype=np.float32).reshape(7,11)
        index=permutation(a.shape,'toy','tile_shuffle')
        map_check(index,a.shape)
        self.assertTrue(np.array_equal(np.sort(a.ravel()),np.sort(a.ravel()[index])))
        self.assertTrue(np.array_equal(index,permutation(a.shape,'toy','tile_shuffle')))
        with self.assertRaises(ValueError):map_check(np.zeros(77,np.int32),a.shape)

    def test_distance_rectangle_and_ring(self):
        m=np.ones((9,9),bool);b=distance_bins(m)
        self.assertEqual(np.bincount(b.ravel(),minlength=4).tolist(),[72,9,0,0])
        ring=np.ones((9,9),bool);ring[2:7,2:7]=False
        r=distance_bins(ring);self.assertTrue((r[ring]==0).all());self.assertTrue((r[~ring]==255).all())

    def test_confusion_conservation_invalid_output(self):
        g=np.arange(36,dtype=np.uint8).reshape(6,6)%6;p=g.copy();g[0,0]=255
        c=cm(g,p,np.ones_like(g,bool))
        self.assertEqual(int(c.sum()),35);self.assertEqual(metric(c),1)
        p[1,1]=255
        with self.assertRaises(ValueError):cm(g,p,np.ones_like(g,bool))

    def test_transitions_net_count_and_by_class(self):
        g=np.array([[0,1],[2,3]],np.uint8);clean=np.array([[0,0],[2,0]],np.uint8)
        bad=np.array([[1,1],[2,1]],np.uint8)
        t=transitions(g,clean,bad,np.ones_like(g,bool))
        self.assertEqual((t['valid'],t['harmed'],t['rescued']),(4,1,1))
        self.assertEqual(sum(x['valid'] for x in t['by_class'].values()),4)

    def test_oracle_any_correct_and_ties(self):
        g=np.array([[0,1,2,3],[4,0,1,2],[3,4,0,1],[2,3,4,0]],np.uint8)
        p0=(g+1)%5;p1=p0.copy();p2=p0.copy();p3=p0.copy();p4=p0.copy()
        p0[0,0]=g[0,0];p1[0,:2]=g[0,:2];p2[0,1:3]=g[0,1:3];p4[-1,-1]=g[-1,-1]
        out,origin=oracle(g,[p0,p1,p2,p3,p4])
        self.assertEqual(int((out==g).sum()),4)
        self.assertEqual(origin[0,:3].tolist(),[0,1,2]);self.assertEqual(int(origin[-1,-1]),4)
        self.assertTrue(np.array_equal(out[1:3],p0[1:3]))

    def test_patch_oracle_one_expert_correct_count(self):
        g=np.zeros((4,5),np.uint8);a=np.ones_like(g);b=a.copy()
        a[:2,:2]=0;b[:2,2:4]=0
        out,origin=oracle(g,[a,b],patch=2)
        self.assertEqual(int((out==g).sum()),8)
        self.assertTrue((origin[:2,:2]==0).all());self.assertTrue((origin[:2,2:4]==1).all())
        self.assertTrue((origin[2:]==0).all())

    def test_composition_and_seam_containment(self):
        mask=np.zeros((9,9),bool);mask[3:6,3:6]=True
        a=np.zeros((9,9),np.uint8);d=np.ones_like(a)
        raw=np.where(mask,d,a).astype(np.uint8)
        smoothed,band=seam_smooth(raw,mask)
        self.assertTrue(np.array_equal(smoothed[~band],raw[~band]))
        self.assertEqual(int(smoothed[4,4]),1)
        self.assertTrue((raw[mask]==1).all());self.assertTrue((raw[~mask]==0).all())
        _,full_band=seam_smooth(raw,np.ones_like(mask))
        self.assertFalse(full_band.any())

    def test_observable_features_never_read_gt(self):
        op=np.ones((13,13,3),np.float32);ds=np.arange(169,dtype=np.float32).reshape(13,13)/168
        fields=feature_arrays(op,ds)
        self.assertTrue((fields['rgb_zero_fraction']==0).all())
        self.assertTrue((fields['dsm_variance']>=0).all());self.assertTrue(np.isfinite(fields['dsm_gradient']).all())

    def test_conditional_counts_only_disagreement(self):
        g=np.array([[0,1],[0,1]],np.uint8);a=g.copy();b=g.copy();b[0,0]=1
        rows=condition_counts(g,[a,b],np.zeros_like(g),np.ones_like(g,bool))
        self.assertEqual(rows['0'],dict(valid=1,correct=[1,0]))

    def test_bootstrap_pairing_and_no_pseudoreplication(self):
        r=bootstrap([.5]*20);self.assertEqual(r['CI95'],[.5,.5]);self.assertEqual(r['n_mask_realizations'],20)
        self.assertIsNone(bootstrap([1.])['mean'])
        self.assertEqual(exact_signflip([1]*20),2/(1<<20))

    def test_entropy_and_logit_stitch_cpu(self):
        import torch
        torch.set_num_threads(1)
        from phase15_inference import infer_one
        class Fake(torch.nn.Module):
            def forward(self,op,ds,rm,dm,return_parts=True):
                z=torch.zeros((len(op),6,*ds.shape[-2:]));z[:,2]=3
                return dict(logits=z,rgb=z,dsm=z)
        op=np.zeros((512,512,3),np.float32);ds=np.zeros((512,512),np.float32);m=np.ones_like(ds,bool)
        with patch.object(torch.Tensor,'cuda',lambda t:t):
            pred,ent,own=infer_one(Fake(),'S1',op,ds,m,m,lambda **kw:None,entropy=True)
        self.assertTrue((pred==2).all());self.assertTrue((ent==1).all());self.assertTrue(all(own.values()))

    def test_s13_graph_equals_original_continuation(self):
        import torch
        from torch import nn
        from torch.nn import functional as F
        from model.rebuild_v1_post_ab_n1 import N1Segmenter
        from model.post_n3_s1_model import Continuation
        from model.post_n5_cross_paths import CrossPaths
        class FakeExpert(nn.Module):
            def __init__(self,kind):
                super().__init__();self.kind=kind;self.channels=32
                self.net=nn.Module();self.net.rgb=nn.Conv2d(3,32,1)
                self.net.decoder=nn.Sequential(nn.Identity(),nn.Conv2d(32,6,1))
                self.net.encoder=nn.Module();self.net.encoder.blocks=nn.ModuleList([nn.Identity() for _ in range(12)])
                self.net.transformer=nn.Module();self.net.transformer.encoder=nn.Module()
                self.net.transformer.encoder.layer=nn.ModuleList([nn.Identity() for _ in range(12)])
            def configure(self,joint):self.requires_grad_(joint)
            def forward(self,r,d):
                x=r if self.kind=='rgb' else d[:,None].repeat(1,3,1,1)
                feature=F.avg_pool2d(self.net.rgb(x),4)
                return F.interpolate(self.net.decoder(feature),x.shape[-2:],mode='nearest'),feature
        torch.manual_seed(42)
        original=N1Segmenter(FakeExpert('rgb'),FakeExpert('dsm'),dict(id='N1-2',information_entry='late',adaptation='last4_and_heads'))
        scratch=Path(os.environ.get('PHASE15_TEST_DIRECTORY',str(Path(__file__).resolve().parents[1]/'test_scratch')));scratch.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as d:
            path=Path(d)/'initial.pth';torch.save(dict(global_step=8000,model=original.state_dict()),path)
            job=dict(id='S1-3',initial_checkpoint_path=str(path),initial_checkpoint_sha256=sha(path))
            legacy=Continuation(FakeExpert('rgb'),FakeExpert('dsm'),job).eval()
            base=copy.deepcopy(original);base.load_state_dict(legacy.state_dict());wrapped=CrossPaths(base,'A1B0C0').eval()
            r=torch.rand(2,3,64,64);ds=torch.rand(2,64,64)
            for kind in ('clean','local','full_missing','present_zero'):
                rm=torch.ones_like(ds,dtype=torch.bool);dm=rm.clone();view=r;aux=ds
                if kind=='local':rm[:,16:48,16:48]=False
                if kind=='full_missing':rm.zero_()
                if kind=='present_zero':aux=ds*0
                with torch.no_grad():
                    a=legacy(view,aux,rm,dm,return_parts=True);b=wrapped(view,aux,rm,dm,return_parts=True)
                for n in ('logits','rgb','dsm','raw'):self.assertTrue(torch.equal(a[n],b[n]),kind+' '+n)

    def test_plan_tampering_rejected(self):
        with self.scratch() as folder:
            b=Path(folder);p=dict(protocol=PROTOCOL,jobs=jobs(),tiles=list(TILES),optimizer_updates=0,
                                 physical_gpus=[0,1],wall_deadline_hours=None,source_files={})
            write(b/'plan.json',p);write(b/'registration.json',dict(plan_sha256=sha(b/'plan.json')))
            validate(b)
            p['optimizer_updates']=1;write(b/'plan.json',p)
            with self.assertRaises(RuntimeError):validate(b)

    def test_oracle_joint_counts_and_composition_known_answer(self):
        g=np.tile(np.arange(6,dtype=np.uint8),(8,1));clean=g.copy();mask=np.zeros_like(g,bool);mask[2:6,2:4]=True
        predictions=[g.copy() for _ in EXPERTS];predictions[0][mask]=(g[mask]+1)%6
        result=oracle_evidence(g,clean,predictions,mask,np.zeros_like(g),{'dsm_mean':np.zeros_like(g)})
        self.assertEqual(sum(map(sum,result['joint_correct_by_class']['valid'])),48)
        raw=result['systems']['known_mask_raw']['mask']['missing_cm']
        self.assertEqual(sum(np.diag(raw)),int(mask.sum()))
        c=result['conditional_counts']['dsm_mean']['mask']['0']
        self.assertEqual(c['valid'],8);self.assertEqual(c['correct'],[0,8,8,8,8])

    def test_full_fixed_summary_synthetic_end_to_end(self):
        from summarize_phase15 import summarize
        with self.scratch() as folder:
            b=Path(folder);p=dict(protocol=PROTOCOL,jobs=jobs(),tiles=list(TILES),optimizer_updates=0,
                                 physical_gpus=[0,1],wall_deadline_hours=None,source_files={})
            write(b/'plan.json',p);write(b/'registration.json',dict(plan_sha256=sha(b/'plan.json')))
            write(b/'code_manifest.json',dict(files={}));write(b/'preparation_complete.json',dict(fixture=True))
            bind=binding(b)
            clean=np.eye(6,dtype=np.int64)*100
            def m(n):
                x=np.eye(6,dtype=np.int64)*n
                for i in range(6):x[i,(i+1)%6]=100-n
                return x.tolist()
            def cell(n=70):
                return dict(clean_cm=clean.tolist(),missing_cm=m(n),intact_clean_cm=clean.tolist(),
                    transitions=dict(valid=600,harmed=6*(100-n),rescued=0))
            for j in jobs():
                rs={}
                for c in j['cases']:
                    cid=case_id(c);row=dict(case=c,binding=bind,arrays={},scopes={'noboundary':{r:cell() for r in ('all','missing','core5')}})
                    write(b/'cases'/(cid+'.json'),row);rs[cid]=sha(b/'cases'/(cid+'.json'))
                write(b/'jobs'/j['id']/'complete.json',dict(binding=bind,optimizer_updates=0,cases=[case_id(c) for c in j['cases']],records=rs))
            names=list(EXPERTS)+['known_mask_raw','known_mask_smoothed','oracle_pixel','oracle_patch128','oracle_patch256']
            for phase,families in (('E',FAMILIES[1:]),('D',FAMILIES)):
                records={}
                for t in TILES:
                    for i in range(1,21):
                        for f in families:
                            n=f'{t}_{i:02d}_{f}'
                            if phase=='E':
                                result={str(k):dict(valid=100,harmed=20 if k==0 else 10,rescued=0) for k in range(4)}
                            else:
                                result=dict(systems={name:{r:cell(90 if name.startswith('oracle') else 50) for r in ('valid','mask','healthy')} for name in names},
                                    conditional_counts={'dsm_mean':{'mask':{'0':dict(valid=20,correct=[10]*5)}}})
                            write(b/'analysis'/phase/(n+'.json'),dict(result=result));records[n]=sha(b/'analysis'/phase/(n+'.json'))
                write(b/'analysis'/phase/'complete.json',dict(binding=bind,records=records))
            out=summarize(b)
            self.assertEqual(out['E']['profile_verdict'],'EDGE_DOMINANT')
            self.assertEqual(out['A']['S1']['intact']['pooled']['PE']['mean'],0)
            self.assertEqual(out['routing']['verdict'],'CONDITIONAL_ENTRY_REQUIRES_OBSERVABLE_REVIEW')
            self.assertFalse(out['routing']['new_training_dispatched'])
            self.assertIsNone(out['B']['5']['PE'])
            self.assertEqual(out['optimizer_updates'],0)

    def test_controller_smoke_order_two_lanes_and_failure_hold(self):
        import types
        import control_phase15 as controller
        class Proc:
            count=100
            def __init__(self,rc=0):
                Proc.count+=1;self.pid=Proc.count;self.returncode=None;self.rc=rc;self.calls=0;self.terminated=False
            def poll(self):
                self.calls+=1
                if self.calls>=2:self.returncode=self.rc
                return self.returncode
            def terminate(self):self.terminated=True;self.returncode=-15
            def kill(self):self.returncode=-9
            def wait(self,timeout=None):return self.returncode
        mutex=types.SimpleNamespace(LOCK_EX=1,LOCK_NB=2,flock=lambda *args:None)
        for fail in (False,True):
            with self.scratch() as folder:
                b=Path(folder);rows=[dict(id=f'r{i}',kind='reference',cases=[]) for i in range(2)]+[dict(id=f'j{i}',kind='missing',cases=[]) for i in range(4)]
                write(b/'queue_status.json',dict(status='REGISTERED_PENDING_PREPARATION',jobs={j['id']:dict(status='PENDING') for j in rows}))
                calls=[]
                def spawn(base,script,args=(),gpu=None,log_name=None):
                    calls.append((script,list(args),gpu))
                    if script=='smoke_phase15.py':
                        write(b/'smoke'/('gpu'+str(gpu))/'complete.json',dict(all_passed=True,binding={},optimizer_updates=0))
                    if script=='run_phase15.py':
                        self.assertTrue((b/'smoke_pass.json').exists())
                        return Proc(1 if fail and args[1]=='r0' else 0)
                    if script=='summarize_phase15.py':write(b/'summary.json',dict(fixture=True))
                    return Proc()
                write(b/'cpu_checks.log',{'fixture':True})
                with patch.dict(sys.modules,{'fcntl':mutex}),patch.object(controller,'validate',return_value={'jobs':rows}),\
                     patch.object(controller,'verify_code'),patch.object(controller,'binding',return_value={}),\
                     patch.object(controller,'accept_job'),patch.object(controller,'start',side_effect=spawn),patch.object(controller.time,'sleep'):
                    if fail:
                        with self.assertRaises(RuntimeError):controller.main(b)
                    else:controller.main(b)
                state=read(b/'queue_status.json')
                self.assertEqual(state['status'],'TECHNICAL_FAILURE_HOLD' if fail else 'PHASE15_COMPLETE_AWAITING_REVIEW')
                used={gpu for script,_,gpu in calls if script=='run_phase15.py'}
                self.assertEqual(used,{0,1})
                if fail:self.assertEqual(sum(script=='run_phase15.py' for script,_,_ in calls),2)


if __name__=='__main__':unittest.main()
