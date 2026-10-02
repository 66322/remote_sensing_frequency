# 下一步：查询已启动的D26，不重复启动

更新2026-10-02。最后服务器观测：2026-10-02本次用户回传，controller PID1571946；GPU0 J0 PID1571983、GPU1 B0 PID1571989，均initializing step=0。目录创建19:12:53+08:00来自目录名，日志行无精确观测时间；不表述为实时PID状态或已完成首batch。本次目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d26_bidirectional_20261002T191253_1513109。[启动证据](../../records/research_d26_launch_observation_20261002/user_reported_launch.json)；固定执行52f94388b1a9c7557e9ef533075661139cd55eda。

九组×8000、GPU0/1两H10080GB、物理batch16无累积、nohup、zzx目录约定不变，不再资源/预算审计。J0/B0已启动，剩余七组由动态队列领取；首训练步/梯度验收尚未收到。按照[冻结协议](../protocols/D26_BIDIRECTIONAL_FEATURE_PLAN_20261002.md)推进，不重训单模态、扩预算或自动扫参。

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D26_DIR="/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d26_bidirectional_20261002T191253_1513109"
D26_PY=$(python -c 'import json; print(json.load(open("records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$D26_PY" -B "$D26_DIR/code/scripts/status_rebuild_v1_d26.py" --directory "$D26_DIR"
tail -n 20 "$D26_DIR/nohup.log"
```

出现训练step>0和实际gradient记录后再更新训练验收；若TECHNICAL_FAILURE，先读该任务日志尾，不重开队列。第一正常完整任务结束后ETA采用实际耗时。九组结束查看screen_result.json/results.csv并按[执行说明](../protocols/D26_EXECUTION_20261002.md)上传轻量原件；从GitHub直接读长输出、离线核对矩阵与预设gate。最多一条成立机制另立seed/独立场景协议，失败不自动追训。

研究阶段仍可行性探索，双方信息互补主问题不变，C1旁支、强基线和最终贡献角色不变。历史held4不独立、Test6禁读。启动不是精度结果。
