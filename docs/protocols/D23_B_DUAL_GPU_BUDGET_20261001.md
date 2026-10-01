# D23正式资源测量：双H100、12tile缓存与TCAP

更新2026-10-01。接续已通过的[工程原件验收](../experiments/D23_B_ENGINE_GITHUB_AUDIT_20261001.md)。本轮是预算测量，不是正式精度实验、不改变研究方向。用户GPU0/1已授权；用户在服务器执行，助手无直连。

## 测量内容

固定提交快照入口scripts/launch_rebuild_v1_d23_budget.py。先跑27项CPU检查，再同时启动物理GPU0/1两个budget worker。两卡均复用正式loader、规范化.npy磁盘缓存和mmap读取链，覆盖12个gate-fit tile（train16排除6_10/7_10/4_11/7_11），256个与正式TCAP相同key/round-robin/专家batch8统计样本；统计标记BUDGET_ONLY，不作为已运行正式统计。

每卡8组各16步，记录CPU样本物化/缓存读取加GPU步骤的完整耗时；专家固定8，gate16，两视图loss单次backward。使用相同keyed样本，八组和两卡公共源码/backend绑定一致。预算TSF整图评价使用该卡16步状态，训练tile2_12的6000×6000、14条件、6固定+TSF，并保存原计数及预测SHA。预算评价不读取Val2或test；不得把mIoU写成开发精度结果。

脚本对相同training tile进行两卡6固定×14条件预测SHA核对，避免设备差异混入后续正式比较。跨卡预测不同、覆盖不完整或绑定不一致时停止汇总并保留记录诊断，不自动改TF32/阈值。

## 预算与停止条件

预计约10–20分钟，实际时间由本轮确认；每worker从启动到guard上限1800秒，controller1850秒后停止进程组。CPU检查120秒超时。每worker主机RSS64GiB、GPUallocated32GiB/reserved40GiB、实验盘32GiB；这是本次有界测量限额，不是服务器容量上限。所有worker使用独立缓存/目录，避免写入争用，测量同时占用主机和两卡资源。运行开始要求两卡空闲、无既有compute任务；任一卡失败停止另一卡，保留全部日志和目录，不删产物。

缓存冷建立/输入SHA验证、已有mmap路径重开、统计、八组步骤与评价分别留记录。12tile缓存是每job独立的工程路径；后续正式默认同格式重建，不偷用预算目录缓存或权重。仅去掉前两步暖机后的p95用于步骤估算，不复用旧crop probe吞吐。

估计每job wall = 300秒 + 1.5 × [最慢卡缓存+统计 + 4000×两卡全部组最慢p95 + 4×最慢卡14条件整图评价合计]。评价4倍由两个Val2 tile×2倍计数/读取余量组成；NoBoundary计数与Val2实际读取未测，是工程估计而不是可靠的已验证上界。checkpoint保存和初始化以300秒及1.5系数预留；记录不足时扩大工程测量或预算，不自动批准正式训练。

summarize_rebuild_v1_d23_budget.py只输出BUDGET_MEASURED_REVIEW_REQUIRED；不生成FULL_ENGINE_RUNTIME_ADMITTED，不自动排8组4000步。助手从GitHub原件复核后才制定正式锁/队列。

## 目录和回传

所有文件在/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d23_b_budget_<timestamp>_<pid>，含launch_budget.py、code固定快照、execution_commit.txt、cpu_checks.log、gpu0/gpu1和各自日志。旧admission目录保持原状。

结束后自动生成紧凑JSON，脚本upload_rebuild_v1_d23_budget_records.py把execution_commit、CPU日志、两卡summary/preflight/cache_measurement/budget_fit_statistics/GPU日志以及compact_review共13份原文件和1份manifest上传同一GitHub分支。每文件5MiB、合计20MiB，仅提交明确文件，非强制推送；大型.npy/.pth缓存/预测/状态留服务器。上传工作树在本次对应实验目录。用户只回复D23_GITHUB_COMMIT，助手直接回读长记录。

本地27项CPU检查通过，追加预算覆盖/泄漏/两卡签名/资源计算失败检查；快照语法检查通过。实际DINO GPU budget流程尚未在服务器运行，不将模拟测试写成真实预算通过。
