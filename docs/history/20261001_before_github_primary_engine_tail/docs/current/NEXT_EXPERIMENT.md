# 下一步：D23完整入口服务器工程验收

1. 用户终端顺序运行GPU0 smoke、GPU1 profile；每任务30分钟上限，先检查空闲与绑定，验证专家8/gate16单次backward、8组接口、14条件小图、3条件训练tile整图与已知缺失精确回退。全部文件留zzx对应records目录，无Val2/Test6，不是正式精度实验。
2. 回传summary/preflight/failure及实际峰值/吞吐。CPU22检查通过；未取得服务器完成记录前不能称完整实验已通过，不能引用旧两遍crop速度代表新缓存路径。
3. 核对完整12tile磁盘缓存与TCAP统计I/O、双卡并行资源、正式源码SHA和wall/job/磁盘预算，生成FULL_ENGINE_RUNTIME_ADMITTED锁后才生成8组各4000步命令。正式模式当前被预算锁拦住，没有默认启动。
4. 完成8组后按原screen逐项比较，frequency无独立增量撤回相应承诺，不扫阈值/半径、不自动续训或补seed。继续补A/双卡诊断原件归档，不重跑已有诊断。

新源码与界限见[入口验收说明](../protocols/D23_B_ENGINE_ADMISSION_20261001.md)。80GB H100取消gate梯度累积，专家固定micro8以保留已验证数值口径；有效batch16不变。研究角色、Test6禁读和门槛不变。
