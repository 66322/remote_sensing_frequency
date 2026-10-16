"""Check that the tile-risk audit rejects altered count evidence."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from analyze_rebuild_v1_mixed_tile_risk import audit_evaluation, matrix


def row():
    cm = [[0] * 6 for _ in range(6)]
    for index in range(5):
        cm[index][index] = 2
    cm[0][1] = 1
    true = [sum(values) for values in cm]
    predicted = [sum(cm[i][j] for i in range(6)) for j in range(6)]
    correct = [cm[i][i] for i in range(6)]
    iou = [correct[i] / (true[i] + predicted[i] - correct[i])
           if true[i] + predicted[i] - correct[i] else None for i in range(6)]
    return {'cm': cm, 'metrics': {'valid_pixels': 11, 'class_true_count': true,
            'class_predicted_count': predicted, 'class_correct_count': correct,
            'per_class_iou': iou, 'mIoU_fg5': sum(iou[:5]) / 5}}


class TileRiskAuditTests(unittest.TestCase):
    def test_valid_matrix_and_tampered_class_iou(self):
        item = row()
        self.assertEqual(matrix(item)['correct'][0], 2)
        altered = copy.deepcopy(item)
        altered['metrics']['per_class_iou'][0] = 1.0
        with self.assertRaisesRegex(RuntimeError, 'per-class IoU'):
            matrix(altered)

    def test_tampered_tile_matrix_rejected_before_pooling(self):
        item = row()
        entry = {'evaluation_ids': ['20'], 'conditions': {condition: {
            'tiles': {'20': {'scopes': {'full': copy.deepcopy(item)}}},
            'pooled': {'full': copy.deepcopy(item)}}
            for condition in ('scale2_clean', 'scale4_clean',
                              'scale2_unseen_blur', 'scale4_unseen_blur')}}
        audit_evaluation(entry)
        entry['conditions']['scale2_clean']['tiles']['20']['scopes']['full']['cm'][0][1] = 0
        with self.assertRaisesRegex(RuntimeError, 'matrix count'):
            audit_evaluation(entry)


if __name__ == '__main__':
    unittest.main()
