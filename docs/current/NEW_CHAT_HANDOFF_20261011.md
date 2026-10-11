# 新对话交接：结构化缺失零训练后继已就绪，待用户一次登记

权威源66322/remote_sensing_frequency / rebuild-v1-protocol-20260915。发布准备日期2026-10-12（Asia/Shanghai）。

## 最后服务器状态

最后用户只读查询2026-10-11T23:34:24.796568+08:00，queue观测23:34:17.832878，RUNNING/controller LIVE=True。CONTENT_PRE/H8/F8 COMPLETE退出，R8 GPU1 8000/8000、endpoint_ordinary仍运行；R16/H16/F16/CONTENT_POST PENDING。3/8整项完成、1评价、4待办。GPU0空闲可由8k阶段等待解释，停用标志未在回报中提供。这是最后观测，不代表实时状态。

原目录research_post_t_paired_v2_20261011T182543_3880702、执行44e4df5afbaeb603e6441e7ef14ff09f228bc027保持。原六训练72000步、主候选R16及阶段检查不变。两卡可用时R8技术完成与配对检查后自动派发GPU0 R16/GPU1 H16，再先空闲卡F16。前测、训练精度和机制原件仍未接收。[原回报](../../records/research_post_t_paired_v2_20261011T182543_3880702/user_reported_progress_20261011T233424.json)、[原执行操作](../protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md)。

## 新授权及后继状态

2026-10-12更新：用户已明确授权把下一阶段排在当前队列之后。[后继执行v0.1](../protocols/STRUCTURED_FAILURE_V0_EXECUTION_20261011.md)已实现、17项CPU合成检查通过，READY_NOT_REGISTERED_SERVER_RUNTIME_UNVERIFIED；尚无服务器新目录/PID回报。等待当前八项技术完成、进程及锁释放后，自动CPU掩码可行性→8clean与6旧端点→640缺失case，0训练。用户此授权覆盖此前“原件科学解读后才启动固定诊断”的排期建议，但科学结论仍须独立验收。

固定范围为四系统（D25 P6 RGB-only、S1-0、M000_masked、M000_context）×四mask族（pixel/random/gradient/matched）×20掩码实现×两Val2。42队列任务：2clean/旧端点任务与40个tile×实现任务，每个后者16输出；Phase1B、尺寸扫描、GT边界族、Vaihingen、DSM镜像和新训练不登记。

[实现验收](../../records/structured_failure_v0_implementation_20261012/verification.json)。CPU合成通过不等于实际6000²影像匹配、真实权重/H100或精度通过。服务器注册重做CPU检查；真实mask只在前序退出后生成，匹配不可行/重复/梯度对比丢失即HOLD，不放宽阈值、不换seed。GPU正式阶段前8clean与6旧rgb_U端点复现必须成功。

唯一登记入口scripts/enqueue_structured_v0.py，从本次发布提交抽取；重复登记只报已有目录。注册时只复制/散列轻量代码并做CPU合成检查，等待期不申请CUDA或扫描影像。前序必须八项COMPLETE、controller/worker退出、锁释放；取得全局lease并验证绑定后才准备。前序失败/停止即HOLD；不删除部分目录、不自动重启控制器或失败任务。

显卡管理入口scripts/manage_structured_v0.py。原与新队列最新明确release/rejoin生效；新入口在原仍活动时同步该卡请求，原卡释放状态不会因队列切换失效。用户主动释放的任务在其他启用卡优先续跑，只复用已绑定完整case，部分case重推理、0训练。需等worker退出并确认卡空闲后给其他工作用。每GPU一worker、累计每任务8h保护、CPU准备4h，无全队24h截止。

## 科学角色与下一步

研究仍为可行性探索与机制定位，主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复旁支。旧T7/U/E=False保持，不后验改选高分模型。结构化缺失是RGB方向待检验子问题，已有证据限重复Potsdam Val2/seed42；不声称双向、未知故障或独立泛化。

固定主PE为S1-0同支持damage的gradient−matched，CB为同权重context−masked；random与语义matched分开，后者GT仅参与诊断生成。20掩码不是20训练seed或地区。healthy空集合None；保存Full/NB原6×6矩阵、逐类计数、伤害/救回和预测SHA。掩码位置/匹配算法已在v0.1代码和说明冻结，不看模型结果调参。尚无本轮真实结果。

立即下一步：用户执行本次给出的后继一次登记命令，并回传STRUCTURED_QUEUE_REGISTERED/日志/status；助手记录真实新目录/PID。当前配对队列继续原样运行。它完成后可显式上传原F/H/R轻量原件供独立验收；后继无须等待聊天端在线才按固定旧模型运行。新后继完成后也显式上传自己的轻量原件，再决定后续配对训练，不根据screen自动开启训练。

服务器由用户执行、无SSH，全部记录快照在/home/jovyan/zzx对应目录。Test6/held4/final关闭。此前交接见[归档](../history/PRE_STRUCTURED_QUEUE_HANDOFF_20261012.md)，设计评审见[历史草案](../protocols/STRUCTURED_FAILURE_EVAL_V0_20261011.md)。
