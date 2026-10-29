# 当前交接：M2完成、DF未获支持，结果归档与存储清理（2026-10-29）

## 已完成与最后观测

最后服务器观测2026-10-29 10:29:51+08:00。M2于08:43 COMPLETE_SERVER_CHECKED，108/108训练、77,868/77,868案例，错误/失败为空。G0/H2/G3通过，G1/G2/G4未过；反向及第二编码器扩展未启动。[结论与主表](../experiments/PHASE3_M2_ACCEPTANCE_AND_CLOSEOUT_20261029.md)、[原始终端与提取结果](../../records/phase3_m2_closeout_terminal_20261029/)。

DF补救相对D0平均+0.276pp、相对DSelf+0.079pp，未稳定超过打乱/熵控制；主融合差平均-0.001261pp，近乎不变；异seed换配0/6正。当前错误对应性加权配方不具备继续扩展依据，不能扩大为所有RGB–DSM问题失败。H2仅为相对DClean局部证据，保护通过不代表有效纠错。主线角色不因这项阴性自动改为地图维护；地图仍是未实施的独立候选。

旧队列自动进入J后，08:47:55的J_F0_s42_J2因CUDA交叉熵与严格确定性不兼容失败，combined STOPPED_NO_AUTOMATIC_RETRY。J无科学结论；R/T/V未顺序派发。10:29两卡0MiB、无计算进程。没有修复、重启或放宽确定性，不能把旧bootstrap当接续入口。

## 本轮明确授权与实际交付

用户要求整理并上传轻量实验证据、写结论与交接、统计本次数据大小并开始清理无用权重/中间大文件；又要求上传不必反复哈希，上传后查看即可。本机连接同步终端证据和结果摘要；完整服务器publication尚未直接接收。原上传器缺现成认证，不索取/打印Token。

清理入口及[协议](../protocols/PHASE3_M2_STORAGE_CLEANUP_20261029.md)已准备：只统计登记M2/combined及登记旧失败目录；先导出证据，再删除明确候选。保留18个R/D0端点及全部计数、配置/轨迹/失败材料、原始数据和预训练；候选最多90个教师/已关闭DSM端点、残余成功恢复文件和具名临时/编译缓存。每项删除有清单和大小回执，不重复重哈希。

**唯一下一步：用户在原服务器执行固定发布版本的存储统计/导出/清理命令，回传cleanup_result与轻量包位置/大小。** 当前没有服务器执行回执，不能说实际已释放空间或已删除权重。收到后更新本交接与共享记录，并通过本机连接补齐可上传的原始轻量统计。

## 固定路径与接续边界

ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro。
M2=records/research_phase3_m2_revision_20261024T092814_2738345；
combined=records/research_phase3_combined_revision_20261024T092814_2738345。
科学源M2 ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd；合并e65c6cb0830985461b3cd30e2f43158dd3d858cb；工程修订752d3835a18a15a04d83b1dcc1841bff98bf0b07、25b124a0cf69ececb6841b55ed90b19fae5b9a08。

服务器由用户执行，无SSH。新对话不重启/重复审计训练。以后若研究J须单独盘点已产生作业与必要兼容修订，不能自动执行原42项或整条228项。新路线仍按分批方案而非一次铺满；Test6/held4/final封存。清理后引用新增retention回执，不改写原始验收。旧交接[存档](../history/HANDOFF_20261029_BEFORE_M2_CLOSEOUT.md)。
