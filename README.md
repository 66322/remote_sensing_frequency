# Remote Sensing Frequency Segmentation

光学影像与DSM遥感语义分割研究。当前处于论文可行性探索：优先评估频率与语义可靠性融合及模态退化/缺失能力，允许同题换解法、换交叉问题或换方向。最终方法与章节未冻结；C1恢复是旁支候选，尚未取代原路线。

研究分支：**`rebuild-v1-protocol-20260915`**。默认`main`不代表该分支最新记录。

从[START_HERE](docs/START_HERE.md)进入，先读[研究定位与决策](docs/current/RESEARCH_DECISION.md)，再读[当前交接](docs/current/HANDOFF.md)、[状态](docs/current/PROJECT_STATUS.md)与[下一步](docs/current/NEXT_EXPERIMENT.md)。运行态只以带时间的证据为准；本仓库不是实时服务器监控。

## 执行与证据

遵守[执行边界](docs/protocols/EXECUTION_BOUNDARIES.md)和[实验准备规则](docs/protocols/EXPERIMENT_PLANNING_RULES.md)。GPU范围以对应已授权协议为准，历史GPU0限制或已完成两卡队列不能自动授权新任务。原始数据与预训练权重只读。大型checkpoint、预测和完整运行日志保留服务器，GitHub存放允许归档的摘要、配置与索引；不能据此声称全部原始产物已上传。

## 目录

- `model/`、`scripts/`、`configs/`：实现、执行入口与配置。
- `runs/`：服务器运行产物。
- `records/`：实验台账与紧凑证据。
- `docs/`：研究决策、当前交接、冻结协议、结果与历史。
