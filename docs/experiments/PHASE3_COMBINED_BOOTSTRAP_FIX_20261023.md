# 合并队列启动前故障与修复（2026-10-23）

状态：SERVER_PRELAUNCH_FAILURE_FIXED_LOCALLY_AWAITING_TARGET_ENVIRONMENT。代码修复提交：[e65c6cb0830985461b3cd30e2f43158dd3d858cb](https://github.com/66322/remote_sensing_frequency/commit/e65c6cb0830985461b3cd30e2f43158dd3d858cb)。不是训练失败或科学机制结果。

## 已接收证据

用户提供服务器终端粘贴全文，副本见[终端证据](evidence/PHASE3_COMBINED_PRELAUNCH_20261023.txt)。服务器日志原件没有直接接收，本记录不宣称全量服务器原件验收。

- 主机提示符 h-aoji-aoji-h100-agent-1-m-0，环境 remote_sensing，Python路径 /home/jovyan/miniconda3/envs/remote_sensing/bin/python。
- 2026-10-23 21:50:30 nvidia-smi显示物理GPU0/1为H10080GB、无计算进程。M2预检最后观测21:52:05+08:00，两卡ready=true；这不是当前实时空闲保证。
- 实际Torch为2.1.2+cu121，CUDA可用。冻结的M2/J/R/T/V运行代码要求2.2.2+cu121；此前助手只检查了CUDA可用，遗漏准确版本核对。
- combined inspect：m2_runs=[]、combined_runs=[]、catalog_present=false。
- M2 inspect通过，Fit12按geospatial_centroid_axis_0分折，labels_used=false；出现INSPECTION_ONLY_NO_RUN_REGISTERED。具体tile顺序及三折见终端证据，不重新编造。
- 21:52:54登记命令的启动日志为 /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/phase3_combined_bootstrap_20261023T215254.log，启动PID2140296，随后Exit1。故障输出没有额外时间戳。
- 第一个目标检查test_phase3_combined_plan.py共4项，3通过、1错误；错误为源码包缺 configs/phase3_combined_execution_manifest.json。后续两个检查尚未运行。

## 原因与范围

90b9bbe启动脚本下载清单到内存，只把清单files里的18个载荷写到包中；清单本身不在自己的哈希列表中，也没有被单独保存。目标测试正确地要求清单存在，导致FileNotFoundError。本地仓库本来有这个文件，原先仓库内测试因此没有暴露打包遗漏。

异常发生在队列目录创建和控制器派发之前。本次调用没有进入正式登记/训练；尚无M2/合并队列注册成功回执。不能把这次启动前失败计作某个训练配方失败，也不能重跑科学实验来修复它。

## 修复

1. prepare_package保存同一次下载的清单原始字节，再下载并校验18个载荷；重用已有包时拒绝改动过的清单或载荷，不覆盖旧证据。
2. registration直接绑定本地这份清单SHA，不在登记尾部另下第二份。控制器同时校验清单SHA、清单载荷表与注册绑定。
3. 非inspect启动在任何包/队列登记前核对Torch2.2.2+cu121及CUDA可用性；不放宽原运行约束。inspect仍可进行目录只读检查。
4. 新增清单落盘/复用/篡改保护和错误版本前置拒绝回归测试。
5. M2继续固定ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd；合并计划仍为228作业/5,088,000更新，顺序、种子、输入、模型、损失和科学门禁不变。

## 验证

在本地没有.git的独立目录，使用真实18文件载荷，通过修复后的prepare_package生成完整下载包，清单逐字节和载荷SHA核对通过；从该包执行实际三个目标检查：6+2+3=11项全部通过。18个载荷中的Python文件均通过Python3.9语法解析。回执见[CPU检查回执](evidence/PHASE3_COMBINED_BOOTSTRAP_FIX_CPU_20261023.json)。

本地环境Python3.13.3、Torch2.7.1+cpu；GPU不可用并已在子进程屏蔽CUDA。以上只验证源码包闭合、接口与CPU合成数据，不是目标Linux/Torch2.2.2/CUDA实测或新任务真实数据验收。真实目标检查由用户在新环境重新登记时执行；无额外试训。

## 下一步

使用独立环境remote_sensing_phase3，避免改动旧remote_sensing。按[PyTorch官方2.2.2安装说明](https://pytorch.org/get-started/previous-versions/#v222)安装torch2.2.2、torchvision0.17.2、torchaudio2.2.2，CUDA12.1轮子；使用numpy<2并准备scipy、Pillow、tifffile、PyYAML，T/V另需rasterio、laspy的lazrs后端、pyproj。

旧启动日志和phase3_combined_package_90b9bbe...保留，不修补旧冻结包。改用本修复提交下载新bootstrap，新包独立命名；先inspect，如无既有合并队列再后台登记一次。新bootstrap会重新检查准确运行版本；不要单独启动M2。缺公开数据仍在后段WAIT_PUBLIC_DATA。

新路线选题建议继续保留，本次工程修复不改变研究角色。全部服务器快照/日志/包仍在/home/jovyan/zzx；没有SSH、无test访问、无自动种子或失败配方重跑。
