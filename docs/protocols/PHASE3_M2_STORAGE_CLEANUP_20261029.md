# M2存储统计、轻量导出与已授权清理（2026-10-29）

状态：SERVER_CLEANUP_COMPLETE_FROM_TERMINAL_RECEIPT。2026-10-29 11:05:39已执行完成，实际大小与保留状态见[清理结果](../experiments/PHASE3_M2_STORAGE_CLEANUP_RESULT_20261029.md)。下文保留已交付实现合同，不再要求执行。来源是用户本轮明确清理授权；不再要求重复批准。用户另明确“没有必要每次哈希，上传后看一下就行”，因此不重复哈希权重、压缩计数或上传文件，已有哈希只作为来源字段引用。

## 范围和保留策略

入口[scripts/closeout_phase3_m2_storage.py](../../scripts/closeout_phase3_m2_storage.py)仅标准库、Python3.9+。从固定records下的一次登记回执绑定当前M2/combined及登记的旧失败目录，统计逻辑字节、实际分配字节、硬链接与最大文件。只处理这些具名目录，不遍历整个zzx、不碰其他论文或数据集。

保留：
- 9个RGB参考R和9个DSM D0端点，供后续必要的J诊断复用；所有J已产生端点保留。
- 全部逐mask/聚合充分计数、trajectory_counts、配置、来源绑定、训练轨迹、参数/完成回执、源码和失败记录。
- 原始数据、预训练、cache/torch、已准备输入与未知用途大文件。

候选删除：
- 36个交叉拟合教师端点；54个已关闭DSM方案端点，共最多90个。
- 当前M2成功作业残余last_resume.pth。
- 登记运行内部temporary及cache/cuda、cache/triton、cache/kernels中的普通文件。
- 多硬链接、符号链接及特殊文件不删除；未知大文件只进入大小清单，不根据“大”或扩展名盲删。

不递归删除目录，不删除原始数据、case_counts或all_aggregates；不修改冻结源码、原complete.json或原验收manifest。旧规则默认保留所有权重，此轮用户明确授权覆盖这一默认；新retirement由独立清理清单记录。历史验收表示当时完整，清理后不能把当前磁盘当作仍有108端点。

## 执行流程与停止条件

1. 要求M2 COMPLETE_SERVER_CHECKED，合并已停止/完成；检查/proc无引用登记运行的活进程，不停止任何进程。
2. 生成inventory_before.json；读取既有G0/summary/gates、绑定及manifest文件名/大小，复用已有SHA字符串，不重算大文件。
3. 生成逐文件cleanup_plan.json，记录角色、路径、大小、inode、mtime及已有端点SHA；初步打印总量和类别。
4. 直接把现成publication、各作业参数/完成回执、必要运行元数据和失败证据打包M2_light_evidence.tar.gz，不复制大权重；查看归档成员名和大小，不逐文件哈希。原充分计数继续留服务器。
5. 新代码在自建小哨兵文件上确认Linux定点unlink及拒绝路径/变更文件，再以目录边界、单硬链接、inode/大小/mtime匹配逐项删除；不读取整个文件计算SHA。
6. 删除明细写deletions.jsonl，随后inventory_after.json和cleanup_result.json记录运行目录大小变化、导出包占用及磁盘空闲前后观测。磁盘空闲变化可能受其他进程影响；目录分配差值和导出额外占用分别报告。
7. 完成回执使再次执行只显示ALREADY_CLEANED。若已有APPLYING但无COMPLETE，停止并要求读取原计划/明细，不能删锁或盲目重新清理。

默认不带--apply仅统计、准备计划和导出。用户已经授权本次清理，交付命令可直接--apply；统计/打包/检查先于删除，不添加确认交互。命令固定到发布提交，脚本在records独立位置，不能覆盖实验code快照。长任务默认nohup，日志和PID留records；无训练、模型导入、CUDA计算或新实验。

## 输出与上传

输出为records/m2_closeout_storage_<实际时间>_<PID>/：
inventory_before.json、cleanup_plan.json、M2_light_evidence.tar.gz、export_manifest.json、export_receipt.json、deletions.jsonl、inventory_after.json、cleanup_result.json。顶层另保存phase3_m2_storage_cleanup_20261029.json与执行锁。

此脚本不要求或写入Token，也不把打包完成冒称GitHub已接收。服务器当前无现成Git认证；先回传小型cleanup_result和大小摘要，完整轻量包可经现有本机连接同步。大于GitHub合适大小的原件继续保留服务器，仅上传索引；不人为切成大量碎片，不因上传失败重做计算。上传后回读summary/gates/交接即可，不重复全量哈希。

已收到现场COMPLETE回执：删除90个端点，保留18个R/D0。实际大小已单独记录；全盘free增量未确认。现成证据包仍待接收，不重复执行清理。

## 本地受影响检查

12项检查通过；Linux实际dir_fd删除检查在Windows跳过，目标服务器执行时仅用自建小哨兵确认。Python3.9语法检查通过。检查候选角色、18/90保留关系、归档成员、路径/进程/状态/大小/回执拒绝；没有训练或服务器清理。最终仅增加净空间记账字段，不改变清理判定。
