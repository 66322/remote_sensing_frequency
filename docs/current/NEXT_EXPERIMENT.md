# 下一步：只读查询已接管的N2队列

最后服务器接管回报（用户终端）：2026-10-05，修复目录时间标记09:17:55（不是queue observed_at或精确训练进度时间）。修复控制器PID3467202已登记，目录controller_repair_20261005T091755_3467074；日志出现POST_AB_ADOPT 0 N2-0 3457210，确认接管原GPU0 worker，没有重启N2-0。ACCEPT_COMPLETE=[]，没有新增完成回报。安装器启动前恢复CPU检查已通过（按登记前执行链推断，未收单独测试日志）；本次只收到控制器日志首条ADOPT，尚未收到后续状态、N2-0实际训练步数或N2-1启动记录，不声称两卡训练已确认。原科学快照86b6a70e5c3482314986fb1259e2fccbd0a5a38b与修复9b196a204e6a45cb54244b4deb5437ff44bd074e分开保留。下一步只读查询状态/进度/日志，不重复登记或再次运行修复。

执行下面查询，回传状态和日志，确认新控制器存活、原N2-0真实progress、原CPU检查后是否进入RUNNING_N2，以及GPU1 N2-1是否派发。无需再次fetch/登记/运行安装器，也不重训N2-0。

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
