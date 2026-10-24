# 长输出直接上传GitHub

生效2026-10-01，来源为用户要求“这种长输出可以直接拉到GitHub上读取”。共享分支rebuild-v1-protocol-20260915；用户在服务器终端执行，本地助手没有服务器直连。

本次工具scripts/upload_rebuild_v1_d23_engine_records.py只读取已有工程验收记录：
cpu_checks.log、gpu0/summary.json、gpu0/preflight.json、gpu0.log、gpu1/summary.json、gpu1/preflight.json、gpu1.log和最新compact_review_*.json。上传前验证摘要、preflight与CPU日志的SHA和设备绑定，并验证服务器轻量归档SHA。单文件5MiB、原件合计20MiB上限仅为此次轻量上传边界。

在本次实验目录内建立github_upload_<时间>_<pid>独立Git工作树，从fetch取得的远端提交开始。GitHub目的路径为records/<实验目录名>/evidence_<时间>_<pid>/，保留8份原文件字节并新增upload_manifest.json。Git只暂存明确列出的9个文件，非强制快进推送；另一台电脑更新分支时推送可能拒绝，上传提交和工作树留在原目录等待接续，不重置、删除或覆盖。

大型预测、权重和tar.gz不进入普通Git；upload_manifest.json保留服务器归档路径、大小和SHA，archive.uploaded=false。原件上GitHub后逐文件回读并复核矩阵/绑定，再更新current入口；上传成功本身不等于完整工程验收、正式预算批准或研究贡献成立。

执行不使用torch、不加载数据、不新增推理或训练、不占用GPU。所有服务器新增脚本快照、上传工作树及记录在/home/jovyan/zzx对应实验目录内。认证使用现有Git设置，仅在服务器终端完成，不回传密码/token或认证输出。

用户只需回复D23_GITHUB_COMMIT一行，或“已上传”；助手读取最新分支中的记录，不再要求粘贴完整JSON/日志。后续不同实验按对应目录与显式文件清单扩展工具，不能递归上传整个records/。若文件超出本次预算则保留服务器并单独规划归档，不截断原件或误称已上传。
