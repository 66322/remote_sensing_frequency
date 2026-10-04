# 下一步：登记Post-A/B后继队列，等待原C/F收束

最后服务器观测：2026-10-04T18:24:33.785422+08:00，来自用户粘贴终端状态；QUEUE=RUNNING，控制器PID2720259，LIVE=True，主体12/18完成。A0—A5及B1—B6 COMPLETE；C0/C1 RUNNING fixed8000，step8000/8000、windows529/529，最近进度18:24:22，仍非COMPLETE；C2—C5 PENDING。F仍PENDING，B3 gate=False，实际SKIPPED_GATE尚待确认。该观测晚于18:07已上传记录快照，不能替代C完成原件，也不代表实时状态。

固定A2 gate=False：综合对A0+0.101643pp（要求≥+0.2）、对A1−0.044694pp（要求≥+0.2）、对A3−0.023958pp（要求≥+0.1）；其余原生安全/fixed检查通过。固定B3 gate=False：几何对B1+0.021260pp（要求≥+0.5）、对B4−0.012852pp（要求≥+0.2）；DSM锚点正确伤害率较A0增加0.011997pp。F触发条件不成立；不追加A/B种子、追训、扫参或换敏感性最佳组救gate。原C继续。

A/B上传验收已完成，不重复上传同阶段，不重训/重评价，原队列不恢复或重建；可以登记新后继队列等待释放。原C继续，固定C2双侧按C0/C1/C3及自身锚点门槛判定。F不手动启动；等待原控制器实际SKIPPED_GATE。

## 后续只读查询

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
POST_DIR="$ROOT/records/research_post_d30_mechanisms_20261004T000812_2446364"
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
REPAIR_DIR=$(python -c 'from pathlib import Path; p=Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_d30_mechanisms_20261004T000812_2446364"); a=sorted(x.parent for x in p.glob("evaluation_repair_*/repair_manifest.json")); print(a[-1])')
"$EXP_PY" -B "$REPAIR_DIR/status_post_d30.py" --directory "$POST_DIR"
python - "$POST_DIR" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
logs=sorted(p.glob('nohup*'),key=lambda x:x.stat().st_mtime)
for f in [x for x in logs if x.is_file() and x.suffix=='.log'][-2:]:
    print(f)
    print('\n'.join(f.read_text(errors='replace').splitlines()[-20:]))
PY
)
```

## C稳定完成后上传

确认C评价与完成绑定及F实际跳过记录后执行，不需要现在再次上传；失败先诊断，不重跑训练或force push。

```bash
(
set -e
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
git fetch origin rebuild-v1-protocol-20260915
UPLOAD_COMMIT=$(git rev-parse FETCH_HEAD)
POST_DIR="$PWD/records/research_post_d30_mechanisms_20261004T000812_2446364"
STAMP=$(date +%Y%m%dT%H%M%S)_$$
UPLOAD_SCRIPT="$POST_DIR/upload_stage_records_$STAMP.py"
git show "$UPLOAD_COMMIT":scripts/upload_post_d30_records.py > "$UPLOAD_SCRIPT"
python -u -B "$UPLOAD_SCRIPT" --root "$PWD" --directory "$POST_DIR"
)
```

回传提交号，助手回读C完成绑定与原始计数后分析。当前step8000不写COMPLETE。[A/B结果](../experiments/POST_D30_AB_RESULTS_20261004.md)。

主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复是旁支，仍处于可行性探索，无确认性新贡献。用户终端操作无SSH，只用GPU0/1两张H10080GB、nohup、seed42/8000步/batch16无累积，全部记录/缓存/快照在zzx对应目录。不重复资源审计，不加seed，不读取Test6/独立final。

## Post-A/B后继条件队列（2026-10-04用户授权）

用户明确要求“按规划进行队列排队吧”。已实现并发布[后继登记与执行协议](../protocols/POST_AB_QUEUE_EXECUTION_20261004.md)：26个训练ID登记，N1四组为可执行首批，其余22组条件预约且执行协议/实现待阶段结果接续。E0只提取已有结果报告，E1待锁定评价条件。登记器先查询原队列，重复登记返回已有目录；nohup等待原18组全部完成、F实际跳过、控制器/worker退出且锁释放，再只用GPU0/1运行N1。首批32000更新，seed42/8000步/batch16，无累积；失败暂停、不自动重试。

N1完成后验整数计数及固定门槛，保存下一匹配基座并停在阶段交接。C2双侧失败会跳过N6。新队列代码/本地CPU8项检查通过，真实权重GPU前向反向尚无服务器执行回报。**当前仅完成GitHub可执行排队包，未收到服务器登记目录/PID，不能写已在服务器排队或运行。**服务器由用户执行协议中的登记命令，代码/日志/缓存全部在zzx新实验目录；不访问Test6，不重问资源或已给授权。
