"""Compatibility and pre-training-only repair admission; no model/data/GPU work."""
import ctypes
import errno
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import phase3_memfd_compat as compat
import phase3_memfd_repair_common as repair


class Function:
    def __init__(self, value, error=0):
        self.value, self.error, self.calls = value, error, []

    def __call__(self, *args):
        self.calls.append(args)
        ctypes.set_errno(self.error)
        return self.value


def fixture(root):
    base, combined = root/"m2", root/"combined"
    for directory in (base, combined):
        (directory/"jobs").mkdir(parents=True)
        (directory/"code").mkdir()
    source = base/"code/fixture.py"
    source.write_bytes(b"fixture\n")
    repair.write(base/"plan.json", {"execution_commit":repair.M2_COMMIT, "core_jobs":108,
        "updates":32000,"batch":16,"auto_retry":False,"physical_gpus":[0,1]})
    repair.write(base/"folds.json", {"fixture":True})
    repair.write(base/"code_manifest.json", {"files":{"fixture.py":repair.sha(source)}})
    repair.write(base/"registration.json", {"binding":repair.bindings(base)})
    repair.write(base/"registration_failure.json", {"automatic_retry":False,
        "error":"test_phase3_m2.py returned non-zero exit status 1"})
    (base/"target_checks.log").write_text("ERROR: test_linux_process_memfd\n"
        "Linux anonymous memfd required; no disk-array fallback\nFAILED (errors=1)\n")
    manifest = combined/"code/configs/phase3_combined_execution_manifest.json"
    repair.write(manifest, {"files":{}})
    repair.write(combined/"registration.json", {"execution_commit":repair.COMBINED_COMMIT,
        "manifest_sha256":repair.sha(manifest),"package_files":{}})
    repair.write(combined/"plan.json", {"m2_execution_commit":repair.M2_COMMIT})
    repair.write(combined/"queue_status.json", {"status":"STOPPED_NO_AUTOMATIC_RETRY",
        "error":"M2 bootstrap failed; see m2_bootstrap.log"})
    return base, combined


class MemfdCompatibility(unittest.TestCase):
    def test_existing_native_binding_is_not_replaced(self):
        native = lambda *args: 7
        module = SimpleNamespace(memfd_create=native)
        self.assertEqual(compat.install(module, platform_name="linux"), "os.memfd_create")
        self.assertIs(module.memfd_create, native)

    def test_missing_python_binding_uses_libc_and_cloexec(self):
        function, module = Function(17), SimpleNamespace()
        backend = compat.install(module, libc=SimpleNamespace(memfd_create=function), platform_name="linux")
        self.assertEqual(backend, "libc.memfd_create")
        self.assertEqual(module.memfd_create("packet"), 17)
        self.assertEqual(function.calls, [(b"packet", 1)])
        self.assertEqual(module.MFD_CLOEXEC, 1)
        self.assertEqual(compat.install(module, platform_name="linux"), backend)

    def test_old_libc_uses_only_verified_x86_64_syscall(self):
        function, module = Function(23), SimpleNamespace()
        self.assertEqual(compat.install(module, libc=SimpleNamespace(syscall=function),
            machine="x86_64", platform_name="linux"), "linux-x86_64-syscall-319")
        self.assertEqual(module.memfd_create(b"packet", flags=1), 23)
        self.assertEqual(function.calls[0][0].value, 319)
        self.assertEqual(function.calls[0][1].value, b"packet")
        self.assertEqual(function.calls[0][2].value, 1)
        with self.assertRaisesRegex(RuntimeError, "no verified syscall"):
            compat.install(SimpleNamespace(), libc=SimpleNamespace(syscall=function),
                           machine="unverified", platform_name="linux")

    def test_kernel_denial_and_invalid_arguments_fail_without_file_fallback(self):
        function, module = Function(-1, errno.EPERM), SimpleNamespace()
        compat.install(module, libc=SimpleNamespace(memfd_create=function), platform_name="linux")
        with self.assertRaises(OSError) as raised:
            module.memfd_create("packet")
        self.assertEqual(raised.exception.errno, errno.EPERM)
        calls = len(function.calls)
        with self.assertRaises(ValueError):
            module.memfd_create("packet\x00bad")
        with self.assertRaises(OverflowError):
            module.memfd_create("packet", flags=2**32)
        self.assertEqual(len(function.calls), calls)
        with self.assertRaisesRegex(RuntimeError, "Linux anonymous"):
            compat.install(SimpleNamespace(), platform_name="win32")


class RegistrationOnlyAdmission(unittest.TestCase):
    def test_all_original_checks_and_real_linux_transport_cannot_be_skipped(self):
        passed = "test_linux_process_memfd (test_phase3_m2.ContractTests) ... ok\nRan 16 tests\nOK\n"
        self.assertTrue(repair.validate_target_checks(passed))
        for value in (passed.replace("16", "15"), passed.replace(" ... ok", " ... skipped"),
                      passed.replace("test_linux_process_memfd", "some_other_test")):
            with self.assertRaises(RuntimeError):
                repair.validate_target_checks(value)

    def test_diagnosed_empty_registration_is_admissible_without_changing_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            base, combined = fixture(Path(temporary))
            before = repair.bindings(base)
            self.assertEqual(repair.verify_sources(base, combined), before)
            self.assertEqual(repair.admit_registration_failure(base, combined)["training_jobs"], 0)
            self.assertEqual(repair.bindings(base), before)

    def test_any_job_or_prior_launch_prevents_training_retry(self):
        for name in ("job", "launch", "queue_status.json", "target_checks.json", "nohup.log", "runtime_repair.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                base, combined = fixture(Path(temporary))
                if name == "job":
                    (base/"jobs/started_job").mkdir()
                elif name == "launch":
                    repair.write(base/"launch.json", {"controller_pid":123})
                else:
                    (base/name).write_text("{}")
                with self.assertRaises(RuntimeError):
                    repair.admit_registration_failure(base, combined)

    def test_foreign_failure_or_combined_progress_refused(self):
        for change in ("failure", "source", "combined_job"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                base, combined = fixture(Path(temporary))
                if change == "failure":
                    (base/"target_checks.log").write_text("some other failure")
                elif change == "source":
                    repair.write(combined/"m2_source.json", {"directory":str(base)})
                else:
                    (combined/"jobs/J_started").mkdir()
                with self.assertRaises(RuntimeError):
                    repair.admit_registration_failure(base, combined)

    def test_original_sources_and_registration_binding_cannot_be_rewritten(self):
        for change in ("source", "plan", "combined_manifest"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                base, combined = fixture(Path(temporary))
                target = {"source":base/"code/fixture.py", "plan":base/"plan.json",
                    "combined_manifest":combined/"code/configs/phase3_combined_execution_manifest.json"}[change]
                target.write_text("changed")
                with self.assertRaises(RuntimeError):
                    repair.verify_sources(base, combined)


if __name__ == "__main__":
    unittest.main()
