# Phase2完成后产物退役
范围仅/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase2_matched_20261013T151120_1310582，代码scripts/cleanup_phase2_completed.py。
依据用户持续授权及[结果核验](../experiments/PHASE_2_RESULTS_20261014.md)。上传dc335e0d固定；archive SHA cc9ea1d202110ebd281e95550d962d13d6adc64a16e0804e833f5f515b38a5e7。
读80MB级archive，不重扫整个zzx、不读取全部大型数组或重跑实验。验证24,643份轻量原件SHA，当前counts/arrays/complete/analysis/summary与上传一致，322+3×1164案例完整且原CM有效、fallback exact。双重进程审计和原controller锁、固定绝对路径/无symlink、文件身份检查。
仅删除val_cache的npy、head_cache的npz、evaluation四固定系统案例arrays.json登记的7类npy；保留全部JSON/源码/配置/轨迹/日志、输入、权重、上传包、tail_rgb/tail_dsm坐标数组。每200项进度；按inode预计完整断链空间，实际空闲变化另记。元数据或证据变化停止，不自动重试。回执及artifact_retirement.json在本实验目录，说明旧array SHA绑定不再在线。
4项本地检查通过，真实服务器清理尚未执行。完成后用户回传SUMMARY/CLEANUP_COMPLETE与complete.json，再同步实际释放及最终保留；无需重复确认既有清理范围。
