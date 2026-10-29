# 下一步：A0首批能力探针准备与双H100预检（2026-10-29）

[A0具体执行合同](../experiments/POST_M2_A0_EXECUTION_20261029.md)及[scripts/post_m2_a0.py](../../scripts/post_m2_a0.py)已经写好，并通过本地语法/三项数据合同检查。状态CODE_PREPARED_LOCAL_CHECKED_SERVER_NOT_PREFLIGHTED；没有新训练、下载模型或修改服务器队列，不能报告新科学结果。

先在服务器确认独立Python≥3.10/Torch≥2.7.1环境、官方DINOv3 ViT-S/16 LVD模型权重取得与许可证、固定源码commit、DINOv2公开初始化、F0数据文件及两张H100/CPU/cgroup余量。接着按执行合同依次运行inventory→双模型smoke→训练和整图评价profile→两模型各2000更新→两模型两块训练内校准→screen。仅当校准达到预定门槛时，评价F0外层4块开发tile。每阶段首败停队，不自动重试；训练/评价耗时分别实测，低CPU/内存时双模型顺序执行。

A1 S0强RGB、S1普通RGB–DSM、S2 RGB+冻结教师、S3 RGB–DSM+教师四臂仅在A0存在可读增量且统一接口/预算冻结后另批实现；A2普通教师与空间错配控制须等A1正向。默认seed42，额外地理折与配对seed17按证据决定，不默认三seed。B/C/D/E/F仍沿[总路线](../experiments/POST_M2_CAPABILITY_PRIOR_PLAN_20261029.md)条件推进。

M2最终补充分析与大件清理仍待服务器回执，详见[交接](HANDOFF.md)；新A0不依赖旧运行权重，不能因它推迟已授权的删除。GitHub是两电脑共享权威，实际A0运行后上传小结果并更新本文件/注册表；上传后回读关键文件即可，不例行重复哈希。
