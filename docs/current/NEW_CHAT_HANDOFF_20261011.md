# 新对话交接：Phase1.5核验完成，配对训练尚未启动（2026-10-13）

Phase1.5轻量原件已上传并独立核验，状态 LIGHT_EVIDENCE_VERIFIED / SCIENTIFIC_REVIEW_COMPLETE。上传提交9d7c27e88c510f2931ac125b7b6b3b0c60850dce，先前认证故障已恢复；不再重跑upload/enqueue/accelerate。最后服务器查询2026-10-13T11:35:58.181880+08:00，队列最后观测11:31:16.761032，完成、controller=False，GPU100/100、D160/160、E120/120；这不是实时查询。

完整2388载荷SHA/大小与原计数核验PASS，58160个CM、1090组bootstrap复算。原权重/数组本体仍在服务器，没有GPU重跑；Val2仅两张反复使用的影像，20mask不是20独立种子。原目录 /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase15_recoverability_20261012T233532_842792；推理45138f0f、CPU接管4842b5eb（63保留、97新完成，1595.46s）。

科学结论：五专家oracle−最佳固定R16=10.1103pp，但简单可靠性分箱偏好未跨tile稳定，routing gate尚未通过；旧RGB/DSM专家架构及训练历史不匹配。S1共同M5不变符合自身DSM回退，不能解释为恢复饱和。ECI1.0205不支持强边界集中。原Structured S1 PE仍CI跨0；Post-T R16−H16局部+0.348562pp，总gate仍5/6底线失败。

用户决定：研究主线RGB–DSM双向条件互补与退化/缺失分割；恢复旁支。允许GPU0/1、至少一天窗口且未完继续；服务器用户执行，无SSH。无Test6/held4/final，无自动失败配方重试或新增seed。采用大内存只读cache与受quota限制的CPU并行，当前冻结运行没有追加预加载。

助手新建议：先2个架构/初始化/fit12/预算一致的单模态专家，再条件性4个融合头，合计最多6训练/64k更新。此为配对可行性草案，**未实现、未登记、未启动、不是用户已确定的新路线**；不因oracle正结果自动转正式routing方法。先落地公共配置、参数/数据绑定和技术核验，再给运行命令。

下一步读[研究决定](RESEARCH_DECISION.md)、[完整结果](../experiments/PHASE_1_5_RESULTS_20261013.md)、[配对草案](../protocols/PAIRED_RELIABILITY_FEASIBILITY_20261013.md)与[复算回执](../../records/phase15_offline_audit_20261013/README.md)。当前不需用户再次上传同一份原件。上传多文件源于递归白名单保存逐case证据和完整源码快照；本次Git传输24.98MiB，文件数不等于大数据。后续建议精确JSONL打包与幂等上传，当前上传器尚未改造，历史原件保留。