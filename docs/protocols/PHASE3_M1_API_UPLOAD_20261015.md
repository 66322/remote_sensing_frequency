# Phase3-M1：复用精简证据包，通过Git Data API归档

## 原因与范围

用户原上传入口已打包4168文件、56.27 MiB，随后出现Receiving objects：23702对象、14%时已204.53 MiB、约786 KiB/s。这是Git从仓库取对象，不能解释为本轮证据包本身达到数百MiB。原脚本设置了depth1与blob过滤，但实际流量未实现预期的免历史数据下载。仅凭现有输出还不能精确判定是过滤协商、延迟取对象还是哪个Git子步骤触发；不编造根因。

本轮包保存JSON/JSONL联合计数、混淆矩阵、样本流校验、初始化/训练/恢复记录和摘要，不包含权重、原始RGB/DSM或逐像素预测。142608个整数矩阵、71280个联合表和样本流记录本身有合理的数据量。解决问题应改变传输方式，不删减不利实验或核验证据。

## 替代入口

`scripts/upload_phase3_m1_api.py --directory <已完成恢复run> --commit <本工具固定提交>`。

仅适用于research_phase3_m1_recovery_20261015T164357_19327及其原绑定。先获取同一个upload.lock，确认控制器锁释放、状态COMPLETE_AWAITING_REVIEW、自检完整，并核对原upload_prepared.json的文件清单、文件SHA和upload_tmp/core.jsonl.gz SHA。直接复用该文件，不重算、不重新打包、不改变实验源码。

如果旧前台上传仍在下载，先在那个终端按一次Ctrl+C，等待提示符返回，再前台执行新入口。它不会终止任何进程；发现旧上传锁或upload_tmp内仍有存活进程时拒绝并发启动。若旧上传已成功写回读回执，入口直接显示回执，不再上传。

用GitHub Git Data API创建本轮blob、以最新base_tree构建只修改本run归档路径的tree、提交后以force=false更新分支。不会执行git fetch、clone、checkout或下载历史blob。分支并发推进时只重新生成少量tree/commit元数据，最多4轮；不强推。已传分块的对象SHA存upload_api_checkpoint.json，可复用。远端同run已有不同归档则拒绝覆盖；同一归档则只校验回读。

凭据仅在服务器前台getpass隐藏输入一次，需要该仓库Contents写权限。令牌只发给https://api.github.com，不写入命令参数、日志、checkpoint、Git配置或归档。公共原始文件回读不携带令牌。请求目标仓库和主机固定。参考：[Git blobs](https://docs.github.com/en/rest/git/blobs)、[Git trees](https://docs.github.com/en/rest/git/trees)、[Git refs](https://docs.github.com/en/rest/git/refs)。

## 格式与传输量

仍保存原core.jsonl.gz的完整内容与原archive_sha256。每块2 MiB，以二进制core_NNN.gz.part写入Git；manifest设置part_encoding=binary，记录每块SHA256和decoded_bytes。旧入口为gz.b64块，新入口也支持校验已存在的旧格式。不重新编码原包的内部证据。

API请求本身需base64，因此56.27 MiB包约需75 MiB请求内容，另有少量元数据；逐块原样回读约56.27 MiB。总传输约131 MiB加HTTP开销，不承诺仅56 MiB，也不承诺固定耗时。不会下载数GB历史对象。

验收读取新归档时，按manifest顺序直接拼接binary块；旧gz.b64块先base64解码再拼接。先校验每块SHA与长度，再校验整体archive_sha256，最后解压JSONL并逐项校验内含文件SHA。原实验执行提交保持09d67c7c30647031b888ef1315d721b867055cbd；manifest单列传输工具提交与脚本SHA。

## 回读和清理

分支确认写入后按固定提交回读manifest、每块和三个摘要，逐块与整体校验；全部通过才写github_upload_receipt.json（all_parts_readback=true）。随后确认upload_tmp没有存活进程，再由原受限清理函数删除本run的upload_tmp，包括中断留下的Git对象副本。若有存活进程，保留目录、打印CLEANUP_DEFERRED，不发送信号。失败或中断时保留本地包及checkpoint；不会删除实验权重、输入、结果和日志。不使用GPU。

## 验证

6项本地测试全部通过：完整API模拟往返与清理顺序、远端损坏不写成功回执/不清理、对象checkpoint复用、并发分支不强推、旧base64包回读、不同远端归档拒绝覆盖。当前没有目标服务器令牌认证、实际上传和回读结果；准备完成不能记作归档已完成。
