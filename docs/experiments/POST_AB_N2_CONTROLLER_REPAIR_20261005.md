# N2控制器故障与保留科学快照的接管修复

最后服务器观测（用户终端回传）：2026-10-05T09:21:05.606873+08:00，QUEUE=RUNNING_N2，修复控制器PID3467202 LIVE=True。GPU0 N2-0原worker PID3457210 LIVE=True，training 940/8000（progress观测09:20:52.566194，1.309439秒/训练步）；GPU1 N2-1新worker PID3467394 LIVE=True，training 60/8000（progress观测09:20:47.378619，1.347363秒/训练步）。N2-2—5 PENDING，两卡各一个worker；两组均已加载12/12训练tile。日志确认ADOPT原N2-0、CONDITIONS_PASS 32、HANDOVER READY COMPLETE和START N2-1，原N2 CPU8项复查PASS。接管后两卡实际训练已确认，未重训N2-0，暂无N2完成或精度结果。科学快照86b6a70e5c3482314986fb1259e2fccbd0a5a38b、修复9b196a204e6a45cb54244b4deb5437ff44bd074e与原plan保留。继续已有队列，只读观察，不重复登记或重启。

## 原始异常与边界

原目录`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_n2_20261005T085829_3456726`；日志nohup_20261005T085831972742.log。POST_AB_START 0 N2-0 3457210后，control_post_ab_n2.py:90报TypeError: unsupported operand type(s) for *: int and NoneType。runtime_plan继承N1的null超时，新增控制器检查直接乘3600，CPU模型检查未覆盖控制器实际监控循环。责任是工程漏测，不能声称实验已失败、N2-0已停止或从未训练。

## 修复与恢复规则

None按既有协议8h，异常/非正/非有限/bool超时拒绝；新登记显式写8，旧plan不改。专用installer拒绝活控制器/持锁或其他后继队列；核对86b6科学提交和完整原manifest。修复仅复制控制器、恢复helper、状态脚本和恢复测试到原目录controller_repair_*，保存旧queue、fix_commit、science_commit、原plan及manifestSHA、文件SHA、接管worker列表及workers_restarted=0。worker和汇总始终运行原code快照与原PYTHONPATH，科学执行签名仍86b6。

RUNNING有精确脚本/目录/job/gpu参数及kernel starttick才接管；PID复用/未知worker/待运行目录已有产物均HOLD。已派发进程结束时校验8000步、science/plan签名、两summary、selected和last checkpointSHA，以及test/final未访问。无完成记录不转回PENDING，不从partial checkpoint自动续训。实际监控循环优先处理在运行卡，再判断另一卡派发，技术失败停止新派发；采用pidfd安全停止超时的接管进程。原N1状态脚本的四组可执行提示已改为通用只读说明，并打印worker存活与progress原件。

## 本地验证（代码已实现；不是服务器实验完成）

Python3.13标准库CPU恢复11项PASS，包括None真实监控循环、接管完成不重复派发、另一卡失败阻断派发、死进程无完成HOLD、待运行已有产物HOLD、PID启动tick复用、错误完成绑定、无自动重试。原N2 CPU八项（Torch2.7.1 CPU）PASS；七文件语法解析PASS。服务器安装器再运行恢复11项CPU检查才启动nohup修复控制器；未声称服务器真实CUDA/速度/精度验证通过。旧科学代码8项检查已在原派发前执行，故障不是模型CPU检查失败。

修复已接管原worker，09:21:05两卡实际训练已确认；下一步按[只读命令](../current/NEXT_EXPERIMENT.md)回传状态和日志。若HOLD，先分析N2-0日志和现存产物，再单独制定技术恢复；不会无条件重训。N2去留仍按原冻结六臂协议，不改变主线、seed、预算、门槛或基座。
