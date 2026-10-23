# 当前状态：合并队列启动前检查失败已修复，待服务器环境就绪（2026-10-23）

- 已接收用户终端片段：最后观测2026-10-23 21:52:05+08:00，物理GPU0/1 H10080GB且ready=true；不是当前实时状态。服务器Python3.9环境remote_sensing实际Torch2.1.2+cu121、CUDA可用。
- M2预检通过：Fit12影像头、geospatial_centroid_axis_0折分、labels_used=false；此前目录检查m2_runs=[]及combined_runs=[]。尚无正式训练注册成功回执。
- 90b9bbe合并启动调用在目标测试阶段因源码包缺执行清单Exit1；此时尚未创建队列/派发训练。旧包和启动日志保留。见[原始片段及修复](../experiments/PHASE3_COMBINED_BOOTSTRAP_FIX_20261023.md)。
- 新合并执行代码：[e65c6cb](https://github.com/66322/remote_sensing_frequency/commit/e65c6cb0830985461b3cd30e2f43158dd3d858cb)，保存并绑定清单、提前拒绝错误Torch/CUDA环境；独立无.git下载包11项CPU检查通过。目标Linux/Torch2.2.2+cu121/CUDA尚待用户验证。
- M2仍固定ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd，108×32k；J42/R18/T30/V30，总228作业/5,088,000更新及门禁不变，B90/C81未开放。公开catalog不存在，T/V真实数据及适配尚未验收。
- 下一步新建独立remote_sensing_phase3环境并按修复提交inspect、后台登记一次；不单独再开M2、不覆盖旧包、不自动重试科学作业。
- 保护范围：旧Val2/Test6/held4/final及新数据公开test继续封存。服务器由用户操作，无SSH；所有原件在/home/jovyan/zzx，中间数据有界内存回收。
- 研究角色不变：RGB–DSM主线、恢复旁支；独立[连续地图维护](../experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)为候选，未实现/训练。
