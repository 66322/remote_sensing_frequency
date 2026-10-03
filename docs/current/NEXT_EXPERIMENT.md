# 下一步：查询既有D30，完成后读损失拆解结果

D28已上传38b85f5并[分析完成](../experiments/D28_FINAL_REVIEW_20261003.md)，不重复上传或启动。D27四gate及D28现象/候选压力gate均未通过，保持冻结阈值；不激活原D29，不对失败配方加种子、扫权重或扩故障寻找正结果。D30是已获用户授权的独立损失机制诊断，不以D28正结果为前提，继续原48次固定混合评价与P/R/PR_area/PR_pixel四静态训练，复用S0/S1。它不是多种子验证，也不是重新开放旧路由贡献。若仅追平S0，报告配方修复；无组达到原预设实用增量/伤害底线则停止本配方，真正通过后另立确认协议。没有新增队列或方向决定。

D30最后存活检查2026-10-03T20:56:13.761513+08:00：重放12/48，四训练PENDING；没有更新的实时观测。查询不依赖当前目录：

```bash
D30_DIR=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d30_loss_decomposition_20261003T205144_2349167
D30_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$D30_PY" -B "$D30_DIR/code/scripts/check_rebuild_v1_d30_handover.py" --directory "$D30_DIR"
"$D30_PY" -B "$D30_DIR/code/scripts/status_rebuild_v1_d30.py" --directory "$D30_DIR"
tail -n 15 "$D30_DIR/nohup.log"
```

先48次固定checkpoint评价，再GPU0 P→PR_area、GPU1 R→PR_pixel，共32000训练步、seed42、物理batch16无累积。PENDING阶段屏障与日志按六次评价递增的done不等于停滞，结合时间戳和windows。此前3.5—4.5小时只是自启动的粗估，最新结束时刻应读status，不拿20:56进度充当当前值。

完成后同分支上传轻量原件：

```bash
"$D30_PY" -B "$D30_DIR/code/scripts/upload_rebuild_v1_d30_records.py" \
  --root /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro --directory "$D30_DIR"
```

结果读取顺序：plan/checkpoint/complete/source绑定→48重放与原路由→P/R/S0/S1的2×2→PR_area/PR_pixel单因素→selected/fixed8000→分项loss/梯度/分母→双方独有信息、QD伤害及逐tile/逐类→冻结gate。不只报最高分。D30若通过才另立确认协议，不自动加seed。

仅物理GPU0/1、两张H10080GB；内存/磁盘充足，无资源探针。物理训练batch16无累积，长任务nohup。快照、临时、缓存、日志均在/home/jovyan/zzx对应实验目录。用户终端操作，无SSH；Test6与独立final禁读，重复开发Val2不是确认性证据。GitHub本分支为共享权威，预测/checkpoint本体留服务器并索引。

[原设计与门槛](../protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)、[实现检查](../experiments/D30_IMPLEMENTATION_20261003.md)、[旧下一步归档](../history/pre_D28_review_20261003/NEXT_EXPERIMENT.md)。
