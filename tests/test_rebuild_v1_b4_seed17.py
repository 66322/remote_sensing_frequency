import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_rebuild_v1_b4_seed17 as b4
from rebuild_v1_b2_common import validate_matched_config


class B4ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.root_patch = patch.object(b4, "ROOT", ROOT)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()

    def test_seed17_configs_are_matched(self):
        configs = b4.validate_configs()
        self.assertEqual(set(configs), {"C17", "R05_KD17", "KD17"})
        reference = configs["KD17"]
        validate_matched_config(configs["R05_KD17"], reference, expected_seed=17)

    def test_queue_has_three_independent_arms(self):
        jobs = b4.build_jobs("unit", b4.ROOT / "records/rebuild_v1_b4_unit")
        self.assertEqual(len(jobs), 12)
        by_name = {job["name"]: job for job in jobs}
        for label in ("C17", "R05_KD17", "KD17"):
            self.assertEqual(by_name[label + "_SMOKE"]["deps"], [])
            self.assertEqual(by_name[label + "_TRAIN"]["deps"], [label + "_SMOKE"])
            self.assertEqual(by_name[label + "_ROBUST"]["deps"], [label + "_TRAIN"])
            self.assertEqual(by_name[label + "_PAIRED"]["deps"], [label + "_TRAIN"])
        self.assertTrue(all("--resume" not in job["command"] for job in jobs))

    def test_seed17_paths_and_four_k_horizon(self):
        for cfg in b4.validate_configs().values():
            self.assertEqual(cfg["seed"], 17)
            self.assertEqual(cfg["schedule"]["scheduler_total_steps"], 4000)
            self.assertEqual(cfg["schedule"]["stop_at_step"], 4000)
            self.assertIn("seed17_sched16000_stop16000", cfg["student_init"])


if __name__ == "__main__":
    unittest.main()
