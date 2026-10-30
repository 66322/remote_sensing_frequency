"""Synthetic CPU contracts for new graph, pairing, migration, counts and scheduler."""
import copy
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch
from torch import nn
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts'), str(ROOT / 'tests')]
torch.set_num_threads(1)
SCRATCH = ROOT / 'test_scratch'
SCRATCH.mkdir(exist_ok=True)
import post_t_paired_v2_common as c
from model.rebuild_v1_d26 import Expert as RealExpert
from model.rebuild_v1_post_ab_n1 import N1Segmenter
from model.post_s1_transfer_model import PrivateDecoder
from model.post_t_paired_v2 import PairedAdaptation, frozen_digest, optimizer_for, intervene, lr_factor
from post_t_paired_v2_data import BatchLedger, batch_digest, Crops
from post_t_paired_v2_runtime import dependencies_ready, blocked, poll_release, PausedForUser
from post_s1_support_evaluation import support_objective, simple_route
from post_t_paired_v2_evaluation import content_screen, evaluate, checkpoint_selection
from control_post_t_paired_v2 import dispatch
from test_post_s1_support import Expert as DSMExpert, inputs
from run_post_s1_transfer import verify_gradients


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(32, 32, 1)
    def forward(self, x):
        return x + .1 * self.conv(x)


class RGBNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Module()
        self.encoder.embedding = nn.Conv2d(3, 32, 1)
        self.encoder.blocks = nn.ModuleList([Block() for _ in range(12)])
        self.rgb = nn.Sequential(nn.Conv2d(32, 32, 1), nn.GroupNorm(8, 32), nn.GELU())
        self.decoder = nn.Sequential(nn.Conv2d(32, 32, 3, padding=1), nn.GroupNorm(8, 32), nn.GELU(), nn.Conv2d(32, 6, 1))
    def forward(self, rgb, dsm):
        x = self.encoder.embedding(torch.nn.functional.avg_pool2d(rgb, 4))
        for block in self.encoder.blocks:
            x = block(x)
        return torch.nn.functional.interpolate(self.decoder(self.rgb(x)), rgb.shape[-2:], mode='nearest')


def experts():
    net = RGBNet()
    return RealExpert(net, net.decoder[-1], 'rgb'), DSMExpert(False)


def fixture(tmp):
    torch.manual_seed(42)
    model = N1Segmenter(*experts(), dict(id='N1-2', information_entry='late', adaptation='last4_and_heads')).eval()
    path = Path(tmp) / 'base.pth'
    torch.save(dict(global_step=8000, model=model.state_dict()), path)
    return path, c.sha(path)


def model(tmp, name):
    path, digest = fixture(tmp)
    return PairedAdaptation(*experts(), c.card(name), path, digest), path, digest


def batch():
    rgb, ds, rm, dm = inputs()
    return dict(rgb=rgb, aux=ds, gt=torch.randint(0, 6, ds.shape), rgb2=rgb, aux2=ds,
                rm2=rm, dm2=dm, treatment=['a', 'b'])


