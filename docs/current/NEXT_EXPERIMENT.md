# 下一步：D27接口修复后补跑原十组，D26不重跑

[D26完整判定/D27根因](../experiments/D26_COMPLETE_D27_FAILURE_REVIEW_20261003.md)。D27十组全部第一次objective失败，没有优化器更新，原科学预算/锚点/选模/gate不变。原授权涵盖必要技术修复；用新目录保留失败快照，禁止在旧目录跨commit resume。

执行一次（先fetch最新修复，解析并冻结该提交；所有产物在zzx新实验目录）：

```bash
(
set -e
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
git fetch origin rebuild-v1-protocol-20260915
D27_COMMIT=$(git rev-parse FETCH_HEAD)
D27_PY=$(python -c 'import json; print(json.load(open("records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
D27_DIR="$PWD/records/research_d27_safe_routing_repair_$(date +%Y%m%dT%H%M%S)_$$"
mkdir "$D27_DIR"
git show "$D27_COMMIT":scripts/launch_rebuild_v1_d27.py > "$D27_DIR/launch.py"
nohup "$D27_PY" -u -B "$D27_DIR/launch.py" \
  --root "$PWD" --directory "$D27_DIR" --commit "$D27_COMMIT" \
  --parent "$PWD/records/research_d26_bidirectional_20261002T191253_1513109" \
  > "$D27_DIR/nohup.log" 2>&1 < /dev/null &
D27_PID=$!
printf '%s\n' "$D27_PID" > "$D27_DIR/controller.pid"
printf 'D27_PID=%s\nD27_DIRECTORY=%s\nD27_LOG=%s\n' "$D27_PID" "$D27_DIR" "$D27_DIR/nohup.log"
)
```

此为待执行命令，助手无服务器直连，尚未观测补跑。不要执行旧resume或重复第二次nohup。首batch应产生D27_TRAIN step1，KeyError不再出现；CPU局部接口通过不等于GPU已验证。异常保留新日志。

原D26已判定，无追加训练/seed。D27完成后新目录用修正版upload_rebuild_v1_d27_records.py上传原轻量记录，用户给提交即可。安全/全局/局部/类别组按原冻结协议读结果。

若要执行新增完整模型接口回归，使用新快照tests/test_d27.py（转移→objective→backward），不要重做资源审计。GPU仅0/1 H10080GB、资源充足、nohup/zzx不变，Test6禁读。[相关失效候选](../experiments/ASSUMPTIONS_AND_RESEARCH_OPPORTUNITIES_20261003.md)待有效D27结果后决定，未新增队列。
