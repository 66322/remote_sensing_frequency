# 诊断轻量原件离线审计
源提交f60491fc1091eb7d272e081e821d9e6397aa9c82，源目录records/research_post_n5_cross_20261006T235526_442218/evidence_20261007T075655372529_677219。
audit_result.json为本次独立复算，git_tree.json为353blob路径/大小/SHA清单。脚本scripts/audit_post_n5_cross_received_records.py只依赖NumPy/stdlib。下载239JSON原件，保持相对路径到输入目录，git_tree.json同目录，运行脚本--directory该目录，按脚本参数指定output；不调用模型/训练/数据集。

全部352载荷路径/大小核对；238 JSON载荷+manifest回读、原源/上传SHA校验。4128矩阵、1168 joint、192 case/576预测索引/106源码索引绑定，固定问题门槛复算PASS。代码manifest三旧plan JSON仅索引，未伪称源码全回读。没有GPU复跑、权重/数组/mask本体重新求SHA；first-batch/parity仅上传元数据验收。两Val tile单seed开发诊断，不当独立重复或泛化确认。

