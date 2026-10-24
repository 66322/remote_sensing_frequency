# D18 matched seed17 replication results (2026-09-28)

Status: **COMPLETE**. Executed commit: `b66a9017129b0d6adc45c71cc6e9ca042548fc0b`.
This is exploratory Val2 evidence; Test6 remains sealed. Train16 has 16 tiles and Val2 has two.
P0 is RGB, P1 is RGB plus RGB-derived gray, P2 is RGB plus DSM. All use the same frozen DINO backbone and 8000 steps.

## Score and prespecified decision

| Training seed | Arm | Macro mIoU_fg5 (%) | Clean (%) | RGB quality (%) | Auxiliary quality (%) |
|---:|---|---:|---:|---:|---:|
| 42 | P0 | 81.3576 | 82.1209 | 79.8308 | 82.1209 |
| 42 | P1 | 81.3979 | 82.0894 | 80.0176 | 82.0866 |
| 42 | P2 | 82.4582 | 83.1255 | 81.1249 | 83.1243 |
| 17 | P0 | 81.1719 | 81.9517 | 79.6122 | 81.9517 |
| 17 | P1 | 81.4496 | 82.1787 | 79.9903 | 82.1800 |
| 17 | P2 | 82.3725 | 83.0430 | 81.0352 | 83.0395 |

| Training seed | P2 passed | Gain vs stronger P0/P1 (pp) | Clean guard | Family guard | Tile clean | Tile family |
|---:|---|---:|---|---|---|---|
| 42 | True | 1.0603 | True | True | True | True |
| 17 | True | 0.9229 | True | True | True | True |

Both seeds pass: **True**.
Main score weights clean, RGB quality and auxiliary quality equally; each family averages its prespecified conditions.
Contrast0.6 and shift8 remain diagnostics outside the gate.

## DSM absence and paired error

| Training seed | Original P2 aux_zero (%) | Same-seed P0 fallback (%) | P0-only correct pixels (clean) | P2-only correct pixels (clean) |
|---:|---:|---:|---:|---:|
| 42 | 81.6224 | 82.1209 | 727251 | 1168212 |
| 17 | 81.5413 | 81.9517 | 681277 | 1236022 |

The same-seed P0 fallback uses an explicit availability mask. Full absence equality with P0 verifies the switch implementation; it does not show learned missing-input detection.
Detailed per-class, per-tile and affected-region integer counts and both confusion matrices are in `decision.json`.
The historical R01 fallback and harm/rescue values remain in each arm summary and are not the same-seed P0 comparison.

## Next decision

Keep the DSM utility candidate. Inspect where P2 introduces errors and DSM absence cost, then design a reliability intervention with matched P0/P1/P2 controls. Plan independent-scene validation after freezing the method and checking prior data exposure.

## Evidence locations and limits

Compact evidence: `records/rebuild_v1_d18_replication_compact_20260928/`.
Full server evaluations: `records/rebuild_v1_d18_replication_20260928/`; training checkpoints: `runs/rebuild_v1/D18_REPL_*_seed17_8000_20260928/`.
Val2 contains only two scenes and was used repeatedly. Seed17 replication does not constitute independent Test6 validation.
The old C0 score is from a different backbone and training start, so absolute performance differences are not attributable to DSM alone.
Check manifest hashes and all six summaries before making another research decision.

## 离线审计与研究判断（2026-09-28）

[`offline_audit.json`](../../records/rebuild_v1_d18_replication_compact_20260928/offline_audit.json)
记录 `PASS`：本机从六份服务器原始摘要复核了各条件的整数混淆矩阵、
两种子的主分数和全部预设门槛，并核对逐图块及逐类配对计数。
归档 `manifest.json` 的状态为 `COMPLETE`、缺项为空；服务器队列三组正式训练、
评估和分析均成功。审计使用的执行提交为 `b66a9017129b0d6adc45c71cc6e9ca042548fc0b`。
本机未取得服务器的原始影像、预测数组或检查点，故这仍是摘要的独立复算，
不是重新推理。

| 训练种子 | P2相对较强P0/P1综合增益 | P2相对P0 clean | P2相对P0 RGB down4 | P2相对P0完整DSM缺失 |
|---:|---:|---:|---:|---:|
| 42 | +1.0603 pp | +1.0046 pp | +1.5944 pp | −0.4986 pp |
| 17 | +0.9229 pp | +1.0913 pp | +1.7081 pp | −0.4103 pp |

两种子各自通过 `gain`、`clean`、`families`、`tile_clean` 和
`tile_families` 五项预设检查。P2在clean下比同种子P0多纠正
1,168,212／1,236,022个像素，也新增727,251／681,277个错误；
净正确像素增加440,961／554,745。完整DSM缺失时，P0独有正确像素
909,804／807,255，多于P2独有正确像素683,813／728,137。
这说明综合收益可以重复，同时错误并未对每个像素单调减少。

clean条件的Building IoU相对P0分别提高3.528／3.950 pp；
完整DSM缺失时Building IoU分别下降0.949／0.242 pp，
Car IoU分别下降0.580／1.361 pp。逐类、逐图块和受损区域完整整数计数
见归档 `decision.json`。不同类别的变化不完全同向，不能把综合门槛
解释成所有类别的安全保证。

**当前决定：** 将P2作为可重复的DSM信息增益开发基线，并明确报告原模型的
缺失代价。已知availability mask时切换同seed P0可作为显式回退对照，
它不是P2自身学得的鲁棒性，也不构成新的方法贡献。下一步先确认一个未参与
本项目方法选择的带标注RGB/高度数据源、空间独立场景及类别映射，
再冻结可靠性干预与匹配对照的下一轮协议。Potsdam Val2只有两幅且反复使用，
跨种子重复仍属于开发证据；Test6继续冻结。外部数据可行性条件见
[独立来源决策](../current/INDEPENDENT_SOURCE_DECISION_20260923.md)。
