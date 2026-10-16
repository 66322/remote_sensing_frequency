# N5执行协议：同预算随机/内容缺失暴露（2026-10-06）

## Material Passport
- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run preparation
- Verification Status: UNVERIFIED（执行包检查通过不等于服务器CUDA完成）
- Version Label: post_n5_execution_v1
- 用户2026-10-06授权“按上述规划进行实验”。本包落实第一优先N5四组；其余族按[扩展规划](POST_N2_EXPANDED_PORTFOLIO_20261006.md)的证据条件推进，不把21组直接派发。

## 研究问题与对照
Potsdam fit12/Val2=3_11、5_10，native512/stride256，NoBoundary fg5主、Full诊断。沿已验收E1的RGB/H缺口检验混合训练暴露能否超越随机缺失，不能把增强收益写成双向新结构贡献。

N5-0原质量/可用性条件序列；N5-1 U随机块；N5-2 H/L各半；固定N5-3 U半、H/L各四分之一。每组8000新更新、batch16无累积、seed42，GPU0/1/0/1。同N1-2完整模型state SHA28bc6f8ca5e1221392598b0a6f2d160e8c633a6a9cf63827067df3e7b81a144b，重新建立原AdamW与学习率调度；不载入N2后验最佳或原optimizer。不改N1Segmenter结构，构造id=N1-2、外部实验id=N5-*分别保存。

## 精确槽、裁剪与监督
每步样本0—7保留原随机尺度/位置/翻转、质量/可用性增强；样本8—15为共同的新暴露槽，四组都使用native512且origin对齐128格的裁剪，保留原keyed tile与fy/fx/翻转。原fy/fx映射到所有可容纳512的128格起点（尾部不足128区域不进入这些训练槽）。这项共同裁剪调整保证整tile U/H/L mask裁进每槽后都精确25%，避免随机尺度插值破坏面积配对。N5-0也共用该裁剪，保留原条件序列；因此它是同阶段控制，不能直接等同旧N1训练流。

新增槽缺失方向按样本偶数RGB、奇数DSM，每步各4样本。规则按零基step%4：
- N5-1：U/U/U/U；
- N5-2：H/L/H/L；
- N5-3：U/U/H/L。
各新增缺失组每槽65536/262144像素物理缺失，另一侧完整，完整/增强view的fusion有效监督相同；own CE仅用该侧可用像素。每4步每方向U/H/L曝光比例精确匹配本组定义。其他8样本保持原质量/可用性序列且跨组相同。每组记录treatment_counts、每loss有效监督计数和梯度诊断，非零布尔日志不冒称真实条件更新暴露证据。

损失沿N1：clean与aug每view 0.5 fusion CE +0.125 RGB own CE +0.125 DSM own CE。不添加教师/区域/置信网络。缺失处仍由另一侧标签监督，不丢语义label。所有训练标签来自fit12 full_gt。

## whole-tile U/H/L/T与冻结时点
沿原E1：cell128，每格半高×半宽块，4个1/8或3/8偏移候选；边缘同裁切，整tile精确25%且各规则块形状/数量相同。U由原42:postN2mask:tile:y:x SHA确定；H选5×5 DSM局部range最高块均值；L选5×5亮度局部std最低块均值。亮度0.299R+0.587G+0.114B，RGB/DSM归一化继承已绑定Loader。

新增T冻结为同几何中5×5亮度局部std最高块均值，即H的argmax几何使用L的score。并列按原候选顺序第一项。T仅Val2生成，fit12不生成，训练不读取T。本提交完整train/mask/eval/gate冻结后，CPU preparation才生成Val2 T；所有T评价在训练选模之后。整个计划不得依据T结果修改。

14tile mask索引：fit12每tile U/H/L；Val2每tile U/H/L/T，44文件，共享所有四worker。SHA、shape、面积、坐标、输入原索引绑定保存。原诊断mask不改写。本族T不是独立地理检验。

