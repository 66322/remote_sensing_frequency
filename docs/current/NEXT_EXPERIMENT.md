# 下一步：按既有授权登记N2六组，原队列不重启

最后服务器记录：原Post-D30于2026-10-05T00:26:01.590322+08:00 COMPLETE（18/18主体、F四项实际SKIPPED_GATE）；N1于07:21:14.003184 COMPLETE_AWAITING_STAGE_PROTOCOL（四项8000步、固定门槛False、N6三项实际SKIPPED_GATE）。两阶段轻量原件已上传并回读；C0—C5/N1-0—3十组20份summary的绑定、整数汇总和固定门槛复算通过。没有本次助手实时服务器查询。N2六组执行包已实现发布，**服务器登记/训练回报尚未收到**；N3/N4/N5仍待各自诊断和协议，不把旧预约状态当可执行。

固定C2剩RGB对C0仅+0.041525pp、对C1−0.004058pp、对C3+0.028336pp；剩DSM对C0−0.041961pp、对C1−0.016106pp、对C3−0.026610pp，双侧门槛False。普通C0已解释DSM锚点改善，完整输入复用固定B0，不承诺蒸馏增量。N1-3对N1-2综合−0.881059pp、clean−0.852801pp、DSM缺失−0.156095pp，最差tile差−2.054791pp；固定gate=False。N2按事前规则使用N1-2作为匹配基座，不叠加失败多深度入口。

## 已落实的新增实验

[N2冻结协议](../protocols/POST_AB_N2_EXECUTION_20261005.md)：同一N1-2初始state、六组同预算/容量，检验双向关系是否超过空间/单向/打乱。CPU8项检查PASS；GPU0/1两卡、每组8000步、batch16无累积、seed42，总48000更新。新结构真实速度待首个实际作业，不作精确完工承诺。技术失败或单作业8小时超时停止新派发，另卡已运行任务收尾；不自动重试。所有记录/代码/缓存只放zzx新独立目录。

## 服务器登记

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
cd "$ROOT"
git fetch origin rebuild-v1-protocol-20260915
COMMIT=本轮回复给出的完整提交号
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
BOOT_DIR="$ROOT/records/post_ab_n2_bootstrap_$(date +%Y%m%dT%H%M%S)_$$"
mkdir -p "$BOOT_DIR"
git show "$COMMIT":scripts/enqueue_post_ab_n2.py > "$BOOT_DIR/enqueue_post_ab_n2.py"
"$EXP_PY" -u -B "$BOOT_DIR/enqueue_post_ab_n2.py" --root "$ROOT" --commit "$COMMIT"
)
```

回传POST_AB_N2_QUEUE_REGISTERED和POST_AB_N2_LOG行。COMMIT使用助手本轮回读核验的提交号。若ALREADY_REGISTERED只看已有目录，不再创建；异常先诊断，不重启旧N1控制器。新阶段控制器nohup运行。

登记后可只读查询：EXP_PY -B 新目录/code/scripts/status_post_ab.py --directory 新目录，并查看显示的nohup日志尾部；不要把旧N1目录的19预约状态当新N2进度。N2完成后新目录/code/scripts/upload_post_ab_n2_records.py --root ROOT --directory 新目录前台上传，再按冻结gate回读。

原C/N1最终原件已验收，无需再次上传本阶段；[完整结果与边界](../experiments/POST_C_N1_RESULTS_20261005.md)。N6实际跳过，N3/N4/N5保持条件研究；不追加C/N1配方救gate。

主线仍RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复是旁支；仍为可行性探索，无确认性新贡献。不重训A/B/C/N1、不增加seed或扫参、不启动F/N6、不访问Test6/independent final。服务器由用户终端执行，无SSH；只用GPU0/1两张H10080GB，每卡一worker，nohup；全部记录/快照/缓存在zzx对应独立目录，不重复资源审计。
