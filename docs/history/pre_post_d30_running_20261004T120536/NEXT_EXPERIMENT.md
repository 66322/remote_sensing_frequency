# 下一步：查询原队列，接收A结果，按原协议续跑

最后服务器观测：2026-10-04T08:41:43.586227+08:00，Post-D30为CONTROLLER_INTERRUPTED，控制器2698383已退出；A0—A5六项COMPLETE，B1—B6/C0—C5待运行，F0—F3有条件。无活跃worker是该时刻的观测，不代表此刻状态。A评价修复已成功，无新增优化器更新；随后A阶段汇总因缺少model导入路径退出。第二次修复2a15ef163c3df7e96ee52c81cb677ebdb1305935已发布并通过本地6项回归，但尚无服务器启动回报。

## 1. 先只读查询，禁止重复启动

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

若有活跃控制器/worker，不再启动修复；查询输出回传后更新带时间戳状态。GPU0/1利用率是辅助信息，不能单独判断完成。

## 2. 仅在仍停止时，同目录恢复一次

目的：重做A阶段汇总并接续既有B/C/F条件队列。A六项完成，不新增其优化器更新或评价。使用GPU0/1、H10080GB，沿原8000步/batch16/nohup协议；异常时保留日志，不自动新建队列挽救。

```bash
(
set -e
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
git fetch origin rebuild-v1-protocol-20260915
FIX_COMMIT=2a15ef163c3df7e96ee52c81cb677ebdb1305935
POST_DIR="$PWD/records/research_post_d30_mechanisms_20261004T000812_2446364"
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
STAMP=$(date +%Y%m%dT%H%M%S)_$$
FIX_SCRIPT="$POST_DIR/recover_summary_$STAMP.py"
FIX_LOG="$POST_DIR/nohup_summary_repair_$STAMP.log"
git show "$FIX_COMMIT":scripts/recover_post_d30.py > "$FIX_SCRIPT"
nohup "$EXP_PY" -u -B "$FIX_SCRIPT" --root "$PWD" --directory "$POST_DIR" --commit "$FIX_COMMIT" > "$FIX_LOG" 2>&1 < /dev/null &
FIX_PID=$!
printf '%s\n' "$FIX_PID" > "$POST_DIR/summary_recovery_$STAMP.pid"
printf 'REPAIR_PID=%s\nREPAIR_LOG=%s\n' "$FIX_PID" "$FIX_LOG"
sleep 5
tail -n 20 "$FIX_LOG"
)
```

预期出现PORTFOLIO_SUMMARY_IMPORT_PASS、PORTFOLIO_REPAIR_CHECKS_PASS，跳过六项完成A并汇总，然后B1/B2；不是重新训练A。若异常只读取修复log与对应worker log，不猜测资源不足。

## 3. 收结果与科学分析

先收A阶段原生汇总、complete/checkpoint绑定与逐tile评价。从远端提取最新scripts/upload_post_d30_records.py到原Post目录执行，勿使用不含修复记录的原冻结上传器；它会保留修复绑定并索引服务器大文件。上传器源码与用法见[scripts](../../scripts/upload_post_d30_records.py)。若当前仍写文件，上传是阶段快照，不把其旧queue记录当最终完成；稳定的完成记录再核对manifest/SHA。

A固定A2对A0/A1/A3，A4/A5为敏感性对照。B固定B3是否超普通增强且超打乱，C是否超同位置硬标签监督，F只由B3全部gate触发。D30四条损失路线未过门槛，梯度原件已上传可继续案头解释；全逐tile原矩阵未上传需另归档。D29/新种子/更多模块未获自动启动授权。

服务器由用户在终端操作，无可用SSH。根目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro；只用物理GPU0/1，两张H10080GB，RAM/磁盘充足。长任务nohup；记录、临时、缓存、执行快照均在/home/jovyan/zzx对应实验目录。当前协议seed42、8000步、物理batch16、无累积。不重复资源审计、容量探针、单模态训练或自动追加多seed。Test6/独立final禁止访问；Val2重复开发，不称独立确认。
