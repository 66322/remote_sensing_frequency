# 下一步：一次启动D27修复补跑与D28自动后接

2026-10-03用户明确要求“一起实现”：D27修复补跑与D28自动后接已实现并完成23项CPU行为检查（D27 15项、D28 8项），新增代码通过Python3.10语法检查。**尚无本次服务器启动观测，不能写成已运行或已经排队。**

目的：D27兑现原10组安全/专家/局部类别研究投入；D28检验同边际、共同失效是否使收益失效。预算80k原授权更新+238次Val2 tile评价，GPU0/1 H10080GB；内存/磁盘充足，无资源探针。缺必需checkpoint、clean无法重现或技术错误明确失败，保留记录；Test6禁读。D26不重跑，D29未排队。

执行一次：

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

保存LINK_DIRECTORY。bootstrap需生成linked_execution.json，里面才是两阶段真正路径。此命令为待执行，当前不声称已运行。若已有repair控制器在跑，入口拒绝重复；检查现有目录，勿反复新建队列。

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
