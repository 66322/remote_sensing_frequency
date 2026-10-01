import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location("probe",Path(__file__).resolve().parents[1]/"scripts/probe_rebuild_v1_d23_gate.py")
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

class ProbeAdmissionTests(unittest.TestCase):
    def test_busy_gpu_and_existing_compute_are_rejected(self):
        for info in ({"used_mib":1025,"util_percent":0},{"used_mib":0,"util_percent":6}):
            with self.assertRaises(RuntimeError):p.require_idle(info)
        p.require_idle({"used_mib":0,"util_percent":0})
        with patch.object(p.subprocess,"check_output",return_value="GPU-a, 123\nGPU-b, 456\n"):
            with self.assertRaisesRegex(RuntimeError,"compute process"):p.reject_existing_compute("GPU-a")
            p.reject_existing_compute("GPU-c")

    def test_inventory_preserves_physical_index_and_uuid(self):
        with patch.object(p.subprocess,"check_output",return_value="0, GPU-a, 0, 0\n1, GPU-b, 2048, 50\n"):
            info=p.gpu_inventory()
        self.assertEqual(info[1],{"uuid":"GPU-b","used_mib":2048,"util_percent":50})

    def test_evidence_file_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"summary.json"
            p.write(path,{"status":"test"})
            before=p.sha(path)
            with self.assertRaises(FileExistsError):p.write(path,{"status":"overwrite"})
            self.assertEqual(p.sha(path),before)

if __name__=="__main__":unittest.main()

