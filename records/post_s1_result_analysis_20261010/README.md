# 2026-10-10 Post-S1旧完整、新部分离线分析

报告：docs/experiments/POST_S1_FULL_TRANSFER_PARTIAL_RESULTS_20261010.md。
evidence_commit f4815a7aa417b1b8344d33603b5e181e1c1ab078；旧完整提交3b7a694edea40014c49d7e1a3bd366d7d7e2ba36。
audit.json保存复算值、覆盖范围、上传原件SHA和完成快照；未下载服务器权重或预测数组。

复算仅需Python+NumPy，不运行模型：在本目录下建立old/new子目录，分别放旧evidence_20261010T212714313891_3255817、新completed_evidence_20261010T212934461958_3255079上传原件，以及对应非截断git_tree.json（相对子树）；至少物化audit.json所列原件和额外检查的JSON。保持gzip-base64-exact-v1原字节，不重新序列化。执行audit_full_partial.py后执行finalize_receipt.py。
程序可复用先前工作副本相同SHA的文件；缺失时须下载对应原件，不能生成缺失结果。基础ordinary别名的字节SHA与先前S1-0 summary完全一致，本次复用并重算。
旧E原计数覆盖P7/R0/S1-0，其他旧E组来自服务器汇总；D0/D1沿用以前审计。新T0—T4常规32项/U/初值/六E均核验。
审计通过不表示科学门槛通过、GPU复现或独立最终泛化；当前T7未收到。
