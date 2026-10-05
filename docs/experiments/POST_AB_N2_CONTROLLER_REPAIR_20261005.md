# N2控制器故障与保留科学快照的接管修复

最后服务器观测（用户回传）：2026-10-05T08:58:59.848681+08:00，N2控制器PID3456909已退出，QUEUE=CONTROLLER_INTERRUPTED。N2-0已派发到GPU0（worker PID3457210），其实际存活/训练步数待核对；不能把旧step=0快照当成当前进度。N2-1—5尚待派发。原科学执行提交86b6a70e5c3482314986fb1259e2fccbd0a5a38b保留。故障为per_job_timeout_hours=null被直接乘3600；这是控制器技术失败，不是N2科学负结果。控制器专用修复和安全接管工具已发布，尚无服务器恢复执行回报。先接管已有worker或验收绑定完成记录；已退出且未有效完成则HOLD、输出日志，不自动重训。不重复登记N2，不重启原C/N1。

## 原始异常与边界

原目录`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_n2_20261005T085829_3456726`；日志nohup_20261005T085831972742.log。POST_AB_START 0 N2-0 3457210后，control_post_ab_n2.py:90报TypeError: unsupported operand type(s) for *: int and NoneType。runtime_plan继承N1的null超时，新增控制器检查直接乘3600，CPU模型检查未覆盖控制器实际监控循环。责任是工程漏测，不能声称实验已失败、N2-0已停止或从未训练。

## 修复与恢复规则

None按既有协议8h，异常/非正/非有限/bool超时拒绝；新登记显式写8，旧plan不改。专用installer拒绝活控制器/持锁或其他后继队列；核对86b6科学提交和完整原manifest。修复仅复制控制器、恢复helper、状态脚本和恢复测试到原目录controller_repair_*，保存旧queue、fix_commit、science_commit、原plan及manifestSHA、文件SHA、接管worker列表及workers_restarted=0。worker和汇总始终运行原code快照与原PYTHONPATH，科学执行签名仍86b6。

RUNNING有精确脚本/目录/job/gpu参数及kernel starttick才接管；PID复用/未知worker/待运行目录已有产物均HOLD。已派发进程结束时校验8000步、science/plan签名、两summary、selected和last checkpointSHA，以及test/final未访问。无完成记录不转回PENDING，不从partial checkpoint自动续训。实际监控循环优先处理在运行卡，再判断另一卡派发，技术失败停止新派发；采用pidfd安全停止超时的接管进程。原N1状态脚本的四组可执行提示已改为通用只读说明，并打印worker存活与progress原件。

## 本地验证（代码已实现；不是服务器实验完成）

Python3.13标准库CPU恢复11项PASS，包括None真实监控循环、接管完成不重复派发、另一卡失败阻断派发、死进程无完成HOLD、待运行已有产物HOLD、PID启动tick复用、错误完成绑定、无自动重试。原N2 CPU八项（Torch2.7.1 CPU）PASS；七文件语法解析PASS。服务器安装器再运行恢复11项CPU检查才启动nohup修复控制器；未声称服务器真实CUDA/速度/精度验证通过。旧科学代码8项检查已在原派发前执行，故障不是模型CPU检查失败。

下一步按[命令](../current/NEXT_EXPERIMENT.md)安装并回传日志。若HOLD，先分析N2-0日志和现存产物，再单独制定技术恢复；不会无条件重训。N2去留仍按原冻结六臂协议，不改变主线、seed、预算、门槛或基座。
