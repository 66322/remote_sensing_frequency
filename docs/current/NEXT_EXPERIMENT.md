# 下一步：重传D26/D27原件并整理结果

D26最后观测2026-10-03T04:04:45.239849+08:00 COMPLETE9/9。旧上传因原文总量超过512MiB停止，D27查询尚未执行；D27最后已知10-02 23:32 WAITING_D26，须新status/queue记录确认。

使用本次提交scripts/upload_rebuild_v1_d26_records.py与upload_rebuild_v1_d27_records.py写入对应实验目录后执行--root工程根目录 --directory对应目录。先各自运行已有status脚本。若一轮失败，另一轮独立上传，不因set -e遗漏第二轮。

D26目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d26_bidirectional_20261002T191253_1513109；D27目录同根records/research_d27_safe_routing_after_d26_20261002T191253_1513109。修正版不重新训练/预测，原件不修改；[无损编码与解码说明](../experiments/D26_COMPLETE_UPLOAD_FIX_20261003.md)。用户回传两提交号即可，助手从GitHub读取、解码核验、整理结果并更新共享状态。

结果复核先验证完整标记、checkpoint/SHA、selected与fixed8000差别、逐tile原矩阵与屏幕指标，随后按D26/D27各自冻结gate判断，不跨实验任意改阈值。读到record_encoding=gzip-base64-exact-v1时必须解码并验证原文SHA，不能把信封当指标JSON。

[假设复核候选](../experiments/ASSUMPTIONS_AND_RESEARCH_OPPORTUNITIES_20261003.md)尚未排队；先收齐结果再决定有限压力评价。Test6禁读，GPU仅0/1、nohup/zzx不变；不资源探针、不重启现有队列。
