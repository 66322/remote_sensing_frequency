# 下一步：登记无训练诊断后继，N2继续原队列

最后服务器观测（用户终端回传）：2026-10-05T12:15:02.465274+08:00，QUEUE=RUNNING_N2，修复控制器PID3467202 LIVE=True。GPU0 N2-0原worker PID3457210 LIVE=True，训练已达8000/8000，正在fixed8000评价；progress观测12:14:49.587910，tile=3_11、condition=geom_warp8+rgb_down4、windows529/529，仅当前条件/tile窗口完成，不是作业COMPLETE。GPU1 N2-1 PID3467394 LIVE=True，training7800/8000，progress观测12:14:52.484868，剩200步约4.4分钟（不含之后验证/评价）。N2-2—5仍PENDING，当前完成标记0/6；没有新中断回报或精度结果。两卡当前训练每步约1.309/1.316秒，后续各两项纯训练约5.82/5.85小时；从12:15开始不计评价的训练完成下界约18:10。计入当前及后续checkpoint选模、fixed8000/selected条件评价与汇总，整队暂估2026-10-05北京时间20:00—22:00（规划范围、非已测评价耗时或保证）；首轮COMPLETE与评价耗时回报后再校准。科学86b6、控制器修复9b196a2、N2-0原worker接管保留；继续现有队列，按需只读查询，不重启。

2026-10-05用户在兼容检查后明确“那开始吧”，已落实E0/E1/E2无训练后继执行包；16项CPU契约/实际控制循环集成检查及10个Python文件语法检查通过。**代码已实现；服务器登记尚待用户终端回报，不称已经排队或CUDA成功。** 新目录research_post_n2_diagnostics_<timestamp>_<pid>，独立nohup控制器先等待N2六组完成、原controller/worker退出和两锁释放，再复核原N2计数/绑定/gate，执行CPU E0→GPU E1→E2。重复登记只报告已有目录，不重启旧队列。

E1固定A0/B1×两方向×U/H/L×Val2共24新tile推理；E2固定N1-2/N2-0/N2-3，复用clean，新增36次，共60新推理、0新训练。只用GPU0/1一worker/卡；T预留规则不评价，N5/N3/N4仍待问题证据及完整族协议，gate只输出问题提示，不自动训练。科学研究角色和旧失败去留不变。真实CUDA兼容性/耗时仍待首项回报；CPU检查不保证服务器任务成功。

## 现在执行：独立后继登记

服务器原remote_sensing终端执行。读取GitHub当前分支并绑定FETCH_HEAD完整提交；本次回复亦提供固定提交版本。登记前只读原队列与既有诊断目录，不会重启N2；成功返回POST_N2_DIAGNOSTICS_REGISTERED、实际目录/PID/log，若ALREADY_REGISTERED则查原目录。CPU失败HOLD_CPU_CHECKS保留目录，先回传日志，不重复登记救配方。

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
cd "$ROOT"
git fetch origin rebuild-v1-protocol-20260915
COMMIT=$(git rev-parse FETCH_HEAD)
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
BOOT_DIR="$ROOT/records/post_n2_diag_bootstrap_$(date +%Y%m%dT%H%M%S)_$$"
mkdir -p "$BOOT_DIR"
git show "$COMMIT":scripts/enqueue_post_n2_diagnostics.py > "$BOOT_DIR/enqueue_post_n2_diagnostics.py"
"$EXP_PY" -u -B "$BOOT_DIR/enqueue_post_n2_diagnostics.py" --root "$ROOT" --commit "$COMMIT"
)
```

等待阶段CUDA不可见、不加载大tile；N2失败/停控制器则HOLD。N2六组完成且释放后，独立复核原件再接续E0/E1/E2，科学N2 gate不成立也可做无训练问题诊断。发生技术失败停止新增派发，detached worker可能仍存活，先查日志，不自动重试。

## 登记后查询

DIAG_DIR替换为登记返回实际完整目录；EXP_PY/ROOT按上面定义。

```bash
"$EXP_PY" -B "$DIAG_DIR/code/scripts/status_post_n2_diagnostics.py" --directory "$DIAG_DIR"
```

报告最后观测、原等待状态、CPU phase、E0/mask状态及每worker存活/window进度。需要时回传登记输出和只读状态；首个真实推理完成后再根据实际耗时估算结束时间。

## 完成后上传

N2原件用原N2 code/scripts/upload_post_ab_n2_records.py --root "$ROOT" --directory "$N2_DIR"上传；本诊断n2_source_audit不是完整N2原件替代。诊断DIAGNOSTICS_COMPLETE_AWAITING_REVIEW后运行：

```bash
"$EXP_PY" -u -B "$DIAG_DIR/code/scripts/upload_post_n2_diagnostics_records.py" --root "$ROOT" --directory "$DIAG_DIR"
```

记录采用无损轻量编码；大.npy/.npz/权重留服务器并保留SHA索引，凭据仅用户交互输入。收到GitHub提交后回读验证，分析N2成立边界和诊断问题，再冻结并落实证据充分的一族N5或N3；N4仍等条件更新暴露证据。T预留到N5完整协议冻结后，13组是条件上限，不自动全跑。

[冻结执行协议](../protocols/POST_N2_DIAGNOSTICS_EXECUTION_20261005.md)；[研究决定](RESEARCH_DECISION.md)；[CPU就绪记录](../../records/research_post_n2_diagnostics_plan_20261005/validation.json)。
