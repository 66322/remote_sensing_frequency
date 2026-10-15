# Phase3-M1：计算完成、服务器自检通过，待归档与独立验收（2026-10-15）

用户回传原恢复run `research_phase3_m1_recovery_20261015T164357_19327` 已于北京时间2026-10-15 19:16:19.431340进入 `COMPLETE_AWAITING_REVIEW`，日志输出 `PHASE3_M1_FINISHED`。11个新主训练共176000次更新完成，随后必需的推理及统计也完成。原执行提交09d67c7c30647031b888ef1315d721b867055cbd；32进程接续入口在318/320时跳过，本次正式结果始终由原执行器生成。

服务器自检：142608个整数矩阵、71280个联合表通过；11项配对样本流均exact，5项历史初始权重检查均exact，legacy_CM_exact及M00_42_causal_reuse_qualified均true；all_required_evidence_complete=true，missing_or_failed=[]。这些是用户回传的服务器自检结果，尚不是独立读取GitHub完整归档后的复核。完成证据与原始自检JSON见[本次记录](../../records/phase3_m1_completion_user_reported_20261015/observation.json)及[自检结果](../../records/phase3_m1_completion_user_reported_20261015/result_verification.json)。

首要M21-M11幅度门禁此前为false：seed17/tile5_10为-0.786910pp，违反不低于-0.2pp下限；C21/42与C21/17按预设跳过。计算完整与科学假设成立分别判断；其他主效应、交互、互补性、固定融合收益及损伤仍需完整摘要和联合计数复核，不能将技术核验通过写成研究路线成功。

下一步运行原绑定的 `code/scripts/upload_phase3_m1.py --directory <上述run>`，在前台完成精简证据上传，取得github_upload_receipt.json且all_parts_readback=true。上传不重跑训练、推理或计数；上传回读成功后清理自己的临时归档和Git工作目录。服务器完整结果归档回执尚未收到，本次提交仅存放完成观察和自检JSON。

随后以GitHub完整归档为准独立验收，并结合预设设计区分普通归一化、输入适配与统一幅度的作用。原控制器正常结束路径包含消费者退出后的缓存清理，但具体清理回执仍待归档审核；不额外删除输入、权重或研究证据。Test6、held4和独立最终数据仍密封，不自动启动后续实验。

## 精简包已生成，旧Git下载过大，准备API替代入口

用户已打包4168文件、56.27 MiB，Git Receiving在14%时已204.53 MiB。该流量是仓库对象下载，精确触发子步骤尚未定位。新入口 `scripts/upload_phase3_m1_api.py` 直接复用upload_tmp/core.jsonl.gz，经Git Data API提交本轮二进制分块和少量tree/commit元数据，不fetch/clone历史。API上传约75 MiB（含base64开销），公共原始文件回读约56 MiB。6项本地测试通过，目标机尚未执行。先Ctrl+C退出旧前台传输，再前台运行新入口；上传锁或旧stage进程存在时拒绝并发。若旧入口已成功则直接返回回执。令牌隐藏输入、不保存。全部回读通过且无存活stage进程后才清理本run上传临时目录。实验数据和接受门槛不变。

[API上传协议](../protocols/PHASE3_M1_API_UPLOAD_20261015.md)。GPU2—7的占用归属仍待UUID/PID检查，不能根据代码数字编号直接断言已证明物理显卡归属。
