# 下一步：查询已登记N2状态与日志，不重复登记

最后服务器记录：原Post-D30于2026-10-05T00:26:01.590322+08:00 COMPLETE（18/18主体、F四项实际SKIPPED_GATE）；N1于07:21:14.003184 COMPLETE_AWAITING_STAGE_PROTOCOL（四项8000步、固定门槛False、N6三项实际SKIPPED_GATE）。两阶段轻量原件已上传并回读；C0—C5/N1-0—3十组20份summary的绑定、整数汇总和固定门槛复算通过。没有本次助手实时服务器查询。N2六组已登记，**实际训练状态/首步回报尚未收到**；N3/N4/N5仍待各自诊断和协议，不把旧预约状态当可执行。

固定C2剩RGB对C0仅+0.041525pp、对C1−0.004058pp、对C3+0.028336pp；剩DSM对C0−0.041961pp、对C1−0.016106pp、对C3−0.026610pp，双侧门槛False。普通C0已解释DSM锚点改善，完整输入复用固定B0，不承诺蒸馏增量。N1-3对N1-2综合−0.881059pp、clean−0.852801pp、DSM缺失−0.156095pp，最差tile差−2.054791pp；固定gate=False。N2按事前规则使用N1-2作为匹配基座，不叠加失败多深度入口。

## 已落实的新增实验

[N2冻结协议](../protocols/POST_AB_N2_EXECUTION_20261005.md)：同一N1-2初始state、六组同预算/容量，检验双向关系是否超过空间/单向/打乱。CPU8项检查PASS；GPU0/1两卡、每组8000步、batch16无累积、seed42，总48000更新。新结构真实速度待首个实际作业，不作精确完工承诺。技术失败或单作业8小时超时停止新派发，另卡已运行任务收尾；不自动重试。所有记录/代码/缓存只放zzx新独立目录。

## 当前N2只读查询

最后服务器登记回报：2026-10-05，目录时间标记08:58:29、日志名08:58:31（不是queue observed_at或精确训练开始时间）。N2六项登记成功，执行提交86b6a70e5c3482314986fb1259e2fccbd0a5a38b，目录`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_n2_20261005T085829_3456726`，控制器PID3456909，日志`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_n2_20261005T085829_3456726/nohup_20261005T085831972742.log`。本次未收到队列状态/首步训练/真实CUDA梯度回报，控制器存活及训练启动尚未独立确认；无需再次登记，不重启原C/N1。

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
NEXT_DIR="$ROOT/records/research_post_ab_followup_n2_20261005T085829_3456726"
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$EXP_PY" -B "$NEXT_DIR/code/scripts/status_post_ab.py" --directory "$NEXT_DIR"
tail -n 60 "$NEXT_DIR/nohup_20261005T085831972742.log"
)
```

回传状态及日志末尾，确认服务器CPU检查、原队列释放及首个N2作业训练进度。查询不启动、恢复或重建任务；出现异常先诊断，不再次登记或重启旧队列。N2完成后使用新目录/code/scripts/upload_post_ab_n2_records.py --root ROOT --directory 新目录前台上传已有轻量结果。

原C/N1最终原件已验收，无需再次上传本阶段；[完整结果与边界](../experiments/POST_C_N1_RESULTS_20261005.md)。N6实际跳过，N3/N4/N5保持条件研究；不追加C/N1配方救gate。

主线仍RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复是旁支；仍为可行性探索，无确认性新贡献。不重训A/B/C/N1、不增加seed或扫参、不启动F/N6、不访问Test6/independent final。服务器由用户终端执行，无SSH；只用GPU0/1两张H10080GB，每卡一worker，nohup；全部记录/快照/缓存在zzx对应独立目录，不重复资源审计。
