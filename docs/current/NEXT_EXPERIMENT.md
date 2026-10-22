# 下一步：现场核验并由用户启动一次性合并队列（2026-10-22）

1. 先读[合并队列执行合同](../protocols/PHASE3_COMBINED_QUEUE_EXECUTION_20261022.md)与[M2执行修订](../protocols/PHASE3_M2_EXECUTION_20261016.md)，核对服务器现有 M2/合并运行目录及物理 GPU0/1 当前状态。历史资源输出不是实时状态。使用最终提交的 `bootstrap_phase3_combined.py --inspect` 只读核验；若已有队列，不重复登记。
2. 用户在服务器终端准备目标 PyTorch/CUDA 环境后，按执行合同登记单一队列。M2 原108×32k先行，G0失败或作业失败即停止；J42和R18只在前段完整性通过后运行。M2-B/C不自动排入。
3. 3DCD/P³ 官方数据下载与 catalog 可并行准备。先核对2D/3D标签编码、DSM单位、三个不重叠地理开发组、P³ RGB/点云/COCO image_id 绑定；只把开发源路径列入 catalog。队列在 `WAIT_PUBLIC_DATA` 等候，不冒充已完成或自动跳过新数据方向。
4. 每段完成先核验作业数、端点与指标 SHA、逐 tile 原始计数、样本流及训练轨迹，再依据预登记判据分析正负结果。T/V 是探索，论文主张前必须补成熟基线和独立确认。重要结论及下一步同步 GitHub 同分支并回读。

不访问旧 Val2/Test6/held4/final 或新数据公开 test，不自动加 seed/重跑，不恢复整轮磁盘 logits 缓存。服务器运行由用户执行；本轮尚未启动。
