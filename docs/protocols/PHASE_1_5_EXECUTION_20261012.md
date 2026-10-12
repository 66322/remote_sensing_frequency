# Phase 1.5 双卡零训练执行协议（2026-10-12）

最新运行记录：REGISTERED_PROGRESS_NOT_YET_QUERIED（用户终端登记；[登记摘录](../../records/research_phase15_recoverability_20261012T232212_836118/registration_observation.json)）。执行包发布时状态为READY_NOT_REGISTERED。用户“按上述规划进行”并“继续”授权落实执行包；服务器仍由用户终端执行，助手无SSH。GPU0/1并行，未完继续，无24小时总截止。本协议落实[主设计](PHASE_1_5_RECOVERABILITY_20261012.md)与[具体规划](PHASE_1_5_TWO_GPU_PLAN_20261012.md)，执行版本PHASE15_V1_2_EXECUTION。

## 冻结范围

两张Potsdam Val2 3_11、5_10，native512/stride256、原FP32/TF32、micro8，seed42冻结模型；D15 DSM-only为原Train16/R50-ViT-B16 seed42、selected15000，明确legacy。图像/标签只经旧Loader读取Val2，Test6/held4/final不加载。20个旧mask ID1–20全部复用，不生成新realization，不重训、不新增seed。

五项E/A/B/C/D及科学去留保持原规划。E和C复用预测/计数；A与B做固定输入干预；D对intact DSM的五expert统一输入评价。DSM zero明确使用已有post_d30_data的dsm_present_zero：归一化DSM全0、dm仍True；它是present-but-zero/OOD参照，不是reported missing，不改变RGB缺失区可评价分母。

100个GPU工作批次，共1540个唯一逻辑case：20个reference、A1280、B80、S1-3 missing160。S1 intact clean两case复用，按上限1538次推理计，已合法smoke产物在全量复用。DSM-only两张预测覆盖所有RGB mask；RGB-only160旧预测复用。真实smoke的跨GPU重复、DSM独立性检查另记工程开销，不能当新科学样本。已有20-case旧T/26项机制诊断和两轮完成队列均不重启。

每case保存Full/NB、all/missing/observed/healthy/edge等支持的int64 6×6 CM、逐类新错恢复及配置/ckpt/mask/DSM-map/prediction绑定。ratio B另保存共同M5支持。A同时保存matched-DSM clean与intact clean参考。D保存raw/smoothed composition、pixel/128/256 oracle、五expert按GT类联合正确bitmask、分箱支持/正确数和来源比例。主要oracle gate为完整NB fg5、四family均值，不使用smoothed结果替代raw，也不称信息论/全局最优mIoU上界。

## 原执行链与新增实现

服务器继承原Structured目录的code_manifest每文件哈希校验后复制到新目录，旧snapshot不改；新增12个scripts与1个CPU测试文件从固定Git提交提取。models沿用原冻结执行图：

- S1-0：N1Segmenter late/last4_and_heads实例严格加载S1-0 state，全部冻结。
- S1-3：严格加载S1-3 state；CrossPaths A1B0C0数学执行链与原Continuation S1-3等价，CPU clean/local/full-missing/present-zero逐logit验证，服务器clean端点再验。
- R16：原PairedAdaptation R16构造，严格加载endpoint16000，核job/age/SHA；保留原S1 native安全路径与私有RGB支路，不误用H/F或secondary checkpoint。
- DSM/RGB：原固定专家pair，分别取dsm/rgb；DSM checkpoint及训练史保持legacy，不把S1内部适应后的DSM分支当DSM-only替代品。

原infer按窗口相加FP32 logits后argmax；新增单候选stitch保留同窗口/micro8/顺序/精度，真实smoke要求S1原预测逐像素及原CM exact。只减少不需要的其他score缓存。熵在**覆盖归一化后的平均logits**上softmax，再H/log6，固定[0,.25)/[.25,.5)/[.5,.75)/[.75,1]四箱；不在logit和上计算受coverage温度污染的熵。旧label无熵的S1160 case重放补缓存，逐像素与旧标签一致后接受。

512块置换按相同形状分组，6000余368边缘不padding/crop；全像素置换为纯双射，固定跨模型与realization。nested从原M25内事前PCG64排序截断。统计随机键只是置换/子集/重采样，不是新训练seed。distance EDT使用False halo（像素中心距离，边缘像素distance1）；composition seam使用真实图内邻域（nearest边界），全mask无人工图外seam；mode tie保留raw。ECI净damage内部非正时INCONCLUSIVE，不加epsilon。

