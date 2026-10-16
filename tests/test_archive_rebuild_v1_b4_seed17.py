import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from archive_rebuild_v1_b4_seed17 import build_decision


class B4ArchiveDecisionTests(unittest.TestCase):
    def test_replication_gate_requires_all_degradation_directions(self):
        global_metrics = {
            "C17": {"clean": 86.0, "dsm_down8": 84.0, "dsm_zero": 83.0},
            "R05_KD17": {"clean": 86.5, "dsm_down8": 84.5, "dsm_zero": 83.5},
            "KD17": {"clean": 86.4, "dsm_down8": 84.7, "dsm_zero": 83.6},
        }
        local = {
            "C17": {"D1_local_missing": -4.0, "D3_local_down8": -1.2},
            "R05_KD17": {"D1_local_missing": -4.5, "D3_local_down8": -1.1},
            "KD17": {"D1_local_missing": -4.0, "D3_local_down8": -0.9},
        }
        result = build_decision(global_metrics, local)
        self.assertTrue(result["gate"]["replication_pass"])

        global_metrics["KD17"]["dsm_zero"] = 83.4
        result = build_decision(global_metrics, local)
        self.assertFalse(result["gate"]["replication_pass"])


if __name__ == "__main__":
    unittest.main()
