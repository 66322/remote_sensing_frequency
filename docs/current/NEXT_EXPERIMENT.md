# 下一步：一次启动18＋4后接队列，并收齐D30原件

D30最新直接运行观测仍为2026-10-03T23:17:45.146029+08:00，控制器2349619存活，PR_area2860/8000、PR_pixel2420/8000；这不是实时状态。随后用户回传S0/S1/P/R的selected及fixed8000完成指标，未包含PR_area/PR_pixel、重放效果或原矩阵。新18＋4队列已实现并通过10项CPU检查，**尚无服务器启动、排队或存活观测**；必须执行下一步里的nohup指令后才可称排队。

执行下面一次即可。把FETCH_HEAD解析为不可变执行commit并保存到新目录；只在D30已完成且释放后使用GPU0/1。当前D30科学gate失败或成功都可执行独立新机制诊断，但技术失败会HOLD。

```bash
(
set -e
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
git fetch origin rebuild-v1-protocol-20260915
POST_COMMIT=$(git rev-parse FETCH_HEAD)
POST_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
test -x "$POST_PY"
POST_DIR="$PWD/records/research_post_d30_mechanisms_$(date +%Y%m%dT%H%M%S)_$$"
mkdir "$POST_DIR"
git show "$POST_COMMIT":scripts/launch_post_d30.py > "$POST_DIR/launch.py"
nohup "$POST_PY" -u -B "$POST_DIR/launch.py" \
  --root "$PWD" --directory "$POST_DIR" --commit "$POST_COMMIT" \
  > "$POST_DIR/nohup.log" 2>&1 < /dev/null &
POST_PID=$!
printf '%s\n' "$POST_PID" > "$POST_DIR/controller.pid"
printf 'POST_PID=%s\nPOST_DIRECTORY=%s\nPOST_LOG=%s\n' "$POST_PID" "$POST_DIR" "$POST_DIR/nohup.log"
sleep 5
tail -n 15 "$POST_DIR/nohup.log"
)
```

用启动打印的绝对POST_DIRECTORY查询，不依赖当前目录：

```bash
POST_DIR=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_d30_mechanisms_实际时间_PID
POST_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$POST_PY" -B "$POST_DIR/code/scripts/status_post_d30.py" --directory "$POST_DIR"
tail -n 20 "$POST_DIR/nohup.log"
```

WAITING_D30才是活跃等待，结合LIVE=True与最后观测时间；RUNNING A/B/C表示接力；F SKIPPED_GATE为预设条件未过，不是技术失败。控制器PID不活跃或TECHNICAL_FAILURE需读对应log，不能盲目再次创建队列。已完成真实组之后提供粗略ETA，等待D30不拿旧时间估算。

新结果按需上传：

```bash
"$POST_PY" -B "$POST_DIR/code/scripts/upload_post_d30_records.py" \
  --root /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro --directory "$POST_DIR"
```

D30原件仍用已有目录下upload_rebuild_v1_d30_records.py显式上传；科学读取四项部分分析→PR_area/PR_pixel→重放→逐tile/类→双向伤害与保留→固定8000→预设gate。无需重新训练S0/S1/P/R。

主体18组144000步，粗估17—25小时，C额外前向可能更慢；条件F另4—7小时，首批正常完成时间可修正，非结束承诺。只使用物理GPU0/1，两张H10080GB；RAM/磁盘充足，无资源探针。seed42、8000步、batch16无累积、nohup。快照、临时、缓存、日志全部在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；Test6与独立final禁读。重复开发Val2不是确认性泛化证据。GitHub本分支为共享权威，大预测/checkpoint本体留服务器并索引。

[四项结果分析](../experiments/D30_FOUR_ARM_REVIEW_20261003.md)、[执行协议](../protocols/POST_D30_EXECUTION_20261003.md)、[机读计划](../../records/research_post_d30_design_20261003/plan.json)。

[旧下一步](../history/pre_post_D30_execution_20261003/NEXT_EXPERIMENT.md)。
