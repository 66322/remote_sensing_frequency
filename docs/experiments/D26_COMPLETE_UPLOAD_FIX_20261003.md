# D26完成观测与轻量上传修复

记录日期2026-10-03。来源为用户回传服务器status及上传报错，非助手直连观测。

D26 queue最后观测2026-10-03T04:04:45.239849+08:00，COMPLETE9/9，完成时刻04:04:45.239824+08:00。J0/B0/CAP/X/XS/XF/XSF/XSF-shS/XSF-shF全部COMPLETE，step8000。该输出证明队列完成记录，不代替checkpoint/指标原件复核。

D26上传在Git worktree/commit/push之前因原文总量超过512MiB而停止；没有最终结果上传成功。bash set -e使D27查询/上传未执行。D27最新已知观测仍2026-10-02 23:32 WAITING_D26，不能推定失败或完成。

修复两个上传脚本：超过1MiB的大JSON可用gzip-base64-exact-v1文本信封保留原始字节；只有压缩后更小时才使用，原大小/SHA256内嵌，上传前逐字节恢复检查。小JSON与日志仍直接可读，服务器原件不改。upload_manifest新增source_files（原文SHA/大小/编码标志），files仍是实际Git内容SHA/大小。512MiB限制现作用于编码后上传内容，单文件80MiB限制保留。不会启动训练/评价。

读到record_encoding=gzip-base64-exact-v1的JSON，须先Base64解码→gzip解压→核对大小/SHA，再解释原JSON；不可把信封当原评价对象。恢复工具scripts/decode_rebuild_light_record.py，--input编码文件 --output新路径，拒绝覆盖已有文件。服务器恢复输出也须放zzx对应目录。

本地三脚本Python3.10语法检查通过；2,800,082字节模拟联合计数记录压缩为5,773字节；原字节、Unicode及int64最大整数精确恢复，小JSON原样保留，错误大小和SHA被拒绝。这只是编码行为检查，不能代替服务器真实上传验证；实际压缩比例以D26/D27_UPLOAD_PREPARED为准。

下一步重传两轮轻量原件；如某一轮仍失败保留错误输出，另一轮可独立上传。收到提交后复核19组状态、指标、矩阵和冻结gate，不把COMPLETE直接当正结论。不需要资源探针或重跑实验。
