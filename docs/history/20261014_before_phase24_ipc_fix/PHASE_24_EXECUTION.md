# Phase2.4/条件Phase2.5执行协议（2026-10-14）

状态：**IMPLEMENTED_CPU_CHECKED_AWAITING_SERVER_SMOKE**。用户已要求“按照上述规划安排具体实验”；本提交完成代码与CPU检查，不代表服务器登记或运行。服务器由用户执行，无SSH。研究门禁以[规划协议](PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)为准；下面冻结工程口径。

## 研究任务与预算

|阶段|任务|新训练|
|---|---|---|
|启动检查|原Phase2队列/锁、原件/代码/权重/mask绑定、GPU0/1资源、Linux CPU检查；两卡真实梯度smoke及12个原CM桥接case|0|
|D0|原1164case CM拆解；P-U 640case完整预测边际的1000次跨像素参照，附属诊断，不作训练门禁|0|
|D1|clean2+P-U640=642联合流/标度诊断；复用启动smoke中10个核心case|0|
|D2|两组source→target温度、alpha、logistic和stump，仅源tile拟合/选择；642个全tile目标评价|0|
|D3|P-M320+dose160+ordinary42=522；使用已锁参数|0|
|T0|clean分布B0小头，对历史mixed B0；相同初始化、裁剪流、标签哈希、优化器和8k预算|1×8k|
|T1/T2|校准不足且实际跨tile probe保护门禁通过，才成对训练信号头/无信号控制|条件2×8k|
|E|所有进入头的4k轨迹与固定8k主端点，统一1164case，同一次专家前向评价多头|0|
|T3/E_T3|T1保护门禁通过且T1−T2≥0.3pp、两tile均正，才训练统计错配控制并评1164case|条件1×8k|

最多4个小头/32k更新；0新专家、0追加训练seed，不救原B1/B3，不访问Test6/held4/final。若门禁不通过，停止对应方案，不加任务凑一天。GPU0/1预留至少24小时，建议24–48小时起，没完成继续；无24h硬截止。真实吞吐通过服务器smoke后测定，状态脚本显示当前阶段估计，不把预约时长写成完成保证。

## 数据、锁与比较口径

原运行固定为 research_phase2_matched_20261013T151120_1310582，执行e5641e07。继承其完整SHA验证代码快照，再覆盖本提交新增模块；不改原目录。原plan/code/prepared三绑定、prepared索引、16k两专家及8k B0/B2端点逐项核验。实际输入是原9,792,000,000 bytes规范化数组，只读入RAM，不复制到新磁盘缓存；不重新访问未开放tile。外部DINO模块仍按原pretrained路径加载，12个原结果CM桥接是实际执行链的必要检查，不能把本地检查说成服务器权重已验。

主指标Potsdam Fit12/Val2（3_11、5_10）、seed42、NoBoundary mIoU_fg5；逐条件先池化两tile int64 6×6 CM，再做条件宏平均。Full、逐类、tile及all/missing/healthy/observed计数均保留。独有正确、三系统流和空间block摘要是计数诊断；两重复Val2及mask重采样区间不代表独立场地确认。

源tile采用2048 block及hash(42,inner,by,bx)%2划分fit/calibration，边缘512 guard。两模态、所有mask相同坐标的组别一致。最多2M行/1GiB有界样本，stripe内逆入选权重；这是guarded interior样本，不宣称全tile无偏。只在源tile fit组拟合温度/模型、源calibration组选alpha/阈值/λ/静态参考；目标全tile只评价。源偏好支持不足或特征常数返回受保护常数回退，不因无信号自动加样本/改阈值。每条目标计数绑定源参数路径和SHA，源参数两份保留。

## 数值和方法边界

原模型前向FP32、microbatch8（最后补齐8）、原TF32/确定性设置、原窗口顺序及nearest128→512拼接。两卡各6个真实case，检查原average/B0/B2、RGB/DSM的Full/NB和四ROI CM完全一致，GPU/CPU逐窗拼接bitwise一致，已知availability严格回退。两卡先做T0/T1/T2/T3真实CUDA backward-only smoke，0优化器更新、梯度有限且非零，失败即hold。CPU16/24/32候选依有效CPU配额裁剪，对同一匿名RAM case预热后测时并比较结果，选择最快配置；不另做专家前向。

原average/B0/B2及T0是window头。新温度/alpha/probe/G头是**post-stitch新决策类**：先用sum/coverage得到mean-stitched logits；概率/校准/NumPy决策FP64，特征FP32。非线性决策与窗口拼接不交换；不能称为原window融合的等价提速。probability mix是同一锁定alpha的附属敏感性结果，不混同旧equal-logit average。Torch/NumPy特征和非零小头导出有数值近似CPU检查，实际部署按上述明确口径评价。

