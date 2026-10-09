# Post-S1运行中完整作业快照与阶段分析（2026-10-09）

用户已授权把当前完整实验记录上传并分析。最新只读查询2026-10-09T21:31:11.112511+08:00，queue观测21:31:07.216349，RUNNING_P3、controller1890742 LIVE=True。CPU/D1完成，P6/P7/P8/P9/P4/P5/P2七完整作业，P3训练8000但仍fixed8000评价、3_11/aux_down4，P0/P1/E待运行，仅GPU0。没有新精度或gate回报。

## 上传入口及一致性
scripts/upload_post_s1_completed_records.py --root ROOT --directory DIR --commit HELPER_COMMIT。HELPER_COMMIT绑定上传工具版本，不改变原科学执行2c5e7d6或code_manifest。工具在一个queue原子快照中冻结COMPLETE名单，逐一accept_worker核complete/summary/checkpoint摘要；只遍历这些作业，绝不读取RUNNING/PENDING目录。若P3在上传名单捕获前已完整结束，可自然收入；捕获后才结束则留待下一快照。不把step8000当作complete。

包含CPU D0原计数、R0_U/ordinary、D1完整交叉推理、已完整P所有JSON与关闭的日志、配置/源码/初始化绑定、固定mask元数据、原S1-0 selected8000基线的ordinary/fixed/U全部轻量记录。数组/权重留服务器，以路径/大小/SHA来源索引；新完整checkpoint由accept核SHA，预测数组本体不在本次轻量快照重hash，不能扩大验收范围。queue_status.json是当时快照，completed_snapshot.json记录包含/排除名单及科学结论是否齐备。

在原zzx实验目录下建立独立github_completed_upload_<stamp> worktree、completed_evidence_<stamp>记录路径；无损gzip-base64-exact-v1、80MiB单文件/512MiB轻量总量保护。单独completed_upload.lock，不占用controller/worker锁，不改原数据、暂停队列、启GPU或重跑。Git非强制push；冲突停止并保留快照，不改训练。--prepare-only可仅出大小/名单报告。发布入口已通过6项stdlib合成回归与help，无真实服务器上传回报。

## 原件收到后的阶段分析
1. 回读upload_manifest与source_files；验证路径/大小/上传SHA及解码SHA，核科学提交、plan/code/checkpoint/mask/input绑定。范围明确不含GPU复跑或服务器全部数组本体重hash。
2. 对全部已收summary独立重算int64 6×6 CM→TP/FP/FN/support/IoU，验证tile→pooled及joint边际/池化、Full/NoBoundary口径。
3. D1四固定权重×四策略分开权重与推理影响，同权重完整/全缺失一致性只属工程契约；D0救回/伤害报告分母与重叠区域，不将净像素差当mIoU。
4. 先报告P7相对S1-0/P6/P8/P9/R0的RGB_U/DSM_U、逐tile同号、clean/fullmissing与primary最差tile保护；固定P7，不后验换最高项。P4—P9冻结四格及控制可先讨论，P2对P6已有一个匹配参数更新对照。
5. 如P3/P0/P1未齐，不声称完成全部2×2×2因素矩阵；E未收，不宣称压力条件可靠或最终P7/双向gate成立。S1-0旧训练龄与新P多8000步的差别必须明示，机制增量以匹配P控制为依据。
6. 实测成本和运行完成不等于精度价值；最终E、新方向Q/独立泛化各自门槛保留。运行中的队列继续原协议，无新增seed/失败配方重跑或GPU1/Test6/held4/独立final。
7. 阶段报告、原件审计范围、未齐项目和去留均同步GitHub并回读；最终完成再做全批快照和E验收。当前只有终端进度/loss，实际阶段精度分析须等待用户执行上传返回COMPLETED_GITHUB_COMMIT。
