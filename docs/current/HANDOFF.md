# 当前交接：D23正式训练已启动并已进行nohup接续

更新：2026-10-01；来源为用户本对话回传，未直连服务器。最后观测没有独立墙钟时间；日志启动标识为20261001T153823，不能冒充实时状态或完成时间。

研究阶段：可行性探索。D23-B用冻结R0/M0专家的八组门控对照，判断语义/频率可靠性能否在退化与缺失条件下产生独立收益。C1仍为旁支，部分解冻为强基线，方向未改。见[研究决策](RESEARCH_DECISION.md)。

## 最后观测与执行绑定

- 正式训练已启动，用户此前日志显示TSF/T0到1000/4000步；随后前台停止并进行nohup接续。
- 最近回传：controller PID746195，GPU0 TSF PID746207，GPU1 T0 PID746208；后台日志有0.5和1.0分钟心跳、xFormers警告。已确认当时进程存在，尚未取得接续后超过1000步或4000步完成证据。
- 唯一本次目录：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d23_b_formal_20261001T152548_658274
- 后台日志：该目录/nohup_20261001T153823_658274.log
- 原启动提交6ba4b49608f6eaae182611f5757685506447c534；nohup接续入口846403ccc83c97731eceb199de99d9049039e64b；工程绑定和runtime lock沿用已验收快照。
- 不再执行“先Ctrl+C再nohup”的历史迁移步骤，不重复启动八组，不修改正在运行的快照。下一步见[NEXT_EXPERIMENT](NEXT_EXPERIMENT.md)。

## 已完成且复用

D23-A互补诊断均值+1.888456pp仅支持准备B，不是可部署收益。CPU/双卡工程验收已完成；预算原件提交54e19cd16416b866bed7b152ba9a3a3f76ac4837已核验13原文件、196矩阵，两卡固定预测及TCAP统计一致。GPU allocated峰值约2.44GiB、主机RSS约12.60GiB。不要重跑smoke/probe/资源预算；新对话不是重验收理由。详见[不可重复事项](DO_NOT_REPEAT.md)。

## 冻结协议与去留

八组T0/TS/TF/TSF/TCAP/TSF_CE/TSF_shuffleS/TSF_shuffleF，seed42，每组4000步固定final的既定开发筛选例外。专家micro8、gate16、两视图联合损失一次backward，无梯度累积。GPU0依次TSF/TS/TCAP/shuffleS；GPU1依次T0/TF/CE/shuffleF。Val2两tile×14条件，六固定对照与每组，NoBoundary fg5主口径，Test6禁读。完整冻结约束见[正式执行协议](../protocols/D23_B_FORMAL_SCREEN_EXECUTION_20261001.md)。

频率无独立增量则撤回对应贡献；gate无收益则关闭这个具体解法，不自动降阈值、补seed或把C1升主线。单seed Val2属于开发证据。光学整幅缺失、未知缺失识别、独立泛化及历史原件完整归档仍未解决。

资源：用户授权GPU0/1两张H10080GB，主机内存/硬盘充足；全部记录在zzx对应目录；长实验nohup。后台无交互Git认证时计算完成后前台运行输出的上传脚本，用户只回传提交号，助手读取GitHub原件。

本轮仅修正文档接续和吞吐决策约定，未启动、停止或修改服务器实验。用户不接受继续重复资源审计；提速建议见[代码审阅](../experiments/D23_THROUGHPUT_CODE_REVIEW_20261001.md)，尚未部署。旧交接归档docs/history/20261001_before_execution_contract/。
