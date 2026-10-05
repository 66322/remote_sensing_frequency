# 下一步：修复并接管原N2队列

最后服务器观测（用户回传）：2026-10-05T08:58:59.848681+08:00，N2控制器PID3456909已退出，QUEUE=CONTROLLER_INTERRUPTED。N2-0已派发到GPU0（worker PID3457210），其实际存活/训练步数待核对；不能把旧step=0快照当成当前进度。N2-1—5尚待派发。原科学执行提交86b6a70e5c3482314986fb1259e2fccbd0a5a38b保留。故障为per_job_timeout_hours=null被直接乘3600；这是控制器技术失败，不是N2科学负结果。控制器专用修复和安全接管工具已发布，尚无服务器恢复执行回报。先接管已有worker或验收绑定完成记录；已退出且未有效完成则HOLD、输出日志，不自动重训。不重复登记N2，不重启原C/N1。

按已授权N2六组执行范围继续，仅GPU0/1、每组8000步、batch16、seed42，不追加实验。先运行以下专用工具；它验证旧控制器已释放锁、原manifest和plan、已派发worker身份与完成绑定。接管仍活着的N2-0或接受已完成结果，继续原待运行N2-1—5。若N2-0已退出且未有效完成，输出N2_RECOVERY_HOLD和worker日志，不自动重启/续训。

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
NEXT_DIR="$ROOT/records/research_post_ab_followup_n2_20261005T085829_3456726"
cd "$ROOT"
git fetch origin rebuild-v1-protocol-20260915
FIX_COMMIT=$(git rev-parse FETCH_HEAD)
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
BOOT_DIR="$NEXT_DIR/repair_bootstrap_$(date +%Y%m%dT%H%M%S)_$$"
mkdir -p "$BOOT_DIR"
git show "$FIX_COMMIT":scripts/repair_post_ab_n2_controller.py > "$BOOT_DIR/repair_post_ab_n2_controller.py"
"$EXP_PY" -u -B "$BOOT_DIR/repair_post_ab_n2_controller.py" --root "$ROOT" --directory "$NEXT_DIR" --commit "$FIX_COMMIT"
)
```

成功会打印N2_CONTROLLER_REPAIR_REGISTERED和N2_REPAIR_LOG，控制器日志应有POST_AB_ADOPT或POST_AB_ACCEPT_COMPLETE。回传整段输出核对；尚无服务器执行反馈。重复运行时若控制器存活仅报告ALREADY_LIVE。修复保存到原实验controller_repair_*，原plan、execution_commit、code_manifest、code和模型结果保留，worker/summary imports仅来自原科学快照。

随后只读查询：

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
NEXT_DIR="$ROOT/records/research_post_ab_followup_n2_20261005T085829_3456726"
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
REPAIR_DIR=$(python -c 'from pathlib import Path; p=Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_n2_20261005T085829_3456726"); a=sorted(x.parent for x in p.glob("controller_repair_*/repair_manifest.json")); print(a[-1])')
"$EXP_PY" -B "$REPAIR_DIR/scripts/status_post_ab.py" --directory "$NEXT_DIR"
tail -n 60 "$REPAIR_DIR/nohup_controller.log"
)
```

8小时包含训练与评价；超时或技术失败停止新派发，另卡已运行任务收尾，无自动重试。N2结束后上传现有轻量记录并复算固定门槛；N3/N4/N5仍待自身诊断/冻结协议；F/N6跳过不改。不访问Test6/independent final，不重训A/B/C/N1、不增加种子或扫参。主线和C/N1科学去留不变，见[研究决定](RESEARCH_DECISION.md)、[C/N1验收](../experiments/POST_C_N1_RESULTS_20261005.md)、[修复说明](../experiments/POST_AB_N2_CONTROLLER_REPAIR_20261005.md)。
