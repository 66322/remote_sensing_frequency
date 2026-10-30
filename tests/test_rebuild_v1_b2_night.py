import importlib.util
import json
import sys
import unittest
import tempfile
import types
from unittest.mock import patch, Mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np
import torch
from rebuild_v1_b2_common import teacher_distribution, region_masks, confusion, validate_matched_config
import run_rebuild_v1_b2_night as queue


class ProtocolTests(unittest.TestCase):
    def test_matched_configs(self):
        ref = json.loads((ROOT / "configs/rebuild_v1/b1_kd_safe_teacher_4k.json").read_text())
        for name in ("b2_r05_teacher_4k.json", "b2_safe_average_teacher_4k.json"):
            cfg = json.loads((ROOT / "configs/rebuild_v1" / name).read_text())
            validate_matched_config(cfg, ref)
            cfg["schedule"]["stop_at_step"] = 500
            with self.assertRaises(ValueError):
                validate_matched_config(cfg, ref)

    def test_average_known_mask_and_normalization(self):
        torch.manual_seed(4)
        a, b = torch.randn(2, 6, 5, 7), torch.randn(2, 6, 5, 7)
        mask = torch.rand(2, 5, 7) > 0.5
        target, p1, weight = teacher_distribution(a, b, mask, 2, "safe_average_teacher_kd")
        expected = (a.div(2).softmax(1) + b.div(2).softmax(1)) / 2
        torch.testing.assert_close(target.sum(1), torch.ones_like(weight))
        torch.testing.assert_close(target.permute(0,2,3,1)[mask], p1.permute(0,2,3,1)[mask])
        torch.testing.assert_close(target.permute(0,2,3,1)[~mask], expected.permute(0,2,3,1)[~mask])
        self.assertTrue(torch.all(weight[mask] == 0))
        self.assertTrue(torch.all(weight[~mask] == 0.5))

    def test_r05_has_no_fallback(self):
        a, b = torch.randn(1, 6, 3, 3), torch.randn(1, 6, 3, 3)
        target, _, weight = teacher_distribution(a, b, torch.ones(1,3,3,dtype=torch.bool), 2, "r05_teacher_kd")
        torch.testing.assert_close(target, b.div(2).softmax(1))
        self.assertTrue(torch.all(weight == 1))

    def test_backward_with_no_grad_teacher_targets(self):
        a, b = torch.randn(1,6,3,3), torch.randn(1,6,3,3)
        for mode in ("r05_teacher_kd", "safe_average_teacher_kd"):
            with torch.no_grad():
                target, _, _ = teacher_distribution(a,b,torch.zeros(1,3,3,dtype=torch.bool),2,mode)
            student = torch.randn(1,6,3,3,requires_grad=True)
            loss = torch.nn.functional.kl_div(student.div(2).log_softmax(1), target, reduction="none").sum(1).mean()*4
            loss.backward()
            self.assertTrue(torch.isfinite(student.grad).all())

    def test_regions_and_confusion_partition(self):
        damage = np.zeros((31,33), bool)
        damage[:15,:16] = True
        masks = region_masks(damage, radius=2)
        self.assertFalse(np.any(masks["damaged"] & masks["intact"]))
        self.assertTrue(np.all(masks["damaged"] | masks["intact"]))
        self.assertFalse(masks["boundary"][0,0])
        self.assertTrue(masks["boundary"][14,15])
        rng = np.random.default_rng(42)
        gt = rng.integers(0,6,damage.shape)
        gt[0,0] = 255
        pred = rng.integers(0,6,damage.shape)
        cm = {k: confusion(gt,pred,v) for k,v in masks.items()}
        np.testing.assert_array_equal(cm["whole"], cm["damaged"]+cm["intact"])
        self.assertEqual(cm["whole"].dtype, np.int64)
        self.assertEqual(cm["whole"].sum(), gt.size-1)

    def test_empty_and_global_boundaries(self):
        for value in (False, True):
            regions = region_masks(np.full((10,11),value))
            self.assertFalse(regions["boundary"].any())
        self.assertEqual(confusion(np.array([[255]]),np.array([[0]]),np.array([[True]])).sum(),0)

    def test_queue_dependencies_and_no_resume(self):
        jobs = queue.commands("unit_test", queue.ROOT / "records/unit_test")
        names = {j["name"] for j in jobs}
        self.assertEqual(len(jobs),10)
        for j in jobs:
            self.assertTrue(set(j["deps"]) <= names)
            self.assertNotIn("--resume", j["command"])
        byname = {j["name"]:j for j in jobs}
        self.assertIn("R05_KD_TRAIN_SMOKE",byname["R05_KD_TRAIN"]["deps"])
        self.assertIn("AVG_KD_TRAIN",byname["AVG_KD_REGIONS"]["deps"])
        self.assertNotIn("R05_KD_TRAIN",byname["AVG_KD_TRAIN_SMOKE"]["deps"])

    def test_logit_aggregation_argmax(self):
        rng = np.random.default_rng(5)
        logits = rng.normal(size=(6,31,33)).astype(np.float32)
        count = rng.integers(1,10,size=(31,33)).astype(np.float32)
        np.testing.assert_array_equal(logits.argmax(0),(logits/count[None]).argmax(0))

    def test_failed_dependency_skips_but_independent_job_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "records").mkdir()
            completed = root / "completed.json"
            completed.write_text(json.dumps({"global_step":4000,"test6_loaded":False}))
            jobs = [dict(name=name,command=["fake"],outputs=[],deps=deps,seconds=5,required=[str(completed)])
                    for name,deps in (("FIRST_TRAIN",[]),("DEPENDENT",["FIRST_TRAIN"]),("SECOND_TRAIN",[]))]
            fcntl = types.SimpleNamespace(flock=lambda *a: None,LOCK_EX=1,LOCK_NB=2)
            failed, success = Mock(), Mock()
            failed.wait.return_value = 1
            success.wait.return_value = 0
            with patch.dict(sys.modules,{"fcntl":fcntl}), patch.object(queue,"ROOT",root), \
                 patch.object(queue.subprocess,"run",return_value=types.SimpleNamespace(returncode=0)), \
                 patch.object(queue.subprocess,"Popen",side_effect=[failed,success]) as launch, \
                 patch.object(queue,"archive_results"):
                rc = queue.execute(root/"records/night",jobs,1,{})
            self.assertEqual(rc,1)
            self.assertEqual(launch.call_count,2)
            states = json.loads((root/"records/night/queue_summary.json").read_text())["statuses"]
            self.assertEqual(states["FIRST_TRAIN"],"FAILED")
            self.assertEqual(states["DEPENDENT"],"SKIPPED")
            self.assertEqual(states["SECOND_TRAIN"],"COMPLETE")
            self.assertEqual(states["QUEUE"],"FINISHED_WITH_ISSUES")

    def test_boundary_failure_does_not_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "records").mkdir()
            job = dict(name="X", command=["fake"], outputs=[],deps=[],seconds=5,required=[])
            fcntl = types.SimpleNamespace(flock=lambda *a: None,LOCK_EX=1,LOCK_NB=2)
            with patch.dict(sys.modules,{"fcntl":fcntl}), patch.object(queue,"ROOT",root), \
                 patch.object(queue.subprocess,"run",return_value=types.SimpleNamespace(returncode=90)), \
                 patch.object(queue.subprocess,"Popen") as launch, patch.object(queue,"archive_results"):
                rc = queue.execute(root/"records/night",[job],1,{})
            self.assertEqual(rc,1)
            launch.assert_not_called()

    def test_timeout_stops_child_and_records_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"records").mkdir()
            job=dict(name="X_TRAIN", command=["fake"],outputs=[],deps=[],seconds=1,required=[])
            fcntl=types.SimpleNamespace(flock=lambda *a:None,LOCK_EX=1,LOCK_NB=2)
            process=Mock()
            process.wait.side_effect=queue.subprocess.TimeoutExpired("fake",1)
            with patch.dict(sys.modules,{"fcntl":fcntl}), patch.object(queue,"ROOT",root), \
                 patch.object(queue.subprocess,"run",return_value=types.SimpleNamespace(returncode=0)), \
                 patch.object(queue.subprocess,"Popen",return_value=process), \
                 patch.object(queue,"terminate") as terminate, patch.object(queue,"archive_results"):
                rc=queue.execute(root/"records/night",[job],1,{})
            terminate.assert_called_once_with(process)
            self.assertEqual(rc,1)


if __name__ == "__main__":
    unittest.main()
