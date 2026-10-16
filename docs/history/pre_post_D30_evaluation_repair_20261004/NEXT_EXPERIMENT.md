# 下一步：查询已排队的18＋4机制队列，收齐D30原件

最后用户回传检查：Post-D30队列2026-10-04T00:11:46.062560+08:00为WAITING_D30，控制器PID2450552 LIVE=True，18主体0完成、22配置任务均PENDING且无活跃worker；D30队列2026-10-04T00:11:52.142311+08:00仍RUNNING、LOCK_FREE=False。正常等待前序释放，尚未开始新GPU训练。执行commit固定01ec8dee82f7e272f6a650aaf9f3e619a0e7c516，目录`research_post_d30_mechanisms_20261004T000812_2446364`。这次未提供D30各job步数/评价进度，不能继续引用23:17的步数为当前进度，不能更新剩余时间估计；四项完成指标已分析，PR_area/PR_pixel、重放效果及原矩阵待收。ps的ELAPSED字段数值异常，不作为运行时长或ETA依据。

已于00:08启动，不要重复执行创建目录或nohup启动指令。当前只做查询；控制器会在D30六job完成、有效汇总、锁释放且无前序worker后自动接力。D30科学gate失败或成功都可执行新机制诊断，技术失败则HOLD。

用启动打印的绝对POST_DIRECTORY查询，不依赖当前目录：

```bash
POST_DIR=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_d30_mechanisms_20261004T000812_2446364
POST_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$POST_PY" -B "$POST_DIR/code/scripts/status_post_d30.py" --directory "$POST_DIR"
ps -p 2450552 -o pid,etime,stat,args
tail -n 20 "$POST_DIR/nohup.log"
```

WAITING_D30才是活跃等待，结合LIVE=True与最后观测时间；RUNNING A/B/C表示接力；F SKIPPED_GATE为预设条件未过，不是技术失败。控制器PID不活跃或TECHNICAL_FAILURE需读对应log，不能盲目再次创建队列。已完成真实组之后提供粗略ETA，等待D30不拿旧时间估算。

新结果按需上传：

```bash
"$POST_PY" -B "$POST_DIR/code/scripts/upload_post_d30_records.py" \
  --root /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro --directory "$POST_DIR"
```

D30原件仍用已有目录下upload_rebuild_v1_d30_records.py显式上传；科学读取四项部分分析→PR_area/PR_pixel→重放→逐tile/类→双向伤害与保留→固定8000→预设gate。无需重新训练S0/S1/P/R。

主体18组144000步，粗估17—25小时，C额外前向可能更慢；条件F另4—7小时，首批正常完成时间可修正，非结束承诺。只使用物理GPU0/1，两张H10080GB；RAM/磁盘充足，无资源探针。seed42、8000步、batch16无累积、nohup。快照、临时、缓存、日志全部在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；Test6与独立final禁读。重复开发Val2不是确认性泛化证据。GitHub本分支为共享权威，大预测/checkpoint本体留服务器并索引。

[四项结果分析](../experiments/D30_FOUR_ARM_REVIEW_20261003.md)、[执行协议](../protocols/POST_D30_EXECUTION_20261003.md)、[机读计划](../../records/research_post_d30_design_20261003/plan.json)。

[旧下一步](../history/pre_post_D30_execution_20261003/NEXT_EXPERIMENT.md)。

[本次启动观测](../../records/research_post_d30_mechanisms_20261004T000812_2446364/launch_observation_20261004T000812.json)。

[00:11存活与等待观测](../../records/research_post_d30_mechanisms_20261004T000812_2446364/progress_observation_20261004T001146.json)。
