# Phase2 首次smoke确定性交叉熵技术修复（2026-10-13）

## 原始观测与边界

最后状态查询2026-10-13T15:02:06.544744+08:00；队列最后更新15:01:28.757852：TECHNICAL_FAILURE_HOLD、controller和全部worker均不存活。旧目录 /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase2_matched_20261013T145903_1304150。prepare/legacy_counts完成，GPU0和GPU1均在smoke的F.cross_entropy正向抛出nll_loss2d_forward_out_cuda_template无确定性实现；没有到达loss.backward/optimizer，更未派A_RGB/A_DSM。smoke1 RUNNING是旧状态残留，不是实时运行。[用户原始日志](../../records/phase2_ce_fix_20261013/server_smoke_failure.txt)。xFormers警告不是本次异常。

## 实现修复

保持torch.use_deterministic_algorithms(True)及原FP32、ignore_index=255、六类无权重mean CE。使用log_softmax按类torch.where求负对数概率总和，分母为整个batch全部有效像素数，避免CUDA NLLLoss reduction；没有改为逐图等权平均，也没有关闭确定性或warn_only。数学目标不变；归约顺序变化，不能声称所有浮点结果逐bit与旧算子一致。损失值/梯度在CPU FP32/BF16输入、不同每图ignore比例下对照原CE通过。新真实GPU smoke首先做两次loss/backward严格重复性与CPU参考容差核验，再做原actual batch16 DINO检查。smoke、两专家和四head统一使用segmentation_ce。

controller在退出后将已结束的RUNNING worker修正为COMPLETE/INTERRUPTED_HOLD，不伪装仍活跃。12项CPU检查通过；4个改动Python语法检查通过。没有真实GPU验证、训练或新服务器登记。

## 一次受控技术替换

用户前台运行新enqueue_phase2.py的--replace-ce-bug-directory，仅接受原f01f9e94代码的smoke0失败、双卡日志明确同一NLL缺陷、原plan/code封印和逐源码SHA不变、jobs空、无任何pth或smoke_pass，且原controller/worker退出、锁自由、目前仅一个旧Phase2目录。任一不符停止，不代替普通失败配方重试。

旧目录不改源码/plan/失败状态、不删证据；新目录独立不可变快照、plan绑定旧plan/code/failure SHA，复验准备及双卡smoke；旧目录仅增加replacement_registered.json关联。不能直接重启旧controller，不自动续checkpoint。两训练16k/四头8k、seed42、split、C/L门禁、GPU0/1与无24h截止均保持。完成后依照执行协议前台上传，无自动方法或额外seed派发。

只有首次CE bug的显式参数允许一次替换；已有其他Phase2目录时拒绝，普通enqueue仍只显示既有状态。
