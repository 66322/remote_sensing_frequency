# 下一步：上传A原生结果，沿原B/C队列继续

最后服务器观测：2026-10-04T17:21:47.568226+08:00（用户终端查询回传），Post-D30为RUNNING，控制器2720259 LIVE=True，主体12/18完成：A0—A5、B1—B6全部COMPLETE；C0在GPU0训练3760/8000步，C1在GPU1训练3780/8000步，两worker PID_LIVE=True；C2—C5 PENDING，F0—F3仍有条件。原队列已进入C，禁止重复恢复或新建队列。旧08:12日志的model导入错误仅作历史记录。本次仍未收到上传提交，GitHub没有新增A/B原生结果；固定A2/B3门槛尚待原件分析，不能由技术完成判定科学成立。

## 上传阶段原件

命令只上传，不训练、不评价、不重启。最新上传器保留修复manifest、A汇总、complete/checkpoint绑定及逐tile JSON，权重/预测仅索引。运行中B记录为阶段快照，不当最终结果；如写入中的JSON或非快进push报错，保留现场回传错误，不重启训练、不force push。

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

回传PORTFOLIO_GITHUB_COMMIT及PORTFOLIO_GITHUB_RECORDS即可。助手回读manifest/SHA及A固定A2对A0/A1/A3；A4/A5仅敏感性，不能替代主候选。B阶段已全部技术完成，同时核对固定B3对B1/B4与A0的完整gate，B5/B6不替换B3。本次回传仅为查询，尚无结果上传。完成A不重训、不重评价。

## 沿原队列继续及只读查询

禁止再执行旧2a15ef恢复指令或另建队列。B完成原控制器接C，F仅固定B3全部gate通过触发；未知错误先诊断，不自动重跑。

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



17:21脚本估算主体剩余6.70小时、结束约2026-10-05 00:03，仅粗排期，F未包含，不承诺完成时间。

用户终端执行无SSH；只用物理GPU0/1两张H10080GB、nohup、seed42、8000步、batch16无累积，全部记录/临时/缓存/快照保存在zzx对应目录。资源充足，不重复资源审计、不加seed、不访问Test6/独立final，Val2重复开发不称独立确认。主线不变，见[研究决定](RESEARCH_DECISION.md)。
