# A0双骨干检查完成后的连续执行（2026-10-30）

> 2026-10-30新故障：原薄层入口TMPDIR过长，已确认AF_UNIX阻塞。旧命令仅保留历史，不再运行；当前接续按[独立IPC修复](POST_M2_A0_IPC_REPAIR_20261030.md)，原模型检查继续复用，旧记录/锁保留。修复目标执行尚待回执。

状态：TARGET_BOTH_MODEL_CHECKS_PASSED；FORMAL_TRAINING_PENDING。最后目标观测为2026-10-30 16:30:50.996411+08:00，来源为用户粘贴的完整终端JSON，未独立取得服务器原始文件。见[回执](../../records/post_m2_a0_capability_20261029/dino3_readiness_server_receipt_20261030.json)、[DINOv3 smoke](../../records/post_m2_a0_capability_20261029/smoke_dino3.json)、[DINOv3 profile](../../records/post_m2_a0_capability_20261029/profile_dino3.json)。

## 当前要做的事

在既有remote_sensing环境、GPU0/1空闲窗口连续完成原A0配对实验，回答同一512视野内冻结DINOv3表示能否被相同线性头读出更多任务信息。服务器仍由用户操作，无SSH；发布入口不代表已启动或产生正式更新。

[薄层脚本](../../scripts/continue_post_m2_a0_20261030.sh)只串接原c22脚本：pair train → pair calibration → screen → 阳性时pair outer → status。沿用原[科学合同与阈值](POST_M2_A0_EXECUTION_20261029.md)，原脚本逐字节不改，不新下载模型/安装依赖，不新增smoke/profile或种子，不自动开始A1/A2、空间头或Full队列。完整固定下载/后台启动命令见[发布回执](../../records/post_m2_a0_capability_20261029/continuation_publication_20261030.json)。

## 已具备的绑定与实际性能

- 原代码提交c22a046407daf42064cbb161429f2648c9b86d66；DINOv3源码6876159a11b4df116f30f667f8c9888617df0751，原生ViT-S/16 LVD权重已通过服务器首次SHA256，既有DINOv2源码/权重复用。
- Python3.11.13、Torch2.7.1+cu126、H100 80GB；同一ROOT内F0 6拟合/2内校准/4外层开发tile已通过盘点和真实加载。每阶段标签/图像只按原入口加载；不另解压/下载数据，封存集不开。
- DINOv2既有profile：4worker/micro16，10.93ms/步；DINOv3：8worker/micro16，14.36ms/步，其中中位取数等待0.109ms。两者有效batch16，评价batch16，CPU取数进程数按各自测量选择，不改变采样流。
- DINOv3首次图像/标签加载35.19秒，模型加载1.83秒，profile总43.74秒。日志file:///表示本地复制进Torch缓存。529窗口预测/拼接0.6641秒，不含完整输入加载及CPU指标统计；不能用该数承诺整个评价时长。
- 两模型各160丢弃profile更新已完成，不计正式训练。原A0正式预算仍为各2000更新、seed42、冻结骨干/384→6浅头/NB128监督。主Full/G/Q/S及新空间头必须使用各自的真实路径profile，不能借用这里的速度。
- profile显存为各候选累计高水位，不能作候选间独立峰值比较。40,000MiB启动空闲阈值是保护条件，不是实际显存需求。

## 连续执行、输出和停止

新入口先只读取已有两份profile及正式启动/失败记录，确认没有重复A0，读取已知Full pipeline的PID/启动回执及/proc命令，拒绝与正在准备或运行的Full控制器争卡；随后只查询物理GPU0/1当前占用。不是重新盘点/测速。若无资源，不注册新作业，不轮询或自动重试。

通过后原子创建ROOT/records/post_m2_a0_capability_20261029/formal_continuation_20261030.started，记录PID、登记时间和原执行commit；不删此记录绕过重复保护。GPU0跑DINOv2、GPU1跑DINOv3，原pair仍在每阶段实际派发前检查设备，两卡各一个模型进程。原pair任一子进程失败会停止另一子进程；薄层入口任何阶段失败即停止后续阶段，保留原栈与pair日志，不热改或重跑。

校准通过须同时满足训练轨迹下降、两者NB fg5 mIoU≥50%、DINOv3总体增益≥0.3pp及逐tile最差增益≥−0.2pp。仅READY_FOR_OUTER_DEVELOPMENT_EVALUATION进入外层4开发tile；INVALID_PROBE或NO_INCREMENT_STOP_A_ROUTE均不评价外层、不启动A1/A2。原screen字符串中的A_ROUTE只按现行规划约束A1/A2，不关闭独立G/Q/S或匹配空间读出。

两份head_2000.pth、train_started/train_complete、trajectory、校准/条件外层的原始整数矩阵与指标、screen及原pair日志均留同一A0目录；薄层完成后另写completed_at.txt。临时数组随原子进程结束释放，不新增磁盘logit缓存。小结果后续回传GitHub，薄层脚本本身不自动上传，不把输出已生成写成已归档。

新TORCH_HOME为ROOT/cache/torch；通过符号链接复用原公开权重，CUDA_CACHE_PATH/XDG_CACHE_HOME/TMPDIR也在ROOT内。已有/root缓存副本、原始数据、公开权重和旧结果均不删除。

## 本地检查边界

交付的单文件Bash入口经语法检查，以及6项轻量控制流测试（真实阶段用小替身，nvidia-smi边界模拟）：阳性进入outer、阴性/INVALID跳过outer、训练/校准首败停止、GPU忙不登记、重复不派发、profile提交不匹配不派发。未导入Torch或产生GPU探针。该检查不冒称目标Linux执行；目标原模型加载和真实测速依据上述服务器回执。目标薄层控制器和正式更新仍待回执，原Full代码4fbabd6b135a41c1ba0891120dcac6546880bf47不因本次元数据或薄层发布切换。
