# D18 seed17 匹配复验：服务器执行与交接

本执行文件对应 [预先制定的研究计划](D18_MATCHED_SEED17_REPLICATION_PLAN_20260928.md)。
当前 GitHub 中只包含可执行代码；服务器短流程、正式训练和结果尚未观察到。
执行前确保服务器没有其他占用 GPU0/1 的实验队列。
如此前拉取失败后仍执行了后台命令，先查看 `launcher.log` 和
`pgrep -af '[r]un_rebuild_v1_d18_replication_queue'`；已有运行进程时先核对
其 Git 提交与状态，不启动第二份。

## 从另一台电脑启动

在服务器终端运行以下命令。完整检查点、预测和日志留在现有项目的 `runs/`
及 `records/`；这些目录均位于 `/home/jovyan/zzx` 下。

```bash
(
  set -e
  cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
  conda activate remote_sensing
  git pull --ff-only origin rebuild-v1-protocol-20260915
  git merge-base --is-ancestor c922fce HEAD
  mkdir -p records/rebuild_v1_d18_replication_queue_20260928
  nohup bash scripts/run_rebuild_v1_d18_replication_queue.sh > records/rebuild_v1_d18_replication_queue_20260928/launcher.log 2>&1 &
)
```

如果 `git pull` 因服务器已有未提交修改而停止，先查看 `git status --short`，
保留现有产物并处理冲突后再启动。不要删除或重置旧 seed42 结果。
如果 HTTPS 询问 `Password`，输入有此仓库权限的 GitHub personal access token，
不能输入账号密码。也可用 `gh auth login` 选 HTTPS 并授权 Git；不要将 token
写入命令行、远端 URL、日志或交给聊天。上述子 shell 的 `set -e` 和提交检查
会使拉取或认证失败时停止，避免误启动旧版本队列。

队列检查源码和配置已提交、官方 DINO 权重、旧 seed42 三组摘要及 66 个逐条件/
逐图块预测文件、R01 历史参考、数据路径、磁盘及两张显卡。先并行运行
P0/P1/P2 的一训练步短流程和评估；三项都通过后，再以两张卡并行完成三项
8000 步正式训练及 11 个条件的 Val2 评估。训练或评估失败会保留其他组产物，
不会把不完整结果判为方法失败。同一提交和配置下重新运行队列可复用已完成组、
从相同签名检查点继续未完成训练。

本轮使用现有 `d18_dino` 环境及固定官方 DINO 权重。缺失软件或资源时，
队列会在预检中停止并写明原因；不会自行下载模型或改动原始数据。

## 查看进度与预计完成时间

```bash
tail -n 30 records/rebuild_v1_d18_replication_queue_20260928/status.tsv
tail -n 10 records/rebuild_v1_d18_replication_queue_20260928/FORMAL_P2_17.log
```

`status.tsv` 每约两分钟给出一次 `ETA UPDATE`，使用当前训练步速、
已完成的评价条件和 seed42 实测单任务约 47 分钟推算剩余时间。
这是估计，不是自动停止期限；某张 GPU 提前空闲可能只是队列只有最后一项任务。
全部成功时确认 `SMOKE_GATE COMPLETE`、三项 `FORMAL` 及其 `EVAL` 均
`COMPLETE`、`ANALYSIS COMPLETE`、`ARCHIVE COMPLETE`。只看 `QUEUE FINISHED`
不足以判断完整成功。

## 结果与跨电脑归档

- 完整训练：`runs/rebuild_v1/D18_REPL_{P0,P1,P2}_seed17_8000_20260928/`
- 评估、预测和判定：`records/rebuild_v1_d18_replication_20260928/`
- 状态、ETA 和完整日志：`records/rebuild_v1_d18_replication_queue_20260928/`
- 精简的两种子六组原始摘要、决策、状态、哈希与文件位置：
  `records/rebuild_v1_d18_replication_compact_20260928/`
- 自动生成的可读结果：`docs/experiments/D18_REPLICATION_RESULTS_20260928.md`

完成后在服务器检查归档状态，再推送精简证据到 GitHub：

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path('records/rebuild_v1_d18_replication_compact_20260928/manifest.json')
report = json.loads(p.read_text())
print(report['status'], 'missing=', report['missing'])
PY
git add records/rebuild_v1_d18_replication_compact_20260928 docs/experiments/D18_REPLICATION_RESULTS_20260928.md
git diff --cached --check
git commit -m "Archive D18 matched seed17 replication results"
git push origin rebuild-v1-protocol-20260915
```

如果归档显示 `INCOMPLETE`，仍可提交状态、已有各组摘要和缺项清单以便另一台
电脑诊断；不要写成复验失败。生成的报告须与 `decision.json` 的双种子门槛及
原模型 DSM 缺失结果一起阅读。回退到同 seed P0 是显式 availability 策略；
旧 R01 回退仍在原摘要内单列。Test6 全程冻结，Val2 仍为探索性证据。

另一台电脑拉取结果后，运行 `python scripts/audit_rebuild_v1_d18_replication_archived.py`
离线复核六组摘要、各门槛、整数混淆矩阵及配对计数，并把生成的
`offline_audit.json` 一起推送到 GitHub。检查点与逐像素预测仍在服务器，
离线审计不等于重新推理。
