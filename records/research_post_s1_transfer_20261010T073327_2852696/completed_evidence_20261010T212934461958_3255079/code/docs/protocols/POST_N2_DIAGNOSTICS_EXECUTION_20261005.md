# Post-N2 E0/E1/E2：已授权的无训练后继执行协议

## 来源、角色与证据边界

- 来源：2026-10-05用户在兼容检查后明确“那开始吧”。本轮落实E0/E1/E2诊断，不从该授权推断N5/N3/N4全部训练。
- 研究阶段：可行性探索；主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复旁支。
- 状态：代码已实现、CPU合成/控制器检查通过；服务器登记和真实CUDA结果尚待用户终端回报。
- 对应规划：[Post-N2证据驱动计划](POST_N2_EVIDENCE_LED_PLAN_20261005.md)。新结果是Potsdam开发验证，不是Vaihingen或正式test。

## 1. 前队列与接续条件

固定服务器根目录`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`。前队列`records/research_post_ab_followup_n2_20261005T085829_3456726`，科学快照86b6a70e5c3482314986fb1259e2fccbd0a5a38b；控制器单独修复9b196a204e6a45cb54244b4deb5437ff44bd074e，原worker与科学快照不动。

最后观测2026-10-05T12:15:02.465274+08:00为RUNNING_N2、控制器3467202存活：N2-0 fixed8000评价、N2-1训练7800/8000，其余四项PENDING。该时刻没有COMPLETE/精度结果。本包不是新的服务器观测。

登记器先只读查询原队列并检查已有诊断目录。重复执行只报告ALREADY_REGISTERED，不另启控制器，不覆盖或重跑部分结果。新目录`records/research_post_n2_diagnostics_<timestamp>_<pid>`保存plan、immutable code、code_manifest、temporary/cache、日志、校准、掩码、预测、计数和完成标记。bootstrap也在zzx/records独立目录。

nohup控制器先等待以下全部满足，再接续：N2_COMPLETE_AWAITING_STAGE_PROTOCOL；六组全部COMPLETE；原控制器与worker退出；原controller.lock释放；获取共享`records/post_ab_successor.lock`后再次确认。前队列技术失败、停止或完成状态不一致则HOLD，绝不重启N2。获取GPU前独立复核六组两套summary/绑定/selected SHA、逐tile整数池化与IoU、joint池化及边际，复算原N2固定screen并与原件逐字段比对。N2科学gate不通过也可以诊断问题，不能挽救该关系配方。

## 2. 共同输入与执行口径

Potsdam fit12原划分只用于阈值校准；Val2固定3_11/5_10。train_held4、Test6、independent final不加载。Loader沿既有d24_data执行链验证D21输入manifest的SHA及文件size/mtime；RGB/255，DSM沿原每tile min–max规范化。报告SHA来源仍为既有输入manifest，不能称本轮重hash全部数据。

各模型复用selected checkpoint，不再根据E0/E1/E2选模。N1-2 SHA固定28bc6f8ca5e1221392598b0a6f2d160e8c633a6a9cf63827067df3e7b81a144b。推理512窗口、stride256、batch8、末batch重复填充但只计真实窗口、FP32 logits均匀拼接、TF32原设置，Torch2.2.2+cu121。模型eval、所有参数requires_grad=False；新optimizer更新严格0。

新code继承原86b6科学manifest并增补独立命名诊断脚本。A0/B1旧代码与N1继承快照有两个旧采样/汇总helper版本差异；新条件不调用这些helper的旧treatment/selection/evaluate。实际模型文件、d24 Loader、d23窗口工具、post_d30 infer必须逐文件匹配来源manifest；严格重建Portfolio/N1/N2对应类并加载完整selected state及signature/selected_step。不以未执行helper字节相同代替执行链核验。

## 3. E0：复用已有逐像素预测

固定模型A0、B1、N1-0、N1-2和全部N2-0—5；原10 primary × Val2，共200条现存case。读取candidate/fixed_rgb/fixed_dsm预测并核SHA和来源绑定，不产生新GPU预测。原几何诊断若纳入时继续排除8像素边缘支持；本批固定primary未含geom诊断。

分别统计all、边界4像素带、内部、小对象、高DSM变化、低RGB对比；Full与NoBoundary同时记录6×6 int64矩阵、逐类计数、四轴joint及四象限分子/分母。边界从有效Full标签的相邻类别差异扩张半径4（9×9最大滤波）；忽略标签不补造。对象按fg5各类4连通，fit12各类对象面积25%分位锁定small-object阈值；对象不是实例标注，只是语义连通块诊断。H/L像素阈值见下节，不把标签用于掩码选择。

固定问题筛选模型N1-2、clean、Full诊断范围：两tile都满足边界/内部锚点正确并集分母分别≥100，两个单侧正确象限在边界+内部总量各≥100，且边界伤害率−内部伤害率≥1pp，才标N3_problem_trigger。Full筛选不替换NoBoundary主指标；触发只证明值得检验区域问题，不证明区域归属是原因。

## 4. E1：内容相关缺失位置

固定A0/B1，两方向RGB受损或DSM受损、U/H/L三规则、Val2，共24次新tile推理。另一侧全可用，缺失像素置零且报告正确掩码。所有模型/方向复用同一whole-tile掩码文件及SHA，窗口重叠共享位置。

输入分数锁定5×5：RGB亮度0.299R+0.587G+0.114B的局部标准差；DSM局部最大−最小。E0高DSM阈值fit12分数采样stride16的75%分位，低RGB为25%分位，均按原tile规范化；E1位置排序不依赖标签或模型错误。

