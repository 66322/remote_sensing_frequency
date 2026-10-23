"""Cheap admission checks: no model, external data, GPU, or training is needed."""
import json
import hashlib
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))
import phase3_combined_plan as p
from phase3_stage_control import worker_environment
import bootstrap_phase3_combined as bootstrap


class Contract(unittest.TestCase):
    def test_downloaded_package_keeps_exact_manifest_and_refuses_changed_copy(self):
        payload = b"source fixture\n"
        manifest = json.dumps({"schema_version":1,"files":{
            "scripts/fixture.py":hashlib.sha256(payload).hexdigest()}}).encode()
        def download(commit, name):
            return manifest if name.endswith("execution_manifest.json") else payload
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)/"package"
            with patch.object(bootstrap,"download",side_effect=download):
                result, digest = bootstrap.prepare_package(package,"a"*40)
                saved = package/"configs/phase3_combined_execution_manifest.json"
                self.assertEqual(saved.read_bytes(),manifest)
                self.assertEqual(result,json.loads(manifest))
                self.assertEqual(digest,hashlib.sha256(manifest).hexdigest())
                self.assertEqual((package/"scripts/fixture.py").read_bytes(),payload)
                bootstrap.prepare_package(package,"a"*40)
                saved.write_bytes(b"changed manifest")
                with self.assertRaisesRegex(RuntimeError,"manifest changed"):
                    bootstrap.prepare_package(package,"a"*40)
                self.assertEqual(saved.read_bytes(),b"changed manifest")

    def test_target_runtime_rejected_before_cuda_probe_if_version_differs(self):
        wrong = SimpleNamespace(__version__="2.1.2+cu121")
        with self.assertRaisesRegex(RuntimeError,"2.1.2\\+cu121"):
            bootstrap.require_target_runtime(wrong)
        for available in (False,True):
            target = SimpleNamespace(__version__="2.2.2+cu121",
                cuda=SimpleNamespace(is_available=lambda:available))
            if available:
                self.assertTrue(bootstrap.require_target_runtime(target)["cuda_available"])
            else:
                with self.assertRaisesRegex(RuntimeError,"CUDA unavailable"):
                    bootstrap.require_target_runtime(target)

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
