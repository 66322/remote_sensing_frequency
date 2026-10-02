# 下一步：查询已启动的D26，不重复启动

更新2026-10-02。最后服务器观测：queue_status为2026-10-02T19:18:19.427139+08:00 RUNNING、COMPLETE0/9；GPU0 J0 training180/8000（19:18:12.689409+08:00），GPU1 B0 training580/8000（19:18:23.902610+08:00）。queue与worker为分别读取的时间戳，B0行更新稍晚；其余七组PENDING。已收到实际训练步，尚无选模/评价指标或原始gradient文件，不作为实时PID查询和精度结论。本次目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d26_bidirectional_20261002T191253_1513109。[启动证据](../../records/research_d26_launch_observation_20261002/user_reported_launch.json)；固定执行52f94388b1a9c7557e9ef533075661139cd55eda。

九组×8000、GPU0/1两H10080GB、物理batch16无累积、nohup、zzx目录约定不变，不再资源/预算审计。J0/B0已进入训练，剩余七组由动态队列领取；首训练步已观测，原始gradient文件及评价结果尚未收到。按照[冻结协议](../protocols/D26_BIDIRECTIONAL_FEATURE_PLAN_20261002.md)推进，不重训单模态、扩预算或自动扫参。

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D26_DIR="/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d26_bidirectional_20261002T191253_1513109"
D26_PY=$(python -c 'import json; print(json.load(open("records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$D26_PY" -B "$D26_DIR/code/scripts/status_rebuild_v1_d26.py" --directory "$D26_DIR"
tail -n 20 "$D26_DIR/nohup.log"
```

训练step>0已观测，原始gradient记录仍待回传后再核验；若TECHNICAL_FAILURE，先读该任务日志尾，不重开队列。第一正常完整任务结束后ETA采用实际耗时。九组结束查看screen_result.json/results.csv并按[执行说明](../protocols/D26_EXECUTION_20261002.md)上传轻量原件；从GitHub直接读长输出、离线核对矩阵与预设gate。最多一条成立机制另立seed/独立场景协议，失败不自动追训。

研究阶段仍可行性探索，双方信息互补主问题不变，C1旁支、强基线和最终贡献角色不变。历史held4不独立、Test6禁读。启动不是精度结果。


## 2026-10-02 19:18进度同步与结论边界

[逐任务观测](../../records/research_d26_progress_20261002T191819/observation.json)、[用户输出](../../records/research_d26_progress_20261002T191819/user_status_stdout.txt)、[暂估结束时间](../../records/research_d26_progress_20261002T191819/eta_estimate.json)已提交。controller PID1571946及本次目录保持，不重复启动。当前只有运行推进证据，D26没有新增精度/频率/语义贡献结论；既有D15—D25结论已在GitHub记录，不因本轮运行改变。

截至本次回传，整轮暂估还需8–12小时，约10月3日03:00–07:00；这是早期速度外推，后续交互/完整评价尚未计时，服务端仍报告ETA_PENDING。第一正常任务完整结束后更新，不额外资源探针。以本分支共享记录为准，不能只留本地或聊天；checkpoint/预测/完整实时日志仍在服务器，完成后上传轻量评价原件再分析。


## 2026-10-02近期文献阅读补充

[双向互补、缺失补偿与频率机制阅读](../literature/D26_RECENT_PAPERS_MECHANISM_READING_20261002.md)补充KTB、DIS2、SGMA、功能熵、MFFNet/FDAM、EBMC和SynIB的机制边界。新增建议为独有信息保持、双向任务补偿与编码频率衰减的条件检验，均未采纳为新运行/贡献。D26固定九组及去留规则不变；完成后优先用现有结果定位瓶颈，按证据选择至多一项，不重启资源审计或重复单模态训练。最后服务器状态仍以已归档观测为准。
