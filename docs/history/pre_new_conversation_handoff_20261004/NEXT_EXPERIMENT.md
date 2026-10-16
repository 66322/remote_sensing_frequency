# 下一步：修复汇总导入路径，保留六项A并接续B/C

历史运行观测：D30在2026-10-04T00:47:08.030508+08:00为COMPLETE，六项全部完成。Post-D30在2026-10-04T06:04:04.397991+08:00为COMPLETE_WITH_TECHNICAL_FAILURES；原控制器2450552已退出（Z、LIVE=False），无活跃worker。A0—A5均训练至8000步，均因评价条件`dsm_present_zero`未被处理而失败；0/18正式完成，B/C未启动，F仍待条件。不能据此评价A机制效果。原执行commit为01ec8dee82f7e272f6a650aaf9f3e619a0e7c516，原目录为`research_post_d30_mechanisms_20261004T000812_2446364`。该失败观测为06:04历史状态；08:41六项A完整完成，随后阶段汇总导入错误令控制器停止，第二次恢复待执行。

恢复在同一目录建立独立、带SHA清单的评价补丁快照，原plan和code快照保持不变。补丁按D27原语义支持present_zero及present_shift_half：DSM虽坏，但两侧可用性mask仍为True，不把未知坏数据当已知缺失。A必须加载8000步保存状态，新增优化器更新数为0，补评价前后核对selected/step8000权重SHA；相同checkpoint的已有评价可校验后复用。补齐A后仍按A→B→C→条件F；F仅由固定B3全部gate通过触发，不新增多seed、D29或新模块。

最新服务器观测2026-10-04T08:41:43.586227+08:00：队列CONTROLLER_INTERRUPTED，控制器2698383 LIVE=False；A0—A5已全部COMPLETE（分别08:22/08:31/08:41），6/18主体完成，B/C全PENDING、F待门槛，无活跃worker。A评价恢复已成功且未重训；阶段A汇总子进程抛出ModuleNotFoundError: No module named 'model'，随后控制器退出。这是脚本搜索路径缺失：cwd=code不自动把code加入独立脚本的sys.path。导入路径修复已本地实现并通过6项回归（含实际汇总子进程--help）；尚无服务器第二次恢复启动观测。恢复在同目录建立新覆盖快照，保留原plan/code及A完成标记，不重跑A，重新生成A阶段汇总后接B/C，仅GPU0/1。

目的与资源：在GPU0/1补齐A评价，随后完成剩余12项主体训练。停止条件：未知错误、原快照/权重绑定改变或已有活跃控制器时退出，保留旧结果。仅做数秒接口检查，不做资源/预算测量。恢复完成前不承诺结束时间，评价-only A的短耗时不能外推B/C训练。

A0/A1新日志已确认越过原故障点；当前按下方状态脚本查询完成数即可，不需重复恢复。下面恢复指令已于08:12执行，仅留作追溯，不再执行。当前只使用下方查询指令（原执行commit仍保留01ec8de）：

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


D30分析更新：六组selected汇总已整理；面积缩放PR_area对S1提高1.730941pp，但仍低于S0 0.064718pp，PR_pixel仍低于S0 1.291674pp，四项新配方continue均False。静态保护/恢复取舍明确，归一化缓解下降但未形成增量；固定checkpoint重放及loss/梯度原件尚未上传，不宣称唯一根因。[完成阶段分析](../experiments/D30_COMPLETED_REVIEW_20261004.md)。原Post-D30队列与gate保持不变。

D30紧凑结果上传（只读D30原件并写GitHub，不调用GPU、不影响当前恢复队列；执行后回传D30_SUMMARY_COMMIT即可）：

```bash
(
set -e
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
git fetch origin rebuild-v1-protocol-20260915
SUMMARY_COMMIT=$(git rev-parse FETCH_HEAD)
D30_DIR="$PWD/records/research_d30_loss_decomposition_20261003T205144_2349167"
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
SUMMARY_SCRIPT="$D30_DIR/upload_summary_$(date +%Y%m%dT%H%M%S)_$$.py"
git show "$SUMMARY_COMMIT":scripts/upload_rebuild_v1_d30_summary.py > "$SUMMARY_SCRIPT"
"$EXP_PY" -B "$SUMMARY_SCRIPT" --root "$PWD" --directory "$D30_DIR"
)
```

此次只上传紧凑分析证据，未上传完整逐tile矩阵；原矩阵全面重算仍待后续归档。


D30原生紧凑证据已于214eb158a59cf8248910ba5e46492189d3a6f953上传，156文件、1134456字节；screen_result已回读。P仅综合门槛失败，最差tile/condition−0.076827pp；PR_area还存在最差−0.298852pp及fixed8000对S0−0.067831pp，不能称完全恢复安全性。PR_pixel仅DSM正确保留65.7654%、仅RGB正确90.1002%，QD伤害3.0660%，仍是明显信息取舍。完整逐tile原矩阵本体未上传，梯度原件已上传但尚未完成综合分析。


当前立即操作：下面第二次恢复执行一次；先拒绝活跃重复控制器，保留A完成标记，重新汇总后接B/C。补丁来源记录含实际PYTHONPATH，只修工程入口，不重跑实验、不重审资源。

```bash
(
set -e
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
git fetch origin rebuild-v1-protocol-20260915
FIX_COMMIT=$(git rev-parse FETCH_HEAD)
POST_DIR="$PWD/records/research_post_d30_mechanisms_20261004T000812_2446364"
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
STAMP=$(date +%Y%m%dT%H%M%S)_$$
FIX_SCRIPT="$POST_DIR/recover_summary_$STAMP.py"
FIX_LOG="$POST_DIR/nohup_summary_repair_$STAMP.log"
git show "$FIX_COMMIT":scripts/recover_post_d30.py > "$FIX_SCRIPT"
nohup "$EXP_PY" -u -B "$FIX_SCRIPT" --root "$PWD" --directory "$POST_DIR" --commit "$FIX_COMMIT" > "$FIX_LOG" 2>&1 < /dev/null &
FIX_PID=$!
printf '%s\n' "$FIX_PID" > "$POST_DIR/summary_recovery_$STAMP.pid"
printf 'REPAIR_PID=%s\nREPAIR_LOG=%s\n' "$FIX_PID" "$FIX_LOG"
sleep 5
tail -n 20 "$FIX_LOG"
)
```

预期先打印PORTFOLIO_SUMMARY_IMPORT_PASS/PORTFOLIO_REPAIR_CHECKS_PASS，再PORTFOLIO_SCREEN 6，随后GPU0 B1/GPU1 B2。阶段汇总读已有结果可能需要一些时间。修复回归6项、原机制10项（此前）通过；服务器启动时校验实际immutable汇总入口，不只本地测试。
