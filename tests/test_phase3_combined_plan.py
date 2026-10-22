"""Cheap admission checks: no model, external data, GPU, or training is needed."""
import json
import hashlib
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))
import phase3_combined_plan as p
from phase3_stage_control import worker_environment


class Contract(unittest.TestCase):
    def test_stage_counts(self):
        plan = json.loads((HERE / "configs/phase3_combined_plan.json").read_text(encoding="utf-8"))
        self.assertTrue(p.validate_plan(plan))
        self.assertEqual(len(p.jobs("J")), 42)
        self.assertEqual(len(p.jobs("R")), 18)
        self.assertEqual(len(p.jobs("T")), 30)
        self.assertEqual(len(p.jobs("V")), 30)

    def test_heldout_paths_rejected_before_file_access(self):
        for value in ("/home/jovyan/zzx/data/Test6/a.tif",
                      "/home/jovyan/zzx/data/held4/a.tif",
                      "/home/jovyan/zzx/data/test/a.tif"):
            with self.assertRaises(ValueError):
                p.admissible_path(value)

    def test_frozen_package_manifest(self):
        manifest = json.loads((HERE / "configs/phase3_combined_execution_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        self.assertGreaterEqual(len(manifest["files"]), 18)
        for name, expected in manifest["files"].items():
            observed = p.digest(HERE / name)
            if observed != expected and (HERE / ".git").exists():
                # Existing Windows checkouts can expose CRLF bytes, while the
                # immutable GitHub blob downloaded by bootstrap is LF.
                blob = subprocess.check_output(["git", "show", "HEAD:" + name], cwd=HERE)
                observed = hashlib.sha256(blob).hexdigest()
            self.assertEqual(observed, expected, name)

    def test_new_stages_keep_temporary_files_in_own_run(self):
        class FakeCommon:
            @staticmethod
            def environment(source, uuid):
                return {"CUDA_VISIBLE_DEVICES": uuid, "TMPDIR": "/old/run/temporary"}
        env = worker_environment(FakeCommon, "/old/run", "/home/jovyan/zzx/new/run", "GPU-1")
        self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "GPU-1")
        self.assertEqual(env["TMPDIR"].replace("\\", "/"), "/home/jovyan/zzx/new/run/temporary")


if __name__ == "__main__":
    unittest.main()
