# 下一步：原C完成后接收最终稳定快照

最后服务器记录快照：2026-10-04T18:07:21.987874+08:00，queue_status=RUNNING，主体12/18完成，A0—A5及B1—B6 COMPLETE；C0/C1在GPU0/1训练至8000步，phase=checkpoint_selection，尚非COMPLETE；C2—C5 PENDING，F仍PENDING。该快照未新查PID存活；最近存活证据为17:21用户查询。不把18:08上传时间当运行完成时间。

固定A2 gate=False：综合对A0+0.101643pp（要求≥+0.2）、对A1−0.044694pp（要求≥+0.2）、对A3−0.023958pp（要求≥+0.1）；其余原生安全/fixed检查通过。固定B3 gate=False：几何对B1+0.021260pp（要求≥+0.5）、对B4−0.012852pp（要求≥+0.2）；DSM锚点正确伤害率较A0增加0.011997pp。F触发条件不成立；不追加A/B种子、追训、扫参或换敏感性最佳组救gate。原C继续。

A/B上传验收已完成，不重复上传同阶段，不重训/重评价，不恢复或另建队列。原C继续，固定C2双侧按C0/C1/C3及自身锚点门槛判定。F不手动启动；等待原控制器实际SKIPPED_GATE。

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
