import importlib.util,sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from d28_pressure import masks,apply,cases,regions,pool_cm
from launch_rebuild_v1_d28 import terminal

class PressureTests(unittest.TestCase):
    def test_exact_disjoint_reproducible_masks_and_balanced_marginals(self):
        pool,meta=masks((67,73),'3_11');again,m=masks((67,73),'3_11')
        self.assertTrue(np.array_equal(pool,again));self.assertEqual(meta,m)
        self.assertEqual(pool.sum(1).sum(1).tolist(),[67*73//4]*2);self.assertFalse((pool[0]&pool[1]).any())
        shared=[(0,0),(1,1)];ind=[(0,0),(0,1),(1,0),(1,1)]
        for modality in (0,1):
            self.assertTrue(np.array_equal(np.mean([pool[p[modality]] for p in shared],0),np.mean([pool[p[modality]] for p in ind],0)))
        self.assertAlmostEqual(np.mean([(pool[a]&pool[b]).sum() for a,b in ind]),meta['quota']/2)
    def test_pressure_changes_only_declared_regions_and_never_labels(self):
        rng=np.random.default_rng(1);item=dict(optical=rng.random((67,73,3),dtype=np.float32),dsm=rng.random((67,73),dtype=np.float32),full_gt=np.zeros((67,73),np.uint8));pool,_=masks((67,73),'3_11')
        for _,recipe,level,pair in cases()[1:]:
            out=apply(item,pool,recipe,level,pair,'3_11')
            self.assertTrue(np.array_equal(out['optical'][~pool[pair[0]]],item['optical'][~pool[pair[0]]]))
            self.assertTrue(np.array_equal(out['dsm'][~pool[pair[1]]],item['dsm'][~pool[pair[1]]]))
            other=dict(item,full_gt=np.ones((67,73),np.uint8));changed=apply(other,pool,recipe,level,pair,'3_11')
            self.assertTrue(np.array_equal(out['optical'],changed['optical']));self.assertTrue(np.array_equal(out['dsm'],changed['dsm']))
            reg=regions(pool,pair);self.assertTrue(np.all(sum(reg[n].astype(int) for n in reg if n!='valid')==1))
    def test_raw_counts_pool_not_average_iou(self):
        a=np.diag([100,1,1,1,1,1]).astype(np.int64);b=np.zeros((6,6),np.int64);b[0,1]=10
        self.assertTrue(np.array_equal(pool_cm([a,b]),a+b));self.assertEqual(pool_cm([a,b]).dtype,np.int64)
    def test_predecessor_requires_all_ten_terminal_and_final_status(self):
        arms=['S0','S1','G0','G1','L0','L1','C0','C1','L1-sh','C1-sh'];s=dict(status='RUNNING',jobs={n:dict(status='COMPLETE') for n in arms})
        self.assertFalse(terminal(s));s['status']='COMPLETE';self.assertTrue(terminal(s));s['jobs']['G1']['status']='RUNNING';self.assertFalse(terminal(s))
        s['status']='COMPLETE_WITH_TECHNICAL_FAILURES';s['jobs']['G1']['status']='TECHNICAL_FAILURE';self.assertTrue(terminal(s));del s['jobs']['C1-sh'];self.assertFalse(terminal(s))
    def test_actual_counts_and_joint_aggregation(self):
        from d27_evaluation import counts,joint_counts,encode_joint
        from summarize_rebuild_v1_d28 import aggregate
        gt=np.array([[0,1,255],[2,3,4]],np.uint8);r=np.array([[0,0,0],[2,3,0]],np.uint8);d=np.array([[0,1,0],[1,3,4]],np.uint8)
        region=np.ones_like(gt,bool)
        rows=[dict(metric=counts(gt,pred,region),joint=encode_joint(joint_counts(gt,r,d,pred,region))) for pred in (r,d)]
        combined=aggregate(rows)
        self.assertEqual(combined['metric']['valid'],10)
        self.assertEqual(combined['joint_report']['only_dsm_correct']['valid'],4)
        self.assertEqual(combined['joint_report']['only_dsm_correct']['fused_correct'],2)
        empty=dict(metric=counts(gt,r,~region),joint=encode_joint(joint_counts(gt,r,d,r,~region)))
        self.assertIsNone(aggregate([empty])['metric']['mIoU_fg5'])
    def test_source_waits_for_lock_and_checkpoint_binding_before_any_gpu(self):
        source=(Path(__file__).resolve().parents[1]/'scripts/launch_rebuild_v1_d28.py').read_text()
        self.assertLess(source.index('if terminal(previous)'),source.index('frozen=checkpoints'))
        self.assertLess(source.index('frozen=checkpoints'),source.index("['nvidia-smi'"))
        self.assertIn('fcntl.LOCK_EX|fcntl.LOCK_NB',source)
        self.assertIn("status='WAITING_EVIDENCE'",source)
        self.assertLess(source.index('if released(parent):break'),source.index('frozen=checkpoints'))
    def test_live_lock_blocks_handover_then_release_allows_it(self):
        from unittest.mock import Mock,patch,mock_open
        from launch_rebuild_v1_d28 import released
        fake=Mock(LOCK_EX=2,LOCK_NB=4);parent=Path('fixture')
        with patch.dict(sys.modules,{'fcntl':fake}),patch.object(Path,'open',mock_open()):
            fake.flock.side_effect=BlockingIOError();self.assertFalse(released(parent))
            fake.flock.side_effect=None;self.assertTrue(released(parent))
            self.assertEqual(fake.flock.call_args.args[1],6)
    def test_missing_required_checkpoints_cannot_be_substituted(self):
        from unittest.mock import patch
        from launch_rebuild_v1_d28 import checkpoints
        root=Path.cwd();parent=root/'records/fixture';runtime=dict(experts={k:dict(path=k+'.pth',step=1,sha256='fixed') for k in ('rgb','dsm')},predecessor_directory=str(root/'records/d26'))
        with patch('launch_rebuild_v1_d28.read',return_value=runtime),patch.object(Path,'exists',return_value=False):
            result=checkpoints(root,parent,{})
        self.assertEqual(result['models'],{});self.assertEqual(len(result['missing']),7)
if __name__=='__main__':unittest.main()
