# 完整T离线原计数验收

最后服务器观测2026-10-11T08:45:44.211597+08:00，TRANSFER_COMPLETE_AWAITING_REVIEW；T0—T9十组全部COMPLETE/8000，CPU完成。快照2026-10-11T09:32:36.322168+08:00，原件379f301f255b9d2348cf11cad79e1374fedd1e7b。此为带时间证据，不是实时服务器查询。

95不同载荷、171828矩阵、20448joint边际；完整范围与局限见[报告](../../docs/experiments/POST_T_FULL_RESULTS_20261011.md)。

审计入口audit_full.py已内嵌本次实际使用的Audit与check函数，依赖Python/NumPy。按upload manifest取得已核对载荷到同目录received/，并保存该快照git_tree.json后运行；所需读取文件列表见audit.json的audit.read_names。程序原样执行同一计数/绑定/gate检查，不访问服务器或GPU。GitHub不重复上传大摘要。无GPU重现；ANALYZED。
