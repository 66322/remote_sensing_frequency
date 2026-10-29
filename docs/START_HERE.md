# 共享入口：M2及存储清理完成，轻量包待接收（2026-10-29）

先读[研究决定](current/RESEARCH_DECISION.md)、[当前交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)；长期规则为[AGENTS](../AGENTS.md)和[执行约定](protocols/EXECUTION_CONTRACT.md)。

M2于08:43完整完成108训练/77,868评价，当前DF配方G1/G2/G4未获支持，不扩展B/C，不否定所有RGB–DSM问题。[科学结论与证据](experiments/PHASE3_M2_ACCEPTANCE_AND_CLOSEOUT_20261029.md)。

11:05:39用户回传清理COMPLETE：删除90端点、保留18个R/D0。目录分配量10.972GB降至2.954GB，减少8.018GB；扣除导出后估计净减7.985GB。全盘free字段没有变化，物理空闲增量未确认。[实际大小、清理与接收状态](experiments/PHASE3_M2_STORAGE_CLEANUP_RESULT_20261029.md)。

现成M2_light_evidence.tar.gz约29.86MB、422成员，仍在服务器。唯一剩余归档动作是下载到本机并用既有连接同步原始轻量统计；当前已上传终端提取结果、交接和清理摘要，不虚报压缩计数已接收。用户要求上传后查看关键内容即可，不反复哈希、不重复清理。

J在M2完成后因CUDA确定性兼容错误停止，未修复/重启，R/T/V未顺序派发。GPU最后观测10:29空闲。旧bootstrap/清理命令不再运行，原验收时108模型和清理后18模型状态分开记载。主线角色、未实施地图候选及封存split不变。
