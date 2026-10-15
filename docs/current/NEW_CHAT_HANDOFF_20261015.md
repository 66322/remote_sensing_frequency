# 新对话接续：Phase2.4已验收收口（2026-10-15）

本轮Phase2.4已完成并完成GitHub原件/整数统计独立验收。原件提交76ae973b869eb3c377be4dae99fcb7224c9e2ac3；执行快照5a84f0eacabe5d6f1c7ed1638e6a9291c58e151f。

原科学门禁calibrated=False、probe=False；T0完成8000更新，T1/T2/T3未派发。原Phase2 L=False和B1/B3未派发不改。没有新专家、训练seed、Test6/held4/final访问或自动失败重跑。

主要发现：T0对旧B0的clean/P-U为+2.6180/+2.4989pp，但DSM-fault在两tile对静态reference为-0.4215/-0.3907pp、最差family×damage -1.8433pp。probe的RGB-fault对reference +3.4802pp，但clean/healthy保护失败。预登记stump对照选中RGB零值比例，zero条件收益强、down4精确回退RGB；它也未通过完整保护。不能用池化均值宣布安全，也不能称所有统计信号没有价值。

用户偏好继续为“暂不受期限限制，优先研究问题和创新性”。建议本轮候选收口，下一交付先做问题论证/数据可达性，停止默认同信息换融合头。真实几何质量观测A、物理高度/尺度表征B仍为建议，用户未选定、未授权新训练；原RGB–DSM条件互补/退化缺失分割主线、恢复旁支定位不自动改写。

独立核验3249分块、3014原文件、2972计数记录、242源码/配置；249248组整数CM、605088项联合边际、201696组correctness flow、2328来源锁、46560项跨阶段原系统CM对比通过；主摘要/主门禁/配对mask区间重建一致。T0有8000条基础流及401条轨迹。验证范围是归档和计数，不是GPU重新训练复现；服务器原数组/.pth未在本机重新hash，旧B0原batch流未再次逐行下载对比。

Potsdam Fit12/两张重复开发Val2（3_11、5_10）、seed42、NoBoundary mIoU_fg5；mask bootstrap不提供独立场景保证。T0/stump附加门禁是验收诊断，不替换原calibrated/probe入场，不倒写派发。

必读docs/START_HERE.md、RESEARCH_DECISION.md、HANDOFF.md、PROJECT_STATUS.md、NEXT_EXPERIMENT.md，以及完整验收报告和records/phase24_review_20261015/verification.json。

不要使用旧D2/T0进度、旧PID或认证排错命令。上传76ae973b已完成回读，评审已接收全部原件。服务器无SSH；未来终端工作仍由用户显式执行。当前没有待启动实验或待恢复上传。