5000 paired-mask bootstrap用PCG64(61011)，跨条件同步ID；主区间不当多场景泛化。exact signflip只是次要、假设对称/可交换；不可把n像素当独立n。候选可观测DSM统计9×9 reflect，阈值由clean Val2无GT quartile事前锁定；真实mask/GT class仅机制描述，不能让learnability自动过门槛。

## 自动执行顺序与smoke

一次enqueue：检查两轮旧queue全部COMPLETE、原controller/worker不存活、controller锁已释放；检查本阶段prefix是否已有记录，已有则只报告路径/状态，不重复启动。创建独立zzx目录、immutable plan和source receipts，CPU测试通过后nohup控制器。

1. CPU准备：核所需旧预测/掩码绑定，生成M5/M10、置换索引、无GT分箱并绑定五checkpoint；不用重复旧完整科学审计。code/数据源不明则HOLD。
2. E CPU空间统计并行启动；GPU0真实smoke固定ID1/tile3_11，包含四族S1旧预测/矩阵exact、各DSM条件、R16/S1-3/DSM原clean重现、DSM对RGB独立性、比例子集与真实oracle守恒。
3. GPU1重放同一个S1 pixel与R16 random case，label/CM及S1 entropy bins必须与GPU0 exact。这是工程同卡型一致性，不是新增realization。
4. 控制器独立检查CPU日志及两份真实smoke PASS receipt并写smoke_pass.json，才打开全量派发。此技术验收自动完成；科学去留仍等所有原件上传后的人工评审，任何方法训练不会自动启动。
5. 100批次在两lane动态取就绪任务；20个references完成后missing批次启动，原smoke缓存合法复用。E/CPU可同时进行。每卡一次一个worker；不把某个模型永久绑定物理卡。
6. 所有GPU批次及E完成→CPU D/C统计→汇总A/B/C/D/E→PHASE15_COMPLETE_AWAITING_REVIEW。无自动新训练。

单worker/技术准备/真实smoke最多6h技术超时，D CPU最多24h技术超时；它们是失控检测，不是24h实验总截止。代码、缓存、临时数组、test_scratch、log、PID、CUDA/Torch/Matplotlib缓存全在/home/jovyan/zzx的新目录。24–48h只是预算范围，需用实际case进度校准；超过一天继续，不添加任务凑时长。

任何技术失败停止后继并终止本控制器拥有的其他child、保留partial产物：SMOKE_FAILED_HOLD或TECHNICAL_FAILURE_HOLD，automatic_retry=False。再次enqueue只展示已有记录。停止/断线不等于可自动重启；后续修复须保留版本/原件并明确接管，不隐藏失败。

## 本地验证与证据等级

20项合成CPU检查与13个新Python语法检查通过。包括原S1-3图等价、FP32 logit stitch/entropy、两卡调度与smoke前置、失败停止无retry、nested/bijection/EDT/oracle/seam/matrix known-answer、plan篡改拒绝、完整1540-case模拟汇总及legacy/高oracle均不派发训练。

范围：本地Python3.13/Numpy2.2.6/SciPy1.15.3/Torch2.7.1+cpu；模拟模型/数组不是服务器原权重/DINO/CUDA科学结果。服务器在绑定d18_dino Torch2.2.2+cu121中启动前再跑同包CPU检查并进行真实smoke。发布时尚无本阶段服务器PID或GPU结果；当前已收到登记PID，但无进度/真实smoke结果，不能写成实验已验证。

## 操作入口

用户从固定发布commit提取scripts/enqueue_phase15.py并运行 --root ROOT --commit COMMIT。启动输出PHASE15_REGISTERED及directory/log，保存返回目录。

只读状态：PY -B DIR/code/scripts/status_phase15.py --directory DIR。
完成或HOLD且所有child退出后，前台上传：PY -B DIR/code/scripts/upload_phase15.py --directory DIR --root ROOT。
上传只包含轻量JSON/日志/代码/索引，精确gzip-base64封装保留原字节/SHA；数组与权重留服务器。认证由用户前台进行，不保存凭据。长输出不要求粘贴，给GitHub提交号后回读核验。

本阶段结果齐全后再评审四组配对训练草案；不自动派发router/adapter/DSM-only重训，历史失败gate不变。
