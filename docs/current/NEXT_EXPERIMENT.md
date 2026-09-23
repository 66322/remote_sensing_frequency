# Next experiment - 2026-09-23: stop the data-audit detour

**Run D10M now: frozen-expert spatial/frequency mechanism experiment.**
Implementation and numerical tests are present; server execution is pending.
The queue is `scripts/run_rebuild_v1_d10m_mechanism_queue.sh`; it automatically
runs a smoke, 20 seed-condition jobs and the final summary. No download,
directory inventory or new expert training is a prerequisite.

Read `docs/protocols/D10M_SPATIAL_FREQUENCY_MECHANISM.md` for the frozen design.

## Correction to the previous schedule

D9A/D9B conclusions have already been extracted. Continued source checks
were for future independent evaluation, not unfinished extraction. Requiring
a geographically new dataset before every exploratory experiment delayed
the untested method hypotheses. DFC19 Google Drive acquisition failed due
to proxy tunnel 403, not a model/data-quality result. Stop retrying it.

The earlier D10P Vaihingen expert-training proposal is deferred, not started.
It would introduce a new domain and require matched expert training before
answering the original mechanism question. D10M uses existing R01/R05.
The strict independent D10 confirmation protocol stays unchanged; its data
requirements no longer block this explicitly exploratory mechanism study.

## What this batch answers

1. Does DSM usefulness change when global Fourier amplitude stays fixed but
   RGB-DSM spatial correspondence changes? Circular/edge-filled shifts at
   4/16/32 px, with a common interior evaluation region, test this distinction.
2. At the same error-harm budget, do local spatial/frequency descriptors
   preserve more rescued predictions than confidence/entropy? Curves are
   diagnostic post-hoc envelopes, not calibrated deployable thresholds.
3. Do these patterns repeat for both existing expert seeds and both Val2
   tiles? The two tiles do not support independent generalization claims.

The queue saves sample probabilities, descriptors and labels for reuse.
It reports full/interior mIoU, correctness harm/rescue, per-class and small-Car
ranking/curves, with exact missing-DSM fallback for safe methods. No labels
are features. Global spectrum preservation does not imply local energy is
unchanged. No raw-score ECE is reported.

## After one completed batch

Read the automatic summary and make a method decision, without another
data audit. If structure cues provide no stable advantage, retain negative
evidence and do not tune another fixed sum. If promising, freeze a bounded
learned-benefit ablation with separate local exploratory fit/calibration/eval
scene groups. Confidence/disagreement and semantic+disagreement controls
are mandatory. D10M alone cannot authorize residual gate training.

Still unfinished: learned semantic representations, learned feature
combinations, calibrated benefit probabilities, held-out corruption families,
RGB failure, and independent confirmation. A meaningful method contribution
requires these experiments; the residual interpolation formula alone is not it.

Physical GPU 0 only; runtime outputs under /home/jovyan/zzx; failed jobs do
not stop subsequent jobs; Test6 frozen; B1-B4 and failed D9B weighted scores
remain closed. No D10M result is claimed before actual server output arrives.
