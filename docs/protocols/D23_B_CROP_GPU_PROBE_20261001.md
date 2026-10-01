# D23-B真实专家crop GPU短测

用户回传：dfa3456核心8项服务器CPU检查PASS，用时1.732秒，结束时钟未回传；A轻量tar.gz已在服务器生成，报告SHA041bc0ad79c3c5f11fdbf4a29479b2c3cf68d60f898b5125d8cf2211e59084b1，当前本地尚未收到或重新hash。见records/research_d23_a_compact_20261001/server_core_check_and_archive_observation.json。

新入口scripts/probe_rebuild_v1_d23_gate.py已实现，3项本地GPU准入/证据写保护检查PASS与语法检查通过，真实GPU尚未执行。短测scope为training-crop-only，不能称整图验收或正式训练预算锁。

目的：接入真实D21 R0/M0最终16000步专家，在训练tile2_12的16份固定512 crop上复现保存训练预测、核对128通道hook及缺失回退，测TSF gate两视图的反传、显存和吞吐。冻结专家；参数更新只作用于短测gate，退出即释放，不保存checkpoint。GT仅训练tile，Val2/Test6/独立final标签禁止加载。

准入：用户选择的一张已分配物理GPU；默认命令选GPU0，已有compute process、显存使用>1024MiB或利用率>5即拒绝，UUID绑定。不会等待或停止其他进程。核验DINO git commit/已跟踪源码洁净、原weights SHA、D21模型/配置/拆分SHA、两checkpoint原字节与签名、原PyTorch版本和训练probe重现；训练RGB/DSM/GT匹配原input_manifest SHA。只fetch并提取新文件，不更新冻结服务器工作副本。

资源：单GPU、单训练tile按需载入，microbatch2/4/8/16对应累积8/4/2/1，有效batch16；每组2步预热＋10步计时，共48次短测gate更新。使用干净视图和中央DSM缺失视图进行接口/反传测量，不据此声称覆盖正式增强流。每步先冻结专家前向取得全有效batch正/负分母，再重算各microbatch前向并按全局分母反传；测量包含这两遍计算，无跨步/全数据密集特征缓存。

GPU allocated保护32GiB、reserved40GiB，host峰值RSS保护8GiB，总时间30分钟；这些是预设停止阈值，不是已测峰值。脚本在步间检查，外部timeout负责时间上限；底层算子瞬时峰值仍可能触发OOM，保留failure.json作为技术失败，不扩展任务。未经实际短测不能承诺耗时；不从A的CPU计数时间估算B工时。

输出records/research_d23_b_crop_probe_<timestamp>_<pid>/，每micro JSON和summary.json/log。输出每组step_median_seconds、allocated/reserved峰值、RSS、两个训练视图的计数、绑定/复现记录。只完成crop资源探针：正式单一训练/整图评价入口、TCAP fit统计、14条件整图及拼接后回退、整图磁盘和RSS测量、wall/job cap仍待完成。不能据crop结果默认排32k正式更新。

## GPU授权补充

用户在本轮明确可使用物理GPU0和GPU1。本次相同crop探针在GPU0/1分别顺序执行，每卡4组共48短测更新、各30分钟保护，核对两卡UUID/显存/吞吐；尚未验证双卡并行整体RSS/I/O和整图工时，不能直接锁正式双卡预算。后续正式双卡队列在完成入口与资源测量后安排，无需再次询问同一GPU使用许可。

## 服务器目录约束

用户明确全部实验记录必须在zzx目录下，实验各自归档。D23-B本次入口、代码快照、GPU0/GPU1 JSON与日志全部在/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d23_b_crop_probe_<timestamp>_<pid>/，子目录code/model、code/scripts、gpu0、gpu1。输出路径resolve后验证zzx与项目records边界，输入DINO/权重/data根也验证zzx边界。后续命令不用/tmp放执行快照。A已有light_evidence归档保持A目录；历史已执行tmp脚本不自动整理、移动或删除。
