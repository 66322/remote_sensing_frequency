# A0 IPC长路径故障与独立执行修复（2026-10-30）

当前：已收到目标prepare通过、修复入口派发及两模型各2k/校准/外层阶段完成回执；工程修复已在真实训练与评价链验证。内校准筛查阳性，原始外层分数/整数矩阵待现成JSON回传。不再prepare/start或重跑检查。原A0源码、数据、公开权重、旧日志、锁及回执保留。详见[失败与修复记录](../../records/post_m2_a0_ipcfix_20261030_release/failure_and_repair.json)、[当前固定发布](../../records/post_m2_a0_ipcfix_20261030_release/publication_receipt.json)。

## 原因与已知状态

原薄层入口TMPDIR=$A0/temporary长100字节。Python在该目录下构造pymp-/listener-路径，典型总长132字节，超过Linux AF_UNIX路径上限。DINOv2/DINOv3原检查都成功，不涉及模型或依赖坏掉。[Linux说明](https://man7.org/linux/man-pages/man7/unix.7.html)、[Python临时目录规则](https://docs.python.org/3.11/library/tempfile.html)、[实际multiprocessing调用](https://github.com/python/cpython/blob/3.11/Lib/multiprocessing/connection.py)。

用户已确认旧wrapper2426676、DINOv2训练2426731、DINOv3训练2426732仍活着，子进程共同父PID2426713。未列出两模型progress.json、train_complete.json或head_2000.pth；未观察到成功更新，不能宣称精确零更新。异常ps ELAPSED数值不用于计算耗时。原父控制器只等待子进程退出，而取数没有超时，线程失败可让它持续等待。

## 变更范围

科学源仍c22a046407daf42064cbb161429f2648c9b86d66；新单文件post_m2_a0_ipcfix_20261030.py是独立执行补丁。科学函数（数据/采样/特征/损失/训练/评价/screen）AST与原版相同，原文件字节未改。修改仅为新输出目录、短TMPDIR/TEMP/TMP及tempfile缓存、30秒取数超时、每阶段600秒保护和自身子进程组清理、执行补丁来源字段。新dict回执同时保存原科学commit与实际execution_patch_commit，不把补丁冒充原运行字节。

新run为ROOT/records/post_m2_a0_ipcfix_20261030，ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro；临时目录为/home/jovyan/zzx/tmp/a0_ipc。日志/代码/权重缓存仍在ROOT内；典型socket59字节。原两份profile逐字节复用，不改原code_commit、不做新smoke/profile；新入口禁止smoke/profile命令。每模型仍2k/seed42、原micro/worker配置、原gate与开发折；不重下数据/模型、不装包，不新增GPU探针或优化预算。

## 用户执行流程

从发布回执的固定代码提交下载repair_post_m2_a0_ipc_20261030.py与post_m2_a0_ipcfix_20261030.py到同一工具目录。先调用prepare，再由用户显式调用start；prepare本身不训练，也不自动重试。

prepare只在原错误仍能从两份日志读到时处理。它读取小进度/端点与原日志，核对已知PID的准确脚本、kind和stdout，再沿父子关系记录本任务后代，按/proc start_ticks防止PID重用，只停止这批已核实身份的故障进程。它不按名称杀进程，不对未知PGID或GPU进程操作。原记录不移动/删除。若发现任何已记录成功更新、轨迹或端点，会保存证据并阻止重放，而不是清空目录重新训练。

无旧正式进度时，prepare验证一次真正AF_UNIX Listener和一个CPU TensorDataset batch的跨进程FD共享，记录地址字节数和原始stderr；不用CUDA、不构造模型、不产生optimizer更新。检查失败就止于准备阶段，保留原栈。只有repair_ready.json完成且未被阻断，start才能显式派发。它还检查原拥有进程是否确已退出、已有Full控制器是否活跃，并由原pair设备门槛确认GPU0/1空闲，不占2–7卡。

start派发独立后台入口，stdin=/dev/null，日志新run/repair_continuation.log。自动阶段为配对训练→配对校准→screen→仅阳性进入外层开发评价。失败即停，无自动重试或人工阶段等待；保留两个头、轨迹、整数矩阵、screen、父/子日志及准备/停止/IPC回执。准备/派发输出不能代替正式首更。新回执仍须用户回传GitHub。

## 后续路线与验证

Full尚未安装的新载荷也改用/home/jovyan/zzx/tmp/pm2_短标识，真实CLI和子进程均接入，DataLoader等待30秒；已安装或运行的旧快照不改。Full新路径仍每条1预热+3计时，七路径28丢弃更新；空间头共8，不扩预算。

原A0新run完成后，空间头调用前显式设置POST_M2_A0_RECORDS为新run路径；代码验证repair_ready原科学源并将该run写入阶段回执，不拷贝新结果覆盖旧失败目录。原A0完成依赖、原线性外层gate、空间头独立gate均保留，G/Q/S不依赖A0阳性。

本地9项针对性检查通过（科学AST、取数超时、来源字段、精确归属、PID重用/僵尸保护、partial阻止重放、短路径实际env接入、空间头显式run绑定），原14项CPU检查也通过；实际完整下载载荷独立导入/manifest核验通过。Windows检查不替代Linux/proc停进程、实际CPU IPC、CUDA首更；本次不再开模型测速来补文档。
