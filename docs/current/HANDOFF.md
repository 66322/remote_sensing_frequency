# 当前交接：M2＋后续机制和新数据队列代码就绪，尚未运行（2026-10-22）

事实来源是 GitHub `66322/remote_sensing_frequency` 的 `rebuild-v1-protocol-20260915` 分支。用户确认上一实验 M2 尚未跑，并要求把既定 M2、同数据的条件几何/表征对照及新公开数据方向写成一起启动的队列；服务器终端由用户操作，无 SSH。本次仅写代码、合同和轻量测试，未查询服务器实时状态、未下载新数据、未登记或启动训练。

研究阶段仍为可行性/机制筛选。主线 RGB–DSM 条件互补与退化/缺失分割，恢复旁支。J/R 为主线的有限机制诊断；3DCD 高度变化 T 与 P³ 建筑对象 V 为独立探索，不自动改变论文方向，也不能从未经强基线对照的小网络结果声称创新。[研究决定](RESEARCH_DECISION.md)和[执行合同](../protocols/PHASE3_COMBINED_QUEUE_EXECUTION_20261022.md)给出角色、去留与证据边界。[原研究草案](../experiments/POST_M2_RESEARCH_OPTIONS_20261022.md)是候选来源。

执行链为原 M2（108×32k，原提交及门禁不改）→J（42×8k，冻结专家）→R（18×32k，公开初始化联合表征）→T（3DCD，30×12k）→V（P³，30×12k）。总计最多228作业/5,088,000更新，GPU0/1双通道串行阶段。仅 M2 G0 完整通过才能开始 J；J完整通过即可开始 R，不根据 J6 正负挑选。T/V 需要公开开发数据 catalog、三独立地理组、明确标签单位；catalog未就绪时状态 `WAIT_PUBLIC_DATA`。任一训练失败停止、不重试。原 B/C 仍未开放。

代码入口 `scripts/bootstrap_phase3_combined.py`（固定完整提交下载并核对 SHA）、`scripts/control_phase3_combined.py`（单队列控制器），`scripts/phase3_j_runtime.py`、`scripts/phase3_r_runtime.py`、`scripts/phase3_public_runtime.py`，配置 `configs/phase3_combined_plan.json`。运行目录全部位于 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records`。启动命令、状态文件和停止条件见执行合同。实际执行提交 SHA 以本次 GitHub 提交链接为准，不能将本交接里的 M2 冻结提交误作新队列提交。

证据边界：本地 CPU 单元测试与静态检查可证明接口及小样本数据流；尚无 Linux 双 GPU、真实 3DCD/P³ 样本、运行时/显存或科学结果验证。旧 Val2/Test6/held4/final 和公开 test 均封存；公开数据输入位置与标签值不能由模板猜测。后续先由用户做现场 inspect 与数据预检，再启动一次，完成后核验所有端点/指标/轨迹，重要结论写回 GitHub 并回读。
