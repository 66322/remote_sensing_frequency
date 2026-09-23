# Current handoff — 2026-09-23 (after D9B)

D9B completed its unfitted decision-benefit screen with zero user-reported
queue failures. The fixed semantic+frequency+expert score beat the better
confidence/entropy direct control in only 1/16 flip-benefit AUROC and 0/16
AUPRC comparisons; the gate failed. Do not train the candidate safety gate
from these features or repeat this Val2 screen. The original server per-stratum
files remain under project `records/`; the compact pooled table and decision
are in `docs/experiments/D9B_RESULTS_20260923.md`. Next: freeze an independent
labelled RGB–DSM source before any fitted model. Test6 stays frozen.

## Current decision

D8 `fix1` completed and failed its sampling gate, so `proceed_seed17=[]`.
D9A completed all 17 queue stages with zero failures. Its tested confidence×JS
disagreement score is below direct confidence difference on benefit AUROC and
AUPRC in all 16 seed-by-condition comparisons. Entropy difference is above
confidence difference on both ranking metrics in all 16 comparisons. Car and
damaged-region ranking advantages also repeat, with small-Car support limited.
The original D9A local-down8 D5 route incorrectly masked degraded DSM as
absent; its two-seed `fix1` correction completed with zero failures and left
the ranking CSVs byte-identical. D5's older per-seed result directories are
missing although its logs report completion, so a matched frozen-expert
safe-entropy versus safe-confidence decision audit was run. Safe entropy won
routed NB mIoU in only 4/16 rows, lost in 10 and tied under DSM zero twice
(mean -0.0089 pp). Its better benefit ranking therefore did not translate
into a safer or stronger simple router. The source-hash-checked class/region
review is complete: entropy routing raises Car
IoU in 12/16 rows but Building in only 1/16, and local-down8 damaged-region
effects reverse across seeds. D9A is closed. The next substantive protocol is
`docs/protocols/D9B_DECISION_BENEFIT_SCREEN.md`; see
`docs/experiments/D9A_ENTROPY_ROUTE_RESULTS_20260923.md` for the final D9A result.

No documented untouched scene source is currently available for fitted D9B:
Potsdam Train16/Val2/Test6 are trained, inspected and historically exposed,
while earlier Vaihingen work used train12/test4. See
`docs/current/D9B_SOURCE_STATUS_20260923.md`. Historical TEST6 remains frozen.

## Read this first on another computer

- Branch: `rebuild-v1-protocol-20260915`
- Repository: https://github.com/66322/remote_sensing_frequency/tree/rebuild-v1-protocol-20260915
- B1–B3 evidence: `records/rebuild_v1_b2_b3_compact_20260921/`
- B4 evidence: `records/rebuild_v1_b4_seed17_compact_20260922/`
- B4 report: `docs/experiments/B4_SEED17_REPLICATION_20260921.md`
- Current state: B4, D8 and D9B screens failed their gates; D9A and local-down8 fix1 complete, full D9 gate unevaluated.
- The D9A entropy-route queue completed with zero failures. Its source-hashed
  server summary, compact transcription and class/region review are archived.

GitHub contains compact metrics, decisions, timestamps and checkpoint references.
Large checkpoints, complete logs, full per-condition CSV files and confusion matrices
remain under `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro` on the experiment
server. Missing GitHub copies are not a reason to rerun completed work.

## Completed B1–B3 state

Seed42 KD minus C is +0.2247 pp clean, +0.5275 pp down8 and +0.6918 pp
DSM-zero. Compared with R05_KD, KD is -0.2217 pp clean but +0.2220 pp down8
and +0.1568 pp zero. Its paired local drops are smaller than R05_KD in all eight
reported seed42 tile/family/region summaries. SAFE and AVG_KD do not provide a
consistent additional benefit.

These are stage results on the repeatedly used two-tile Val2 development split.

## Completed B4 state

B4 ran from 2026-09-21 17:22:07 to 2026-09-22 01:29:52 +08:00. All three
smokes, 4000-step trainings, global robustness evaluations and paired local
evaluations completed. TEST6 was not loaded.

| Arm | clean | DSM down8 | DSM zero |
|---|---:|---:|---:|
| C17 | 86.6027 | 84.9647 | 83.3285 |
| R05_KD17 | 86.1756 | 84.9972 | 83.1646 |
| KD17 | 86.6258 | 85.2065 | 83.2083 |

KD17 minus R05_KD17 is +0.4502 pp clean, +0.2093 pp down8 and +0.0438 pp
zero. The global degradation ordering repeats, although the zero advantage is tiny.

For paired local damaged regions, KD17 is 0.2855 pp worse than R05_KD17 under
local missing and 0.0372 pp worse under local down8. Both local directions reverse
seed42. KD17 is also 0.1202 pp below C17 on global DSM-zero.

## Decision

The frozen B4 gate fails. The defensible finding is a small global degradation
trend that repeats across two seeds, combined with a local mechanism result that
does not replicate. Do not present the current SafeMaxConfidence distillation as a
validated local reliability method, automatic missing detector, Optical fallback or
generally superior robust model.

B1–B4 are closed as mechanism/ablation evidence for the current implementation.
Any next main-method experiment must change the reliability design and use a new
frozen evaluation source. Repeating the same models on Val2 or extending their
training budget is not justified by B4.

## Provenance caveat

The B4 trainers reported Git HEAD `abb3d97`, while later B4 files had been installed
selectively on the server. The preflight source hashes retained in the original
server package are authoritative for executed code identity. The compact GitHub
package was reconstructed from validated archiver output supplied by the user;
checkpoint paths and SHA256 values are in `run_provenance.json`.

## Reusable prompt

“Read `docs/START_HERE.md`, `docs/current/HANDOFF.md`,
`docs/experiments/D8_RESULTS_20260922.md`,
`docs/experiments/D9A_RESULTS_20260923.md`,
`docs/experiments/D9A_ENTROPY_ROUTE_RESULTS_20260923.md` and
`docs/protocols/D9_DSM_BENEFIT_DIAGNOSTIC.md` on branch
`rebuild-v1-protocol-20260915`. B1–B4 and D8 are closed; D9A and its
local-down8 correction are complete. Audit the entropy-route class/region
strata, then inventory new labelled scenes before fitting benefit predictors.
The documented Potsdam and Vaihingen scenes are exposed. Keep TEST6 frozen,
use physical GPU0 only, and store
runtime artifacts under `/home/jovyan/zzx`.”
