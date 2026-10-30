"""Exercise the delivered shell orchestration with small stand-ins; no GPU probes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
BASH = Path(r'D:\soft\git\Git\bin\bash.exe')
COMMIT = 'c22a046407daf42064cbb161429f2648c9b86d66'
STUB = '''import json, os, sys
from pathlib import Path
a0 = Path(os.environ['A0'])
command = ' '.join(sys.argv[1:])
with (a0/'calls.txt').open('a') as f: f.write(command+'\\n')
if os.environ.get('FAIL_PHASE') == command: sys.exit(7)
if command == 'screen':
    (a0/'calibration_screen.json').write_text(json.dumps({'status': os.environ['SCREEN_STATUS']}))
'''
SHIM = '''import os, subprocess, sys
if sys.argv[1:] == ['-B', '-']:
    def gpu_output(command, **kwargs):
        if any('query-compute-apps' in arg for arg in command):
            return 'GPU-0, 123\\n' if os.environ['STUB_BUSY'] == '1' else ''
        return '0, NVIDIA H100, 81081, GPU-0\\n1, NVIDIA H100, 81081, GPU-1\\n'
    subprocess.check_output = gpu_output
    exec(compile(sys.stdin.read(), '<delivered-preflight-with-nvidia-boundary-mocked>', 'exec'))
else:
    sys.exit(subprocess.run([sys.executable]+sys.argv[1:]).returncode)
'''

@unittest.skipUnless(BASH.is_file(), 'Local Bash required')
class ContinuationTests(unittest.TestCase):
    def run_case(self, screen='READY_FOR_OUTER_DEVELOPMENT_EVALUATION', fail='', busy=False, duplicate=False, mismatch=False):
        with tempfile.TemporaryDirectory(prefix='a0_chain_') as d:
            root = Path(d)/'root'
            a0 = root/'records/post_m2_a0_capability_20261029'
            a0.mkdir(parents=True)
            (a0/'post_m2_a0.py').write_text(STUB)
            for kind in ('dino2','dino3'):
                (a0/('profile_'+kind+'.json')).write_text(json.dumps(dict(kind=kind,
                    status='PROFILE_COMPLETED_NO_SCIENTIFIC_RESULT', code_commit='0'*40 if mismatch else COMMIT)))
            if duplicate: (a0/'formal_continuation_20261030.started').mkdir()
            weight = root/'pretrained/dinov3/dinov3_vits16_pretrain_lvd1689m-08c60483.pth'
            weight.parent.mkdir(parents=True); weight.write_bytes(b'stub')
            script = (BASE/'scripts/continue_post_m2_a0_20261030.sh').read_text()
            script = script.replace('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro', root.as_posix())
            runner = Path(d)/'runner.sh'; runner.write_bytes(script.encode())
            bindir = Path(d)/'bin'; bindir.mkdir()
            shim = Path(d)/'shim.py'; shim.write_text(SHIM)
            (bindir/'python').write_bytes(('#!/usr/bin/env bash\nexec "'+Path(sys.executable).as_posix()+'" "'+shim.as_posix()+'" "$@"\n').encode())
            env = dict(os.environ, SCREEN_STATUS=screen, FAIL_PHASE=fail, STUB_BUSY=str(int(busy)))
            env['PATH'] = str(bindir)+os.pathsep+env['PATH']
            result = subprocess.run([str(BASH),'--noprofile','--norc',runner.as_posix()],
                env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            calls = (a0/'calls.txt').read_text().splitlines() if (a0/'calls.txt').exists() else []
            return result.returncode, calls, result.stdout, (a0/'formal_continuation_20261030.started').exists()

    def test_positive_runs_outer(self):
        rc, calls, output, registered = self.run_case()
        self.assertEqual(rc,0,output)
        self.assertEqual(calls,['pair --phase train','pair --phase evaluate --split calibration','screen','pair --phase evaluate --split outer','status'])
        self.assertTrue(registered)

    def test_negative_and_invalid_skip_outer(self):
        for status in ('NO_INCREMENT_STOP_A_ROUTE','INVALID_PROBE'):
            with self.subTest(status=status):
                rc,calls,output,_ = self.run_case(screen=status)
                self.assertEqual(rc,0,output)
                self.assertEqual(calls,['pair --phase train','pair --phase evaluate --split calibration','screen','status'])

    def test_first_failure_stops_chain(self):
        for phase in ('pair --phase train','pair --phase evaluate --split calibration'):
            with self.subTest(phase=phase):
                rc,calls,output,_ = self.run_case(fail=phase)
                self.assertNotEqual(rc,0,output)
                self.assertEqual(calls[-1],phase)
                self.assertNotIn('screen',calls)

    def test_busy_gpu_does_not_register(self):
        rc,calls,output,registered = self.run_case(busy=True)
        self.assertNotEqual(rc,0,output); self.assertEqual(calls,[])
        self.assertFalse(registered)

    def test_duplicate_does_not_dispatch(self):
        rc,calls,output,_ = self.run_case(duplicate=True)
        self.assertNotEqual(rc,0,output); self.assertEqual(calls,[])

    def test_profile_mismatch_does_not_dispatch(self):
        rc,calls,output,registered = self.run_case(mismatch=True)
        self.assertNotEqual(rc,0,output); self.assertEqual(calls,[])
        self.assertFalse(registered)

if __name__ == '__main__': unittest.main(verbosity=2)
