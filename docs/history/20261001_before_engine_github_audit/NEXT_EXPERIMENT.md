# 下一步：上传已有轻量记录，从GitHub核验

1. 在已有实验records/research_d23_b_engine_admission_20261001T140528_658274内执行scripts/upload_rebuild_v1_d23_engine_records.py，读取已生成compact_review_20261001T141936239377.json及7份原件。独立上传工作树也在该实验目录内；只上传9个明确文件，不重跑任务。用户回复提交号即可，不再粘贴长输出。[上传规则](../protocols/LIGHT_RECORD_UPLOAD_20261001.md)。
2. 助手从上传提交读取原件，复核GPU0 smoke八组/14条件、CPU22项测试、GPU1 profile单次backward与整图3条件、重载/缺失回退/设备/源码与专家SHA。最新片段补了GPU1完成时钟与CPU报告；GPU0完整头部仍待原件。[本次补充边界](../experiments/D23_B_ENGINE_RECORD_UPLOAD_PREPARATION_20261001.md)。
3. 完整绑定通过后，测12tile磁盘缓存/TCAP统计I/O及双卡并行预算，冻结正式wall/job/磁盘与资源锁，才生成8组各4000步队列。当前正式锁/队列未生成，最后回传无正式训练。GPU1小规模步速不能直接替代正式预算。
4. 按冻结screen比较精度/机制/风险；训练tile工程指标不作为开发Val2或论文test结果。失败保持原门槛，允许关闭解法/撤回频率承诺，不自动续训或补seed。

共享记录以同一GitHub分支为准。所有服务器产物保持zzx对应实验目录；禁止读取旧Test6。大型预测/权重/归档留服务器，GitHub索引并不代表全部原件上传。
