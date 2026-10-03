# 共享入口：D30已实现，等待服务器一次nohup后接启动

用户2026-10-03明确“按上述规划进行，随后加入已进行的队列后面”。D30已实现、执行授权已记录；**待用户服务器执行下面一次nohup命令，尚未收到D30 PID/队列观测，不能写成已在排队**。执行commit固定9db12dfb7ee85dff91dd6c246c7f161b60aca603。本地18项行为检查17通过、1项Linux文件锁检查跳过；服务器启动时自动执行全部18项CPU检查。未在本地或服务器启动训练。

权威分支rebuild-v1-protocol-20260915。先读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)。

D27已完成并复核，当前四gate失败；D28最后收到18:34 RUNNING0/7，其后状态未知。新D30复用S0/S1，用48次checkpoint诊断和4组静态训练拆开损失目标。原D29未激活。仅GPU0/1 H10080GB、RAM/磁盘充足、batch16无累积、nohup、zzx对应目录，无资源探针。

[D30协议](protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)、[实现与检查](experiments/D30_IMPLEMENTATION_20261003.md)、[D27原件复核](experiments/D27_FINAL_REVIEW_20261003.md)。不要将代码已实现或本文授权当作服务器已排队；执行NEXT命令后检查真实PID/等待状态。[实施前入口归档](history/pre_D30_implementation_20261003/START_HERE.md)。
