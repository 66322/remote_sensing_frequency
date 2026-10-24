# 2026-10-11 23:34 后的具体实验与GPU排期

状态：原队列正在执行；本文记录排期解释和后继准备范围，不新增运行队列，不改变科学协议或已加载执行快照。

最后服务器只读查询2026-10-11T23:34:24.796568+08:00：queue观测23:34:17.832878、RUNNING、controller LIVE=True。CONTENT_PRE/H8/F8 COMPLETE且worker退出；H8/F8均8000步。R8 GPU1 RUNNING/LIVE=True、8000/8000、phase=endpoint_ordinary（3_11/aux_down4，529/529窗口仅指该case）。R16/H16/F16/CONTENT_POST PENDING。3/8整项完成、1项评价中、4项待办；训练更新回报24000/72000，R8尚未完成整项技术验收。此为最后观测，不代表实时状态。

H8/F8完整worker耗时10338.760/10277.432秒（约2h52m/2h51m）；R8当前6936.955秒且仍评价。remaining_train_hours=0仅表示训练步数已满，不表示任务已结束。没有本轮精度或DSM内容原件，loss差不能作方法结论。

GPU0空闲可由原8k→16k阶段依赖解释；status回报未包含gpu_blocked字段，不能仅据利用率断言release状态。控制器需H8/F8/R8整项COMPLETE并完成三组batch配对检查后才派发16k。若两卡启用、无外部占卡且技术检查通过，按现代码GPU0→R16、GPU1→H16，先完成卡→F16。无需重复enqueue、rejoin或手动启动worker。

## 当前阶段的可执行顺序

|顺序|GPU0|GPU1|切换条件|
|---|---|---|---|
|23:34最后观测|本队列无活动worker，用户报告利用率0|R8固定终点评价|R8完整退出、controller验收成功|
|16k首批|R16新16000步|H16新16000步|三组8k技术完成、batch配对通过、卡启用且无外部进程|
|16k后续|先空闲的任一卡承接F16，另一卡继续原任务|同左|共享队列自动派发|
|训练结束|一张可用卡跑CONTENT_POST|另一卡空闲|R16/H16/F16全技术完成|
|收尾|汇总、显式上传轻量原件|无新增GPU工作|全8项COMPLETE并进程退出后按原上传入口|

R16/H16/F16均从S1-0独立初值和新优化器开始，不是8k checkpoint继续加8000步。原8k、16k配对预算/日程与R16主候选不变，不按8k成绩淘汰16k。单卡被用户释放后，任务保存退出并在另一张启用卡排队续跑；释放卡供用户使用，不自动占用。

H8在21:39:17完成，到23:34:24已约1h55m没有本队列后续GPU0任务，这是阶段屏障的利用率代价。代码不支持热插入新族；改动磁盘脚本不会改变现controller已加载逻辑，直接开16k worker会与controller登记、partial目录和证据绑定冲突。本轮不热改、不重启、不绕过8k完整验收。后续新队列设计可将独立任务依赖做细，但须先实现/验证并形成新的执行版本。

## 下一轮具体准备及推理顺序

依据[设计评审](STRUCTURED_FAILURE_EVAL_V0_20261011.md)，Phase 1A固定四系统（D25 P6 RGB-only、S1-0、M000_masked、M000_context）、四mask家族（U-pixel、U-block-random、S-grad、语义匹配U-block-matched）、20实现、两Val2，640缺失逻辑输出case＋8clean，新增训练0。它未实现/未登记，不能当作现成可启动队列。

准备交付按以下依赖完成，不因某卡空闲跳过：
1. CPU生成器：精确面积、块primitive一致、无重叠/裁边、固定随机流、梯度位置规则与语义匹配算法；只用输入/标签检查可行性，不读模型结果调参数。
2. known-answer计数核验：same-support damage、tile池化、seed均值、no-Car、harm/rescue、healthy空集合NA、mask与模型绑定；同时核对真实模型前向。
3. 冻结20组mask bank与全部SHA、完整解析配置、推理断点记录和卡释放逻辑，明确匹配失败处理。
4. 原训练队列完成、原件接收与阶段检查后，查询卡/进程/锁；再使用独立目录登记Phase 1A。没有第二个常驻队列在等待或抢卡。
5. 正式推理先做8个clean逻辑基准并核对同源端点，再按mask ID的成组任务分配两卡；每组保留完整模型/家族/tile对应，不按中途效应改mask、换主模型或扩大样本。
6. 完成640case后一次分析；Phase 1B M333复核与Phase 2新训练依证据安排，均未自动授权登记。

当前可先完成本地轻量CPU实现准备；服务器训练期间不启动大量mask生成/影像扫描或GPU诊断。此排期文件本身不代表上述实现/测试已经完成。Test6/held4/final不访问，不自动增加训练seed或重试失败配方。

## 时间估算口径

已得到H/F的完整8k worker约2h51–52m，以及H/F/R训练计算步速约0.6466/0.6564/0.6689秒。16k纯训练约2.87–2.97h/组，此外还有初始评价、4次验证、完整终点、可能的次要checkpoint评价、读盘和散列，不能按训练小时直接承诺完成时间。R8正进行ordinary评价，后续还有U/E及可能的次要选模评价，529/529不是整轮评价结束。

排期为两轮16k卡槽（R16与H16并行，再F16），另含R8剩余评价和CONTENT_POST；完整16k首项耗时仍未测。保留一天以上弹性，无24h截止。新Phase 1A耗时须以自己的首正式批次校准，不能用训练step速度推算。

来源：[23:34用户终端原字段](../../records/research_post_t_paired_v2_20261011T182543_3880702/user_reported_progress_20261011T233424.json)。执行代码核对版本44e4df5afbaeb603e6441e7ef14ff09f228bc027：scripts/control_post_t_paired_v2.py、post_t_paired_v2_runtime.py、run_post_t_paired_v2.py。
