# Cross-direction research notes — 2026-09-20

Purpose: exploratory planning for Potsdam RGB–DSM segmentation after B1 and D5 fair-routing validation. This note is not evidence of an implemented method or a launched server job. Existing results are development results on Val2, not independent test confirmation.

## Primary sources consulted

1. Hernández-Sequeira et al. Adapting Semi-Supervised Segmentation methods to Multimodal Remote Sensing Data. ISPRS Archives, 2025. DOI: 10.5194/isprs-archives-XLVIII-M-7-2025-21-2025. https://isprs-archives.copernicus.org/articles/XLVIII-M-7-2025/21/2025/index.html
   Adapts semi-supervised segmentation to multimodal remote-sensing inputs. Combining extra modalities and semi-supervision is already studied; that combination alone is not a novelty claim.

2. Difference-Complementary Learning and Label Reassignment for Multimodal Semi-Supervised Semantic Segmentation of Remote Sensing Images (DLLR). IEEE TIP, 2025. DOI: 10.1109/TIP.2025.3526064. https://ieeexplore.ieee.org/document/10838294/
   Optical–SAR multimodal semi-supervision uses complementary learning and pseudo-label reassignment. Relevant prior art for cross-modal pseudo-label mechanisms, although the modalities differ from RGB–DSM.

3. Geometry-Guided Semi-Supervised Multimodal Segmentation for UAV-Based Rice-Lodging Mapping. Remote Sensing 18(17), 2961, 2026. DOI: 10.3390/rs18172961. https://www.mdpi.com/2072-4292/18/17/2961
   Publisher search excerpts describe RGB–DSM semi-supervision, geometric guidance and reliability-related pseudo-label weighting. Full-page retrieval returned HTTP 429; this is an abstract/excerpt-level overlap warning, not a completed full-paper novelty audit.

4. RS-MTDF: Multi-Teacher Distillation and Fusion for Remote Sensing Semi-Supervised Semantic Segmentation. arXiv:2506.08772, 2025 preprint. https://arxiv.org/abs/2506.08772
   Studies foundation-model multi-teacher distillation for remote-sensing semi-supervision. Multiple teachers plus semi-supervision is not in itself a new contribution.

5. GSNet: Towards Open-Vocabulary Remote Sensing Image Semantic Segmentation. AAAI, 2025. DOI: 10.1609/aaai.v39i9.33022. https://ojs.aaai.org/index.php/AAAI/article/view/33022
   Combines generalist and remote-sensing-specialist representations with language-guided fusion. Establishes that remote-sensing open-vocabulary segmentation is already a substantive research area.

6. SegEarth-OV: Towards Training-Free Open-Vocabulary Segmentation for Remote Sensing Images. CVPR, 2025. https://openaccess.thecvf.com/content/CVPR2025/papers/Li_SegEarth-OV_Towards_Training-Free_Open-Vocabulary_Segmentation_for_Remote_Sensing_Images_CVPR_2025_paper.pdf
   https://arxiv.org/abs/2410.01768
   Candidate optical open-vocabulary inference baseline. Training-free downstream inference does not mean every component has never been trained. Dependency setup, input normalization and pretrained-data overlap must be checked before running.

## Planning implications (suggestions, not verified contributions)

- Closest extension: limited annotation under unreliable auxiliary modalities. Test whether a corrupted DSM produces overconfident pseudo-label errors and whether reliability-based handling improves them beyond fixed averaging and optical-only alternatives at matched coverage.
- Prior art already overlaps RGB–DSM geometry-guided semi-supervision. Do not claim first combination or novelty until full-paper comparison and mechanism-specific evidence exist.
- Semi-supervision means a labeled subset plus unlabeled images; point/scribble/image-level supervision is a different protocol. A fully supervised teacher trained on all Train16 labels cannot be reused to claim a strict reduced-label budget.
- Open-vocabulary exploration needs text-conditioned predictions and a meaningful unseen-category protocol. Evaluating six familiar class names alone does not establish unseen-category generalization. DSM can potentially guide geometry, but should not impose a fixed six-class semantic head on unseen categories.
- Immediate overnight candidates: existing-route region-level evaluation, equal-budget teacher-target ablations, and pseudo-label error diagnostics. New semi-supervised or open-vocabulary training is a separate engineering phase, not an already runnable queue.
- Keep GPU0 serial execution, validation-only development, unique output paths, execution-boundary checks, configuration/checkpoint hashes and saved int64 confusion matrices. No use of historically exposed test6.

## Scope

This note preserves source provenance for the current planning discussion. It does not modify project status or authorize claims beyond the supplied validation results. Timing estimates for future jobs must be calibrated from a smoke run; no job was launched while writing this note.
