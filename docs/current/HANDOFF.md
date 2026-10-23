# 当前交接：合并队列启动前失败已修复，待正确环境登记（2026-10-23）

共享来源为GitHub rebuild-v1-protocol-20260915。当前主线RGB–DSM条件互补/退化缺失分割，恢复旁支；独立[连续地图维护选题](../experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)仍为助手建议，未实现或训练。

用户已尝试按90b9bbe启动合并队列。终端证据显示：最后GPU观测2026-10-23 21:52:05+08:00，物理0/1为H10080GB且ready=true；M2影像头预检及地理分折通过、未读标签；此前inspect无M2/合并目录，公开catalog不存在。随后启动前目标检查因缺执行清单失败，尚无正式队列/训练注册成功回执。不能把旧资源观测写成实时状态。

[故障与修复记录](../experiments/PHASE3_COMBINED_BOOTSTRAP_FIX_20261023.md)保存用户粘贴终端副本及CPU验证回执。根因是下载包遗漏其清单；已修复落盘、绑定和篡改检查，独立无.git下载包11项CPU检查通过。助手此前检查遗漏准确Torch版本：服务器2.1.2+cu121不符合冻结2.2.2+cu121；修复版在登记前拒绝错误环境。尚未完成目标Linux/CUDA验证。

当前合并执行代码固定[e65c6cb](https://github.com/66322/remote_sensing_frequency/commit/e65c6cb0830985461b3cd30e2f43158dd3d858cb)；替代90b9bbe的打包/前置检查。M2仍固定ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd，108×32k不变；J42/R18/T30/V30、总228作业/5,088,000更新及科学门禁不变。T/V数据/catalog尚未准备，B90/C81未开放。

立即下一步：用户在服务器新建独立remote_sensing_phase3环境，安装Torch2.2.2+cu121对应依赖；新提交bootstrap先inspect无重复队列后后台登记一次。保留旧包和失败日志，不修改旧冻结包，不单独再启动M2；不是重跑失败科学作业。失败不自动重试；缺公开数据在后段WAIT_PUBLIC_DATA。详见[执行协议](../protocols/PHASE3_COMBINED_QUEUE_EXECUTION_20261022.md)。

服务器由用户操作，无SSH，只用物理GPU0/1；现场再次检查外来占用。旧Val2/Test6/held4/final与新数据公开test封存。未来原件放/home/jovyan/zzx独立目录，中间数据有界内存回收。新选题不作为原队列前置。重要记录同步GitHub并回读；[修复前交接](../history/HANDOFF_20261023_BEFORE_BOOTSTRAP_FIX.md)已归档。
