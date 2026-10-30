# D23-A现有预测互补诊断结果

证据等级：用户回传的服务器开发诊断；现已满足准备B的工程门槛。代码已实现，实际日志报告COMPLETE；完整原始JSON尚在服务器，未完成本电脑逐tile联合张量复核。该诊断使用标签选择专家，不能部署，也不是所有融合方法的理论mIoU上界。

## 配置与最后观测

分支rebuild-v1-protocol-20260915；执行脚本来自提交961c7197d07a636c0d7d46bba7937e15395cf4f8，SHA256为04435db2bf0c21351e5684daa1588481c0cfdcd97a5a952585c2c7c89957b74d。Potsdam Val2 3_11/5_10；D21 R0/M0 seed42固定最终16000步专家；5个条件 clean/rgb_down4/aux_noise_std010/aux_zero/aux_local_zero_q1，20预测文件、10 pair，FullGT与NoBoundary均核对原混淆矩阵，主口径NoBoundary fg5。无新模型、推理或训练；Test6及独立final false。

服务器输出：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d23_feasibility_20261001_20261001T124227_658274。最后观测2026-10-01T12:44:35.075903+08:00 COMPLETE；profile于12:42:40.802781+08:00 PASS。不是GPU实时状态。

## 可用条件下互补诊断增益

分母为诊断每条件pooled NoBoundary fg5；差值相对该条件较强R0与相同缺失回退M0。

| 条件 | 增益pp |
|---|---:|
| clean | 1.59273714942888 |
| rgb_down4 | 2.4155417779414545 |
| aux_noise_std010 | 1.6570893076976567 |
| 三条件等权平均 | 1.888456078355997 |

本轮从回传数值独立重算均值相符。原工程分配规则为均值≥0.5pp且rgb_down4>0，全部满足，eligible_to_prepare_B=true。缺失两条件不用于此增益平均，不能凭回传摘要推断其逐像素计数或具体性能；须读取原decision/tile JSON。

## 资源与完整性

单pair profile12.5138秒，峰值RSS611,663,872bytes，预计主范围115.5334秒；实际full114.1585秒、峰值RSS612,552,704bytes（584.1758MiB）。日志10 pair均COMPLETE。脚本完成意味着其权重字节SHA、GT manifest/SHA、prediction SHA、train/eval签名与原6×6计数检查均没有报错；此结论来自用户粘贴日志，本轮没有直连或独立读取上述字节。不要称全部原件已归档。

轻量回传转录：[user_pasted_server_observation.json](../../records/research_d23_a_compact_20261001/user_pasted_server_observation.json)。完整profile/profile.json、full/decision.json、10tile-condition JSON与日志留在上面服务器目录；补轻量归档即可，无需重跑A。

## 下一步

进入B准备，而非宣布机制通过：完整语义S与频率F是否识别纠错仍未检验。新model/rebuild_v1_d23_gate.py核心支持8种等参数gate、6固定比较、128通道hook、对称监督sum/count；本地8项合成检查PASS，服务器实际D21模型及滑窗后回退、训练/整图评价入口、TCAP gate-fit统计、实际吞吐与磁盘预算仍待完成。B正式队列尚未实现或启动。

进入B的原参数/门槛保持方案；不能因A空间较大而放宽收益或harm/rescue保护。若可学习选择没有实际增量关闭此解法，频率无独立增量撤回频率贡献；C1保持旁支。
