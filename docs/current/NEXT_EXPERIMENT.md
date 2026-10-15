## 2026-10-15启动故障后更新

用户回传首次run `research_phase3_m1_20261015T142532_2652995` 于14:26在RGB_CLEAN导入时报 `No module named 'model'`，状态FAILED_OR_INTERRUPTED_NO_RETRY，控制器已退出。14项输入已核对；未见TRAIN派发，新增训练更新未观测。原因是执行入口缺少代码根目录搜索路径，非科学门禁失败。

已修复入口路径，增加输入准备前真实模型导入检查及无关工作目录/无PYTHONPATH的独立子进程回归。下一步用修复提交bootstrap，并显式指定 `--supersede-failed /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m1_20261015T142532_2652995`。仅此已识别的空训练失败run通过全部退出及状态检查后可被新run取代；旧目录完整保留，已有其他run则不重复开队列。恢复尚无服务器执行回执。

## 修复前执行包登记（历史状态）

# 下一步：启动固定提交的Phase3-M1执行包（2026-10-15）

Phase3-M1已按用户要求落实执行包，尚未取得服务器启动回执。仅使用本篇遥感RGB/DSM/标签，GPU0/1，固定16k、batch16；11个新主训练，最多2个条件反证，总上限13个新训练208k更新。旧M00/42在绑定合格时复用，Test6/held4/final不读，点云论文不进入本轮。

双卡共享就绪队列，空闲卡可以领取另一seed任务。GPU到CPU交接只等内存接收，不等计数完成；RGB故障前向跨所有DSM对照共享。Fit训练RAM在全部训练消费者结束后分进程释放，条件预测匿名RAM在最后计数消费者结束后关闭，成功作业的滚动优化器在端点与主计数核验后退役。GPU无后续任务时先退出，CPU继续收尾；所有自有进程退出后清理runtime cache/temporary。负结果、失败恢复状态、必要16k权重和充分整数证据保留。

[执行与清理协议](../protocols/PHASE3_M1_EXECUTION_20261015.md)；[科学设计](../protocols/PHASE3_M1_DESIGN_20261015.md)；[包清单](../../configs/phase3_m1_execution_manifest.json)；[本机检查记录](../../records/phase3_m1_implementation_review_20261015.json)。

用户已明确要求按上述规划落实具体实验并清理无用缓存，不重复申请GPU/时间/清理授权。唯一下一步是在服务器用原d18_dino Python运行固定提交的scripts/bootstrap_phase3_m1.py --root /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro --commit <本执行包的完整提交SHA>，建议连注册一起nohup。助手无服务器直连，不能宣称已启动。程序输出新run、控制器PID、日志与只读状态命令；同一协议已注册则只显示状态，不重复创建队列。

本机17项覆盖中16项适用检查通过；Linux memfd检查在注册时执行，实际GPU梯度检查并入首个正式更新。无需重跑已通过且代码绑定未变的完整逻辑模拟。没有新实测吞吐或结束时间。

不使用旧Phase2/2.4入口、不重启上传、不恢复T1/T2/T3。原门禁False保持。[Phase2.4验收](../experiments/PHASE_24_ACCEPTANCE_AND_ROUTE_REVIEW_20261015.md)。
