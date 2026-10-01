# 下一步：读取TS错误，保留正在执行的TF

2026-10-01最新用户回传：日志显示TS启动后TECHNICAL_FAILURE，GPU1 TF PID815379在elapsed_minutes=2.0打印D23_GATE_TRAIN TF 1。没有独立观测墙钟，不作为实时存活保证。GPU0空闲是TS失败所致；TF最后观测已开始训练，不应为诊断TS停止TF。

代码已确认prepare_resume_job在旧失败目录没有checkpoint时仍提前创建target，而worker新训练拒绝已有output目录，构成确定的接续缺陷。此缺陷已修复：仅有checkpoint才创建目标目录用于复制，否则把未创建路径交给worker。11项本地针对性检查通过，包括失败无checkpoint的新目录条件。该缺陷是否就是本次TS实际异常，仍需读取TS本次log_path中的末尾错误；不要把推断当作服务器错误原件。

立即下一步仅读取queue_status中TS日志末尾，同时保留TF继续执行；暂不重复运行--resume-queue（TF工作进程仍可能存活）。上一空闲等待修复保留；模型/engine/runtime lock不变。修复代码已发布，服务器尚未执行此版。TSF/T0完成保留，八组仍未完成。
