# 下一步：把当前正式队列用nohup接续

用户已前台启动GPU0 TSF/GPU1 T0，必须先在原终端Ctrl+C停止旧controller，再以--resume-queue接续同一实验目录。未完成组从最近checkpoint恢复，完成组跳过；不新开第二份八组实验。模型/数据/损失和4000步保持，原产物保留。

具体规则见[nohup与接续](../protocols/D23_NOHUP_AND_RESUME_20261001.md)。nohup启动重定向stdin=/dev/null，stdout/stderr与PID落本次zzx目录。每30秒日志更新；训练/评价全部结束后前台运行打印的上传脚本，完成认证后原件上GitHub，不要求粘贴长输出。
