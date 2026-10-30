import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from mixed_followup_gate import require_original_complete


class FollowupGateTests(unittest.TestCase):
    def setUp(self):
        self.summary = dict(status='COMPLETE', completed=42, planned=42,
                            failures=[], test6_loaded=False)
        self.analysis = dict(completed=42, selected=42, integer_count_audit='PASS',
                             test6_loaded=False, comparisons=[
                                 dict(dataset=dataset, comparison=name)
                                 for dataset in ('potsdam', 'vaihingen')
                                 for name in ('D_recovery_x_DSM_interaction',
                                              'D_DSM_minus_gray_capacity')])

    def test_complete_queue_and_integer_audit_pass(self):
        require_original_complete(self.summary, self.analysis)

    def test_queue_status_alone_does_not_open_gate(self):
        with self.assertRaisesRegex(RuntimeError, 'integer audit'):
            require_original_complete(self.summary, None)
        self.analysis['completed'] = 36
        with self.assertRaisesRegex(RuntimeError, 'integer audit'):
            require_original_complete(self.summary, self.analysis)

    def test_failed_queue_or_missing_d_comparison_is_rejected(self):
        self.summary['failures'] = [dict(job='D', error='failed')]
        with self.assertRaisesRegex(RuntimeError, 'incomplete'):
            require_original_complete(self.summary, self.analysis)
        self.summary['failures'] = []
        self.analysis['comparisons'].pop()
        with self.assertRaisesRegex(RuntimeError, 'D interaction'):
            require_original_complete(self.summary, self.analysis)


if __name__ == '__main__':
    unittest.main()
