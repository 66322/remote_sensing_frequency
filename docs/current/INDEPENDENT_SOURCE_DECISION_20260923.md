> 历史阶段记录：保留下文当时的判断、建议与条件，不是当前执行指令。研究定位以[研究决策说明](RESEARCH_DECISION.md)为准，待办以[下一步](NEXT_EXPERIMENT.md)为准。特别是外部来源等待、旧seed要求与旧GPU范围不得直接沿用到新任务。

# Independent-source decision after D9B — 2026-09-23

This decision uses only dataset documentation. No data, labels or historical
Potsdam Test6 tiles were downloaded or opened. D9B's failed fixed-score gate
remains binding; finding a source does not by itself authorize a safety gate.

| Candidate | Documented modalities and labels | Fit to the current question | Decision |
|---|---|---|---|
| [US3D / 2019 IEEE GRSS DFC](https://www.grss-ieee.org/community/technical-committees/2019-ieee-grss-data-fusion-contest/) | Multi-band satellite imagery, LiDAR-derived height rasters and semantic labels in training regions across Jacksonville and Omaha | Closest documented external candidate for image+height semantic segmentation and geographically separated scenes. Its bands, GSD, height-as-input use and class mapping differ from Potsdam; Car-specific confirmation may be impossible. Contest validation/test reference labels are undisclosed. Access requires registration and the official page gives publication-use conditions. | **First feasibility candidate**, not a frozen split. Confirm that accessible labelled image/height/semantic triplets can be paired and that their permitted use covers the proposed experiment. |
| [2018 IEEE GRSS DFC Houston](https://www.grss-ieee.org/community/technical-committees/2018-ieee-grss-data-fusion-contest/) | 5-cm RGB, 0.5-m LiDAR DSM and 20-class 0.5-m raster labels for a training region | A possible second source, but alignment/resolution and label remapping change the task substantially. Published test reference labels are withheld; one exposed campus training region may not yield a strong geographically independent evaluation. Publication-use approval is specified by the organizer. | **Fallback feasibility candidate** only if US3D is unusable; do not pool its metrics with Potsdam without a separate protocol. |
| Existing Potsdam Train16 / Val2 / historical Test6 | Aligned RGB–DSM and six classes; only Train16 and Val2 labels usable in this project | Train16 trained the frozen experts, Val2 has repeatedly guided decisions, and historical Test6 is frozen. | Not independent confirmation; do not load Test6. |
| Vaihingen full reference release | 33 TOP/DSM patches; [ISPRS says complete reference data have been downloadable since 2018](https://www.isprs.org/resources/datasets/benchmarks/UrbanSemLab/default.aspx) | Server metadata confirmed 17 formerly unused IDs have extracted optical, DSM and complete-label files with matching dimensions. [The official patch map](https://www.isprs.org/resources/datasets/benchmarks/UrbanSemLab/2d-sem-label-vaihingen.aspx) shows all patches from one mosaic, interleaved with or adjacent to legacy-used patches. | Same-domain development source only; **not** independent final D10 confirmation. |

DFC19-specific interpretation: the
[contest description](https://www.grss-ieee.org/community/technical-committees/2019-ieee-grss-data-fusion-contest/)
says JAX and OMA are different cities, the optical data are pan-sharpened
WorldView-3 rather than Potsdam RGB, and LiDAR-derived height and semantic
labels are projected into geographic tiles. Car is not among the categories
explicitly listed on that page; do not claim small-Car validation without
confirming a Car label in the actual DFC19 masks and class documentation. The linked
preprocessed `gt_nDSM` is an above-ground-height raster, not necessarily the
same DSM representation as Potsdam. A D10 experiment using it must explicitly
assume that this height modality is available at inference and report its
different source/resolution. No source-specific split or class mapping is
frozen until the actual archive and labels are checked.

Source-access update, 2026-09-23: the server's attempt to fetch the
SynRS3D-linked Google Drive archive failed immediately with proxy tunnel
`403 Forbidden`, recorded at
`records/rebuild_v1_d10_dfc19_acquire_20260923/user_reported_failure.json`.
This is an access failure, not evidence that DFC19 lacks data. Do not retry
the same URL through the same proxy unchanged. The
[JHU/APL contest repository](https://github.com/pubgeo/dfc2019/tree/master/data)
offers official torrent metadata and points to IEEE DataPort; either route
still needs an access check before transfer. Its
[class table](https://github.com/pubgeo/dfc2019/blob/master/data/README.md#classification-labels)
lists Ground (02), Trees (05), Buildings (06), Water (09),
Bridge/elevated road (17), and Unlabeled (65): **no Car**. Accordingly DFC19
can confirm benefit selection across cities/domains for its available
classes, but cannot validate the small-Car claim.

The [official SynRS3D repository](https://github.com/JTRNEO/SynRS3D)
provides a more concrete acquisition lead for DFC19: its authors describe
preprocessed `opt`, `gt_nDSM` and `gt_ss_mask` directories and links for
Jacksonville/Omaha. This is evidence that a usable triplet format exists,
not proof that our server already holds it or that the redistribution terms
supersede the IEEE GRSS contest conditions. Verify the authoritative terms
before obtaining or publishing with those files. SynRS3D itself is synthetic
and has a different class taxonomy; it is not real-world confirmation.

The generic metadata-only locator previously found no named triplets under
`/home/jovyan/zzx`; its directory-name screen does not exclude different
layouts. The Vaihingen-specific inventory has already been completed.

## Minimal source acceptance decision

Accept a candidate for a new benefit-predictor experiment only when all of
these facts are recorded before model fitting:

1. The user can access enough labelled **image, height and semantic-mask
   triplets** under the dataset's terms, and confirms that none of the chosen
   evaluation scenes guided this project's model or threshold selection.
2. Scene identities and geographic footprints support disjoint fitting,
   calibration and evaluation partitions. Splitting patches from one scene
   is insufficient.
3. Bands, height units/normalization, alignment, ignore labels and a class
   mapping are frozen. A missing Car class limits claims about small Car.
4. The evaluation plan states which condition families can be synthesized
   without relying on forbidden or undisclosed labels.

If US3D fails these checks, assess Houston once. If neither qualifies, stop
the learned DSM-benefit line rather than optimizing another Val2 score. The
original research theme can continue only through a different method and an
honest non-confirmatory evidence claim.
