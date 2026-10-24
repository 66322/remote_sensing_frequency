# Phase1.5独立离线核验

上传提交9d7c27e88c510f2931ac125b7b6b3b0c60850dce；证据源records/research_phase15_recoverability_20261012T233532_842792/evidence_20261013T113931418057_1206639。

[audit_result.json](audit_result.json)和[mechanism_checks.json](mechanism_checks.json)均PASS。全部2388载荷恢复原字节后核对manifest/源文件SHA与大小，1540逻辑case、100GPU批、D160/E120及执行/接管绑定；原计数复算范围见回执。[audit.py](audit.py)与[check_mechanisms.py](check_mechanisms.py)保留复算逻辑。程序路径对应本次本地decoded目录；复用时调整ROOT到解码后的工作副本，不需要服务器GPU。

GitHub文本接口曾归一化17个空文件/EOF/CRLF载荷；改用base64精确取回后全部字节校验通过，未改原实验。此处只提交新审计，不重复上传2388原件、数组或权重。部分计数相加检验是汇总一致性，不能替代服务器数组重算。没有GPU复现或原权重/预测数组本体独立哈希；次要signflip未独立复算。20mask及像素不作独立地点/训练种子。科学结论详见[分析报告](../../docs/experiments/PHASE_1_5_RESULTS_20261013.md)。