# 合并队列登记回执：待确认M2运行阶段（2026-10-23）

证据级别：用户粘贴终端回执，副本见[原始片段](evidence/PHASE3_COMBINED_REGISTRATION_20261023.txt)。尚未接收队列实际queue_status.json、M2日志或训练轨迹，不称训练已开始或控制器目前仍存活。

## 本次已确认

- 用户沿用remote_sensing旧环境，已将Torch升级为2.2.2+cu121，torchvision0.17.2+cu121、torchaudio2.2.2+cu121；NumPy1.26.4。torch.cuda.is_available()为True，修复版COMBINED_RUNTIME_CHECK通过。新建环境是隔离选项，不是强制步骤。
- pip安装期间的SSL/代理重试最终成功，不是本次运行失败。依赖解析提示旧xformers0.0.23.post1要求Torch2.1.2，与当前版本不兼容；这是已知依赖冲突，是否影响DINO实际前向尚无日志证据，不能直接判定已失败。
- 使用e65c6cb0830985461b3cd30e2f43158dd3d858cb，combined inspect仍为空目录、catalog不存在。
- 启动日志 /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/phase3_combined_bootstrap_20261023T222041.log。
- 日志依次出现COMBINED_RUNTIME_CHECK、COMBINED_TARGET_CHECKS_PASSED 3、PUBLIC_CATALOG_STATUS ready=false/catalog absent、COMBINED_REGISTERED。
- 登记目录 /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_20261023T222112_2164225；目录登记时间2026-10-23 22:21:12+08:00，入口PID2164225，返回控制器PID2166328。
- shell显示入口进程Done，符合源码中派生独立控制器后正常退出；不能据此判定控制器退出，也不能据此证明控制器仍存活。

## 当前边界与下一步

三组目标检查通过，说明此前遗漏清单的打包故障已消除；这不是M2首个正式更新、实际模型CUDA梯度或科学实验验收。最后GPU0/1空闲证据仍为21:52:05，不能把22:21登记时间当成新的GPU利用率观测。

立刻只读检查已登记目录queue_status.json、m2_source.json、m2_bootstrap.log、nohup.log，控制器PID2166328当前存活，以及records下唯一M2目录的queue_status.json、registration_failure.json、target_checks.log与nohup.log。M2启动脚本可能仍在登记/输入准备，不能仅凭GPU暂未忙碌判断卡死。

不重复combined bootstrap登记、不单独再启动M2、不盲目改装xformers。若实际失败，先定位错误与是否已开始训练，再决定工程修复；不自动重跑失败科学作业。缺3DCD/P³数据在后段WAIT_PUBLIC_DATA，不阻止当前M2/J/R推进。

合并执行仍e65c6cb，M2仍ac325cd，最多228作业/5,088,000更新，科学门禁不改；RGB–DSM主线及独立新路线候选角色不变。
