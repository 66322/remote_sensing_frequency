# D23-B完整入口实现与工程验收（2026-10-01）

研究仍处可行性探索，优先频率＋语义可靠性，C1为旁支；不改原8组、4000步、6固定比较、14条件、NoBoundary fg5及收益/风险门槛。GPU工程记录不能替代正式精度证据。

## 80GB H100后的实现调整

用户询问为何累积：旧8×2是保持专家数值口径的工程选择，非显存所限。本轮新实现冻结专家每次8样本前向，拼接detach证据后gate每视图16样本计算，两视图损失一次合并、一次backward/optimizer.step；不再执行gate梯度累积。有效batch仍16、各8组同初始化和样本流。新路径需要服务器资源/反传验收，旧0.308秒/步是两遍低缓存路径，不能引用为新路径速度。

## 执行链和状态

scripts/run_rebuild_v1_d23.py → d23_engine.py／d23_lifecycle.py → model/rebuild_v1_d23_gate.py。GPU UUID准入、D21权重/源码/PyTorch/DINO/输入文件SHA和保存预测复现检查保留。代码快照从同一提交提取，gate显式按快照路径导入。

- keyed sample索引与组别/微批无关；scale0.5–2、双向flip0.5与D18九条件概率固定。退化在CPU按样本一次生成；评价先对整图退化再裁窗口。前11条件保留旧D21算子及噪声种子；新增std020用预定SHA256键/NumPy PCG64、shift16右移replicate、整图行1/8条带。
- TCAP formal统计固定256训练裁剪（clean＋treated），轮转覆盖12个gate-fit tile，E通道double在线population均值/方差，冻结后写入checkpoint buffer；smoke的单训练tile统计明确ADMISSION_ONLY，不可替代正式统计。
- 正式训练固定AdamW3e-4/wd.01、100warmup(.1初比率)、poly4000，最后4000步、仅gate可训练，保存/重载与签名检查；有显式resume，不用Val2选checkpoint。磁盘缓存只取当前阶段允许tile，按源SHA和npy SHA绑定、按需mmap，避免逐样本重复整张TIFF加载。
- 整图沿用D21 uniform窗口logit累加（512/256），所有组专家均固定batch8、尾批用最后窗口填充后丢弃填充输出。尾批处理比旧D21有所明确化，因此6固定比较全部在新口径重算，不声称逐像素等同旧D21预测。拼接后每个已知缺失像素复制同次完整R0 logits；aux条件R0预测SHA应与clean相同。
- 保存预测与SHA、每tile Full/NoBoundary int64 6×6矩阵、support/TP/FP/FN、harm/rescue（全区/available/missing/逐类），pool从计数重算。g直方图为含重叠的窗口像素诊断。gate18145参数、仅卷积296222720 MAC/512crop，不包含专家和证据计算。
- summarize_rebuild_v1_d23.py只接收8组完整记录，核对原计数pool、绑定与固定基线跨组预测SHA，按原门槛逐项输出通过/未过/NA；不自动续训、加种子或改阈值。

代码已实现、CPU合成检查通过，不等于服务器完整训练/整图验收已通过。checkpoint resume和完整Val2流程尚需服务器验证；部分评价已存在时保留并拒绝覆盖，不提供自动评价续跑。正式运行拒绝缺失或不匹配的FULL_ENGINE_RUNTIME_ADMITTED预算锁；目前该锁未生成，正式队列未启动。

## 下一服务器任务

顺序执行GPU0 smoke、GPU1 profile，每个任务外层30分钟超时。smoke在Train tile2_12做8组各2次更新、768×768含尾批窗口、14条件与6固定比較；profile在同训练tile做TSF12次更新、整张影像clean/aux_zero/1/8局部缺失评价。两个任务都不读取Val2或Test6，不生成正式TCAP统计；只保存明确标记的admission权重。

目标：核对新专家8/gate16一次反传、GPU1、重载、整图计数/回退与资源。保留24GiB host RSS、32/40GiB allocated/reserved GPU、32GiB目录文件预算保护（工程上限，不代表80GB卡容量）。卡忙、数值非有限、SHA/回退/计数不符、超时/超限即停并留failure文件。不重复旧crop探针。所有代码/JSON/预测/权重/日志写项目records/research_d23_b_engine_admission_<timestamp>_<pid>，不超出zzx。

预计数分钟级，实际用时需回传；未用旧crop吞吐推算全队列。单卡验收后仍需12tile缓存/TCAP I/O与双卡并行预算核对，再生成正式锁及8组队列。用户已授权GPU0/1，两卡H100 80GB、内存磁盘充足为用户声明，实际型号/总显存由新preflight记录。
