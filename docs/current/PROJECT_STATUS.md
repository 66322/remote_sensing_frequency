# 当前状态：Phase2.4原件验收完成，主门禁未通过（2026-10-15）

本轮Phase2.4已完成并完成GitHub原件/整数统计独立验收。原件提交76ae973b869eb3c377be4dae99fcb7224c9e2ac3；执行快照5a84f0eacabe5d6f1c7ed1638e6a9291c58e151f。

原科学门禁calibrated=False、probe=False；T0完成8000更新，T1/T2/T3未派发。原Phase2 L=False和B1/B3未派发不改。没有新专家、训练seed、Test6/held4/final访问或自动失败重跑。

主要发现：T0对旧B0的clean/P-U为+2.6180/+2.4989pp，但DSM-fault在两tile对静态reference为-0.4215/-0.3907pp、最差family×damage -1.8433pp。probe的RGB-fault对reference +3.4802pp，但clean/healthy保护失败。预登记stump对照选中RGB零值比例，zero条件收益强、down4精确回退RGB；它也未通过完整保护。不能用池化均值宣布安全，也不能称所有统计信号没有价值。

用户偏好继续为“暂不受期限限制，优先研究问题和创新性”。建议本轮候选收口，下一交付先做问题论证/数据可达性，停止默认同信息换融合头。真实几何质量观测A、物理高度/尺度表征B仍为建议，用户未选定、未授权新训练；原RGB–DSM条件互补/退化缺失分割主线、恢复旁支定位不自动改写。

独立核验3249分块、3014原文件、2972计数记录、242源码/配置；249248组整数CM、605088项联合边际、201696组correctness flow、2328来源锁、46560项跨阶段原系统CM对比通过；主摘要/主门禁/配对mask区间重建一致。T0有8000条基础流及401条轨迹。验证范围是归档和计数，不是GPU重新训练复现；服务器原数组/.pth未在本机重新hash，旧B0原batch流未再次逐行下载对比。

Potsdam Fit12/两张重复开发Val2（3_11、5_10）、seed42、NoBoundary mIoU_fg5；mask bootstrap不提供独立场景保证。T0/stump附加门禁是验收诊断，不替换原calibrated/probe入场，不倒写派发。

服务器完成状态最后观测：2026-10-15T00:13:16.405679+08:00，PHASE24_COMPLETE_AWAITING_REVIEW，SMOKE12/D1累计642/D2 642/D3 522/E1164，CPU_PENDING0，控制器与GPU worker均退出。该时刻运行事实不推断实时资源。

用户已完成HTTPS交互认证，上传入口输出PHASE24_GITHUB_COMMIT 76ae973b869eb3c377be4dae99fcb7224c9e2ac3并回读完成。评审端逐字节/原计数验收已完成。研究阶段从运行/待上传切换为本轮收口；科学候选未通过，不启动补救训练。

[完整报告](../experiments/PHASE_24_ACCEPTANCE_AND_ROUTE_REVIEW_20261015.md)；[验证](../../records/phase24_review_20261015/verification.json)。
