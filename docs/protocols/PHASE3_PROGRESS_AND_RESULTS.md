# 当前队列进度与结果的只读查看（2026-10-24）

本页仅查询现有记录，不登记、不启动、不恢复、不训练、不清理，也不读取数据集像素或封存split。实际运行状态由用户执行后产生，本文不增加新的服务器观测。运行目录从全局单次登记回执绑定，不按glob误选旧失败run。

## 日常先看M2、合并阶段、失败与GPU

在原remote_sensing终端执行：

```bash
conda activate remote_sensing
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
python -B "$ROOT/records/phase3_engineering_restart_package_752d3835a18a15a04d83b1dcc1841bff98bf0b07/scripts/status_phase3_engineering_restart.py" --tail 20
```

该脚本已在服务器存在，不需要下载新版本或更改运行源码。--tail 20只显示末尾日志；--tail 0可省去日志。需要持续观察时，可用watch -n 60运行同一Python命令，Ctrl+C只退出watch，不停止后台训练。不要每秒全量读所有日志或将瞬时GPU利用率当作实验进度。

| 字段 | 如何解释 |
|---|---|
| observed_at | 查询或文件中的最后观测；同时核对progress文件更新时间，不能拿旧记录当现在 |
| completed_trainings | 已完成M2训练作业数，分母108；不是全队列228，也不等于评价/完整阶段验收全部完成 |
| latest_training_progress的step | 当前M2作业更新数，目标32000；active为当时队列活跃作业，latest两个progress只代表最近写入 |
| job_failure_count、failed_or_blocked、controller_failure | 新错误或阻断证据，出现非零/FAILED/STOPPED先读首个原栈，不自动重跑 |
| evaluation、cpu_tasks、counted_cases | 评价/CPU计数进度；更新数暂不变可能在评价，不单凭GPU空闲或step停住判死 |
| remaining_training_hours | 该作业的剩余纯优化时间，排除评价；不是整队列ETA |
| WAIT_M2 | 合并监督器正常等待M2完整性验收 |
| RUNNING_J/R/T/V | 已进入对应后段；此时要看该段记录，旧M2进度不再变化是正常的 |
| WAIT_PUBLIC_DATA | 等3DCD和P³两份数据合同就绪，代码不会自动下载或跳过 |
| COMPLETE_SERVER_CHECKED | 对应阶段完整性通过；还需读科学gates和指标，不等于假设正结果或正式test结果 |

M2任务名中的T0–T3是内层OOF教师，不是后段3DCD的T阶段。ps的异常ELAPSED不用于估时。已收到的xFormers禁用警告未阻断此前优化更新，不因此换包或重启。

## 查看五段记录、近期进度和已生成结果

以下使用Python标准库，只读取登记回执、状态JSON、进度JSON和汇总文本；打印最近两份进度不等于断言这两项仍活跃。后段阶段status可能在首个作业完成后才写入，显示null不能单独判定未启动，应结合COMBINED和近期progress。M2的complete.json也可能先于该作业最后一轮轨迹计数完成，不能只数文件就宣布完整验收。

```bash
python -B - <<'PY'
import json
from datetime import datetime
from pathlib import Path

records = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records")
receipt = json.loads((records / "phase3_engineering_restart_20261024_once.json").read_text(encoding="utf-8"))
m2 = Path(receipt["m2_directory"]).resolve()
queue = Path(receipt["combined_directory"]).resolve()
if any(p.parent != records.resolve() for p in (m2, queue)):
    raise RuntimeError("Unexpected registered directory")

def read(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

print("QUERY_TIME", datetime.now().astimezone().isoformat())
q = read(queue / "queue_status.json") or {}
print("COMBINED", q.get("status"), q.get("observed_at"), q.get("error", ""))
for stage, base, budget in [("M2", m2, 32000), ("J", queue, 8000),
                            ("R", queue, 32000), ("T", queue, 12000),
                            ("V", queue, 12000)]:
    status = read(base / ("queue_status.json" if stage == "M2"
                         else stage.lower() + "_status.json"))
    print("\nSTAGE", stage, "STATUS", json.dumps(status, ensure_ascii=False))
    pattern = "*/progress.json" if stage == "M2" else stage + "_*/progress.json"
    recent = sorted((base / "jobs").glob(pattern), key=lambda p: p.stat().st_mtime)[-2:]
    for path in recent:
        row = read(path) or {}
        stamp = datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat()
        print("RECENT", path.parent.name, str(row.get("step")) + "/" + str(budget),
              "loss", row.get("loss"), "file_mtime", stamp,
              "complete_receipt", (path.parent / "complete.json").is_file())
    pub = base / "publication" if stage == "M2" else base / "publication" / stage
    for name in ("summary.json", "gates.json"):
        row = read(pub / name)
        if row is not None:
            print("RESULT", pub / name, json.dumps(row, ensure_ascii=False))
    if not (pub / "summary.json").is_file():
        print("RESULT_SUMMARY_NOT_YET_PRESENT", pub)
    for name in ("metrics.csv", "metrics.json", "REPORT.md"):
        if (pub / name).is_file():
            print("RESULT_FILE", pub / name)

report = m2 / "publication" / "REPORT.md"
if report.is_file():
    print("\nM2_REPORT_PREVIEW\n" + "\n".join(report.read_text(encoding="utf-8").splitlines()[:80]))
PY
```

RESULT_SUMMARY_NOT_YET_PRESENT表示尚无该段汇总，不单独等于失败或未启动；需结合状态判断。summary即使存在，也要读status和errors，INCOMPLETE_NO_RETRY报告不能当正式完整结果。训练loss用于观察优化，不替代开发mIoU或机制判定。

M2逐作业progress位于M2/jobs/<ID>/progress.json；其阶段报告在M2/publication/REPORT.md、summary.json、gates.json和metrics.csv。J/R/T/V逐作业位于合并目录jobs/<阶段>_<...>/，阶段状态为j_status.json等，结果在合并目录publication/<阶段>/summary.json与metrics文件。J另有REPORT.md/gates.json，R/T/V不保证有同名报告或门禁文件。具体保留内容见[数据与产物索引](../experiments/PHASE3_DATA_AND_ARTIFACT_STORAGE_20261024.md)。

## 需要诊断或分析时

先保留查询时间、COMBINED/M2状态、活跃或最近作业的step与更新时间、失败原栈及已有summary/gates；不要先重新启动。用户可回传状态摘要；报告/指标较长时按[轻量上传](LIGHT_RECORD_UPLOAD_20261001.md)写回GitHub并告知提交，不粘整份大日志，不为上传失败重算。

M2有已存在凭据时的轻量上传入口；后段服务器publication并不自动等于已上传GitHub，结束还需按[保存规则](../experiments/PHASE3_DATA_AND_ARTIFACT_STORAGE_20261024.md)整理端点/计数/轨迹和额外修订材料。所有查询须遵守[长期约定](EXECUTION_CONTRACT.md)，当前运行不因查看而重新预检或改动。
