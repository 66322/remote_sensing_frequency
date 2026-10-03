# 下一步：D27已上传并复核，接收D28完成记录

## 最新原件复核：D27上传cedbc59，四项科学门槛均失败

D27完整轻量包已上传1017文件。已核对500份tile原件（selected主200、fixed8000主200、DSM局部60、全幅缺失40）和60份完成/验证/梯度/日志，逐文件SHA、63000矩阵与6000联合表复核一致，重算selected分数与screen差0。[完整报告](../experiments/D27_FINAL_REVIEW_20261003.md)与[离线重算](../../records/research_d27_review_20261003/recomputed_results.json)。不是再次训练，也未下载服务器预测/权重本体；其他诊断与大summary本体未全面遍历。

关键结果：保护/恢复selected降低1.77—1.89pp，fixed8000也降低1.78—1.85pp，两tile均下降。G1仅DSM正确保留37.67%→57.65%，仅RGB正确95.87%→91.63%；QD融合伤害1.35%→2.62%。G1同一双模态残差专家平均权重99.48%，族间变化不足，非“仅使用DSM”或零梯度证据。known missing工程回退维持。原四科学gate false，关闭本轮安全配方/动态/局部/类别确认路径，不扩大为研究问题失败，不追加原失败候选训练或改门槛。

protect/recover分项loss与分项梯度没有日志，不能证明唯一根因；分区归一化与类别平衡的收益取舍仅机制解释假设。D28保持预先指定七模型继续，最后观测仍18:34 RUNNING、0/7，未收到后续状态；D29原2×2前提未满足，不自动启动。下一步接收D28完成原件，按同边际故障现象判断保留问题/换解法/停止。[D27源包](https://github.com/66322/remote_sensing_frequency/tree/cedbc594d4e438d3c220ee80d3e82f563a8c2ae3/records/research_d27_safe_routing_repair_20261003T092243758628_2001983/evidence_20261003T184023096720_2284806)。

## 最新服务器启动观测：2026-10-03 09:22（目录时间）

用户已执行ba7088e联合入口。bootstrap输出确认D27控制器PID2001987、D28控制器PID2002037均已启动，并生成linked_execution.json。D27目录`research_d27_safe_routing_repair_20261003T092243758628_2001983`；D28目录`research_d28_pressure_20261003T092243758628_2001983`；联合目录`research_d27_d28_linked_20261003T092243_1955790`，均在既定工程records下。此为最后收到的启动观测，不代表当前进程仍存活。

当前确认级别仅“两个控制器启动且联合索引生成”；D27首步/worker GPU绑定、D28实际WAITING_D27状态及后续接力尚需queue_status与控制器日志确认。不要重执行联合启动命令。下一步只读查询现有目录；原GPU0/1、nohup/zzx、预算、loss、科学门槛和D29条件规则不变。[启动原件](../../records/research_d27_d28_linked_20261003T092243_1955790/startup_observation.json)。


2026-10-03用户明确要求“一起实现”：D27修复补跑与D28自动后接已实现并完成23项CPU行为检查（D27 15项、D28 8项），新增代码通过Python3.10语法检查。**已收到本次两个控制器启动输出，训练首步与D28等待状态尚待核对。**

目的：D27兑现原10组安全/专家/局部类别研究投入；D28检验同边际、共同失效是否使收益失效。预算80k原授权更新+238次Val2 tile评价，GPU0/1 H10080GB；内存/磁盘充足，无资源探针。缺必需checkpoint、clean无法重现或技术错误明确失败，保留记录；Test6禁读。D26不重跑，D29未排队。

以下启动命令已于本次执行，保留作为执行记录；不要再次启动：

```bash
(
set -e
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
git fetch origin rebuild-v1-protocol-20260915
LINK_COMMIT=$(git rev-parse FETCH_HEAD)
LINK_PY=$(python -c 'import json; print(json.load(open("records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
test -x "$LINK_PY"
LINK_DIR="$PWD/records/research_d27_d28_linked_$(date +%Y%m%dT%H%M%S)_$$"
mkdir "$LINK_DIR"
git show "$LINK_COMMIT":scripts/launch_rebuild_v1_d27_d28.py > "$LINK_DIR/launch.py"
nohup "$LINK_PY" -u -B "$LINK_DIR/launch.py" \
  --root "$PWD" --directory "$LINK_DIR" --commit "$LINK_COMMIT" \
  > "$LINK_DIR/nohup.log" 2>&1 < /dev/null &
LINK_PID=$!
printf '%s\n' "$LINK_PID" > "$LINK_DIR/controller.pid"
printf 'LINK_PID=%s\nLINK_DIRECTORY=%s\nLINK_LOG=%s\n' "$LINK_PID" "$LINK_DIR" "$LINK_DIR/nohup.log"
)
```

保存LINK_DIRECTORY。bootstrap需生成linked_execution.json，里面才是两阶段真正路径。已收到该命令两个控制器启动输出，尚未核对训练首步与等待状态。若已有repair控制器在跑，入口拒绝重复；检查现有目录，勿反复新建队列。

启动后查询（将首行替换为输出的实际LINK_DIRECTORY）：

```bash
LINK_DIR=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d27_d28_linked_实际时间_PID
LINK_PY=$(python -c 'import json; print(json.load(open("records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
cat "$LINK_DIR/linked_execution.json"
tail -n 20 "$LINK_DIR/nohup.log"
D27_DIR=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["D27"])' "$LINK_DIR/linked_execution.json")
D28_DIR=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["D28"])' "$LINK_DIR/linked_execution.json")
"$LINK_PY" -B "$D27_DIR/code/scripts/status_rebuild_v1_d27.py" --directory "$D27_DIR"
"$LINK_PY" -B "$D28_DIR/code/scripts/status_rebuild_v1_d28.py" --directory "$D28_DIR"
tail -n 10 "$D27_DIR/nohup.log"
tail -n 10 "$D28_DIR/nohup.log"
```

D28等待期间status脚本已在快照，无需等依赖复制。D27完成后D28须同时核验十组终态和controller.lock释放；缺S1/G0/G1/L1任一所需checkpoint写WAITING_EVIDENCE，不替换。非终态控制器死亡写PREDECESSOR_CONTROLLER_STOPPED。锁竞争检查无权杀掉其他任务。

两阶段结束后（沿用上面的变量）：

```bash
"$LINK_PY" -B "$D27_DIR/code/scripts/upload_rebuild_v1_d27_records.py" --root "$PWD" --directory "$D27_DIR"
"$LINK_PY" -B "$D28_DIR/code/scripts/upload_rebuild_v1_d28_records.py" --root "$PWD" --directory "$D28_DIR"
```

失败时也保留日志；D28启动绑定前失败尚无完整code_manifest，不能伪装为已完成轻量包。[实现与检查](../experiments/D27_D28_IMPLEMENTATION_20261003.md)、[冻结研究设计](../protocols/D27_D28_LINKED_RESEARCH_PLAN_20261003.md)。D29待两阶段结果后另冻结。


## 历史已执行：D27原件上传cedbc59（无需重复）

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D27_DIR="$PWD/records/research_d27_safe_routing_repair_20261003T092243758628_2001983"
RESULT_PY=$(python -c 'import json; print(json.load(open("records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$RESULT_PY" -B "$D27_DIR/code/scripts/upload_rebuild_v1_d27_records.py" --root "$PWD" --directory "$D27_DIR"
```

收到D27_GITHUB_COMMIT后从GitHub直接读取原件。无需粘贴长JSON，D28继续运行，完成后再上传其轻量包。
