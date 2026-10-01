# 当前交接：D24双卡队列已启动，查询已有目录

更新2026-10-02 00:19:37（Asia/Shanghai）；共享分支rebuild-v1-protocol-20260915，本页所属提交为最新文档版本。固定执行提交cf1955d966163978b5c8af433f3845b5ca05da9e；启动须绑定此版本。上次交接[归档](../history/HANDOFF_20261002_BEFORE_D24_TRAINING_OBSERVATION.md)。

最后观测：用户回传队列时间2026-10-02T00:18:59.788679+08:00，QUEUE=RUNNING、COMPLETE=0/15；A0 GPU0 training 2360/4000（00:19:02.780409），A2 GPU1 training 2140/4000（00:19:01.680178），其余13组PENDING。A0第2000步选模后已继续训练；双卡均有持续步数增长，初始化阶段已结束。见[进度证据](../../records/research_d24_progress_20261002T001859/observation.json)。这是用户回传最后观测，不是服务器实时直连；梯度检查原件与新效果指标尚未收到。

实际目录：`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d24_overnight_20261002T000843_877409`，固定执行版本不变。D23 8/8已完成；原件6038520、完整分析7467082。无服务器直连，D23旧恢复及D24启动命令均不重复。

阶段仍可行性探索；光学可用时DSM有益融合、负迁移与缺失为问题主线。D23当前TSF具体解法关闭确认路径，所有gate综合低于M0_safe；不改旧阈值或追训，C1旁支、部分解冻强基线角色不变。用户要求多角度夜间规划后明确“按计划进行吧”，因此长队列执行已授权；具体方法是重写版实现，不是已验证贡献。

[D24科学协议](../protocols/D24_OVERNIGHT_MULTIPERSPECTIVE_20261001.md)15组全部实现：A表示×Pair四组，B同容量原型×类别CE四组，C光学CE/全域/纠错区域/打乱区域KD四组，D增强三新增组＋共享A2。15×4000=60000更新，seed42/fit12/Val2。训练物理batch16无累积，BF16训练/FP32评价，2000/4000 clean选模、选定后14条件记录。两个H10080GB、RAM/磁盘充足、nohup、对应zzx新目录；不重做资源测量。每job6h上限，技术失败保留、其他job继续，无自动参数扫描或复验。

15项本地CPU检查PASS，实际共用目标覆盖15组反传；mask整幅/局部精确回自身光学、last4/head梯度/教师冻结、B同capacity、C同数量空间打乱、优化器/EMA下一步恢复一致、线程预取顺序、int64计数及harm/rescue身份通过。[源码绑定](../../records/research_d24_overnight_plan_20261001/local_validation.json)。只有本地合成数据，Torch2.7.1+cpu；服务器Torch2.2.2+cu121的worker已启动；持续训练更新已由服务器回传日志支持，梯度检查原件与效果指标仍未收到，不能写成效果验证。

立即查询本次已有目录进度，不创建第二队列；[执行说明](../protocols/D24_OVERNIGHT_EXECUTION_20261001.md)仅用于查询、上传或确有异常时同目录恢复。GPU0 A0→A3→C0→D2→C3→D1→B1→B3；GPU1 A2→A1→C2→D0→C1→B0→B2。12训练tile常驻内存，8个CPU线程预取4batch；C仅DSM变化条件复用光学预测并完整留计数。D23绑定的固定预测直接复用，不重跑旧模型资源探针。所有快照/临时文件在新实验zzx目录；主工作副本不用切分支或覆盖。

服务器由用户终端执行，无直连方式；目录、两个STARTED及双卡持续训练进度已收到，继续既定队列。首步无需重跑；完整gradient_check与日志随轻量上传读取。完整长记录用自带轻量uploader上GitHub，二进制留服务器。不要再次询问已知设备/资源/目录/是否nohup。

去留按新协议的匹配CE/容量/空间否证比较；单seed双开发tile只能筛选，最多两条假设另立确认。通用更新/增强有效不等于机制有效，C的光学能力子问题不等于双模态融合贡献。Test6禁读；SGMA完整代码、RGSNet全文/频率新意及独立泛化仍未解决，不成为本轮其他机制启动的绝对前置。

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D24_DIR="$PWD/records/research_d24_overnight_20261002T000843_877409"
python -B "$D24_DIR/code/scripts/status_rebuild_v1_d24.py" --directory "$D24_DIR"
tail -n 20 "$D24_DIR/nohup.log"
```
