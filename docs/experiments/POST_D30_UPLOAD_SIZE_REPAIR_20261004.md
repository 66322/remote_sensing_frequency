# Post-D30轻量上传体积修复（2026-10-04）

用户终端上传失败：source_bytes=1899091199、upload_bytes=761504860、files=1751，超过512 MiB。失败发生在worktree创建、commit/push之前；无结果上传、无新训练/评价。沿用原控制器，不重启。最新服务器运行观测仍为17:21，A/B12项完成，C0/C1运行。

源码检查发现旧上传器只对≥1 MiB JSON压缩，所有中小JSON及log原样上传。实际各文件占比尚未收到，不能宣称该问题已经完全解释761 MB。修复将JSON/log阈值降至4096字节，仍采用gzip-base64-exact-v1，原始字节、大小、SHA256以及解码校验保持不变；不删矩阵、计数、配置或绑定，不提高512 MiB总上限/80 MiB单文件上限。数据/权重/预测仍server-only索引。原始文件不改动。

每次准备生成原Post目录下upload_preparation_*.json，包含原始/上传字节、source SHA与前20大文件。--prepare-only可只准备不触发Git；正常模式符合原体积门禁后直接上传。若仍超限输出前20项并停止，不自动扩大上传边界。正常命令见[NEXT](../current/NEXT_EXPERIMENT.md)。由于C仍在运行，未完成文件仅阶段快照，不能作为最终完成证据。

本地6项回归PASS：中等JSON/log逐字节恢复、小JSON可读性、聚合中等JSON超过旧门禁但压缩后可过、SHA/长度篡改拒绝。Python3.10语法检查通过。只是本地工程证据；服务器修复后实际体积与push仍待回报，A2/B3科学门槛未分析。
