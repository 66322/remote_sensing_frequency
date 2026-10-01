# D23-B整图工程输出尾部核对（2026-10-01）

来源：用户粘贴输出尾部，无直连。服务器目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d23_b_engine_admission_20261001T140528_658274。上一执行命令代码40fca5a；本次附件不含提交/设备/身份/状态/observed_at/signature/train头部，不能独立验收两卡或补写完成时钟。GPU1 profile为上一命令顺序推测，未核对preflight原件；GPU0 smoke与服务器22CPU测试结果未完整回传。

附件中可完整解析aux_zero和aux_local_zero_stripe_eighth的三个R0/M0_safe/TSF记录。整图6000×6000、FullGT36000000有效像素，各6×6原始矩阵、support/TP与fg5 mIoU本轮复算相符。整幅缺失36000000像素，条带缺失4500000像素，六条missing记录harm/rescue均0；missing_logits_equal全部true（服务器程序报告，本地无原logits重做字节比对）。整幅缺失三个预测SHA及原矩阵一致。

资源（尾部报告）：总98.16204657秒，aux_zero评价35.50991239秒，条带评价23.05190708秒；峰值GPUallocated2439812608 bytes=2.27225GiB/reserved3028287488=2.82031GiB，主机RSS10096214016=9.40283GiB。只用于该工程任务，不当正式4000步工时或最终模型精度；训练稳态step耗时未回传。尾部明确formal_training_started=false、formal_fit_statistics=false。首个TSF片段条件头缺失，仅保存为unlabeled，不升级为clean正式结果。

下一动作：从已有gpu0/gpu1 summary.json、preflight.json和cpu_checks.log输出紧凑绑定/状态/时钟/训练秒数/条件计数摘要，并在当前实验目录创建轻量归档索引；不重跑smoke/profile、不读新影像、不启动训练。不把缺头日志当方法负结果。

待完整绑定核对后再测12tile缓存/TCAP I/O与双卡并行预算，生成正式runtime lock与8组队列。目前正式锁未生成、正式训练未启动；原机制/风险门槛不变。

用户决定从本轮起GitHub为共享记录入口，两电脑先读远端分支，见[记录规则](../protocols/RECORD_SOURCE_AND_HANDOFF.md)。本记录及紧凑证据直接在GitHub维护，不依赖本地缓存同步。
