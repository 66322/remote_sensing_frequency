# Phase2 结果核验与判断（2026-10-14）
## 来源与验收范围
Potsdam Fit12/Val2（3_11、5_10）、seed42；运行research_phase2_matched_20261013T151120_1310582，执行e5641e073bf4421e346f589199c291a6e94db8b2。最终队列记录2026-10-14T00:39:03.210695+08:00为PHASE2_COMPLETE_AWAITING_REVIEW，摘要00:39:01。核心4训练48k完成，无B1/B3。用户上传dc335e0d13d3a1bb4b58e253feaa22cc516275ef成功。
[摘要原件](../../records/research_phase2_matched_20261013T151120_1310582/light_evidence/summary.json)、[清单](../../records/research_phase2_matched_20261013T151120_1310582/light_evidence/manifest.json)、[核验](../../records/phase2_review_20261014/verification.json)。
309分块SHA及压缩流SHA、24643原件逐文件SHA/bytes核对；3814案例完整（average8k322、average16k/B0/B2各1164）；183072个6×6非负整数CM检查，95项汇总/轨迹分数离线重算一致。case绑定与counts完成SHA一致；双专家初值、参数清单一致且16000条batch流相同，B0/B2各8000条流相同。服务器大数组/权重未在本地重哈希，不能将轻量验收写成所有大文件的字节审计。

## 实验已验证：固定面板表现
下面为NoBoundary mIoU_fg5百分数，先同条件池化两tile CM再对注册条件等权；Full指标另外保存在原始CM，不混用口径。
| 系统 | clean | 已知缺失P-M | 未报告退化P-U（主指标） | ordinary |
|---|---:|---:|---:|---:|
| 平均融合 |84.8403|75.8629|76.1475|77.3805|
| B0逐类静态校准 |84.3712|75.8067|75.7565|77.2603|
| B2容量对照 |84.2793|76.1952|75.8231|77.5972|

B0/B2相对平均融合P-U分别-0.3909/-0.3244pp，clean分别-0.4691/-0.5610pp；B2在P-M/ordinary分别+0.3323/+0.2167pp。这是面板间收益/损失，不支持笼统“全面提升”。16k RGB-only clean86.6343、P-U77.5036，均高于这三种融合；DSM-only clean62.4805。不能将弱DSM复制三通道基线当DSM能力上限。

P-U方向分解：RGB故障 average73.3221、B0 73.1024、B2 72.6211；DSM故障 average78.9729、B0 78.4106、B2 79.0250。B2只是DSM故障方向微增0.0522pp、RGB故障方向下降0.7009pp，未形成双向收益。
P-M missing ROI三系统均73.5372105，与逐窗口精确回退及3814案例fallback回执一致；whole/healthy仍受两模态可用位置混合影响。

## 实验已验证：轨迹
| step | RGB Full fg5 | RGB NB fg5 | DSM Full fg5 | DSM NB fg5 |
|---|---:|---:|---:|---:|
|4000|80.8165|86.0484|59.5040|62.6169|
|8000|81.4401|86.5728|59.2948|62.4142|
|12000|81.7547|86.9054|59.4600|62.6392|
|16000|81.5183|86.6343|59.3389|62.4805|

8k→16k clean NB仅RGB+0.0615pp、DSM+0.0663pp；RGB12k更高、DSM波动很小，未见后半程持续增长，不能证明全局训练充分。clean Full secondary选择与主比较固定16k分开；不能事后改年龄改善主结果。8k来自同一16k学习率轨迹，不是独立8k日程的因果预算实验。

## C/L与静态后停止
C=True：RGB故障方向H_initial18.4441pp、DSM故障3.6653pp，两tile均正，公平专家下仍存在条件互补的诊断空间。C与H_initial已从原CM独立重算。
L=False，支持量报告通过；熵尾部胜率约0.77–0.89不等于全规则收益通过。L预定规则相对固定参照的RGB方向增益+15.0541pp，DSM方向-0.4779pp（两tile均负），不满足双向要求。只否定本轮预注册信号规则的入场条件，不否定所有多变量可靠性模型。
静态参照B2，残余诊断差RGB14.1959pp、DSM11.2745pp，clean retention-0.56097pp超过-0.3pp保护。static_gate从CM独立重算完全一致。L和clean保护均未通过，B1/B3不派发，dynamic_accepted=null不是“动态头训练失败”。
[门禁复算边界](../../records/phase2_review_20261014/gate_recomputation.json)：L的distinct-coordinate union依赖服务器tail_rgb/tail_dsm.npy，本地轻量包不能独立复算该项；原件和小型坐标数组继续保留，不能称L全部独立再验收。

## 路线角色与下一步
主线仍是RGB–DSM双向条件互补与退化/缺失分割，恢复旁支。本轮是有价值的匹配专家/静态对照与停止证据，尚非新方法贡献。当前B0/B2固定配方不支持作为改善方案继续扩预算；不自动延长、改门禁、补seed或新训练。
下一不确定性是：弱DSM与校准/训练分布如何导致clean及RGB故障损失，以及剩余oracle诊断空间是否有可部署结构。下一协议待本轮去留分析，不用oracle差直接承诺可恢复提升。固定两Val2、重复20mask、单seed只支持开发阶段，不支持独立泛化或多seed显著性。

## 清理决定
用户已授权及时清理无用途产物。该轮保留最终计数/轨迹/代码/配置/必要权重及L坐标证据，退役val_cache *.npy、head_cache *.npz和3814已计数案例的7类compact arrays（pred/rgb/dsm/entropy_bin/mask/rm/dm）。不会删除tail_rgb/tail_dsm、JSON/日志、源数据/预训练/输入与权重。两缓存约461GiB来自19:36旧实测，另有预测数组，实际可释放量由执行清单inode去重核算。
cleanup_phase2_completed.py已实现，4项本地范围/文件变化/硬链接及证据保留检查通过；清理尚未在服务器执行。清理前再核对上传archive、当前计数与绑定、队列/进程/锁，逐文件unlink并留退役回执。原array complete SHA路径退役，离线指标仍由保存CM重算。
