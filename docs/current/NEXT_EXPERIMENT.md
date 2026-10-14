# 下一步：查询已登记的Phase2.4新目录（2026-10-14）

**REGISTERED_LAUNCH_OBSERVED_AWAITING_STATUS**。新目录research_phase24_protected_20261014T193915_2149100、执行5a84f0ea、PID2149894。用户REGISTERED输出证明全部26 Linux CPU测试通过无skip并已创建控制器；真实CUDA/原CM桥接与此后存活状态仍待查询。[登记记录](../../records/phase24_registration_20261014/observation_193920.json)。

用户只读执行：
```bash
D=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase24_protected_20261014T193915_2149100
PY=/home/jovyan/miniconda3/envs/d18_dino/bin/python
"$PY" -B "$D/code/scripts/status_phase24.py" --directory "$D"
tail -n 60 "$D/nohup_20261014T193920570637.log"
```

不再登记、重复替换或重启controller；185408_2127460原失败目录保留但不是当前进度。若状态显示准备/双卡smoke，等待其通过后自动继续；若technical hold，读取对应错误原件，保留现场，不自动重跑。

随后接收新最后观测、GPU/CPU吞吐与实际阶段，再估计结束时间。核心T0一项、条件T1/T2/T3按门禁，最多4头32k，0专家/seed，GPU0/1≥24h可续无硬截止。无Test6/held4/final、SSH或整轮大cache。完成且进程退出后再用户显式upload_phase24.py、轻量归档回读。[执行](../protocols/PHASE_24_EXECUTION_20261014.md)、[门禁](../protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)、[登记前下一步](../history/20261014_before_phase24_registration/NEXT_EXPERIMENT.md)。
