# 下一步：继续两卡N2训练，按需只读查询

最后服务器观测（用户终端回传）：2026-10-05T12:15:02.465274+08:00，QUEUE=RUNNING_N2，修复控制器PID3467202 LIVE=True。GPU0 N2-0原worker PID3457210 LIVE=True，训练已达8000/8000，正在fixed8000评价；progress观测12:14:49.587910，tile=3_11、condition=geom_warp8+rgb_down4、windows529/529，仅当前条件/tile窗口完成，不是作业COMPLETE。GPU1 N2-1 PID3467394 LIVE=True，training7800/8000，progress观测12:14:52.484868，剩200步约4.4分钟（不含之后验证/评价）。N2-2—5仍PENDING，当前完成标记0/6；没有新中断回报或精度结果。两卡当前训练每步约1.309/1.316秒，后续各两项纯训练约5.82/5.85小时；从12:15开始不计评价的训练完成下界约18:10。计入当前及后续checkpoint选模、fixed8000/selected条件评价与汇总，整队暂估2026-10-05北京时间20:00—22:00（规划范围、非已测评价耗时或保证）；首轮COMPLETE与评价耗时回报后再校准。科学86b6、控制器修复9b196a2、N2-0原worker接管保留；继续现有队列，按需只读查询，不重启。

已确认最后观测12:15:02为RUNNING_N2、原N2-0最终评价及N2-1训练7800步。继续当前队列；需要查看进度时执行下面只读查询并回传输出。无需再次fetch/登记/运行安装器，也不重训N2-0。

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
NEXT_DIR="$ROOT/records/research_post_ab_followup_n2_20261005T085829_3456726"
REPAIR_DIR="$NEXT_DIR/controller_repair_20261005T091755_3467074"
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$EXP_PY" -B "$REPAIR_DIR/scripts/status_post_ab.py" --directory "$NEXT_DIR"
tail -n 60 "$REPAIR_DIR/nohup_controller.log"
tail -n 20 "$NEXT_DIR/cpu_checks.log"
)
```

修复目录和日志：`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_n2_20261005T085829_3456726/controller_repair_20261005T091755_3467074/nohup_controller.log`。状态脚本会同时打印queue旧观测与worker当前存活/progress原件，二者时间口径不同。若CPU_VERIFYING，先以CPU日志说明是否仍在检查；若中断或HOLD，分析对应日志，不自动重启。若RUNNING_N2，继续既有六组两卡队列；不因本次只看到ADOPT就另开队列。

原故障08:58:59为null超时直接乘3600。修复按原协议8h处理，保留原plan/code_manifest/科学快照。原worker和后续workers继续执行原86b6代码；控制器单独9b196a2。只用GPU0/1，每卡一个worker，各8000步，batch16、seed42。8h包含训练与评价，超时或技术失败停止新派发、另卡已运行任务收尾，不自动重试。

N2完成后上传当前目录既有轻量记录并复算预设门槛。C/N1原件已验收，科学去留不变；N3/N4/N5仍待各自诊断和冻结协议，F/N6跳过不改，不访问Test6/independent final，不追加种子或扫参。主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复为旁支。详见[研究决定](RESEARCH_DECISION.md)、[C/N1验收](../experiments/POST_C_N1_RESULTS_20261005.md)、[控制器故障与修复](../experiments/POST_AB_N2_CONTROLLER_REPAIR_20261005.md)。


## 2026-10-05后续规划（助手建议，尚未激活）

根据用户本次要求，已核对相关原始论文并形成[条件实验规划](../protocols/POST_N2_EVIDENCE_LED_PLAN_20261005.md)：N2完成后先E0空间诊断与E1内容相关缺失，建议E1触发N5四组优先；N3五组需区域问题证据，N4四组需实际条件更新暴露证据。新增E2物理缺失×标记可靠性只作无训练诊断。潜在训练仍最多13组，不默认全部运行。当前每批两侧own CE和抽样非零梯度记录不足以证明弱侧更新缺口；不重做D25分头/PCGrad或D8类别采样。

上述是建议优先级与待冻结设计，不是N3/N4/N5已实现/排队，也未修改旧N2协议、旧预约或当前队列。最后服务器观测已更新至12:15:02，未获得新的精度回报。研究主线、旁支角色与C/N1失败去留不变；无新增训练、seed或Test6访问。


2026-10-05后继安排兼容检查：用户询问现在安排与冲突，已核对[规划第11节](../protocols/POST_N2_EVIDENCE_LED_PLAN_20261005.md)与现有六组控制器。可现在准备执行包/CPU检查与登记条件计划，GPU接续等N2六组完成、原件验收、控制器和worker退出且两锁释放。目前仅GitHub规划登记，执行包/服务器队列仍PREPARATION_PENDING。E1先U/H/L共24评价单元，T预留规则改为N5完整协议冻结后再评价；当前N2与原19预约状态不改，不重启旧队列。N5/N3/N4仍4/5/4条件上限，先一个有证据族，不自动全部运行。
