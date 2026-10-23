# 下一步：准备冻结环境，用修复入口登记合并队列（2026-10-23）

1. 不重复M1审计或改动旧包。已有用户回执证明M2影像头预检通过；90b9bbe合并调用因漏存执行清单在登记前停止。先保留失败日志与旧包，详见[修复记录](../experiments/PHASE3_COMBINED_BOOTSTRAP_FIX_20261023.md)。
2. 在服务器新建独立remote_sensing_phase3（Python3.9）环境，安装冻结Torch2.2.2+cu121及对应torchvision0.17.2/torchaudio2.2.2、numpy<2与所需依赖。原remote_sensing为2.1.2，不能直接登记。用户GPU0/1授权持续有效，现场再次检查占用。
3. 使用完整执行提交e65c6cb0830985461b3cd30e2f43158dd3d858cb下载bootstrap_phase3_combined.py；先--inspect核对没有已有合并队列，再用nohup后台登记一次。不要单独启动M2；新bootstrap在登记前检查准确Torch版本和CUDA，M2仍从ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd启动，原门禁不改。
4. 查看启动日志中的COMBINED_REGISTERED及实际目录queue_status.json/m2_bootstrap.log；没有这些回执不称已训练。首次真实目标检查失败则保留现场，不自动重试。M2 G0通过后J/R按完整性运行。
5. 3DCD/P³数据和catalog可并行准备，缺数据在后段WAIT_PUBLIC_DATA。公开test及旧Val2/Test6/held4/final封存，失败无自动重跑/加种子，全部原件在/home/jovyan/zzx；阶段完成核验原件与轨迹再分析并同步GitHub。

## 独立新路线的下一步

用户已授权继续探索，助手优先推荐[连续建筑地图维护](../experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。先在SpaceNet7公开训练源中冻结有效月份、真实事件数、AOI隔离、当期地图监督和前缀评价合同；随后实施B1独立重建/B3递归模型及B2简单滤波/迟滞重置，量化自然错误持续、变化发现延迟和GT旧图诊断差距。拟议首阶段为三个地理开发划分、seed42、六个训练作业，具体清单与预算尚待数据验包后登记，不表示已入队。

若简单方法仍有残差，再做单步/rollout与普通递归/拟议维护的正交对照；若无残差则停止该机制。完整核验纠正漏标保留备选，异步水域时间错配暂缓。新路线无代码/数据运行回执，不能启动现成命令。

该研究不作为既定队列的新前置，不隐含暂停、改排或自动追加任务；服务器训练仍由用户执行，实施时另建合同与独立目录。新主线需明确决定并同步入口。