T1/T2/T3网络相同，最后一层零初始化：
z=zRGB+tanh(h(features))*(zDSM-zRGB)，有符号系数[-1,1]，0.01 mean|gate|惩罚。
初始化严格等于RGB/availability回退且梯度非零，不承诺训练后clean自动受保护，仍需完整门禁。T2只把前13个质量信号槽置零，保留availability；名义网络相同，有效容量不同，不能把差异纯解释为某个物理机制。T3仅将3个DSM统计槽固定错位256输入像素：训练在512 crop内wrap；部署在整tile统计图内wrap，RGB/DSM原图、专家预测和标签不动。crop和tile包裹范围不同，作为预登记敏感性控制报告。

训练batch16、4个裁剪预取线程、4个待取批次。T0使用clean，T1/T2/T3复用原mixed损坏生成器；每一步与旧B0的8000个batch hash核对。专家冻结，优化器只含小头；不缓存整轮logits。T1/T2在GPU0/1各自执行同一配对数据流；推理与4k/8k多头评价共享专家前向，不宣称跨卡训练已经共享一次forward。

## 资源与产物

父进程不导入Torch/CUDA，规范化输入只读fork共享；两GPU模型常驻，动态分派独立case。每卡最多2个在途匿名Linux memfd包、<1GiB clean低分辨率logit缓存、8个mask LRU；CPU128行stripe处理，最后消费者ACK后关闭包。无磁盘数组fallback、无全轮head/val cache、无逐case全图预测落盘。所有socket/临时文件/库缓存都在该新实验目录，结束进程退出回收RAM。

读取有效CPU/cgroup RAM/GPU空闲，不沿用旧1.9TiB观测当实时值。RAM envelope须低于min(128GiB,当前有效可用RAM的25%)；常见192core配置约89GiB估算包络。另预留24core给数据/控制/null；大部分数值库每进程1线程，统计实际16/24/32并行。启动要求两卡至少24GiB可用且没有外部计算进程；GPU忙时不登记新队列，可在释放后再次执行登记入口。

磁盘启动要求4GiB可用储备，这是准入储备，不是整个实验硬上限。新磁盘只存必要整数CM、稀疏联合流/block摘要、来源、源参数、batch哈希、损失轨迹和小头端点；记录真实大小，不能继续声称需要600GiB缓存。rolling resume只保留一个，4k/8k轻量参数和计数保留；完整endpoint评价且CM复算通过后，自动退役rolling resume及4k临时pth，写逐文件SHA/身份回执。8k小头暂留待审，原专家/数据/旧运行不删除。

上传只使用显式白名单，将原JSON/JSONL和单份CPU检查日志按原bytes/SHA装为一个gzip JSONL的分块；不递归上传数组/权重/所有log。上传阶段有持久marker，断开后重新执行同一上传入口可继续，不另建科学队列。提交后fetch回读所有archive分块与summary/manifest。评审完成后再决定端点价值及后续依赖，不能在本轮提前删必要专家。

## 启动、状态、完成和失败

用户取包含本执行包的40位提交SHA，取出scripts/enqueue_phase24.py执行。入口先查询research_phase24_protected_*；存在即输出原队列状态并返回，不重复登记/派发。无替换/重试参数。控制器只接受REGISTERED状态；工程失败或外部中断停止GPU worker并记TECHNICAL_FAILURE_HOLD，不自动续跑失败配方。Linux CPU与真实GPU检查全部通过后自动继续D0–E及条件头，不需要逐阶段手动启动。

新目录由登记入口打印，位于/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase24_protected_<timestamp>_<pid>。查看：
python -B <D>/code/scripts/status_phase24.py --directory <D>
状态含QUERY_OBSERVED、LAST_OBSERVED、进程存活、GPU窗口进度、CPU并发、阶段case和当前阶段ETA。GPU空闲可为准备/源拟合/单条件任务；先读状态，不用GPU占用代替成功判定。

PHASE24_COMPLETE_AWAITING_REVIEW才表示完整结束。结果验证器重算summary/gate/配对mask区间、核对源锁和每条整数CM；验证通过才退役训练临时产物。用户执行：
python -u -B <D>/code/scripts/upload_phase24.py --directory <D>
不在后台无交互进程中等待GitHub密码，不自动启动后续专家训练。

## 本地验证与尚未验证

Windows/Python3.13.3/Torch2.7.1+cpu：20项测试中18项通过，2项Linux memfd测试跳过；14个Python文件编译通过。固定边际、分块CM/ROI/三系统流、特征halo、source/target分离、常数信号、原B0初态SHA、配对头初态、零初态非零梯度、Torch/NumPy导出及离线错误summary拒绝均检查。新D0从旧1164case原计数复算，640个P-U及六个gap差值与已验收结论在1e-10内一致。

Linux跨进程memfd、Torch2.2.2+cu121、两卡真实CM/梯度/吞吐/峰值均**等待服务器smoke**，不是已验证实验结果。[本地检查清单](../../records/phase24_execution_20261014/implementation_audit.json)。
