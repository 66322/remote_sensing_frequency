# D27 接在D26之后：固定执行说明（2026-10-02）

用户已授权“按照规划进行实验，添加到已有实验后面，之前跑完就进行这组”。十组代码已实现，14项CPU行为检查、11个文件Python3.10语法、三项标准库CLI检查通过；未连接服务器、未观测排队或CUDA执行。固定plan在records/research_d27_plan_20261002/plan.json。执行commit从本说明同一次提交取得；继承源码固定52f94388b1a9c7557e9ef533075661139cd55eda。

## 衰减和预算

S0/S1/G0/G1/L0/L1/C0/C1/L1-sh/C1-sh各8000，seed42、batch16、两顺序视图共享一次optimizer更新、无梯度累积，80k总更新。冻结现有RGB/DSM原专家；三个轻量残差头从零输出初始化，router从均匀权重初始化；共同fit统计取首个clean训练batch，存入checkpoint，所有组一致。原编码器不更新。head学习率2e-4、warmup100、相同AdamW/线性衰减；每500保存，4000/8000三状态validation选模，完整selected24条件评价与fixed8000诊断。

局部和类别路由是dense soft MoE，所有专家都计算；不宣称稀疏效率。专家辅助CE均在各自条件选中样本且两模态共有效的stride4采样标签上求区域均值，三个专家等权平均再乘0.1；完整候选CE按valid像素平均。保护项按原RGB正确且两侧有效区域平均，恢复项在仅DSM正确区域按当前出现类别宏平均，各乘0.1。两视图各0.5，空区域为0。GT/质量ID仅用于目标，forward没有这些参数。无实测GPU效果，CPU检查不当作精度结论。

## 看结果前冻结的细化

- G1为主要安全候选，G0为普通CE对照；静态/图像级/局部/类别完整2×4矩阵，两个打乱对照。先运行G0/G1，随后静态、局部、类别与打乱，组的科学id顺序不改。
- L1-sh固定半高半宽shift路由场；C1-sh对每个输入sample的fingerprint产生keyed随机类别条件置换，保持availability两通道，训练/评价均如此。没有全程固定可逆类别映射。
- 缺失内部已结构回退，伤害率应为0；L1去留中的“局部缺失伤害”落实为D26预先定义boundary16邻域计数（含单侧区域，额外伤害为0），不将恒等回退当新机制。H_R分母是RGB原本正确数，baseline伤害0时不宣称相对降低20%。
- 动态分工门槛：至少两条件族专家平均权重相差0.02，至少一个条件族专家argmax分歧率0.01。路由诊断来自重叠窗口/补齐尾batch，描述性而非独立样本N。
- 类别机制需至少三个fg类均值增益>0，无类均值损失低于−0.5pp；并按原建议相对局部与随机条件对照各至少+0.2pp。
- 增加dsm_present_zero与dsm_present_shift_half两个诊断，DSM仍标记present，用于区分同carrier head处理与有用DSM输入；不是missing评价或checkpoint选择条件。
- 零残差初始会使router/前级第1步梯度为0；检查其梯度存在有限，500步起要求所有学习路径已活跃。冻结原专家全程无gradient。
- 上述细化在新训练前冻结，不修改D26原screen或将旧方案失败重新命名。

## 接队列规则

新launcher只读取前驱：
/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d26_bidirectional_20261002T191253_1513109。

自己的code、plan、cache、临时文件、日志、PID全部在独立D27目录。复制原依赖时git show固定D26 commit；新代码git show固定新commit。主工作副本无需checkout/pull，新D27不会修改D26 plan/worker/queue。

等待期间每分钟输出D27_WAITING_D26，不申请GPU、不做预算或资源测量。必须前驱九个job都COMPLETE/TECHNICAL_FAILURE/TIMEOUT且controller状态终结，并取得已释放的前驱controller锁，才领GPU0/1。前驱某个技术失败不自动重试；当原队列正常结束并包含失败时，D27仍可独立运行，因为它只依赖既有原单模态anchors，不依赖D26候选checkpoint。原controller中断/worker仍活着则持续等待，需先恢复原队列。

设备只检查其他存活进程，暂占用时等待，不杀其他任务。每D27 job8h上限，仅停止新controller自己创建的进程组；技术失败继续其余组，整轮生成不完整状态而不伪造科学gate。terminal/nohup断开不会结束detachedworkers；手工controller中断须通过同执行commit的--resume-queue恢复，先检查旧worker仍活着，不重复启动。

使用同一个固定后接目录：
records/research_d27_safe_routing_after_d26_20261002T191253_1513109。
启动前若已有plan则拒绝新启动，防止同一后接任务重复排队。第一次启动用本提交的launch脚本和--parent。后台已启动/等待须由用户服务器输出确认；本地准备不能写成服务器已排队。

查询：D27_DIR/code/scripts/status_rebuild_v1_d27.py --directory D27_DIR，读取最后观测与worker进度。
完成后：D27_DIR/code/scripts/upload_rebuild_v1_d27_records.py --root ROOT --directory D27_DIR。上传原JSON/logs/矩阵/绑定，预测及weights只索引留服务器。GitHub为共享事实源；Test6禁读、Val2反复开发、held4历史暴露均不作独立final。


## 2026-10-02接力条件复核

用户要求确认实际排队和自动接力。原9e316adc固定launcher的九任务终态+前驱锁释放条件再次核对，针对前驱条件检查通过；新只读scripts/check_rebuild_v1_d27_handover.py核对PID命令所属目录/僵尸状态、180秒心跳、前驱终态和锁、活跃worker与日志，7项诊断逻辑检查通过。查询不触发GPU任务或资源测量。实际服务器排队输出仍未收到，GitHub只有实现提交，不能宣称“已在排队”。后接执行code/plan仍固定9e316adc2fa6fd1f2ee0a554d86c9b3f27d1f64c；新提交只增加诊断与记录，不改变执行绑定。