每128×128网格放一64×64块；每格候选起点为高度/宽度的1/8或3/8，共4位置。U取seed42+tile+cell坐标SHA确定的均匀索引，H取候选块平均DSM分数最高，L取RGB对比分数最低；平分取第一。边缘格保留同一裁切形状、块高/宽为格高/宽的一半。Potsdam6000边缘格112，块56；精确总面积25%，每格一块且分离，U/H/L块形状多重集及数量一致。偶数尺寸/边缘分离契约不满足则停止，不能改面积凑数。

这些控制匹配网格、面积、形状、数量和最小间隔约束，但不强行匹配全部块间距离或被遮类别构成。输出受损/未损伤/全范围矩阵、mask区域类别计数、own专家四象限，报告位置和类别构成混杂，不将合成遮挡称真实MNAR或纯因果效应。

固定门槛：同一H或L×方向上，A0和B1的NoBoundary pooled fg5均比U低≥0.5pp，且每模型两tile均同号，标N5_problem_trigger。按原始矩阵池化，不平均tile指标替代pooled。所有四种筛选组合报告，不增强度/seed追门槛。T高RGB纹理预留规则不生成、不推理；须N5完整训练配置、掩码和判定冻结后另立执行步骤。

## 5. E2：物理损伤与标记分离

固定N1-2、N2-0、N2-3；同E1的U位置、两个受损方向、两个tile。每个方向四case：clean intact/all-valid；false_positive intact但报告该侧25%缺失；known_missing该侧物理置零且正确报告；false_negative完全相同物理置零但报告all-valid。原clean预测每模型两tile复用并核SHA/计数；概念case共48单元，clean跨方向复用6条现存预测，新增36次tile推理。

模型按报告掩码在forward内部再次清零，故false_positive和known_missing可能得到同一内部输入；这是该系统误报的工作方式，不把相同输出称新机制证据。记录送入infer之前物理tensor与报告mask各自SHA，漏报与已知缺失的物理tensor必须相同。E2 own logits是适应分支诊断，不能误作原固定锚点分区。

分别报告known−false_negative成本和clean−false_positive成本、逐tile/类/区域/原始joint。漏报成本pooled≥0.5pp且两tile均正标problem_signal；只作标记依赖诊断，不自动训练新置信网络、不替换N2科学gate。

## 6. 排队、资源、停止与验收

登记前16项CPU契约/控制器集成测试，180秒上限，CUDA不可见，临时文件在新目录temporary。检查失败保存HOLD_CPU_CHECKS，无自动重复登记。等待阶段不读取大tile、不初始化GPU。N2释放后CPU验收→fit12校准/掩码→E0（4小时上限）→E1→E2。只用GPU0/1，各卡一worker：E1_A0卡0/E1_B1卡1；E2_N1-2卡0/E2_N2-0卡1，之后E2_N2-3卡0。

每worker评价上限8小时，有限正数配置，null/非有限值拒绝。技术失败/超时停止新增派发，另一卡已运行任务收尾；控制器中断保留detached worker，先查存活与日志再明确修复，不自动重跑。卡上其他活进程仅等待，不杀进程、不重做资源审计。脚本/CPU通过不保证真实CUDA模型成功，服务器首项完成回报后验收运行兼容性。

E1/E2新增共60次tile推理；E0是CPU已有预测分析。当前无相同推理实测时长，不承诺具体结束时刻。状态显示最后观测、各worker phase/window进度；首轮实际耗时后再估算。任何gate都只生成诊断报告，最终DIAGNOSTICS_COMPLETE_AWAITING_REVIEW；N5/N3/N4仍需诊断分析与各族完整实现、匹配控制后另登记。无追加种子、无失败A/B/C/N1/N2救配方、无F/N6派发。

完成标记绑定plan/code_manifest、模型selected/source completion、maskmanifest、summary SHA。汇总复核条件/tile全集、各scope/region int64矩阵/逐类TP/FP/FN/support/valid和fg5、joint稀疏编码与三分支边际、空间位置分区相加，复核E0逐记录SHA。保留预测.npy/掩码.npz服务器原件及SHA索引。

## 7. 上传与交接

上传入口scripts/upload_post_n2_diagnostics_records.py仅由用户交互终端调用；可先--prepare-only查看体积。保存全部顶层provenance、CPU/worker/nohup日志、E0和新任务JSON计数、校准/掩码manifest、screen、服务器预测/掩码SHA索引。≥4096字节记录用既有gzip-base64-exact-v1无损编码，保留原始字节SHA与压缩载荷SHA，单文件80MiB/总512MiB门限；原.npy/.npz与权重不入普通Git。

在实验目录下独立detached Git worktree，显式添加evidence文件，向同一分支非force推送。需认证则由用户输入，不存凭据。N2原始summary仍用其既有上传器单独上传；本诊断上传的n2_source_audit不替代完整N2原件。收到上传后回读manifest/原计数、分析证据边界并更新共享入口和交接。服务器记录未到GitHub前不称已接收或已验收全部结果。

查询方式（DIAG_DIR取登记输出实际目录）：

```bash
"$EXP_PY" -B "$DIAG_DIR/code/scripts/status_post_n2_diagnostics.py" --directory "$DIAG_DIR"
```

完成后上传：

```bash
"$EXP_PY" -u -B "$DIAG_DIR/code/scripts/upload_post_n2_diagnostics_records.py" --root "$ROOT" --directory "$DIAG_DIR"
```