class PairedTests(unittest.TestCase):
    def test_native_record_counts_endpoint_resume_and_protection(self):
        from summarize_post_s1_support import verify_summary
        shape = (512, 512)
        gt = (np.arange(512 * 512).reshape(shape) % 6).astype(np.uint8)
        rm, dm = np.ones(shape, bool), np.ones(shape, bool)
        rm[4:8, 4:8] = False
        base_pred = np.zeros(shape, np.uint8)
        candidate = base_pred.copy()
        candidate[~rm] = gt[~rm]
        item = dict(full_gt=gt, noboundary_gt=gt.copy())
        values = dict(candidate=base_pred, fixed_rgb=base_pred, fixed_dsm=base_pred)
        class Refs:
            def get(self, *args): return values, {}
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            out = Path(tmp)
            args = (None, lambda *a: item, Refs(), {'data': {'validation': ['3_11', '5_10']}}, out, {'test': True}, lambda **kw: None, out, ['rgb_U'])
            with patch('post_t_paired_v2_evaluation.view', return_value=({}, rm, dm, None)), patch('post_t_paired_v2_evaluation.infer', return_value=({'candidate': candidate}, None)) as infer_mock:
                summary = evaluate(*args, 'first')
                verify_summary(out / 'first/summary.json')
                checks = []
                evaluate(*args, 'first', expected=summary, endpoint_checks=checks)
                self.assertEqual(len(checks), 2)
                self.assertEqual(infer_mock.call_count, 2)
                bad = candidate.copy(); bad[0, 0] = 1
                infer_mock.return_value = ({'candidate': bad}, None)
                with self.assertRaisesRegex(RuntimeError, 'outside allowed support'):
                    evaluate(*args, 'bad')
                changed = copy.deepcopy(summary)
                changed['tiles']['rgb_U']['3_11']['scopes']['full']['metrics']['candidate']['valid']['cm'][0][0] += 1
                with self.assertRaisesRegex(RuntimeError, 'raw counts'):
                    evaluate(*args, 'first', expected=changed)

    def test_lossless_jsonl_upload(self):
        from upload_post_t_paired_v2 import encode_record, decode_record
        raw = (json.dumps({'step': 1, 'sha256': 'a' * 64}) + '\r\n').encode() * 200
        encoded = encode_record(raw)
        self.assertLess(len(encoded), len(raw))
        self.assertEqual(decode_record(encoded), raw)

    def test_design_exact_groups_budget_and_two_gpus(self):
        p = c.make_plan(Path('/home/jovyan/zzx/x'), Path('unused'), 'commit', c.source_plan())
        c.validate(p)
        self.assertEqual(sum(j['steps'] for j in p['jobs']), 72000)
        self.assertEqual(p['physical_gpus'], [0, 1])
        self.assertIsNone(p['runtime']['wall_deadline_hours'])
        for key, value in [('physical_gpus', [0, 1, 2]), ('max_gpu_workers', 3), ('new_seeds', True), ('total_optimizer_steps', 96000)]:
            q = copy.deepcopy(p)
            q[key] = value
            with self.assertRaises(ValueError):
                c.validate(q)
        with self.assertRaises(ValueError):
            c.card('X8')

    def test_trainable_scope_classifier_excluded(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            for name in ('F8', 'H8', 'R8'):
                m, _, _ = model(tmp, name)
                names = [n for n, p in m.named_parameters() if p.requires_grad]
                self.assertTrue(all(n.startswith(('branch.', 'private_rgb.')) for n in names))
                self.assertFalse(any(n.startswith('private_rgb.net.decoder.3.') for n in names))
                enc = [n for n in names if n.startswith('private_rgb.net.encoder.')]
                self.assertEqual(bool(enc), name == 'R8')
                if enc:
                    self.assertTrue(all(int(n.split('.')[4]) >= 8 for n in enc))
                self.assertEqual(any(n.startswith('private_rgb.net.rgb.') for n in names), name != 'F8')

    def test_initial_equivalence_all_mechanisms_and_frozen_protection(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            path, digest = fixture(tmp)
            base = PrivateDecoder(*experts(), dict(c.card('F8')), path, digest, dict(path=path, sha256=digest)).eval()
            b = batch()
            with torch.no_grad():
                expected = base(b['rgb'], b['aux'], b['rm2'], b['dm2'])
            for name in ('F8', 'H8', 'R8'):
                m = PairedAdaptation(*experts(), c.card(name), path, digest).eval()
                with torch.no_grad():
                    actual = m(b['rgb'], b['aux'], b['rm2'], b['dm2'])
                self.assertTrue(torch.equal(expected, actual), name)

    def test_real_hook_private_gradient_and_frozen_states(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            for name in ('H8', 'R8'):
                m, _, _ = model(tmp, name)
                before = frozen_digest(m)
                opt = optimizer_for(m, c.source_plan()['training'])
                b = batch()
                m.train()
                loss, _ = support_objective(m, b)
                loss.backward()
                g = verify_gradients(m)
                self.assertTrue(all(g['groups_nonzero'].values()))
                opt.step()
                self.assertEqual(frozen_digest(m), before)
                parts = m(b['rgb'], b['aux'], b['rm2'], b['dm2'], True)
                outside = (~parts['residual_support'])[:, None]
                self.assertTrue(torch.equal(parts['logits'].masked_select(outside), parts['base_logits'].masked_select(outside)))
                self.assertTrue(all(p.grad is None for p in m.private_rgb.net.decoder[-1].parameters()))

    def test_zero_support_still_valid_backward(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            m, _, _ = model(tmp, 'R8')
            b = batch()
            b['rm2'][:] = True
            m.train()
            loss, _ = support_objective(m, b)
            loss.backward()
            self.assertFalse(any(verify_gradients(m)['groups_nonzero'].values()))

    def test_optimizer_groups_and_two_schedules(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            m, _, _ = model(tmp, 'R8')
            opt = optimizer_for(m, c.source_plan()['training'])
            for g in opt.param_groups:
                enc = all(n.startswith('private_rgb.net.encoder.blocks.') for n in g['names'])
                self.assertEqual(g['initial_lr'], 2e-5 if enc else 2e-4)
        self.assertEqual(lr_factor(100, 8000), 1.)
        self.assertEqual(lr_factor(8000, 8000), 0.)
        self.assertGreater(lr_factor(8000, 16000), 0.)

    def test_content_does_not_touch_base_rgb_or_support(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            m, _, _ = model(tmp, 'R8')
            m.eval()
            b = batch()
            got = {}
            for mode in ('C', 'Z', 'S'):
                m.dsm_intervention = mode
                with torch.no_grad():
                    got[mode] = m(b['rgb'], b['aux'], b['rm2'], b['dm2'], True)
            for mode in ('Z', 'S'):
                for key in ('rgb', 'dsm', 'base_logits', 'residual_support'):
                    self.assertTrue(torch.equal(got['C'][key], got[mode][key]))
                self.assertFalse(torch.equal(got['C']['logits'], got[mode]['logits']))
        x = torch.arange(64.).reshape(1, 1, 8, 8)
        self.assertTrue(torch.equal(torch.sort(intervene(x, 'S').flatten()).values, x.flatten()))

    def test_batch_hash_rng_independent_resume_and_mismatch(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            a, b = Path(tmp) / 'a', Path(tmp) / 'b'
            a.mkdir(); b.mkdir()
            sample = batch()
            digest = batch_digest(sample)
            random.seed(999); np.random.seed(888); torch.manual_seed(777)
            self.assertEqual(batch_digest(sample), digest)
            first = BatchLedger(a, [])
            first.record(1, sample); first.close()
            resumed = BatchLedger(a, [], 1)
            resumed.record(2, sample); resumed.close()
            second = BatchLedger(b, [a / 'batch_hashes.jsonl'])
            second.record(1, sample)
            changed = dict(sample, gt=sample['gt'] + 1)
            with self.assertRaises(RuntimeError):
                second.record(2, changed)
            second.close()

    def test_resume_optimizer_and_random_state_matches_uninterrupted(self):
        from run_post_t_paired_v2 import save
        from collections import Counter
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            m, path, digest = model(tmp, 'R8')
            opt = optimizer_for(m, c.source_plan()['training'])
            b = batch()
            m.train()
            for _ in range(2):
                opt.zero_grad(set_to_none=True)
                loss, _ = support_objective(m, b)
                loss.backward(); opt.step()
            saved = Path(tmp) / 'resume.pth'
            save(saved, m, opt, 2, {'fixture': True}, None, Counter(), {}, [n for n, p in m.named_parameters() if p.requires_grad])
            opt.zero_grad(set_to_none=True)
            loss, _ = support_objective(m, b)
            loss.backward(); opt.step()
            expected = copy.deepcopy(m.state_dict())
            other = PairedAdaptation(*experts(), c.card('R8'), path, digest)
            other_opt = optimizer_for(other, c.source_plan()['training'])
            st = torch.load(saved, weights_only=False)
            other.load_state_dict(st['model']); other_opt.load_state_dict(st['optimizer']); other.train()
            other_opt.zero_grad(set_to_none=True)
            loss, _ = support_objective(other, b)
            loss.backward(); other_opt.step()
            self.assertTrue(all(torch.equal(v, other.state_dict()[n]) for n, v in expected.items()))

    def test_release_keeps_other_gpu_enabled(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            b = Path(tmp)
            c.write(b / 'control/gpu_0.json', dict(blocked=True))
            self.assertTrue(blocked(b, 0)); self.assertFalse(blocked(b, 1))
            with self.assertRaises(PausedForUser):
                poll_release(b, 0)
            poll_release(b, 1)

    def test_stage_barriers_not_scientific_selection(self):
        s = c.initial_state({})
        self.assertFalse(dependencies_ready('H8', s))
        s['jobs']['CONTENT_PRE']['status'] = 'COMPLETE'
        self.assertTrue(dependencies_ready('R8', s))
        self.assertFalse(dependencies_ready('R16', s))
        for n in ('H8', 'F8', 'R8'):
            s['jobs'][n]['status'] = 'COMPLETE'
        self.assertTrue(dependencies_ready('F16', s))

    def run_scheduler(self, migration=False, failure=False):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            b = Path(tmp)
            (b / 'logs').mkdir()
            p = c.make_plan(Path('/home/jovyan/zzx/x'), b, 'commit', c.source_plan())
            s = c.initial_state(p)
            calls = []
            t = [0.]
            class Process:
                pid = 77
                def __init__(self, n, gpu, resume):
                    self.n, self.gpu, self.resume = n, gpu, resume
                    folder = b / 'jobs' / n
                    folder.mkdir(parents=True, exist_ok=resume)
                    if migration and n == 'H8' and not resume:
                        c.write(folder / 'paused.json', {})
                    elif not (failure and n == 'H8'):
                        c.write(folder / 'complete.json', {})
                def poll(self):
                    if migration and self.n == 'H8' and not self.resume:
                        c.write(b / 'control/gpu_0.json', dict(blocked=True))
                        return 75
                    return 2 if failure and self.n == 'H8' else 0
            def spawn(cmd, **kwargs):
                n = cmd[cmd.index('--job') + 1]
                gpu = int(cmd[cmd.index('--gpu') + 1])
                calls.append((n, gpu, '--resume' in cmd))
                return Process(n, gpu, '--resume' in cmd)
            def sleep(n):
                t[0] += 1
            with patch('summarize_post_t_paired_v2.audit_streams', return_value={}):
                ok = dispatch(b, b, p, s, {}, popen=spawn, sleep=sleep, clock=lambda: t[0],
                              check=lambda gpu, previous: 'GPU-' + str(gpu), accept=lambda *a: None)
            return ok, calls, s

    def test_dual_gpu_fifo_all8_tasks(self):
        ok, calls, state = self.run_scheduler()
        self.assertTrue(ok)
        self.assertEqual([n for n, _, _ in calls], c.ORDER)
        self.assertEqual(set(g for _, g, _ in calls), {0, 1})

    def test_released_job_migrates_without_new_recipe(self):
        ok, calls, state = self.run_scheduler(migration=True)
        self.assertTrue(ok)
        self.assertIn(('H8', 0, False), calls)
        self.assertIn(('H8', 1, True), calls)
        self.assertEqual(sum(n == 'H8' for n, _, _ in calls), 2)
        resume_index = calls.index(('H8', 1, True))
        self.assertTrue(all(g == 1 for _, g, _ in calls[resume_index:]))

    def test_failure_stops_dispatch_no_recipe_retry(self):
        ok, calls, state = self.run_scheduler(failure=True)
        self.assertFalse(ok)
        self.assertEqual(sum(n == 'H8' for n, _, _ in calls), 1)
        self.assertFalse(any(n == 'R8' for n, _, _ in calls))

    def test_source_complete_and_release_both_required(self):
        import post_t_mechanism_common as old
        s = dict(status='MECHANISM_COMPLETE_AWAITING_REVIEW', CPU='COMPLETE', jobs={n: dict(status='COMPLETE') for n in old.ORDER})
        self.assertEqual(c.predecessor_verdict(s, False, False, True), 'READY')
        self.assertEqual(c.predecessor_verdict(s, False, True, True), 'WAITING_PREDECESSOR_RELEASE')
        s['jobs'][old.ORDER[-1]]['status'] = 'PENDING'
        self.assertEqual(c.predecessor_verdict(s, False, False, True), 'HOLD_INVALID_COMPLETE')


if __name__ == '__main__':
    unittest.main()
