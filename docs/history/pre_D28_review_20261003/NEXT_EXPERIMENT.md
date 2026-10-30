# D30正常运行：继续只读查询，D28结果可上传

## 最新实际存活检查：2026-10-03 20:56:13

用户只读查询确认D30控制器2349619 LIVE=True，两个重放worker存活，ACTIVE_RUNNING。queue最后观测20:56:08.886753+08:00；replay_G0 GPU0 6/24、replay_G1 GPU1 6/24，共12/48（25%），uniform模式已完成，expert0开始。四训练P/R/PR_area/PR_pixel仍PENDING，这是设计的重放阶段屏障。查询已正常，无新技术错误，不重复启动。

D28现在有直接状态观测：COMPLETE、controller.lock free；其state最后观测2026-10-03T19:27:53.313658+08:00。科学结果仍待上传/读取，不能从队列完成推出研究gate通过。以上是最后收到的状态，不宣称实时存活。[本次观测](../../records/research_d30_loss_decomposition_20261003T205144_2349167/progress_observation_20261003T205613.json)。


## D30最新服务器观测：2026-10-03 20:52

用户已执行nohup启动，控制器PID2349619，CPU检查PASS；GPU0 replay_G0 PID2349792、GPU1 replay_G1 PID2349798已开始uniform固定混合评价。最后worker观测20:52:55.972803+08:00。D30已经完成自动接力并进入重放，四组新训练尚未观测开始；不是仍待启动，也不需要重复启动。当前时刻存活情况须用只读查询确认。

运行目录：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d30_loss_decomposition_20261003T205144_2349167。按冻结控制器执行链，开始worker表示D28终态、summary、锁释放与残留worker检查已通过；D28完整科学结果仍未读取，不能据此判断现象/gate。查询报错源于启动括号内cd不保留，当前shell在jovyan、相对plan路径不存在；错误只影响查询，不影响后台作业。查询改用绝对plan路径。[启动原件](../../records/research_d30_loss_decomposition_20261003T205144_2349167/startup_observation.json)。


## 当前可执行查询（不依赖当前目录）

```bash
D30_DIR=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d30_loss_decomposition_20261003T205144_2349167
D30_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$D30_PY" -B "$D30_DIR/code/scripts/check_rebuild_v1_d30_handover.py" --directory "$D30_DIR"
"$D30_PY" -B "$D30_DIR/code/scripts/status_rebuild_v1_d30.py" --directory "$D30_DIR"
tail -n 15 "$D30_DIR/nohup.log"
```

ACTIVE_RUNNING表示控制器在运行。先48次checkpoint重放，再GPU0 P→PR_area、GPU1 R→PR_pixel；共32000训练更新，物理batch16无累积。日志done按整种混合模式结束后每6次递增，单个tile已完成但done=0不表示停滞；结合tile/condition/windows和observed_at判断。

完成后上传：

```bash
"$D30_PY" -B "$D30_DIR/code/scripts/upload_rebuild_v1_d30_records.py" \\
  --root /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro --directory "$D30_DIR"
```

D28原件也需上传，才能分析相关失效结果：

```bash
D28_DIR=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d28_pressure_20261003T092243758628_2001983
"$D30_PY" -B "$D28_DIR/code/scripts/upload_rebuild_v1_d28_records.py" \\
  --root /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro --directory "$D28_DIR"
```

仅GPU0/1 H10080GB；RAM/磁盘充足；nohup，快照/缓存/临时/日志在zzx对应目录。无资源探针，Test6禁读，原D29未激活，D27四gate失败保留。旧启动命令已[归档](../history/D30_before_startup_observation_20261003/NEXT_EXPERIMENT.md)，不要重复执行。[设计](../protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)。
