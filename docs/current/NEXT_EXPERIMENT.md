# 下一步：查询既有D30，完成后读损失拆解结果

## 2026-10-03新增规划：12组主体＋4组条件实验

用户要求结合实验与近期论文多规划几组，已形成[后续组合计划](../protocols/POST_D30_PORTFOLIO_20261003.md)及[论文核对](../literature/POST_D28_MECHANISM_READING_20261003.md)。A四组比较全特征/共享对齐与错配；B四新组＋复用A0构成局部对应×增强及错配对照；C四组比较双向缺失任务适配/蒸馏/教师正确筛选/同mask硬CE；F四组仅在B通过后检验两侧高频。先A/B八组，再C四组；每组拟seed42、8000步，未新增多seed。普通单模态锚点复用。

状态明确：**仅规划，未实现、未排队、未启动**。这是用户要求下的新机制建议，不改变D27/D28旧门槛，不激活D29，不改D30队列。计划写明匹配对照、继承预算、额外计算、候选停止条件与未实现接口；执行授权和真实排队状态另记录。主问题/候选/旁支角色不变，不能把规划中的新机制当已验证贡献。D30最新用户回传检查为2026-10-03 23:17；P/R与重放完成，最后两组仍运行，科学指标尚未收到。

D28已上传38b85f5并[分析完成](../experiments/D28_FINAL_REVIEW_20261003.md)，不重复上传或启动。D27四gate及D28现象/候选压力gate均未通过，保持冻结阈值；不激活原D29，不对失败配方加种子、扫权重或扩故障寻找正结果。D30是已获用户授权的独立损失机制诊断，不以D28正结果为前提，继续原48次固定混合评价与P/R/PR_area/PR_pixel四静态训练，复用S0/S1。它不是多种子验证，也不是重新开放旧路由贡献。若仅追平S0，报告配方修复；无组达到原预设实用增量/伤害底线则停止本配方，真正通过后另立确认协议。没有新增队列或方向决定。

D30最后直接存活检查2026-10-03T23:17:45.146029+08:00：控制器2349619 LIVE=True、ACTIVE_RUNNING；队列23:17:41记录training。replay_G0/G1均24/24 COMPLETE，P/R均8000步且COMPLETE；GPU0 PR_area2860/8000、GPU1 PR_pixel2420/8000。粗估剩余1.47小时，对应10月4日00:46左右，非结束承诺。本次未收到评价指标，results.csv尚未生成，不能从训练loss比较效果。

查询不依赖当前目录：

```bash
D30_DIR=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d30_loss_decomposition_20261003T205144_2349167
D30_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$D30_PY" -B "$D30_DIR/code/scripts/check_rebuild_v1_d30_handover.py" --directory "$D30_DIR"
"$D30_PY" -B "$D30_DIR/code/scripts/status_rebuild_v1_d30.py" --directory "$D30_DIR"
tail -n 15 "$D30_DIR/nohup.log"
```

先48次固定checkpoint评价，再GPU0 P→PR_area、GPU1 R→PR_pixel，共32000训练步、seed42、物理batch16无累积。PENDING阶段屏障与日志按六次评价递增的done不等于停滞，结合时间戳和windows。此前3.5—4.5小时只是自启动的粗估，最新结束时刻应读status，不拿旧观测进度充当当前值。

完成后同分支上传轻量原件：

```bash
"$D30_PY" -B "$D30_DIR/code/scripts/upload_rebuild_v1_d30_records.py" \
  --root /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro --directory "$D30_DIR"
```

结果读取顺序：plan/checkpoint/complete/source绑定→48重放与原路由→P/R/S0/S1的2×2→PR_area/PR_pixel单因素→selected/fixed8000→分项loss/梯度/分母→双方独有信息、QD伤害及逐tile/逐类→冻结gate。不只报最高分。D30若通过才另立确认协议，不自动加seed。

仅物理GPU0/1、两张H10080GB；内存/磁盘充足，无资源探针。物理训练batch16无累积，长任务nohup。快照、临时、缓存、日志均在/home/jovyan/zzx对应实验目录。用户终端操作，无SSH；Test6与独立final禁读，重复开发Val2不是确认性证据。GitHub本分支为共享权威，预测/checkpoint本体留服务器并索引。

[原设计与门槛](../protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)、[实现检查](../experiments/D30_IMPLEMENTATION_20261003.md)、[旧下一步归档](../history/pre_D28_review_20261003/NEXT_EXPERIMENT.md)。

## 23:17已完成组的只读部分结果

当前重放、P/R已完成，可先读取S0/S1/P/R的selected和fixed8000。以下只调用已有汇总函数读取完成原件，不调用总汇总main、不写screen、不占用GPU训练。保留率为0—1，scores为百分数；完整统计与绑定复核仍待上传。不能据此宣告PR_area/PR_pixel或总gate已完成。

```bash
D30_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
"$D30_PY" -B - <<'PY'
import json, sys
from pathlib import Path
base = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d30_loss_decomposition_20261003T205144_2349167")
sys.path[:0] = [str(base/"code"/"scripts"), str(base/"code")]
from summarize_rebuild_v1_d30 import summary, describe
plan = json.loads((base/"plan.json").read_text())
for age, tag in (("selected", "evaluation"), ("fixed8000", "fixed8000")):
    for arm in ("S0", "S1", "P", "R"):
        folder = base/("reused" if arm in ("S0", "S1") else "jobs")/arm
        if arm in ("P", "R") and not (folder/"complete.json").is_file():
            print(arm, "not complete")
            continue
        result = describe(summary(folder, tag, plan), plan)
        print(json.dumps(dict(
            age=age, job=arm, scores=result["scores_pp"],
            QD_harm=result["QD_harm"],
            only_rgb_correct=result["only_rgb_correct"]["retention"],
            only_dsm_correct=result["only_dsm_correct"]["retention"]
        ), ensure_ascii=False))
PY
```
