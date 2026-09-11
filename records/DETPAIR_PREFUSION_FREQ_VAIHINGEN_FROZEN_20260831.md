# Deterministic Paired Pre-Fusion Frequency Experiment — Vaihingen

## 1. Research question

Test whether cross-modal frequency information used before the first Optical–DSM fusion improves semantic segmentation relative to direct bimodal fusion.

## 2. Compared models

### F0
Original bimodal baseline with ordinary decoder and no pre-fusion frequency calibration.

### P1
F0 + a 593-parameter pre-fusion cross-modal high-frequency calibration module before the first Optical–DSM SE fusion.

P1 uses optical HF energy, DSM HF energy, and their normalized discrepancy to predict a spatial DSM HF scale:

F'_d = F_d + (S_d - 1) H_d

Common F0/P1 parameters are exactly seed-matched at initialization. P1 is exactly F0-equivalent at initialization.

## 3. Deterministic paired protocol

- Dataset: ISPRS Vaihingen
- Train tiles: 1,3,7,11,13,17,23,26,28,32,34,37
- Test tiles: 5,15,21,30
- crop: 512
- physical batch: 4
- gradient accumulation: 4
- effective sampled batch: 16
- AdamW
- backbone LR: 6e-5
- decoder/head LR: 6e-4
- prefreq LR: 6e-4
- warmup: 1500
- Poly denominator: 160k
- evaluated every 2000 updates
- deterministic CUDA protocol
- flattened pixel-wise CE for deterministic diagnostic protocol
- both runs stopped at 40k updates

## 4. Main 34k paired result

Both models reach their best NB mIoU at exactly 34k.

| Metric | F0 | P1 | Delta |
|---|---:|---:|---:|
| NB OA | 92.0958 | 92.2596 | +0.1638 pp at paired 34k |
| NB mF1 fg5 | 90.2884 | 90.5897 | +0.3013 pp |
| NB mIoU fg5 | 82.7268 | 83.1941 | +0.4673 pp |
| Full mF1 fg5 | 86.6707 | 86.8619 | +0.1912 pp |
| Full mIoU fg5 | 77.0438 | 77.3105 | +0.2667 pp |

Note: F0's independent best NB OA occurs at 14k (92.2786); the table above is the strictly paired 34k comparison.

## 5. Late-stage stability

- 20k–40k mean NB mIoU delta: +0.2886 pp
- P1 wins 8/11 evaluation points
- 30k–40k mean delta: +0.5006 pp
- P1 wins 6/6
- 32k–40k mean delta: +0.5732 pp
- P1 wins 5/5
- final 40k NB mIoU delta: +0.2946 pp

The 32k F0 point is unusually low, therefore the 32k–40k mean should not be used alone as the primary effect size.

## 6. NB per-class IoU at paired 34k

| Class | F0 | P1 | Delta |
|---|---:|---:|---:|
| Impervious | 87.2709 | 87.5901 | +0.3192 |
| Building | 95.0799 | 94.9563 | -0.1236 |
| Low vegetation | 68.8302 | 69.6543 | +0.8241 |
| Tree | 84.1664 | 84.4253 | +0.2589 |
| Car | 78.2866 | 79.3447 | +1.0581 |

Four of five foreground classes improve.

## 7. P1 frequency behavior at 34k, noBoundary

| Class | Mean S | S<0.95 | S>1.05 | Mean discrepancy |
|---|---:|---:|---:|---:|
| Impervious | 0.9257 | 61.88% | 0.00% | 0.6655 |
| Building | 0.9348 | 50.40% | 0.00% | 0.8222 |
| Low vegetation | 0.9425 | 40.46% | 0.00% | 0.7837 |
| Tree | 0.9612 | 15.23% | 0.00% | 0.9377 |
| Car | 0.9531 | 27.85% | 0.00% | 1.2341 |

At the best checkpoint P1 primarily performs spatially adaptive DSM high-frequency attenuation rather than high-frequency enhancement.

A simple monotonic rule "larger discrepancy -> stronger suppression" is NOT supported. The gate conditions jointly on optical HF energy, DSM HF energy, and discrepancy.

## 8. Interpretation

The result supports the potential value of applying cross-modal frequency conditioning before the first Optical–DSM fusion.

The current evidence does NOT prove that pre-fusion frequency processing is universally superior, nor does it establish causal relationships between a specific scale value and class performance.

The learned P1 behavior is better described as cross-modal frequency-guided DSM high-frequency calibration / attenuation than as high-frequency enhancement.

## 9. Next validation

Repeat the matched F0 vs P1 experiment on Potsdam before considering P2 or making a general cross-dataset claim.
