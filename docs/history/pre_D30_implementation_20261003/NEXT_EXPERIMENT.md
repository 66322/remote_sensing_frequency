# 下一步：D28后接D30损失拆解计划

**状态：方案已整理，D30尚未实现/排队。** 不需要重跑D27或重新测量资源。

[D30完整设计](../protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)、[机器计划](../../records/research_d30_plan_20261003/plan.json)：

1. D28技术完成、锁释放、worker退出后交接，仅GPU0/1。
2. G0/G1原checkpoint各做四种固定混合×三条件×两tile，共48次诊断。
3. GPU0跑P→PR_area，GPU1跑R→PR_pixel。每组8000步，复用旧S0/S1，保持相同数据/预算/随机初始化/选模。
4. 记录分项目标/梯度、双方独有信息保留、逐tile/类伤害；同步轻量原件。预计交接后3.5—4.5小时，不含D28剩余时间。

这轮回答当前损失配方失败原因，不预先承诺提升。新归一化只恢复基线则是修复结论；无实用增量停止此配方。原D29不激活，D27门槛不修改。当前用户要求规划，本文没有可以立即运行的D30启动脚本；实施时需完成目标兼容与接力检查后提供一次nohup命令。

## D28当前查询与完成后上传

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D28_DIR="$PWD/records/research_d28_pressure_20261003T092243758628_2001983"
RESULT_PY=$(python -c 'import json; print(json.load(open("records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$RESULT_PY" -B "$D28_DIR/code/scripts/status_rebuild_v1_d28.py" --directory "$D28_DIR"
tail -n 15 "$D28_DIR/nohup.log"
```

若日志D28_QUEUE_FINISHED COMPLETE summary_exit=0，运行：

```bash
"$RESULT_PY" -B "$D28_DIR/code/scripts/upload_rebuild_v1_d28_records.py" --root "$PWD" --directory "$D28_DIR"
```

失败则先保留并读取错误尾日志，不能将技术失败当科学失败。D27完整包已上传，无需再传；只需给D28_GITHUB_COMMIT即可从远端读完整记录。


[旧下一步归档](../history/pre_D30_plan_20261003/NEXT_EXPERIMENT.md)。
