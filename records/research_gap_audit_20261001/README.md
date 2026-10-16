# 本轮局部计数复核

日期2026-10-01，输入固定提交37adbaf5fb11a56b41052d3685565f418e9df8cb；范围与结果见[count_audit.json](count_audit.json)。

只检查D21 Potsdam seed42 R0/M0/F2各11条件、FullGT/NoBoundary两个scope。对每个6×6矩阵验证36项均为非负safe integer；逐tile逐元素相加与pooled一致；OA=trace(C)/sum(C)，fg5为前五类TP/(row_sum+col_sum−TP)等权均值，按原摘要单位比较。没有读取预测、影像或权重字节，没有复算全32项任务。R0/M0最终步与训练、评价记录的checkpoint SHA一致，但未重新hash二进制。

输入文件已经存在records/rebuild_v1_d21_compact_20260928/，本次没有转写原始矩阵。结果为摘要内部一致性及绑定复核，不是新精度实验、全量原始归档或独立确认。
