# 下一步：用户终端登记已就绪N5四组

用户2026-10-06授权“按上述规划进行实验”。第一批[执行协议](../protocols/POST_N5_EXECUTION_20261006.md)、训练/掩码/普通与预留评价/汇总/队列/上传已实现，15项CPU与11文件语法通过。服务器登记/首步尚无回报，不称正在训练。最新服务器观测仍N2 10月5日22:11、诊断23:27全部完成。

运行scripts/enqueue_post_n5.py，使用本次发布的固定执行提交，不git checkout覆盖服务器原工作副本。该入口先核对原N1/N2/诊断完成/存活/锁与N5既有登记；只派发四组，两波GPU0/1，所有代码/临时/掩码/记录在zzx新目录。重复执行入口只报告已有N5，不自动再建一条队列。登记输出N5_QUEUE_REGISTERED和N5_LOG；随后用返回目录的code/scripts/status_post_n5.py只读查询，并查看返回nohup日志。

每组固定N1-2模型state、同新8000步/seed42/batch16。新增8/16槽native512网格对齐、U/H/L规则与方向预算配对，N5-3为固定候选。选模仍原clean/两全缺失三状态；Val2 T在完整协议冻结后生成，评价结果不改训练或选checkpoint。

四组完成后退出N5_COMPLETE_AWAITING_REVIEW；使用该目录code/scripts/upload_post_n5_records.py上传轻量原件，接收复算再按规划判定下一族。N3需要N5后独立边界问题仍在；R1需要E4；N4需要真实更新暴露；R2需要N5/N3各自通过。E3/E4/E5/E6及其余族尚未成为本批可执行任务，不能把条件预约当自动排队。无需重复确认已有条件执行授权。

技术故障停止新派发，可能已有worker继续；先status/log定位，不自动重训/重登记/改超时。具体超时12h/job、6h mask CPU；无效null在Popen前拒绝。CPU检查不是真实CUDA验证。

研究阶段可行性探索，主线RGB–DSM双向条件互补与退化/缺失分割；恢复旁支。Potsdam fit12/Val2=3_11、5_10，native512/stride256、NoBoundary fg5主。只GPU0/1、nohup、用户终端、无SSH/重复资源审计/新增seed/Test6/independent final。大权重/预测/mask留服务器SHA索引。

[扩展规划](../protocols/POST_N2_EXPANDED_PORTFOLIO_20261006.md)；[已验收结果](../experiments/POST_N2_E0_E1_E2_RESULTS_20261006.md)；[交接](HANDOFF.md)。