## 选模、评价与固定去留
4000/8000沿原clean、DSM全缺失、RGB全缺失三状态平均NoBoundary fg5选模，平分早选。固定8000保留。普通selected32/fixed22条件沿旧实际执行链；新增content selected/fixed各8条件（两方向×U/H/L/T）×2tile，记录fixed原锚点联合计数、all/mask/other及可用区域。selected=8000时只对同checkpoint/输入复用并重新绑定原件；否则分别推理。

固定主比较N5-3 vsN5-1：
1. T两方向pooled fg5差平均≥+0.5pp，两tile方向平均差各>0；
2. clean、DSM全缺失、RGB全缺失相对N5-0各≥−0.1pp；
3. 原evaluation.missing加全部local去重列表的均值相对N5-1≥−0.1pp；
4. 原primary逐condition×tile最差差相对N5-1≥−0.2pp；
5. fixed8000的T主差>0。
selected通过只形成开发候选；双方向角色另要求每方向pooled及各tile差>0。只一方向收益不能称双向成立。四组全部报告，不能改选N5-2救主gate。若只H/L训练规则好或U追平，关闭当前混合暴露增量，不扫强度、追加seed或追训。

完整summary使用int64 6×6矩阵、逐类计数、每tile pooled重算，joint按truth/fixed_rgb/fixed_dsm/candidate保存。临时派发检查与结果汇总不产生新训练。两tile/seed42属于开发证据，不做像素伪重复显著性。

## 运行、停止与恢复
入口scripts/enqueue_post_n5.py从用户指定固定commit取新文件，复制原诊断已绑定科学依赖快照，形成独立code_manifest。在新建GPU任务前检查N1/N2/诊断最后queue完成状态、原controller/worker退出及锁释放；复核六N2/固定N1-2和五诊断completion/summary绑定、N5问题触发。查records/research_post_n5_*已有登记则只回报，不再启动。

注册锁和post_ab_successor.lock保证同族/跨后继唯一；controller启动再次查来源。CPU检查先于nohup controller，mask CPU准备先于首worker。只用GPU0/1，每卡一个worker，两波0/1→2/3。nvidia-smi只核对实际派发GPU身份/占用，不重复资源审计。仅派发四组，不自动启动N3/R1/N4/R2。

per_job_timeout_hours=12、cpu_stage_timeout_hours=6，拒绝null/非正/非有限值，首Popen前validate。作业超时先terminate、60秒仍存活则kill。其他技术故障停止新派发；已在另卡的worker可完成，原件保留。控制器意外退出写CONTROLLER_INTERRUPTED，worker可能仍活，必须明确诊断/接管；重新运行enqueue只报告既有登记，不自动重训。worker --resume仅供另立恢复方案手动使用，队列不传此参数。

全部快照/临时/缓存/日志/掩码/权重/矩阵在/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_n5_<timestamp>_<pid>。用户终端运行，无SSH，无Test6、independent final、held4读取。预计N5约9—12小时加新增规则评价/CPU准备；本族比N2多8规则评价，实际可能超出该区间，首完整作业回报后更新。12h/job为保护上限，不是预测。

## 原件上传与后继
scripts/status_post_n5.py只读。四组后controller写N5_COMPLETE_AWAITING_REVIEW并退出，打印上传提醒。scripts/upload_post_n5_records.py继承修复后的无损gzip-base64轻量上传，保留执行py/md、全部轻量json/log、mask/server artifact索引；权重/预测/mask本体不进普通Git。原始记录不压缩覆盖；prepare-only可先查看大小，不触发训练。

N5完成后接收分析，E3构成标准化/E5条带迁移和N3边界重新筛选按扩展计划另发独立执行包；本批尚未实现E3/E4/E5/E6完整任务，不把这些诊断写成已派发。此安排执行规划的第一阶段，不把尚无证据的条件族变成可执行占位项。
