---
origin_skill: experiment-agent
mode: plan
date: 2026-10-01
verification_status: UNVERIFIED
version: code_plan_v1
---

# D24：今晚四个角度、15组开发筛选

记录2026-10-01 22:37:26（Asia/Shanghai）。**分组与科学比较协议已定稿；执行代码尚未完成，未启动。** 用户要求今晚多跑几组、借鉴不同角度论文；具体方法是本轮助手建议，不是最终方向采纳或已验证贡献。计划基于[完整D23结果](../experiments/D23_EIGHT_ARM_RESULTS_20261001.md)，基准提交746708281ecb4d291bb582efcef8f5890ea5b774。

[机器计划](../../records/research_d24_overnight_plan_20261001/plan.json)和[15组清单](../../records/research_d24_overnight_plan_20261001/jobs.csv)为本轮实现合同。旧[四组草案](D24_PAIRED_TASK_ADAPTATION_DRAFT_20261001.md)保留历史；本协议替代其下一步地位。定稿不等于代码验收，更不等于服务器运行。

## 问题与为何扩大实验角度

主线仍是光学可用时，DSM质量变化下的有益融合、负迁移控制和缺失推理。D23只能关闭当前冻结专家＋S/F门控＋硬效用损失组合：所有学习gate综合低于M0_safe，去掉效用项的CE更好，现有S/F增量不足。它没有检验任务表示能否更新、类别原型、知识进入光学分支或新结构下增强因素的贡献。

这轮不重新训练旧TSF，也不拼接全部文献模块。A检验表示/目标，B检验类别结构，C检验可用模态的知识迁移，D分离普通增强。C明确是原问题下“缺失时怎样保留知识”的能力子问题；它的光学单模态结果不能冒充双模态融合收益，也不自动取代主线。部分解冻为强基线，C1恢复仍旁支。频率暂不纳入本轮；这撤回的是旧实现贡献承诺，不宣判整个频率问题无效。

## 分组、主要对照与论文依据

| 路线 | 组与因子 | 主要比较 | 要解决的未知 |
|---|---|---|---|
| A，4组 | A0骨干冻结＋CE；A1骨干冻结＋Pair；A2最后4块更新＋CE；A3最后4块更新＋Pair | A1−A0、A3−A2；A2−A0及目标×更新交互 | 目标是否有独立增量？还是收益全部来自表示更新？ |
| B，4组 | B0通用原型槽＋像素CE；B1类别原型＋像素CE；B2通用槽＋类别平衡CE；B3类别原型＋类别平衡CE | B1−B0、B3−B2检验语义；B2−B0、B3−B1检验类别权重 | 类别对应是否比普通记忆/容量有用？能否保留小类纠错？ |
| C，4组 | C0光学CE；C1全域KD；C2纠错区域KD；C3同数量、空间打乱区域KD | C2−C0、C2−C1、C2−C3 | DSM知识能否进入光学分支？区域对应是否真正必要？ |
| D，新增3组 | D0无Q/D；D1仅质量Q；D2仅缺失D；D3= A2，Q＋D共享 | D1−D0、D2−D0、A2−D1、A2−D2及Q×D交互 | 新结构下普通增强能解决多少，机制是否只是增强效果？ |

合计16个逻辑单元、**15次独立训练、每组4000步、共60000次优化更新**。D3和A2是完全相同模型/数据流/预算/选模，故共享一次运行；B0结构不同，不能冒充A2而删掉容量对照。

