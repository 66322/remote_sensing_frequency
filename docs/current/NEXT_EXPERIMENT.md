# 下一步：同目录恢复评价，接续B/C

最后服务器观测：D30在2026-10-04T00:47:08.030508+08:00为COMPLETE，六项全部完成。Post-D30在2026-10-04T06:04:04.397991+08:00为COMPLETE_WITH_TECHNICAL_FAILURES；原控制器2450552已退出（Z、LIVE=False），无活跃worker。A0—A5均训练至8000步，均因评价条件`dsm_present_zero`未被处理而失败；0/18正式完成，B/C未启动，F仍待条件。不能据此评价A机制效果。原执行commit为01ec8dee82f7e272f6a650aaf9f3e619a0e7c516，原目录为`research_post_d30_mechanisms_20261004T000812_2446364`。该失败观测为06:04历史状态；08:14已确认控制器及A0/A1 worker存活，新评价推进仍待worker日志核对。

恢复在同一目录建立独立、带SHA清单的评价补丁快照，原plan和code快照保持不变。补丁按D27原语义支持present_zero及present_shift_half：DSM虽坏，但两侧可用性mask仍为True，不把未知坏数据当已知缺失。A必须加载8000步保存状态，新增优化器更新数为0，补评价前后核对selected/step8000权重SHA；相同checkpoint的已有评价可校验后复用。补齐A后仍按A→B→C→条件F；F仅由固定B3全部gate通过触发，不新增多seed、D29或新模块。

最新服务器回传观测2026-10-04T08:14:26.221138+08:00：恢复队列RUNNING，控制器2698383 LIVE=True；A0分配GPU0、worker2698740存活，A1分配GPU1、worker2698743存活；0/18正式完成。A2—A5待补评价，B/C未开始，F待门槛。A0/A1的progress_at仍是02:31/02:32旧记录，当前控制器心跳和PID存活不等于新评价已推进；本次控制器日志没有新的报错，也没有PORTFOLIO_REPAIR_EVAL_ONLY或新评价进度。下一步只读worker日志确认权重读取/缓存校验/新评价或错误，不重启队列。

目的与资源：在GPU0/1补齐A评价，随后完成剩余12项主体训练。停止条件：未知错误、原快照/权重绑定改变或已有活跃控制器时退出，保留旧结果。仅做数秒接口检查，不做资源/预算测量。恢复完成前不承诺结束时间，评价-only A的短耗时不能外推B/C训练。

先查询A0/A1 worker的新日志；进度字段为旧时间时，不能据此判断新的阶段。下面恢复指令已于08:12执行，仅留作追溯，不再执行。当前只使用下方查询指令（原执行commit仍保留01ec8de）：

```bash
(
set -e
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
git fetch origin rebuild-v1-protocol-20260915
FIX_COMMIT=$(git rev-parse FETCH_HEAD)
POST_DIR="$PWD/records/research_post_d30_mechanisms_20261004T000812_2446364"
POST_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
STAMP=$(date +%Y%m%dT%H%M%S)_$$
FIX_SCRIPT="$POST_DIR/recover_evaluation_$STAMP.py"
FIX_LOG="$POST_DIR/nohup_repair_$STAMP.log"
git show "$FIX_COMMIT":scripts/recover_post_d30.py > "$FIX_SCRIPT"
nohup "$POST_PY" -u -B "$FIX_SCRIPT" --root "$PWD" --directory "$POST_DIR" --commit "$FIX_COMMIT" > "$FIX_LOG" 2>&1 < /dev/null &
FIX_PID=$!
printf '%s\n' "$FIX_PID" > "$POST_DIR/recovery_$STAMP.pid"
printf 'REPAIR_PID=%s\nREPAIR_LOG=%s\n' "$FIX_PID" "$FIX_LOG"
sleep 5
tail -n 20 "$FIX_LOG"
)
```

正常应出现`PORTFOLIO_REPAIR_CHECKS_PASS runtime_conditions=32`、`PORTFOLIO_STARTED 0 A0`/`1 A1`和worker日志`PORTFOLIO_REPAIR_EVAL_ONLY ... optimizer_updates=0`。训练代码/原快照不被覆盖。出现异常读取打印的REPAIR_LOG及对应worker日志，不重复新建队列。

查询修复后的进度（选已落盘manifest的最新修复快照）：

```bash
POST_DIR=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_d30_mechanisms_20261004T000812_2446364
POST_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
REPAIR_DIR=$(python -c 'from pathlib import Path; p=Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_d30_mechanisms_20261004T000812_2446364"); print(sorted(x.parent for x in p.glob("evaluation_repair_*/repair_manifest.json"))[-1])')
"$POST_PY" -B "$REPAIR_DIR/status_post_d30.py" --directory "$POST_DIR"
```

修复版状态脚本不会用A补评价耗时估计剩余训练。旧code/scripts/status_post_d30.py仍可读进度，但其ETA不适用于这次评价恢复。

收集结果时，从本分支提取更新后的scripts/upload_post_d30_records.py到本实验目录执行；它包含修复manifest/快照/日志与job补丁绑定，预测及权重只索引。D30另用其已有上传器上传完成原件，再离线重算全部矩阵，不需重训。

只使用物理GPU0/1，两张H10080GB，RAM与磁盘充足；seed42、8000步、物理batch16、无累积、nohup。快照/临时/缓存/日志均在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；不重复资源审计或预算探针。Test6及独立final禁止访问；重复开发Val2不等于独立泛化。GitHub本分支为共享权威，大预测/checkpoint保留服务器并索引。

[故障与恢复说明](../experiments/POST_D30_EVALUATION_REPAIR_20261004.md)、[原执行协议](../protocols/POST_D30_EXECUTION_20261003.md)、[机读设计](../../records/research_post_d30_design_20261003/plan.json)。
