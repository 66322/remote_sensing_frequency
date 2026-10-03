# 下一步：执行一次D30后接启动命令

用户2026-10-03明确“按上述规划进行，随后加入已进行的队列后面”。D30已实现、执行授权已记录；**待用户服务器执行下面一次nohup命令，尚未收到D30 PID/队列观测，不能写成已在排队**。执行commit固定9db12dfb7ee85dff91dd6c246c7f161b60aca603。本地18项行为检查17通过、1项Linux文件锁检查跳过；服务器启动时自动执行全部18项CPU检查。未在本地或服务器启动训练。

目的：D27损失取舍的机制拆解；48次既有checkpoint诊断＋4组8000步，共32000新更新。仅GPU0/1 H10080GB，物理batch16无累积；RAM/磁盘充足，无资源探针；nohup，所有快照/缓存/临时/记录在zzx对应目录。预计D28交接后3.5—4.5小时。绑定缺失/变化、D28技术失败、组件检查失败停止，不访问Test6，不自动重试/新增作业。

下面只执行一次，现有D28保持运行。D30会自行等它结束；若D28已完成则完成交接检查后开始。

```bash
(
set -e
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
git fetch origin rebuild-v1-protocol-20260915

D30_COMMIT=9db12dfb7ee85dff91dd6c246c7f161b60aca603
D30_PY=$(python -c 'import json; print(json.load(open("records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
test -x "$D30_PY"
D30_DIR="$PWD/records/research_d30_loss_decomposition_$(date +%Y%m%dT%H%M%S)_$$"
mkdir "$D30_DIR"
git show "$D30_COMMIT":scripts/launch_rebuild_v1_d30.py > "$D30_DIR/launch.py"

nohup "$D30_PY" -u -B "$D30_DIR/launch.py" \
  --root "$PWD" --directory "$D30_DIR" --commit "$D30_COMMIT" \
  > "$D30_DIR/nohup.log" 2>&1 < /dev/null &
D30_PID=$!
printf '%s\n' "$D30_PID" > "$D30_DIR/controller.pid"
printf 'D30_PID=%s\nD30_DIRECTORY=%s\nD30_LOG=%s\n' \
  "$D30_PID" "$D30_DIR" "$D30_DIR/nohup.log"
sleep 5
tail -n 15 "$D30_DIR/nohup.log"
)
```

保存D30_DIRECTORY。启动最初可能VERIFYING_CPU，几秒钟CPU检查后WAITING_D28；不因GPU未占用而重复启动。源快照有几十个小文件；不重新测量显存/内存或数据预算。

随后只读查询（替换D30_DIR为实际输出）：

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D30_DIR=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/替换为启动输出的D30目录名
D30_PY=$(python -c 'import json; print(json.load(open("records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$D30_PY" -B "$D30_DIR/code/scripts/check_rebuild_v1_d30_handover.py" --directory "$D30_DIR"
"$D30_PY" -B "$D30_DIR/code/scripts/status_rebuild_v1_d30.py" --directory "$D30_DIR"
tail -n 15 "$D30_DIR/nohup.log"
```

ACTIVE_QUEUED_WAITING_PREDECESSOR＝D30控制器存活、无worker、等待D28；ACTIVE_INITIALIZING＝初始化/CPU检查/绑定正在处理；ACTIVE_RUNNING＝开始本组执行。HOLD或NEEDS_ATTENTION读取nohup尾日志，不能反复新建目录。D28仍运行时，新组GPU为空是正确排队状态。

完成后上传：

```bash
"$D30_PY" -B "$D30_DIR/code/scripts/upload_rebuild_v1_d30_records.py" --root "$PWD" --directory "$D30_DIR"
```

沿用D28现有查询/上传，不需要再上传已复核的D27完整包：

```bash
D28_DIR="$PWD/records/research_d28_pressure_20261003T092243758628_2001983"
"$D30_PY" -B "$D28_DIR/code/scripts/status_rebuild_v1_d28.py" --directory "$D28_DIR"
"$D30_PY" -B "$D28_DIR/code/scripts/upload_rebuild_v1_d28_records.py" --root "$PWD" --directory "$D28_DIR"
```

D28上传在技术完成后执行，GitHub为共享权威。原D29未激活；D27四gate失败保留。科学设计见[D30](../protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)，检查见[实现记录](../experiments/D30_IMPLEMENTATION_20261003.md)。
