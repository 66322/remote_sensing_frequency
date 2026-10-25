import json
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import stop_phase3_m2_owned_workers as stop


class StopCurrentM2Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        records = Path(self.temp.name) / 'records'
        m2 = records / stop.M2.name
        combined = records / stop.COMBINED.name
        m2.mkdir(parents=True)
        combined.mkdir()
        self.m2 = m2
        for name, value in (('RECORDS', records), ('M2', m2), ('COMBINED', combined),
                            ('LATCH', records / stop.LATCH.name)):
            patcher = patch.object(stop, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        stop.LATCH.write_text(json.dumps(dict(status='CONTROLLERS_LAUNCHED',
            m2_directory=str(m2), combined_directory=str(combined),
            m2_controller_pid=100, combined_controller_pid=200)), encoding='utf-8')
        (m2 / 'queue_status.json').write_text(json.dumps(dict(status='RUNNING')), encoding='utf-8')
        (m2 / 'gpu_inventory_launch.json').write_text(json.dumps(dict(selected={
            '0': ['0', 'uuid0'], '1': ['1', 'uuid1']})), encoding='utf-8')

    def test_inspect_requires_two_exclusive_owned_gpu_workers(self):
        with patch.object(stop, 'bound_entry'), patch.object(stop, 'proc_parent', return_value=100), \
                patch.object(stop, 'gpu_apps', return_value=[(301, 'uuid0'), (302, 'uuid1')]):
            result = stop.inspect()
        self.assertEqual(result['workers'], {0: 301, 1: 302})

        with patch.object(stop, 'bound_entry'), patch.object(stop, 'proc_parent', return_value=999), \
                patch.object(stop, 'gpu_apps', return_value=[(301, 'uuid0'), (302, 'uuid1')]):
            with self.assertRaisesRegex(RuntimeError, 'not owned'):
                stop.inspect()

        with patch.object(stop, 'bound_entry'), patch.object(stop, 'proc_parent', return_value=100), \
                patch.object(stop, 'gpu_apps', return_value=[(301, 'uuid0'), (399, 'uuid0'), (302, 'uuid1')]):
            with self.assertRaisesRegex(RuntimeError, 'single-owner'):
                stop.inspect()

    def test_abort_signals_only_verified_gpu0_worker(self):
        snapshot = dict(m2_controller_pid=100, combined_controller_pid=200,
                        workers={0: 301, 1: 302})
        with patch.object(stop, 'proc_parent', return_value=100), \
                patch.object(stop, 'bound_entry'), patch.object(stop, 'gpu_apps', return_value=[]), \
                patch.object(stop.os, 'kill') as kill:
            stop.abort_current_run(snapshot)
        kill.assert_called_once_with(301, signal.SIGTERM)
        markers = list(self.m2.glob('manual_abort_intent_*.json'))
        self.assertEqual(len(markers), 1)
        self.assertFalse(json.loads(markers[0].read_text(encoding='utf-8'))['resumable'])

    def test_abort_refuses_changed_parent_before_marker_or_signal(self):
        snapshot = dict(m2_controller_pid=100, combined_controller_pid=200,
                        workers={0: 301, 1: 302})
        with patch.object(stop, 'proc_parent', return_value=999), \
                patch.object(stop.os, 'kill') as kill:
            with self.assertRaisesRegex(RuntimeError, 'parent changed'):
                stop.abort_current_run(snapshot)
        kill.assert_not_called()
        self.assertFalse(list(self.m2.glob('manual_abort_intent_*.json')))

    def test_entry_identity_requires_exact_mode_and_directory(self):
        good = ['python', 'entry.py', '--mode', 'm2', '--directory', str(self.m2)]
        with patch.object(stop, 'proc_args', return_value=good):
            stop.bound_entry(100, 'm2', self.m2)
            with self.assertRaisesRegex(RuntimeError, 'unexpected process'):
                stop.bound_entry(100, 'combined', self.m2)


if __name__ == '__main__':
    unittest.main()