- A借鉴[SimMLM，ICCV2025](https://openaccess.thecvf.com/content/ICCV2025/html/Li_SimMLM_A_Simple_Framework_for_Multi-modal_Learning_with_Missing_Modality_ICCV_2025_paper.html)的任务损失排序思想。原文跨医学/分类任务；本轮是固定光学参照的clean排序，不是原MoFe复现，不把坏DSM“更多模态必然更好”作为前提。
- B借鉴[SGMA，TGRS2026](https://arxiv.org/html/2603.02505v1)的类别语义原型，以及[STARS，2026预印本](https://arxiv.org/html/2601.17342v1)的类别平衡学习。我们的类别CE平衡不是SGMA模态采样算法；不依赖尚未获取的SGMA完整代码，不直接比较异划分论文表分数。
- C借鉴[STARS](https://arxiv.org/html/2601.17342v1)的缺失模态知识迁移问题，以及[PNDC，TMI2025](https://pubmed.ncbi.nlm.nih.gov/40031068/)的正负影响区域校准思想。本轮为固定教师logit KD；不是STARS共享/特有翻译复现，也不是PNDC完整方法复现。PNDC仅摘要和局部官方代码核对，证据边界保持。
- D借鉴[传感器失效分割基准，CVPR2025 Workshop](https://arxiv.org/abs/2503.18445)区分缺失与噪声能力的评价思想；普通Q/D是强基线，不能因新命名变成创新。更多来源边界见[近期文献映射](../literature/RECENT_MULTIMODAL_SEGMENTATION_20261001.md)。

## 共同数据、初始化与更新范围

Potsdam RGB＋既有逐tile归一化DSM；使用D23同一fit12，具体tile名单在机器计划。Val2为3_11、5_10。四个Train16保留tile本轮不读；初始化checkpoint曾用历史训练数据，不能把这四个tile称为独立验证。Test6及独立final均禁读/不加载。

均seed42、512裁剪、tile均匀采样再均匀裁剪，共享按step/sample索引的样本和增强随机流。A/B/D从已绑定M0 checkpoint继续，C从R0继续；优化器重置。M0 SHA为23b2939ea50867c96c0a17626fd4a85a27100ebd8296b2fc96440ed8bc3d34de，R0 SHA为29aa15f4cd149012996ddeadd7a5b40f593f99854318acd1d0d0acb286ed5975。不是从D23学习gate接着训练。

共同融合载体为现有M0的stride4 RGB＋DSM特征相加/解码，加入**显式可用性mask**：DSM detail输出在相加前乘mask；不能通过DSM数值恰好为零推断缺失。整幅缺失时等于同一更新模型自己的光学路径；这条路径不保证等于旧固定R0。局部mask按同一空间规则映射至stride4，记录边缘覆盖约定。

A0/A1只冻结DINO，RGB投影、DSM detail和decoder可训练；它们不是D23全部专家冻结。A2/A3/B/C/D再更新DINO最后4个block，早期block和最终encoder norm冻结。实际源码可复用post-D21的last_four_trainable/AContinuation思想；不能复用D23 detach链后只切requires_grad。变化原因是用户要求跨角度筛选，且表示更新须包含已有部分解冻强基线。旧草案的“冻住全部专家、另加gate”不再是本轮载体。

两视图为clean和同裁剪的augmented，标签对齐；普通任务损失为两视图CE的平均。默认CE为所有有效训练像素的六类CE，fg5只是评价主指标。A/B采用QD，C采用Q，D按因子；路线间不得因增强不同就声称机制增量。

4000步、有效/物理batch16、**不累积梯度**；BF16训练，损失/优化器FP32；AdamW head_lr=2e-4，encoder_last4_lr=2e-5，weight_decay=.01，betas=.9/.999；warmup100步从0.1倍率开始，之后线性衰减至4000步为零。全组同精度策略，历史FP32训练不是唯一匹配对照。保存每500步checkpoint，2000/4000步仅clean Val2选模，主指标pooled NoBoundary fg5；平分选更早步。选择后只做一次完整14条件评价。4000是筛选预算，不证明已收敛，也不将超时标成科学失败。

## 四条路线的具体机制合同

**A：clean光学参照Pair。**每个clean crop计算模型全模态平均CE及固定R0平均CE，增加
`0.1 * mean(max(0, CE_full_clean - stopgrad(CE_fixed_R0_clean)))`。
目标只作用clean；固定参照避免通过恶化少模态分支改善排序。A0/A2也计算同一教师诊断以匹配前向开销，但不加入Pair。不得把此局部平均CE排序解释成mIoU单调保证。两更新范围各自CE是必须保留的主要对照。

**B：同容量原型记忆。**两模态各6槽、每槽128维，以clean训练特征、EMA=.99更新并stop-gradient；类别槽用训练label归类，通用槽用确定性空间hash均匀分6桶。两者使用同shape投影：query/key拼接256→32，value256→128，6槽注意力，零初始化128→128输出投影，作为decoder前残差。DSM与记忆残差同乘可用mask；缺失不读取DSM派生残差。全部bank同一全局训练特征均值初始化；无支持的槽不更新。每组参数数目/初值完全一致，差异只在槽分配与CE reduction。EMA只用fit12，在validation/inference冻结。类别平衡CE为有效batch内每个出现类别的CE均值再等权平均，不改变crop采样次数。该实现是待开发建议，不预先宣称“可靠性”估计已校准。

**C：固定教师知识迁移。**四组同一光学学生、同更新范围、同Q与CE；固定M0_safe教师看到对应两视图的光学＋DSM，固定R0提供比较。教师不训练，学生推理不加载DSM/教师/label。KD为温度2的`T² KL(p_teacher || p_student)`，权重.1。C1全有效区域；C2选择“教师预测正确且固定R0错误”的训练像素；C3对同一mask的有效像素序列作固定循环空间位移，严格保留选中数、保留原位置教师目标。KD在所选像素归一化、两视图平均；空区域为零并记录，不回退全域。C0也计算教师/R0诊断，但KD权重为零。区域标签只用于训练，不能进推理。C2若只胜C0、不胜C1/C3，不成立区域选择贡献。

**D：Q×D。**Q在clean、rgb_down2/down4/blur5/local_down4_q1、aux_down4/noise_std010七种条件中等概率选一种，复用D23确切退化算子。D在all_present/aux_zero/aux_local_zero_q1按.5/.25/.25选择。QD先Q后D，随机数按样本键独立预定；关闭某因子仍沿同一crop/flip流。D0第二视图为clean；D1仅Q，D2仅D，D3共享A2。不是重跑历史R03/R04/R05：载体、fit12继续训练、短预算及显式mask不同；历史结果只作参照。

## 评价、保留原件与去留

Potsdam原分辨率512窗/stride256、uniform FP32 logit stitch；评价FP32及已有TF32政策。全部模型同14个D23条件。主综合为clean、四RGB退化均值、两DSM退化均值的三项平均；Full/6类为诊断。保存int64 6×6矩阵、每类原计数、逐tile、条件/可用区域、checkpoint/配置/源码/输入SHA；不得只保存四舍五入分数。

harm/rescue同时保留两种参照：固定R0用于组间比较；模型自身DSM缺失路径用于判断辅助模态的净贡献。表示更新可能改变光学能力，固定R0纠错不全是DSM特异效应。C按相对C0的光学clean fg5和RGB退化表现判断；其对DSM退化不敏感是“不用DSM”的结构事实，不是学到故障检测。

本轮**实用筛选门槛，不是统计显著性或确认性贡献**：
- 融合机制相对对应CE/容量主对照综合至少+.2pp，clean不低于−.1pp，逐tile/family不低于−.3pp；有用融合还须报告相对M0_safe，未胜过强基线不能声称整体融合优越。
- 主张减负迁移时：固定R0口径、九个可用条件，harm至少降低10%，rescue至少保留90%；必须同时报告自身光学参照结果。主张精度提升与主张减害分开，不能强迫所有目标通过同一代理门槛。
- A检验Pair−CE；A2单独上涨只支持更新强基线。B类别原型须胜同capacity的B0/B2，不能只比较A2；B3还需相对B1的类别平衡增量至少+.1pp才支持组合额外效果。
- C2相对C0 clean至少+.2pp，相对C1和C3均至少+.1pp，RGB family不得下降超过.1pp，逐tile下降不超过.3pp；空区域/原计数一并报告。
- D只回答增强效应，不把常规增强的正结果当作新论文机制。
- 单seed、两个反复使用的开发tile，15次筛选具有选择偏差；不把像素或条件当独立重复，不生成确认性p值。最多保留两条高信息量假设另立多种子/未见条件/独立来源计划。失败不自动扫权重、延长或加种子；预算未收敛与技术失败单独标注。

## 夜间队列与启动边界

GPU0/1各一任务，独立进程，控制器nohup，stdin=/dev/null。CPU tile cache、pin_memory、persistent_workers、每组8 workers和prefetch4提高供给；不重复资源/预算审计，不因短时利用率低就变更科学预算。中间log必须区分缓存、训练、选模、全图评价，不能只重复xFormers旧警告。

优先次序按jobs.csv：
- GPU0：A0 → A3 → C0 → D2 → C3 → D1 → B1 → B3。
- GPU1：A2 → A1 → C2 → D0 → C1 → B0 → B2。

先覆盖A四组、C基线/候选、D基线/缺失对照，再补区域否证与语义四组。B靠后因新增原型结构最多，不能拖住更快可实现的A/C/D；若分阶段发布，尚未实现的job标IMPLEMENTATION_PENDING，不把它们作为失败或假称整队列可运行。

所有code、logs、PID、checkpoint、cache、轻量归档及临时文件在本轮独立`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d24_overnight_<timestamp>_<pid>`；不覆盖D23，禁止/tmp。每job最长6小时，超时保存状态并标技术未完成，只处置自己启动且绑定目录的进程；其他job继续，无自动重跑。不限制整队列只能熬到某个钟点，也不保证15组明早全部完成。新图耗时尚未知；只用首批正常任务进度更新ETA，无另行测量任务。

启动前只需新行为必要检查：部分更新范围梯度确实非零/冻结层无梯度，教师无梯度，B同capacity/推理无label，C打乱mask数精确一致，mask缺失返回自身光学，checkpoint/RNG可恢复、队列不重复完成job。完成实现及这些检查后发布固定执行提交与nohup命令，直接接续已知环境。**目前没有新的可运行命令，也没有声称实验已经开始。**
