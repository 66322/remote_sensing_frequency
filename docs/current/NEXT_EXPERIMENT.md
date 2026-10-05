# 下一步：继续两卡N2训练，按需只读查询

最后服务器观测（用户终端回传）：2026-10-05T09:21:05.606873+08:00，QUEUE=RUNNING_N2，修复控制器PID3467202 LIVE=True。GPU0 N2-0原worker PID3457210 LIVE=True，training 940/8000（progress观测09:20:52.566194，1.309439秒/训练步）；GPU1 N2-1新worker PID3467394 LIVE=True，training 60/8000（progress观测09:20:47.378619，1.347363秒/训练步）。N2-2—5 PENDING，两卡各一个worker；两组均已加载12/12训练tile。日志确认ADOPT原N2-0、CONDITIONS_PASS 32、HANDOVER READY COMPLETE和START N2-1，原N2 CPU8项复查PASS。接管后两卡实际训练已确认，未重训N2-0，暂无N2完成或精度结果。科学快照86b6a70e5c3482314986fb1259e2fccbd0a5a38b、修复9b196a204e6a45cb54244b4deb5437ff44bd074e与原plan保留。继续已有队列，只读观察，不重复登记或重启。

已确认RUNNING_N2、原N2-0训练940步及N2-1训练60步。继续当前队列；需要查看进度时执行下面只读查询并回传输出。无需再次fetch/登记/运行安装器，也不重训N2-0。

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
NEXT_DIR="$ROOT/records/research_post_ab_followup_n2_20261005T085829_3456726"
REPAIR_DIR="$NEXT_DIR/controller_repair_20261005T091755_3467074"
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$EXP_PY" -B "$REPAIR_DIR/scripts/status_post_ab.py" --directory "$NEXT_DIR"
tail -n 60 "$REPAIR_DIR/nohup_controller.log"
tail -n 20 "$NEXT_DIR/cpu_checks.log"
)
```

修复目录和日志：`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_n2_20261005T085829_3456726/controller_repair_20261005T091755_3467074/nohup_controller.log`。状态脚本会同时打印queue旧观测与worker当前存活/progress原件，二者时间口径不同。若CPU_VERIFYING，先以CPU日志说明是否仍在检查；若中断或HOLD，分析对应日志，不自动重启。若RUNNING_N2，继续既有六组两卡队列；不因本次只看到ADOPT就另开队列。

原故障08:58:59为null超时直接乘3600。修复按原协议8h处理，保留原plan/code_manifest/科学快照。原worker和后续workers继续执行原86b6代码；控制器单独9b196a2。只用GPU0/1，每卡一个worker，各8000步，batch16、seed42。8h包含训练与评价，超时或技术失败停止新派发、另卡已运行任务收尾，不自动重试。

N2完成后上传当前目录既有轻量记录并复算预设门槛。C/N1原件已验收，科学去留不变；N3/N4/N5仍待各自诊断和冻结协议，F/N6跳过不改，不访问Test6/independent final，不追加种子或扫参。主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复为旁支。详见[研究决定](RESEARCH_DECISION.md)、[C/N1验收](../experiments/POST_C_N1_RESULTS_20261005.md)、[控制器故障与修复](../experiments/POST_AB_N2_CONTROLLER_REPAIR_20261005.md)。
