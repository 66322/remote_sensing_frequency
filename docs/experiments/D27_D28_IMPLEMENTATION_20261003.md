# D27→D28连续执行实现与验收

2026-10-03用户明确要求“一起实现”：D27修复补跑与D28自动后接已实现并完成23项CPU行为检查（D27 15项、D28 8项），新增代码通过Python3.10语法检查。**尚无本次服务器启动观测，不能写成已运行或已经排队。**

## 执行范围

D27原十组S0/S1/G0/G1/L0/L1/C0/C1/L1-sh/C1-sh，每组8000更新，seed42、物理batch16无累积，原loss、增强、选模与科学门槛不变；training_batch修复保留treatment。D26不重跑，原D27失败快照保留。D27新repair目录与D28新pressure目录、联合执行索引目录分别保存。D29未实现或排队。

D28预指定RGB/DSM锚点、D26 B0、D27 S1/G0/G1/L1。固定7模型×16压力输入×2tile=224，另14 clean，共238次tile评价，无优化器、训练或test6读取。两侧各25%面积；共享/独立支持池配对具有完全相同的单侧边际。配方、强度、窗口512/stride256、推理batch8与FP32/TF32预先冻结。

## 工程边界

联合入口启动两个独立脱离终端的控制器。D28先写WAITING_D27；D27十组终态且原控制器锁释放后才核验所需selected checkpoint及SHA；缺项写WAITING_EVIDENCE并退出，不替换或重训。前序控制器非终态死亡写PREDECESSOR_CONTROLLER_STOPPED。两阶段只派发物理GPU0/1，每GPU一个worker。启动检查竞争进程，不测资源预算、不测吞吐探针；RAM/磁盘充足、H10080GB为已知约束。新控制器、worker、代码快照、缓存、临时文件、日志及预测均在zzx相应目录。

D28从D27不可变执行快照复制实际父依赖（D26父代码52f9438），并叠加自身代码；双方同一执行提交，保存code_manifest/plan/checkpoint_binding。压力mask不作为模型输入，模态可用性始终both_present。D27 fit_condition从selected checkpoint恢复，不用压力集初始化。每模型每tile先clean：与旧对应候选或固定锚点比较完整/NoBoundary整数矩阵及预测SHA，失败停止该worker，再进入压力前向。四支持组合共享变换缓存，减少重复CPU预处理。

保存逐case/tile/scoped int64 6×6、6^4稀疏联合计数、类别计数、受损/未受损分区、路由描述、checkpoint与源代码SHA，预测留服务器并索引。汇总先加原始矩阵再算IoU；等权四recipe/severity cell，只作开发筛选，不当独立重复或自然相关故障证明。压力结果不得挽救原D27失败gate，D29不自动启动。

## 本地验证及限制

D27实际training_batch→objective→backward，冻结锚点梯度、初始化、匹配容量、回退、路由粒度等15项通过；D28精确面积、边际匹配、标签独立、原始联合计数/空区域、终态、锁竞争、缺checkpoint不替换等8项通过。锁竞争测试使用模拟fcntl，尚不是服务器内核锁实测；CPU小尺寸与FakeExpert不代替真实DINO/ViT和CUDA验收。Python3.10语法检查通过。上一轮D27只有技术失败，新的CUDA启动、进度与科学结论仍须服务器日志。

## 启动/进度/上传

仅执行一次联合入口，命令见[下一步](../current/NEXT_EXPERIMENT.md)。保存输出LINK_DIRECTORY。该目录linked_execution.json提供D27/D28实际路径和PID。启动后应看到LINKED_CONTROLLER_STARTED 27和28；D27首步日志D27_TRAIN；D28 WAITING_D27。完成D27、锁释放和绑定后D28_STARTED。若只看到bootstrap PID，不足以证明接力排队。

结束后运行各快照upload_rebuild_v1_d27_records.py、upload_rebuild_v1_d28_records.py，交互使用GitHub凭据（控制器不存凭据、不自动push）；大JSON按原无损编码协议上传，权重/预测只上传索引。五入口本轮同步，实验结果需后续原件上传再更新。
