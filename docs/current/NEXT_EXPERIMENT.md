# 下一步：查询已登记诊断后继，不再次启动

最后服务器观测（用户终端回传）：2026-10-05T13:14:31.018288+08:00，原N2 QUEUE=RUNNING_N2，修复控制器PID3467202 LIVE=True。该次登记输出未给六组step/COMPLETE计数，不从旧12:15完整进度推断当前作业状态。随后后继E0/E1/E2成功登记：目录records/research_post_n2_diagnostics_20261005T131434_3591073，返回控制器PID3591245、执行提交883fccc0b97714cfe0a87b54bfeb2a2fc09820d7。已收到登记标识，但尚无该控制器LIVE/WAITING_N2状态回报；待只读查询，不冒称E0或GPU评价已启动。

## 现在只读查询

登记已成功，前置CPU检查未阻止启动；cpu_checks.log原件尚未上传。原N2未被重启，新诊断新增训练0。控制器应按协议等待N2六组完成/原控制器及worker退出/两锁释放，再验收原件、CPU E0和GPU E1/E2；这描述预定行为，真实等待状态需下面输出确认。

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
DIAG_DIR="$ROOT/records/research_post_n2_diagnostics_20261005T131434_3591073"
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$EXP_PY" -B "$DIAG_DIR/code/scripts/status_post_n2_diagnostics.py" --directory "$DIAG_DIR"
tail -n 30 "$DIAG_DIR/nohup_20261005T131435243732.log"
)
```

预期等待状态WAITING_N2 + LIVE=True、E0/MASKS及五worker PENDING。若原队列已完成，可能转CPU_AUDIT_AND_E0或RUNNING_E1/E2；若HOLD/CONTROLLER_INTERRUPTED/LIVE=False，保留原目录和可能存活worker，先分析日志，不自动重启/重复登记。只查询，不需要再次fetch。

## 执行绑定与范围

执行提交883fccc0b97714cfe0a87b54bfeb2a2fc09820d7；日志位于上述目录nohup_20261005T131435243732.log。N2科学86b6、修复9b196a2及原worker保持。E0读取已有200个case；E1固定A0/B1×两方向×U/H/L×Val2共24新tile推理；E2固定N1-2/N2-0/N2-3，复用clean，新36次，共60新推理、0训练。只用GPU0/1，每卡一worker，nohup，全部产物zzx相应独立目录。

T预留规则不评价、Test6/independent final不加载。N5/N3/N4仅问题证据及完整族协议成立才另登记，gate只输出诊断问题，不自动训练。真实CUDA和耗时仍待首项回报。研究主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复旁支；不重训失败配方、不加seed。

## 完成后上传与分析

N2原件用其既有code/scripts/upload_post_ab_n2_records.py上传；本诊断n2_source_audit不是完整N2原件替代。诊断完成DIAGNOSTICS_COMPLETE_AWAITING_REVIEW后，在ROOT/DIAG_DIR/EXP_PY已按上述定义的终端调用：

```bash
"$EXP_PY" -u -B "$DIAG_DIR/code/scripts/upload_post_n2_diagnostics_records.py" --root "$ROOT" --directory "$DIAG_DIR"
```

记录无损轻量编码，大.npy/.npz/权重留服务器并保留SHA索引，凭据仅用户交互输入。收到GitHub原件后回读验证、分析N2去留和E0/E1/E2结果，再只落实一个证据充分的N5或N3研究族；N4仍等条件更新暴露证据。13组为条件上限，不自动全跑。

[执行协议](../protocols/POST_N2_DIAGNOSTICS_EXECUTION_20261005.md)；[本次登记证据](../../records/research_post_n2_diagnostics_20261005T131434_3591073/registration_observation.json)；[研究决定](RESEARCH_DECISION.md)。
