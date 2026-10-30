# Post-D30阶段汇总导入错误

最新服务器观测2026-10-04T08:41:43.586227+08:00：队列CONTROLLER_INTERRUPTED，控制器2698383 LIVE=False；A0—A5已全部COMPLETE（分别08:22/08:31/08:41），6/18主体完成，B/C全PENDING、F待门槛，无活跃worker。A评价恢复已成功且未重训；阶段A汇总子进程抛出ModuleNotFoundError: No module named 'model'，随后控制器退出。这是脚本搜索路径缺失：cwd=code不自动把code加入独立脚本的sys.path。导入路径修复已本地实现并通过6项回归（含实际汇总子进程--help）；尚无服务器第二次恢复启动观测。恢复在同目录建立新覆盖快照，保留原plan/code及A完成标记，不重跑A，重新生成A阶段汇总后接B/C，仅GPU0/1。

错误链：six A workers COMPLETE → launcher subprocess python code/scripts/summarize_post_d30.py cwd=code → evaluation → post_d30_data → model import失败。Python独立脚本以scripts目录作为sys.path[0]，父进程的sys.path插入不继承；此前CPU测试和wrapper各自补路径，因此没暴露阶段汇总入口问题。由此GPU空闲，不是六组A失败，也不是B/C跑完。

恢复器显式设置PYTHONPATH为immutable code、code/scripts，所有后续子进程继承；未来启动器设置同一路径，未来summarizer本身补根目录。现有code/、plan.json和完成记录保持原字节及签名，旧评价修复manifest不改；新覆盖manifest记录实际import roots。完成A不重新dispatch，原controller对全部A完成checkpoint/summary绑定复核并汇总，然后B/C及条件F原顺序接力。恢复启动前拒绝活跃控制器/worker，保留原队列备份。

回归6项通过，包括真实subprocess --help以目标工作目录导入汇总执行链，Python3.10语法检查4文件通过。这是本地工程证据，不等于第二次服务器恢复已成功；启动时会用服务器原immutable汇总脚本做同样入口检查，之后才接队列。无新训练设置、多seed、resource probe、test6/final开放。

D30原生紧凑证据已于214eb158a59cf8248910ba5e46492189d3a6f953上传，156文件、1134456字节；screen_result已回读。P仅综合门槛失败，最差tile/condition−0.076827pp；PR_area还存在最差−0.298852pp及fixed8000对S0−0.067831pp，不能称完全恢复安全性。PR_pixel仅DSM正确保留65.7654%、仅RGB正确90.1002%，QD伤害3.0660%，仍是明显信息取舍。完整逐tile原矩阵本体未上传，梯度原件已上传但尚未完成综合分析。

[启动指令](../current/NEXT_EXPERIMENT.md)；[原失败紧凑记录](../../records/research_post_d30_mechanisms_20261004T000812_2446364/summary_import_failure_20261004T084143.json)。
